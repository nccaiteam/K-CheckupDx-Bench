# -*- coding: utf-8 -*-
"""Appendix Figure A1 - BMI source-naming experiment (54 cases / 514 pairs; 10 runs).
Computes all values from the released data and result files.

JMIR submission format: no title/caption embedded in the image (panel letters A-D
only; descriptive text lives in the manuscript legend), 1200 x 1200 px PNG
(8 in x 8 in @ 150 dpi) plus vector PDF.  Output goes to <repo>/figures/.
Run:  python src/make_figureA1_final.py   (paths are resolved relative to this file)
"""
import os, json, glob, re, statistics as st
from collections import defaultdict, Counter
from itertools import combinations
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ── 서체: JMIR 권고(Times New Roman). 실제 TNR이 있으면 그것을,
#    없으면 메트릭 호환 대체(Liberation Serif / Nimbus Roman)를 사용.
plt.rcParams.update({
    "font.family": "serif",
    "font.serif": ["Times New Roman", "Liberation Serif", "Nimbus Roman", "DejaVu Serif"],
    "mathtext.fontset": "stix",
    "pdf.fonttype": 42,
    "ps.fonttype": 42,
})

import matplotlib.gridspec as gridspec
import numpy as np

# ── 출력 규격: 1200 x 1200 px  (figsize * dpi; bbox_inches="tight"는 쓰지 않음)
PX, DPI = 1200, 150
SIDE = PX / DPI                       # 8.0 in
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))   # repo root
OUT = os.path.join(BASE, "figures")
os.makedirs(OUT, exist_ok=True)

def panel_label(ax_, s_, dx=-0.17):
    """JMIR: 패널 문자만 각인. 설명문은 원고 Figure legend에 기술."""
    ax_.text(dx, 1.02, s_, transform=ax_.transAxes, fontsize=15,
             fontweight="bold", ha="left", va="bottom")

SEV = {"정상A": 0, "정상": 0, "정상B": 1, "복부비만": 1, "질환의심": 2}
ENG = {"질환의심": "suspected", "정상A": "Normal A", "정상B": "Normal B"}
MODES = ["zeroshot", "named", "grounded"]
MLAB = ["zero-shot", "source-named\n(notification cited,\ntable absent)", "rule-grounded\n(verbatim table)"]
MODELS = ["claude-fable-5", "gpt-5.6-sol"]
MODLAB = ["Claude Fable 5", "GPT-5.6 Sol"]
BLU, ORA = "#4C78A8", "#F58518"

LAD = {}
for l in open(f"{BASE}/data/pubset_bmi_3cond.jsonl", encoding="utf-8"):
    x = json.loads(l); LAD[x["case_id"]] = x
TIER = sorted([c for c, x in LAD.items() if not x.get("ladder_id")],
              key=lambda c: float(LAD[c]["value"]))
LADC = [c for c, x in LAD.items() if x.get("ladder_id")]

def runs(m, md):
    fs = glob.glob(f"{BASE}/results/results_{m}_{md}_bmi_3cond_run*.jsonl")
    return [{r["case_id"]: r for r in map(json.loads, open(p, encoding="utf-8"))}
            for p in sorted(fs, key=lambda x: int(re.search(r"run(\d+)", x).group(1)))]

def mono(run):
    g = defaultdict(list)
    for c in LADC: g[LAD[c]["ladder_id"]].append(LAD[c])
    v = t = 0
    for lid, rs in g.items():
        rs = sorted(rs, key=lambda x: float(x["value"])); d = rs[0]["direction"]
        for a, b in combinations(rs, 2):
            s1, s2 = SEV[run[a["case_id"]]["prediction"]], SEV[run[b["case_id"]]["prediction"]]
            t += 1
            if (s1 > s2) if d == "high" else (s1 < s2): v += 1
    return 100 * v / t

def mj(rs, c):
    cc = Counter(r[c]["prediction"] for r in rs).most_common()
    return "TIE" if len(cc) > 1 and cc[0][1] == cc[1][1] else cc[0][0]

R = {(m, md): runs(m, md) for m in MODELS for md in MODES}

fig = plt.figure(figsize=(SIDE, SIDE))
gs = gridspec.GridSpec(2, 2, figure=fig, wspace=0.48, hspace=0.40,
                       left=0.095, right=0.985, top=0.955, bottom=0.085)
# 각인 제목/캡션 없음 — 제목·패널 설명은 원고 Figure legend가 담당(JMIR)
x = np.arange(3); w = 0.34

# ---------------- A. tier accuracy ----------------
a = fig.add_subplot(gs[0, 0])
for i, (m, lab, col) in enumerate(zip(MODELS, MODLAB, [BLU, ORA])):
    vals = []
    for md in MODES:
        rs = R[(m, md)]
        vals.append(100 * sum(1 for c in TIER if mj(rs, c) == LAD[c]["expected"]) / len(TIER))
    a.bar(x + (i - .5) * w, vals, w, label=lab, color=col)
    for xi, v in zip(x, vals):
        a.annotate(f"{v:.1f}", (xi + (i - .5) * w, v + 1), ha="center", va="bottom",
                   fontsize=10, color=col)
