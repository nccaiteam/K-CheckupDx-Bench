# -*- coding: utf-8 -*-
"""Figure 1 - Benchmark construction, dual verification, and evaluation pipeline.
Pure diagram (no data dependency).

JMIR submission format: no title/caption embedded in the image (the legend lives
in the manuscript), 1200 x 1200 px PNG (8 in x 8 in @ 150 dpi) plus vector PDF.
Output goes to <repo>/figures/.   Run:  python src/make_figure1.py
"""
import os
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

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
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "figures")
os.makedirs(OUT, exist_ok=True)

fig = plt.figure(figsize=(SIDE, SIDE))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

# 각인 제목/캡션 없음 — 제목은 원고 Figure legend가 담당(JMIR: 그림 안에 제목을 넣지 않음)

EDGE = "#555555"; PURPLE = "#9b30c9"; DARK = "#333333"

def box(x0, x1, y0, y1, fc, title, body, tfs=12.5, bfs=10.5, body_dy=-0.022):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                 boxstyle="round,pad=0.006,rounding_size=0.012",
                 fc=fc, ec=EDGE, lw=1.4))
    cy = (y0 + y1) / 2; cx = (x0 + x1) / 2
    ax.text(cx, y1 - 0.018, title, ha="center", va="top", fontsize=tfs, fontweight="bold")
    ax.text(cx, cy + body_dy, body, ha="center", va="center", fontsize=bfs, linespacing=1.4)

def arrow(p, q, color=DARK, rad=0.0, lw=2.2):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=16,
                 lw=lw, color=color, connectionstyle=f"arc3,rad={rad}"))

# 3 columns (square canvas), 4 rows
C1 = (0.025, 0.295); C2 = (0.365, 0.635); C3 = (0.705, 0.975)
R1 = (0.805, 0.975); R2 = (0.555, 0.725); R3 = (0.325, 0.465); R4 = (0.040, 0.225)

# ---- row 1: criteria -> generation -> verification ----
box(*C1, *R1, "#d9e8f5", "Published criteria",
    "MOHW notification Annex 4\n(tiered determination rules)\n+ professional-society\ncutoffs")
box(*C2, *R1, "#fdeecd", "Programmatic generation",
    "Boundary-value analysis ·\nvalue-ladder construction\n(threshold ±1–3 units,\nfillers)")
box(*C3, *R1, "#fbe3ec", "Dual verification",
    "Independent rule engine:\n100% label agreement;\n0/6,321 violations\n(negative control)")

# ---- row 2: released sets + confound audit ----
box(*C1, *R2, "#e2efdc", "Tier-classification set",
    "v1.0 · 144 cases · 20 items\n77 boundary (32 inclusive-\nthreshold) · 67 representative")
box(*C2, *R2, "#e2efdc", "Value-ladder set",
    "v1.3 · 528 cases · 22 ladders\n6,321 ordered pairs\n(direction-aware; BMI split)")
box(*C3, *R2, "#fbe3ec", "Confound audit",
    "v1.1→v1.2: Hb upper tail\nv1.2→v1.3: uric-acid lower\ntail — identified & removed")

# ---- row 3: LLM evaluation (spans columns 1-2) ----
box(C1[0], C2[1], *R3, "#e8e2f4", "LLM evaluation",
    "Claude Fable 5 · GPT-5.6 Sol · zero-shot vs rule-grounded\n10 runs / model / condition",
    body_dy=-0.020)

# ---- row 4: outcomes (full width) ----
box(C1[0], C3[1], *R4, "#fdf9df", "Outcomes",
    "Grounding effect — run-level exact rank test\n"
    "Monotonicity violations — label-independent\n"
    "Test–retest reliability — flip, agreement, Fleiss κ\n"
    "Safety-critical errors — Wilson upper bound\n"
    "Stratified reporting: BMI vs non-BMI", body_dy=-0.020)

# ---- arrows ----
ym1 = (R1[0] + R1[1]) / 2
arrow((C1[1] + 0.004, ym1), (C2[0] - 0.004, ym1))                  # criteria -> generation
arrow((C2[1] + 0.004, ym1), (C3[0] - 0.004, ym1))                  # generation -> verification
ax.text((C2[1] + C3[0]) / 2, ym1 + 0.018, "verify\nall labels", ha="center", va="bottom",
        fontsize=8.5, style="italic", linespacing=1.2)
arrow((C2[0] + 0.03, R1[0] - 0.006), ((C1[0] + C1[1]) / 2 + 0.03, R2[1] + 0.008), rad=0.22)  # generation -> tier set
arrow(((C2[0] + C2[1]) / 2, R1[0] - 0.006), ((C2[0] + C2[1]) / 2, R2[1] + 0.008))           # generation -> ladder set
arrow(((C3[0] + C3[1]) / 2, R1[0] - 0.006), ((C3[0] + C3[1]) / 2, R2[1] + 0.008), color=PURPLE)  # verification -> audit
ym2 = (R2[0] + R2[1]) / 2
arrow((C3[0] - 0.004, ym2), (C2[1] + 0.004, ym2), color=PURPLE)    # audit -> ladder set
ax.text((C2[1] + C3[0]) / 2, ym2 - 0.018, "revise &\nre-verify", ha="center", va="top",
        fontsize=8.5, style="italic", color=PURPLE, linespacing=1.2)
arrow(((C1[0] + C1[1]) / 2, R2[0] - 0.006), ((C1[0] + C1[1]) / 2, R3[1] + 0.008))  # tier set -> LLM eval
arrow(((C2[0] + C2[1]) / 2, R2[0] - 0.006), ((C2[0] + C2[1]) / 2, R3[1] + 0.008))  # ladder set -> LLM eval
arrow(((C1[0] + C2[1]) / 2, R3[0] - 0.006), ((C1[0] + C2[1]) / 2, R4[1] + 0.008))  # LLM eval -> outcomes

png = os.path.join(OUT, "figure1_pipeline.png")
plt.savefig(png, dpi=DPI)                       # -> 1200 x 1200 px
plt.savefig(os.path.join(OUT, "figure1_pipeline.pdf"))

from PIL import Image
im = Image.open(png).convert("RGB")             # 알파 채널 제거(흰 배경 고정), 제출 시스템 호환
im.save(png, dpi=(DPI, DPI))
w, h = im.size
assert (w, h) == (PX, PX), f"unexpected size {w}x{h}"
print(f"saved {png} ({w}x{h} px) / .pdf")
