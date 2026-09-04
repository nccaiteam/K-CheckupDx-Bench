# -*- coding: utf-8 -*-
"""Figure 2 - Structure of monotonicity violations (value-ladder v1.3).
Recomputes all panel values from the released result files; CI/P annotations in
panel C are the published cluster-bootstrap values (Table 4 of the manuscript).

JMIR submission format: no title/caption embedded in the image (panel letters A-D
only; descriptive text lives in the manuscript legend), 1200 x 1200 px PNG
(8 in x 8 in @ 150 dpi) plus vector PDF.  Output goes to <repo>/figures/.
Run:  python src/make_figure2.py   (paths are resolved relative to this file)
"""
import os, json, glob, statistics as st
from collections import defaultdict, Counter
from itertools import combinations
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

# ── 서체: JMIR 권고(Times New Roman). 실제 TNR이 있으면 그것을,
#    없으면 메트릭 호환 대체(Liberation Serif / Nimbus Roman)를 사용.
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})


# ── 출력 규격: 1200 x 1200 px  (figsize * dpi; bbox_inches="tight"는 쓰지 않음)
PX, DPI = 1200, 150
SIDE = PX / DPI                       # 8.0 in
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root
OUT = os.path.join(BASE, "figures")
os.makedirs(OUT, exist_ok=True)

def panel_label(ax_, s_):
    """JMIR: 패널 문자만 각인. 설명문은 원고 Figure legend에 기술."""
    ax_.text(-0.17, 1.02, s_, transform=ax_.transAxes, fontsize=15,
             fontweight="bold", ha="left", va="bottom")

SEV = {"정상A": 0, "정상": 0, "정상B": 1, "복부비만": 1, "질환의심": 2}
BLU, ORA = "#4C78A8", "#F58518"
MODELS = ["claude-fable-5", "gpt-5.6-sol"]

def load(p):
    return [json.loads(l) for l in open(p, encoding="utf-8")]

def viol(recs):
    lad = defaultdict(list)
    for r in recs:
        if r.get("ladder_id"):
            lad[r["ladder_id"]].append(r)
    out = {"BMI": [0, 0], "non": [0, 0]}
    for lid, g in lad.items():
        g = sorted(g, key=lambda r: float(r["value"]))
        d = g[0]["direction"]
        k = "BMI" if lid.startswith("BMI") else "non"
        for a, b in combinations(g, 2):
            s1, s2 = SEV[a["prediction"]], SEV[b["prediction"]]
            out[k][1] += 1
            out[k][0] += (s1 > s2) if d == "high" else (s1 < s2)
    return out

RUNS = {m: [load(f"{BASE}/results/results_{m}_zeroshot_ladder_v1.3_run{i}.jsonl")
            for i in range(1, 11)] for m in MODELS}
RATE = {}
for m in MODELS:
    non, bmi = [], []
    for recs in RUNS[m]:
        s = viol(recs)
        non.append(100 * s["non"][0] / s["non"][1])
        bmi.append(100 * s["BMI"][0] / s["BMI"][1])
    RATE[m] = {"non": non, "bmi": bmi}

def reliability(runsets):
    bycase = defaultdict(list)
    for recs in runsets:
        for r in recs:
            bycase[r["case_id"]].append(r["prediction"])
    n = len(runsets)
    flip = 100 * sum(1 for ps in bycase.values() if len(set(ps)) > 1) / len(bycase)
    agree = []
    for i, j in combinations(range(n), 2):
        di = {r["case_id"]: r["prediction"] for r in runsets[i]}
        dj = {r["case_id"]: r["prediction"] for r in runsets[j]}
        agree.append(100 * sum(1 for c in di if di[c] == dj[c]) / len(di))
    disagree = 100 - st.mean(agree)
    N = len(bycase); pj = Counter(); Pi = []
    for ps in bycase.values():
        cnt = Counter(ps)
        for c, k in cnt.items(): pj[c] += k
        Pi.append((sum(k * k for k in cnt.values()) - n) / (n * (n - 1)))
    Pbar = st.mean(Pi); pj = {c: k / (N * n) for c, k in pj.items()}
    Pe = sum(v * v for v in pj.values())
    kappa = (Pbar - Pe) / (1 - Pe)
    return flip, disagree, 100 * (1 - kappa)

REL = {m: reliability(RUNS[m]) for m in MODELS}

fig, ax = plt.subplots(2, 2, figsize=(SIDE, SIDE))
fig.subplots_adjust(left=0.10, right=0.985, top=0.955, bottom=0.085, wspace=0.42, hspace=0.38)
# 각인 제목/캡션 없음 — 제목·패널 설명은 원고 Figure legend가 담당(JMIR)

# ---------------- Panel A ----------------
a = ax[0, 0]
x = np.arange(2); w = 0.34
for i, (m, lab, col) in enumerate(zip(MODELS,
        ["Claude zero-shot\n(10-run mean±SD)", "GPT zero-shot\n(10-run mean±SD)"], [BLU, ORA])):
    means = [st.mean(RATE[m]["non"]), st.mean(RATE[m]["bmi"])]
    sds = [st.stdev(RATE[m]["non"]), st.stdev(RATE[m]["bmi"])]
    a.bar(x + (i - .5) * w, means, w, yerr=sds, capsize=4, label=lab, color=col)
    for xi, v, s in zip(x, means, sds):
        a.annotate(f"{v:.2f}", (xi + (i - .5) * w, v + s + 0.25),
                   ha="center", va="bottom", fontsize=10, color=col)
