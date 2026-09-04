# -*- coding: utf-8 -*-
"""
Grounding 효과 exact McNemar — 다수결 판정 기반 (단일 런 게재 금지 정책 정합)
사용법:
  python score_mcnemar.py --zs zs_run1.jsonl zs_run2.jsonl ... --gr gr_run1.jsonl ...
동일 모델의 zero-shot 런들과 grounded 런들을 넣으면:
  1) 케이스별 다수결 판정 산출 (동률 시 해당 케이스 '불안정'으로 별도 집계, 검정 제외)
  2) 다수결 정답 여부로 쌍대 exact McNemar (이항검정, 양측)
  3) 민감도: 런 조합별 단일런 McNemar p 범위 병기
"""
import json, argparse
from collections import Counter
from math import comb

def load(path):
    return {r["case_id"]: r for r in map(json.loads, open(path, encoding="utf-8"))}

def majority(runs, cid):
    votes = [runs_i[cid]["prediction"] for runs_i in runs if runs_i[cid]["prediction"]]
    if not votes: return None, True
    c = Counter(votes).most_common()
    tie = len(c) > 1 and c[0][1] == c[1][1]
    return c[0][0], tie

def exact_mcnemar(b, c):
    """b,c = 불일치 두 방향 건수. 양측 exact binomial."""
    n = b + c
    if n == 0: return 1.0
    k = min(b, c)
    p = sum(comb(n, i) for i in range(0, k + 1)) * 2 / 2**n
    return min(1.0, p)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zs", nargs="+", required=True)
    ap.add_argument("--gr", nargs="+", required=True)
    a = ap.parse_args()
    ZS = [load(p) for p in a.zs]; GR = [load(p) for p in a.gr]
    # 혼재 가드: 각 그룹은 단일 (model, mode)여야 함
    def cond_of(runs, expect_mode, tag):
        conds = {(r["model"], r["mode"]) for run in runs for r in run.values()}
        if len(conds) != 1:
            raise SystemExit(f"[중단] --{tag} 파일들에 서로 다른 조건 혼재: {sorted(conds)}")
        (m, mo), = conds
        if mo != expect_mode:
            raise SystemExit(f"[중단] --{tag}에 mode={mo} 파일이 있음 (기대: {expect_mode})")
        return m
    mz = cond_of(ZS, "zeroshot", "zs"); mg = cond_of(GR, "grounded", "gr")
    if mz != mg:
        raise SystemExit(f"[중단] zs 모델({mz})과 gr 모델({mg}) 불일치")
    model = mz
    # 견고한 교집합: 전체 런의 공통 케이스만 사용, 누락 발생 시 보고
    all_sets = [set(r) for r in ZS + GR]
    ids = sorted(set.intersection(*all_sets))
    n_union = len(set.union(*all_sets))
    if len(ids) < n_union:
        print(f"[경고] 런 간 케이스 불일치: 공통 {len(ids)} / 합집합 {n_union} — 공통 케이스만 사용")
    zt, gt, ties = {}, {}, 0
    for cid in ids:
        exp = ZS[0][cid]["expected"]
        mz, tz = majority(ZS, cid); mg, tg = majority(GR, cid)
        if tz or tg: ties += 1; continue
        zt[cid] = (mz == exp); gt[cid] = (mg == exp)
    b = sum(1 for c in zt if zt[c] and not gt[c])      # zs 정답 → gr 오답
    c_ = sum(1 for c in zt if not zt[c] and gt[c])     # zs 오답 → gr 정답
    both_w = sum(1 for c in zt if not zt[c] and not gt[c])
    n = len(zt)
    p = exact_mcnemar(b, c_)
    print(f"모델: {model} | 케이스 {n} (동률 제외 {ties})")
    print(f"다수결 정확도: zero-shot {100*sum(zt.values())/n:.1f}%  grounded {100*sum(gt.values())/n:.1f}%")
    print(f"불일치: zs오답→gr정답 {c_}건 / zs정답→gr오답 {b}건 / 양쪽 오답 {both_w}건")
    print(f"exact McNemar 양측 p = {p:.5f}")
    # 민감도: 단일런 조합 p 범위
    ps = []
    for zi in ZS:
        for gi in GR:
            bb = cc = 0
            for cid in ids:
                exp = zi[cid]["expected"]
                z_ok = zi[cid]["prediction"] == exp; g_ok = gi[cid]["prediction"] == exp
                if z_ok and not g_ok: bb += 1
                if g_ok and not z_ok: cc += 1
            ps.append(exact_mcnemar(bb, cc))
    print(f"민감도(단일런 {len(ps)}조합): p 범위 [{min(ps):.5f}, {max(ps):.5f}]")

if __name__ == "__main__":
    main()
