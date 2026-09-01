# -*- coding: utf-8 -*-
"""
K-CheckupDx-Pub v1.0 파일럿 LLM 평가 러너
대상 모델: Claude Fable 5 (claude-fable-5), GPT-5.6 Sol (gpt-5.6-sol)

사용법:
  export ANTHROPIC_API_KEY=...   # Claude용
  export OPENAI_API_KEY=...      # GPT용
  python run_pilot.py --provider anthropic --model claude-fable-5 --mode zeroshot
  python run_pilot.py --provider openai    --model gpt-5.6-sol    --mode zeroshot
  # 규칙 제공(rule-grounded) 조건:
  python run_pilot.py --provider anthropic --model claude-fable-5 --mode grounded

출력: results_{model}_{mode}.jsonl (케이스별 원시 응답 + 파싱된 판정)
"""
__VERSION__ = "1.5"  # 정본 버전 — CLAUDE.md가 실행 전 검증함

import argparse, json, os, re, sys, time
from pathlib import Path

# ---------------- 프롬프트 ----------------
SYSTEM_ZEROSHOT = (
    "당신은 한국 국가건강검진(일반건강검진) 결과 판정 시스템입니다. "
    "제시된 검사항목, 성별, 결과값을 보고 보건복지부 「건강검진 실시기준」의 판정기준에 따라 "
    "판정을 내리십시오. 반드시 제시된 선택지 중 하나만 고르고, "
    '다른 설명 없이 JSON 형식 {"판정": "<선택지>"} 로만 응답하십시오.'
)

# 고시 별표4 판정기준표 (rule-grounded 조건에서 시스템 프롬프트에 삽입)
GOSI_RULES = """[판정기준표 — 건강검진 실시기준 별표4]
- 수축기혈압(mmHg): 정상A <120 / 정상B 120-139 / 질환의심 >=140
- 이완기혈압(mmHg): 정상A <80 / 정상B 80-89 / 질환의심 >=90
- 혈압(복합): 정상A는 수축기 120미만 '이며' 이완기 80미만. 정상B는 수축기 120-139 '또는' 이완기 80-89. 질환의심은 수축기 140이상 '또는' 이완기 90이상. (상위 등급 조건 우선)
- 공복혈당(mg/dL): 정상A <100 / 정상B 100-125 / 질환의심 >=126
- 총콜레스테롤(mg/dL): 정상A <200 / 정상B 200-239 / 질환의심 >=240
- HDL콜레스테롤(mg/dL): 정상A >=60 / 정상B 40-59 / 질환의심 <40
- 트리글리세라이드(mg/dL): 정상A <150 / 정상B 150-199 / 질환의심 >=200
- LDL콜레스테롤(mg/dL): 정상A <130 / 정상B 130-159 / 질환의심 >=160
- AST(U/L): 정상A <=40 / 정상B 41-50 / 질환의심 >=51
- ALT(U/L): 정상A <=35 / 정상B 36-45 / 질환의심 >=46
- 감마GTP(U/L): 남 정상A 11-63 / 정상B 64-77 / 질환의심 >=78; 여 정상A 8-35 / 정상B 36-45 / 질환의심 >=46
- 혈색소(g/dL): 남 정상A 13.0-16.5 / 정상B 12.0-12.9 / 질환의심 <12.0; 여 정상A 12.0-15.5 / 정상B 10.0-11.9 / 질환의심 <10.0
- 혈청크레아티닌(mg/dL): 정상 <=1.5 / 질환의심 >1.5
- eGFR(mL/min/1.73m2): 정상 >=60 / 질환의심 <60
- BMI(kg/m2): 정상A 18.5-24.9 / 정상B 25-29.9 / 질환의심 <18.5 또는 >=30
- 허리둘레(cm): 남 정상 <90, 복부비만 >=90; 여 정상 <85, 복부비만 >=85
- 골밀도 T-score: 정상A >=-1.0 / 정상B -1.0초과~-2.5초과 구간(-1.1 ~ -2.4) / 질환의심 <=-2.5
- 요단백: 정상A 음성(-) / 정상B 약양성(±) / 질환의심 양성(+1) 이상
- HbA1c(%): 정상A <5.7 / 정상B 5.7-6.4 / 질환의심 >=6.5 (대한당뇨병학회)
- 요산 남(mg/dL): 정상 <=7.0 / 질환의심 >7.0 (고요산혈증)
"""

SYSTEM_GROUNDED = SYSTEM_ZEROSHOT + "\n\n다음 판정기준표를 정확히 적용하십시오.\n" + GOSI_RULES