a.set_xticks(x); a.set_xticklabels(["Non-BMI\n(5,807 pairs)", "BMI only\n(514 pairs)"])
a.set_ylabel("Monotonicity violation rate (%)")
a.set_ylim(0, 16.8)
a.legend(fontsize=9, loc="upper left")
a.grid(axis="y", alpha=.3)
panel_label(a, "A")
a.annotate("Rule-grounded:\n0.00 (both models,\n10 runs each)",
           xy=(0.36, 0.47), xycoords="axes fraction", ha="center", va="center",
           fontsize=10, bbox=dict(boxstyle="round", fc="#f2f2f2", ec="#999999"))

# ---------------- Panel B ----------------
b = ax[0, 1]
for m, lab, col, mk in zip(MODELS, ["Claude zero-shot", "GPT zero-shot"], [BLU, ORA], ["o", "s"]):
    means = [st.mean(RATE[m]["non"]), st.mean(RATE[m]["bmi"])]
    sds = [st.stdev(RATE[m]["non"]), st.stdev(RATE[m]["bmi"])]
    b.errorbar([0, 1], means, yerr=sds, marker=mk, ms=9, lw=2.5, capsize=4,
               label=lab, color=col, zorder=3)
cn, cb = st.mean(RATE[MODELS[0]]["non"]), st.mean(RATE[MODELS[0]]["bmi"])
gn, gb = st.mean(RATE[MODELS[1]]["non"]), st.mean(RATE[MODELS[1]]["bmi"])
b.annotate(f"{cn:.2f}%", (0, cn), xytext=(0, -22), textcoords="offset points",
           ha="center", fontsize=10.5, color=BLU)
b.annotate(f"{gn:.2f}%", (0, gn), xytext=(0, 13), textcoords="offset points",
           ha="center", fontsize=10.5, color=ORA)
b.annotate(f"{cb:.2f}%", (1, cb), xytext=(13, -4), textcoords="offset points",
           ha="left", fontsize=10.5, color=BLU)
b.annotate(f"{gb:.2f}%", (1, gb), xytext=(13, -4), textcoords="offset points",
           ha="left", fontsize=10.5, color=ORA)
b.annotate("BMI: Claude 2.5×\nP<.001", xy=(0.27, 0.66), xycoords="axes fraction",
           fontsize=10, color="#B22222")
b.annotate("Non-BMI: GPT 4.5×\nP=.01", xy=(0.30, 0.055), xycoords="axes fraction",
           fontsize=10, color="#B22222")
b.set_xlim(-0.28, 1.34)
b.set_xticks([0, 1]); b.set_xticklabels(["Non-BMI ladders", "BMI ladders"])
b.set_ylabel("Monotonicity violation rate (%)")
b.set_ylim(-2.3, 14.6); b.set_yticks(range(0, 15, 2))
b.legend(fontsize=9, loc="upper left")
b.grid(axis="y", alpha=.3)
panel_label(b, "B")

# ---------------- Panel C ----------------
c = ax[1, 0]
rows = [  # published cluster-bootstrap values (Table 4)
    ("Non-BMI", -0.49, -0.971, -0.075, "P=.01", "Claude < GPT", "#B22222"),
    ("All pairs", +0.05, -0.729, +1.070, "P=.99", "no difference", "#888888"),
    ("BMI only", +6.07, +5.515, +6.270, "P<.001", "Claude > GPT", "#B22222"),
]
ys = [2, 1, 0]
for (lab, d, lo, hi, p, dirn, col), y in zip(rows, ys):
    c.plot([lo, hi], [y, y], color=col, lw=2.5, zorder=2)
    c.plot(d, y, marker="D", ms=9, color="black", zorder=3)
    c.annotate(f"{d:+.2f} pp  {p}\n({dirn})", (max(hi, d) + 0.35, y), va="center",
               fontsize=10, linespacing=1.15)
c.axvline(0, color="red", ls="--", lw=1.2)
c.set_yticks(ys); c.set_yticklabels([r[0] for r in rows], fontsize=10)
c.set_ylim(-0.6, 2.6)
c.set_xlim(-2.6, 9.9)
c.set_xlabel("Violation-rate difference (Claude − GPT), pp\n(run-mean cluster bootstrap 95% CI)",
             fontsize=10)
c.grid(axis="x", alpha=.3)
panel_label(c, "C")

# ---------------- Panel D ----------------
d = ax[1, 1]
x = np.arange(3); w = 0.34
for i, (m, lab, col) in enumerate(zip(MODELS, ["Claude, 10 runs", "GPT, 10 runs"], [BLU, ORA])):
    vals = list(REL[m])
    d.bar(x + (i - .5) * w, vals, w, label=lab, color=col)
    for xi, v in zip(x, vals):
        d.annotate(f"{v:.2f}", (xi + (i - .5) * w, v + 0.12), ha="center", va="bottom",
                   fontsize=10, color=col)
d.set_xticks(x)
d.set_xticklabels(["Flip proportion\n(%)", "Pairwise\ndisagreement (%)", "(1 − Fleiss κ)\n× 100"])
d.set_ylabel("Instability (%, lower = more reliable)")
d.set_ylim(0, 12.6)
d.legend(fontsize=9, loc="upper right")
d.grid(axis="y", alpha=.3)
panel_label(d, "D")

png = os.path.join(OUT, "figure2_monotonicity.png")
plt.savefig(png, dpi=DPI)                       # -> 1200 x 1200 px
plt.savefig(os.path.join(OUT, "figure2_monotonicity.pdf"))

from PIL import Image
im = Image.open(png).convert("RGB")             # 알파 채널 제거(흰 배경 고정), 제출 시스템 호환
im.save(png, dpi=(DPI, DPI))
w, h = im.size
assert (w, h) == (PX, PX), f"unexpected size {w}x{h}"
print(f"saved {png} ({w}x{h} px) / .pdf")