a.set_xticks(x); a.set_xticklabels(MLAB, fontsize=8.5)
a.set_ylabel("Tier accuracy (%, majority vote, 9 cases)", fontsize=10)
a.set_ylim(0, 118); a.legend(fontsize=9, loc="upper left"); a.grid(axis="y", alpha=.3)
panel_label(a, "A")

# ---------------- B. monotonicity ----------------
b = fig.add_subplot(gs[0, 1])
for i, (m, lab, col) in enumerate(zip(MODELS, MODLAB, [BLU, ORA])):
    means, sds = [], []
    for md in MODES:
        v = [mono(r) for r in R[(m, md)]]
        means.append(st.mean(v)); sds.append(st.stdev(v))
        b.scatter([x[MODES.index(md)] + (i - .5) * w] * len(v), v, s=10, color=col,
                  alpha=.45, zorder=3)
    b.bar(x + (i - .5) * w, means, w, yerr=sds, capsize=4, label=lab, color=col, alpha=.75)
    for k, (xi, v, s) in enumerate(zip(x, means, sds)):
        if v > 0:
            vv = [mono(r) for r in R[(m, MODES[k])]]
            ytop = max(v + s, max(vv)) + 0.35
            b.annotate(f"{v:.2f}", (xi + (i - .5) * w, ytop), ha="center",
                       va="bottom", fontsize=9.5, color=col)
b.annotate("0.00 / 0.00\n(all 10 runs)", xy=(2, 1.4), ha="center", va="bottom",
           fontsize=10, color="#555555")
b.set_xticks(x); b.set_xticklabels(MLAB, fontsize=8.5)
b.set_ylabel("BMI monotonicity violations (%, 514 pairs)", fontsize=10)
b.set_ylim(0, 17.2)
b.legend(fontsize=9, loc="upper right"); b.grid(axis="y", alpha=.3)
panel_label(b, "B")

# ---------------- C. flip ----------------
c = fig.add_subplot(gs[1, 0])
for i, (m, lab, col) in enumerate(zip(MODELS, MODLAB, [BLU, ORA])):
    vals = []
    for md in MODES:
        rs = R[(m, md)]
        vals.append(100 * sum(1 for cc in LAD if len({r[cc]["prediction"] for r in rs}) > 1) / len(LAD))
    c.bar(x + (i - .5) * w, vals, w, label=lab, color=col)
    for xi, v in zip(x, vals):
        if v > 0:
            c.annotate(f"{v:.1f}", (xi + (i - .5) * w, v + 0.6), ha="center", va="bottom",
                       fontsize=10, color=col)
c.annotate("0.0 / 0.0\n(all 10 runs)", xy=(2, 2.2), ha="center", va="bottom",
           fontsize=10, color="#555555")
c.set_xticks(x); c.set_xticklabels(MLAB, fontsize=8.5)
c.set_ylabel("Flip proportion (%, 10 runs)")
c.set_ylim(0, 56); c.legend(fontsize=9, loc="upper right"); c.grid(axis="y", alpha=.3)
panel_label(c, "C")

# ---------------- D. case-level heatmap ----------------
d = fig.add_subplot(gs[1, 1])
cols = [(m, md) for m in MODELS for md in MODES]
M = np.zeros((len(TIER), len(cols)))
for r_, cid in enumerate(TIER):
    for c_, (m, md) in enumerate(cols):
        p = mj(R[(m, md)], cid)
        M[r_, c_] = 1 if p == LAD[cid]["expected"] else (0.5 if p == "TIE" else 0)
d.imshow(M, cmap=plt.cm.RdYlGn, vmin=0, vmax=1, aspect="auto")
d.set_xticks(range(len(cols)))
SH = {"zeroshot": "zs", "named": "na", "grounded": "gr"}
d.set_xticklabels([f"{'C' if m == MODELS[0] else 'G'}·{SH[md]}" for m, md in cols], fontsize=9.5)
d.set_yticks(range(len(TIER)))
d.set_yticklabels([f"BMI {LAD[c]['value']} → {ENG[LAD[c]['expected']]}" for c in TIER],
                  fontsize=8.5)
for r_ in range(len(TIER)):
    for c_ in range(len(cols)):
        d.text(c_, r_, "O" if M[r_, c_] == 1 else ("~" if M[r_, c_] == 0.5 else "X"),
               ha="center", va="center", fontsize=9,
               color="white" if M[r_, c_] != 0.5 else "#555555")
d.axvline(2.5, color="k", lw=1.5)
panel_label(d, "D")   # B와 동일한 x 오프셋으로 정렬

png = os.path.join(OUT, "figureA1_bmi.png")
plt.savefig(png, dpi=DPI)                       # -> 1200 x 1200 px
plt.savefig(os.path.join(OUT, "figureA1_bmi.pdf"))

from PIL import Image
im = Image.open(png).convert("RGB")             # 알파 채널 제거(흰 배경 고정), 제출 시스템 호환
im.save(png, dpi=(DPI, DPI))
w, h = im.size
assert (w, h) == (PX, PX), f"unexpected size {w}x{h}"
print(f"saved {png} ({w}x{h} px) / .pdf")