# criteria-named: 기준표 내용 없이 '어느 기준을 쓸지'만 명시 (BMI 3조건 실험용)
SYSTEM_NAMED = SYSTEM_ZEROSHOT + "\n\n판정은 보건복지부 「건강검진 실시기준」 별표4의 판정기준에 따르십시오. (기준표 원문은 제공되지 않습니다. 해당 고시의 기준을 기억에 근거해 적용하십시오.)"

def user_prompt(case):
    sex = {"M": "남성", "F": "여성", "공통": "해당없음(공통)"}[case["sex"]]
    return (
        f"검사항목: {case['item']}\n"
        f"단위: {case['unit']}\n"
        f"성별: {sex}\n"
        f"결과값: {case['value']}\n"
        f"선택지: {', '.join(case['options'])}\n"
        '위 결과의 판정을 JSON으로만 답하십시오. 형식: {"판정": "<선택지 중 하나>"}'
    )

# ---------------- API 호출 ----------------
def call_anthropic(model, system, user, max_retries=5):
    import anthropic
    client = anthropic.Anthropic()  # ANTHROPIC_API_KEY 환경변수 사용
    for i in range(max_retries):
        try:
            # claude-fable-5: temperature 미지원(400 거부), adaptive thinking으로
            # 응답이 [thinking, text] 구조일 수 있음 → text 블록 순회 추출
            msg = client.messages.create(
                model=model, max_tokens=2000,
                system=system, messages=[{"role": "user", "content": user}])
            for block in msg.content:
                if getattr(block, "type", None) == "text":
                    return block.text
            # thinking 블록만 오고 text 없음 → 조용한 결손 대신 재시도 유도 (Task D §9)
            raise RuntimeError("no text block in response (thinking-only) — retrying")
        except Exception as e:
            wait = 2 ** i
            print(f"  [retry {i+1}] {e} — {wait}s 대기", file=sys.stderr)
            time.sleep(wait)
    return None

def call_openai(model, system, user, reasoning_effort="medium", max_retries=5):
    from openai import OpenAI
    client = OpenAI()  # OPENAI_API_KEY 환경변수 사용
    for i in range(max_retries):
        try:
            # GPT-5.6 계열은 Responses API 권장 (gpt-5.6 alias는 Sol로 라우팅)
            resp = client.responses.create(
                model=model,
                reasoning={"effort": reasoning_effort},
                input=[{"role": "system", "content": system},
                       {"role": "user", "content": user}],
                max_output_tokens=1000)
            return resp.output_text
        except Exception as e:
            # Responses API 미지원 환경이면 chat.completions로 폴백
            try:
                resp = client.chat.completions.create(
                    model=model, temperature=0, max_tokens=200,
                    messages=[{"role": "system", "content": system},
                              {"role": "user", "content": user}])
                return resp.choices[0].message.content
            except Exception as e2:
                wait = 2 ** i
                print(f"  [retry {i+1}] {e2} — {wait}s 대기", file=sys.stderr)
                time.sleep(wait)
    return None



# ---------------- Mock 프로바이더: 고시 규칙엔진 ----------------
# 목적: (1) API 키 없이 파이프라인 전체(e2e) 테스트
#       (2) 골든라벨 이중검증 — 규칙엔진과 라벨 불일치 시 데이터 버그
def rule_engine(case):
    item, sex = case["item"], case["sex"]
    v = case["value"]
    def tier3(x, b1, b2):  # b1=B시작(포함), b2=의심시작(포함), high 방향
        return "정상A" if x < b1 else ("정상B" if x < b2 else "질환의심")
    if item == "요단백":
        return {"음성(-)":"정상A","약양성(±)":"정상B"}.get(v, "질환의심")
    if item == "혈압(복합)":
        s, d = [float(x) for x in v.split("/")]
        if s >= 140 or d >= 90: return "질환의심"
        if (120 <= s <= 139) or (80 <= d <= 89): return "정상B"
        return "정상A"
    x = float(v)
    if item == "수축기혈압":   return tier3(x, 120, 140)
    if item == "이완기혈압":   return tier3(x, 80, 90)
    if item == "공복혈당":     return tier3(x, 100, 126)
    if item == "총콜레스테롤": return tier3(x, 200, 240)
    if item == "트리글리세라이드": return tier3(x, 150, 200)
    if item == "LDL콜레스테롤": return tier3(x, 130, 160)
    if item == "AST":          return tier3(x, 41, 51)
    if item == "ALT":          return tier3(x, 36, 46)
    if item == "감마GTP":      return tier3(x, 64, 78) if sex == "M" else tier3(x, 36, 46)
    if item == "HbA1c":        return tier3(x, 5.7, 6.5)
    if item == "HDL콜레스테롤":
        return "정상A" if x >= 60 else ("정상B" if x >= 40 else "질환의심")
    if item == "혈색소":
        a, b = (13.0, 12.0) if sex == "M" else (12.0, 10.0)
        return "정상A" if x >= a else ("정상B" if x >= b else "질환의심")
    if item == "골밀도 T-score":
        return "정상A" if x >= -1.0 else ("정상B" if x > -2.5 else "질환의심")
    if item == "BMI":
        if x < 18.5 or x >= 30: return "질환의심"
        return "정상A" if x < 25 else "정상B"
    if item == "혈청크레아티닌": return "정상" if x <= 1.5 else "질환의심"
    if item == "eGFR":          return "정상" if x >= 60 else "질환의심"
    if item == "요산(남)":      return "정상" if x <= 7.0 else "질환의심"
    if item == "허리둘레":
        t = 90 if sex == "M" else 85
        return "정상" if x < t else "복부비만"
    return None

