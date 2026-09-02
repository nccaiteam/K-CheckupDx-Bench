# -*- coding: utf-8 -*-
"""
단조성 위반 채점 + 반복 시행 일치도 분석
사용법:
  단조성:   python score_monotonicity.py results_모델_모드_run1.jsonl [run2 ...]
  (여러 run 파일을 주면 run별 단조성 + 시행간 일치도까지 함께 산출)
출력: monotonicity_summary.md
"""
import json, sys
from collections import defaultdict
from itertools import combinations
import pandas as pd

SEV = {"정상A": 0, "정상": 0, "정상B": 1, "복부비만": 1, "질환의심": 2}

def load(path):
    return pd.DataFrame([json.loads(l) for l in open(path, encoding="utf-8")])

def monotonicity(df):
    """ladder_id별로 값 정렬 후 심각도 순서 위반 쌍 계산 (direction-aware)"""
    out = []
    for lid, g in df.groupby("ladder_id"):
        g = g.copy()
        g["v"] = g["value"].astype(float)
        g["s"] = g["prediction"].map(SEV)
        g = g.dropna(subset=["s"]).sort_values("v")
        direction = g["direction"].iloc[0]
        rows = list(g[["v", "s", "case_id", "prediction"]].itertuples(index=False))
        for (v1, s1, c1, p1), (v2, s2, c2, p2) in combinations(rows, 2):
            # high: 값↑=심각도 비감소여야 함 → s1>s2 위반 / low: 값↑=심각도 비증가 → s1<s2 위반
            viol = (s1 > s2) if direction == "high" else (s1 < s2)
            out.append(dict(ladder_id=lid, v1=v1, v2=v2, s1=s1, s2=s2,
                            p1=p1, p2=p2, c1=c1, c2=c2, violation=viol))
    return pd.DataFrame(out)

def main():
    paths = sys.argv[1:]
    if not paths:
        print("사용법: python score_monotonicity.py <results_run1.jsonl> [run2 ...]")
        sys.exit(1)
    md = ["# 단조성 위반 · 반복 시행 분석\n"]
    run_dfs = []
    for p in paths:
        df = load(p)
        run_dfs.append(df)
        mono = monotonicity(df)
        n_v = int(mono["violation"].sum())
        rate = 100 * n_v / len(mono) if len(mono) else 0
        name = f"{df['model'].iloc[0]} / {df['mode'].iloc[0]} / {p}"
        md.append(f"## {name}")
        md.append(f"- 정확도(참고): {100*df['correct'].mean():.1f}%  (n={len(df)})")
        n_null = int(df["prediction"].isna().sum())
        if n_null:
            md.append(f"- ⚠️ null 예측 {n_null}건 — 쌍 계산에서 제외되어 분모가 축소됨. 러너 v1.4 미만이면 업그레이드 필요")
        md.append(f"- **단조성 위반: {n_v} / {len(mono)}쌍 ({rate:.2f}%)**")
        # ---- v1.2 자동 보고 삽입점 ----

        # ---- 자동 교란 분리 보고 (v1.2) ----
        bmi_mask = mono["ladder_id"].str.startswith("BMI")
        nb = int(mono[~bmi_mask]["violation"].sum()); nt = int((~bmi_mask).sum())
        md.append(f"- BMI 제외: {nb} / {nt}쌍 ({100*nb/nt:.2f}%)" if nt else "")
        bo = int(mono[bmi_mask]["violation"].sum()); bt = int(bmi_mask.sum())
        md.append(f"- BMI만: {bo} / {bt}쌍 ({100*bo/bt:.2f}%)" if bt else "")
        # near_boundary enrichment (v1.2 데이터에 near_boundary 필드 존재 시)
        if "near_boundary" in df.columns:
            nbmap = df.set_index("case_id")["near_boundary"]
            vio2 = mono[mono.violation]
            if len(vio2):
                near_v = vio2["c1"].map(nbmap).mean()
                base = mono["c1"].map(nbmap).mean()  # 쌍 수준 기저율 (v1 기준)
                md.append(f"- 위반 v1의 임계 ±3ε 근접률: {100*near_v:.1f}% (기저율 {100*base:.1f}%, enrichment {near_v/base:.2f}배)")
        if n_v:
            vio = mono[mono.violation]
            # 위반 관여 케이스의 최소 단위(인접쌍 우선) 요약
            by_lad = vio.groupby("ladder_id").size().sort_values(ascending=False)
            md.append("- 사다리별 위반: " + "; ".join(f"{k}({v}쌍)" for k, v in by_lad.items()))
            adj = vio.nsmallest(10, ["v2"])  # 대표 10건
            for _, r in vio.head(10).iterrows():
                md.append(f"  - {r.ladder_id}: {r.v1}→{r.p1}({int(r.s1)}) vs {r.v2}→{r.p2}({int(r.s2)})")
        md.append("")
    # 반복 시행 일치도 (2개 run 이상) — 동일 조건(모델×모드)만 허용
    if len(run_dfs) >= 2:
        conds = {(d["model"].iloc[0], d["mode"].iloc[0]) for d in run_dfs}
        if len(conds) > 1:
            md.append("## 반복 시행 일치도: 계산 생략")
            md.append(f"- 서로 다른 조건 {sorted(conds)}이 함께 입력됨 — 일치도는 동일 조건 런끼리만 유효. 파일을 조건별로 나눠 재실행하십시오.")
            run_dfs = []  # 이하 계산 차단
    if len(run_dfs) >= 2:
        md.append("## 반복 시행 일치도")
        base = run_dfs[0][["case_id", "expected"]].copy()
        preds = pd.DataFrame({f"run{i+1}": d.set_index("case_id")["prediction"]
                              for i, d in enumerate(run_dfs)})
        preds = preds.dropna()
        n_runs = len(run_dfs)
        # 케이스별 완전일치율
        unanimous = (preds.nunique(axis=1) == 1)
        md.append(f"- 전 시행 완전일치 케이스: {unanimous.sum()} / {len(preds)} ({100*unanimous.mean():.1f}%)")
        # pairwise agreement 평균
        pa = []
        for a, b in combinations(preds.columns, 2):
            pa.append((preds[a] == preds[b]).mean())
        md.append(f"- 평균 pairwise agreement: {100*sum(pa)/len(pa):.1f}%")
        # 다수결 정확도
        exp = run_dfs[0].set_index("case_id")["expected"].reindex(preds.index)
        maj = preds.mode(axis=1)[0]
        md.append(f"- **다수결 정확도: {100*(maj==exp).mean():.1f}%** "
                  f"(run별: {', '.join(f'{100*(preds[c]==exp).mean():.1f}%' for c in preds.columns)})")
        flips = preds[~unanimous]
        if len(flips):
            md.append(f"- flip 케이스 {len(flips)}건:")
            for cid, row in flips.head(15).iterrows():
                md.append(f"  - {cid}: {' / '.join(str(v) for v in row.values)} (기대 {exp[cid]})")
    open("monotonicity_summary.md", "w", encoding="utf-8").write("\n".join(md))
    print("완료 → monotonicity_summary.md")
    print("\n".join(md[:8]))

if __name__ == "__main__":
    main()
