# -*- coding: utf-8 -*-
"""
파일럿 결과 채점·분석: 경계값 오류율 사전 신호 확인
사용법: python score_pilot.py results_claude-fable-5_zeroshot.jsonl results_gpt-5.6-sol_zeroshot.jsonl
출력: pilot_summary.md + pilot_analysis.xlsx
"""
import json, sys
import pandas as pd

SEV = {"정상A": 0, "정상": 0, "정상B": 1, "복부비만": 1, "질환의심": 2}

def load(path):
    df = pd.DataFrame([json.loads(l) for l in open(path, encoding="utf-8")])
    df["is_boundary"] = df["case_type"].str.contains("경계")
    df["is_inclusive"] = df["case_type"].str.contains("포함")  # =threshold (등호 포함) 케이스
    df["exp_sev"] = df["expected"].map(SEV)
    df["pred_sev"] = df["prediction"].map(SEV)
    # 방향성 오류: under = 심각도 과소평가(위음성 방향), over = 과대평가(위양성 방향)
    df["err_dir"] = "correct"
    bad = df["prediction"].notna() & (df["prediction"] != df["expected"])
    df.loc[bad & (df["pred_sev"] < df["exp_sev"]), "err_dir"] = "under(위음성방향)"
    df.loc[bad & (df["pred_sev"] > df["exp_sev"]), "err_dir"] = "over(위양성방향)"
    df.loc[df["prediction"].isna(), "err_dir"] = "unparsed"
    # 환자안전 위해 계층(계층3): 기대=질환의심인데 정상A/정상 출력
    df["safety_critical_err"] = (df["expected"] == "질환의심") & df["prediction"].isin(["정상A", "정상"])
    return df

def acc(d):
    return 100 * d["correct"].mean() if len(d) else float("nan")

def summarize(df, name):
    lines = [f"## {name}  (n={len(df)})"]
    lines.append(f"- 전체 정확도: **{acc(df):.1f}%**")
    lines.append(f"- 경계값 케이스 정확도: **{acc(df[df.is_boundary]):.1f}%** (n={df.is_boundary.sum()})")
    lines.append(f"- 구간 대표 케이스 정확도: **{acc(df[~df.is_boundary]):.1f}%** (n={(~df.is_boundary).sum()})")
    lines.append(f"- 등호 포함(=threshold) 케이스 정확도: **{acc(df[df.is_inclusive]):.1f}%** (n={df.is_inclusive.sum()})")
    gap = acc(df[~df.is_boundary]) - acc(df[df.is_boundary])
    lines.append(f"- **경계값 성능 격차(대표-경계): {gap:+.1f}%p** ← 사전 신호 핵심 지표")
    ed = df["err_dir"].value_counts()
    lines.append(f"- 오류 방향: 위음성방향 {ed.get('under(위음성방향)',0)}건 / "
                 f"위양성방향 {ed.get('over(위양성방향)',0)}건 / 파싱실패 {ed.get('unparsed',0)}건")
    sc = int(df["safety_critical_err"].sum())
    n_sus = int((df["expected"] == "질환의심").sum())
    lines.append(f"- **환자안전 위해 오류(질환의심→정상A/정상): {sc}건 / 질환의심 기대 {n_sus}건 "
                 f"({100*sc/n_sus:.1f}%)** ← 계층③ primary safety signal")
    # 항목별 저성능 top5
    by_item = df.groupby("item")["correct"].agg(["mean", "count"]).sort_values("mean")
    worst = by_item.head(5)
    lines.append("- 저성능 항목 Top5: " + "; ".join(
        f"{i}({100*r['mean']:.0f}%, n={int(r['count'])})" for i, r in worst.iterrows()))
    return "\n".join(lines), by_item

def main():
    paths = sys.argv[1:]
    if not paths:
        print("사용법: python score_pilot.py <results1.jsonl> [results2.jsonl ...]")
        sys.exit(1)
    md = ["# K-CheckupDx-Pub v1.0 파일럿 평가 결과\n"]
    xl = {}
    for p in paths:
        df = load(p)
        name = f"{df['model'].iloc[0]} / {df['mode'].iloc[0]}"
        s, by_item = summarize(df, name)
        md.append(s + "\n")
        key = df["model"].iloc[0].replace("/", "_")[:20] + "_" + df["mode"].iloc[0][:8]
        xl[key] = df
        xl[key + "_항목별"] = by_item.reset_index()
    # 모델 간 경계값 케이스 불일치 목록 (두 결과 이상일 때)
    if len(paths) >= 2:
        d1, d2 = load(paths[0]), load(paths[1])
        m = d1.merge(d2, on="case_id", suffixes=("_1", "_2"))
        dis = m[(m.correct_1 != m.correct_2) & m.is_boundary_1]
        md.append(f"## 모델 간 경계값 불일치: {len(dis)}건\n")
        if len(dis):
            md.append(dis[["case_id", "item_1", "value_1", "expected_1",
                           "prediction_1", "prediction_2"]].to_markdown(index=False))
        xl["모델간_불일치"] = dis
    open("pilot_summary.md", "w", encoding="utf-8").write("\n".join(md))
    with pd.ExcelWriter("pilot_analysis.xlsx") as w:
        for k, v in xl.items():
            v.to_excel(w, sheet_name=k[:31], index=False)
    print("완료 → pilot_summary.md, pilot_analysis.xlsx")
    print("\n".join(md[:3]))

if __name__ == "__main__":
    main()