def call_mock(case):
    import json as _j
    return _j.dumps({"판정": rule_engine(case)}, ensure_ascii=False)

# ---------------- 응답 파싱 ----------------
def parse_judgment(text, options):
    if text is None:
        return None, "no_response"
    m = re.search(r'\{[^{}]*"판정"\s*:\s*"([^"]+)"[^{}]*\}', text)
    if m and m.group(1) in options:
        return m.group(1), "json"
    # JSON 실패 시 선택지 문자열 매칭 (긴 것 우선: '정상A'가 '정상'보다 먼저)
    for opt in sorted(options, key=len, reverse=True):
        if opt in text:
            return opt, "substring"
    return None, "unparsed"

# ---------------- 메인 ----------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--version", action="version", version=f"run_pilot {__VERSION__}")
    ap.add_argument("--provider", choices=["anthropic", "openai", "mock"], required=True)
    ap.add_argument("--model", required=True)
    ap.add_argument("--mode", choices=["zeroshot", "named", "grounded"], default="zeroshot")
    ap.add_argument("--input", default="pubset_v1.0.jsonl")
    ap.add_argument("--reasoning-effort", default="medium", help="OpenAI GPT-5.6 전용")
    ap.add_argument("--sleep", type=float, default=0.3)
    # mock은 대기 불필요
    ap.add_argument("--limit", type=int, default=0, help="테스트용 케이스 수 제한(0=전체)")
    ap.add_argument("--runs", type=int, default=1, help="반복 시행 횟수 (결과: results_..._runK.jsonl)")
    args = ap.parse_args()

    cases = [json.loads(l) for l in open(args.input, encoding="utf-8")]
    if args.limit:
        cases = cases[: args.limit]
    system = {"grounded": SYSTEM_GROUNDED, "named": SYSTEM_NAMED, "zeroshot": SYSTEM_ZEROSHOT}[args.mode]
    tag = Path(args.input).stem.replace("pubset_", "")
    for run_k in range(1, args.runs + 1):
        suffix = f"_run{run_k}" if args.runs > 1 else ""
        out_path = f"results_{args.model.replace('/', '_')}_{args.mode}_{tag}{suffix}.jsonl"
        _run_once(cases, system, out_path, args)

def _run_once(cases, system, out_path, args):

    done = set()
    if Path(out_path).exists():  # 재실행 시 이어하기
        done = {json.loads(l)["case_id"] for l in open(out_path, encoding="utf-8")}
        print(f"기존 결과 {len(done)}건 발견 — 이어서 실행")

    with open(out_path, "a", encoding="utf-8") as f:
        for i, c in enumerate(cases):
            if c["case_id"] in done:
                continue
            up = user_prompt(c)
            if args.provider == "mock":
                raw = call_mock(c)
            elif args.provider == "anthropic":
                raw = call_anthropic(args.model, system, up)
            else:
                raw = call_openai(args.model, system, up, args.reasoning_effort)
            pred, how = parse_judgment(raw, c["options"])
            rec = {**c, "model": args.model, "mode": args.mode,
                   "prediction": pred, "parse_method": how, "raw": raw,
                   "correct": (pred == c["expected"]) if pred else False}
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
            f.flush()
            mark = "O" if rec["correct"] else "X"
            print(f"[{i+1}/{len(cases)}] {c['case_id']} {c['item']}={c['value']} "
                  f"기대={c['expected']} 예측={pred} {mark}")
            time.sleep(0 if args.provider == "mock" else args.sleep)
    print(f"\n완료 → {out_path}")

if __name__ == "__main__":
    main()
