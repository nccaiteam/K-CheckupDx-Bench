# -*- coding: utf-8 -*-
"""Figure 1 - Benchmark construction, dual verification, and evaluation pipeline.
Pure diagram (no data dependency).  python make_figure1.py
"""
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig = plt.figure(figsize=(10.275, 6.065))
ax = fig.add_axes([0, 0, 1, 1]); ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off")

ax.text(0.5, 0.978, "Figure 1. Benchmark construction, dual verification, and evaluation pipeline",
        ha="center", va="top", fontsize=14.5, fontweight="bold")

EDGE = "#555555"; PURPLE = "#9b30c9"; DARK = "#333333"

def box(x0, x1, y0, y1, fc, title, body, tfs=12.5, bfs=10.5):
    ax.add_patch(FancyBboxPatch((x0, y0), x1 - x0, y1 - y0,
                 boxstyle="round,pad=0.008,rounding_size=0.015",
                 fc=fc, ec=EDGE, lw=1.4))
    cy = (y0 + y1) / 2; cx = (x0 + x1) / 2
    ax.text(cx, y1 - 0.026, title, ha="center", va="top", fontsize=tfs, fontweight="bold")
    ax.text(cx, cy - 0.028, body, ha="center", va="center", fontsize=bfs, linespacing=1.4)

def arrow(p, q, color=DARK, rad=0.0, lw=2.2):
    ax.add_patch(FancyArrowPatch(p, q, arrowstyle="-|>", mutation_scale=16,
                 lw=lw, color=color, connectionstyle=f"arc3,rad={rad}"))

# ---- top row ----
box(0.034, 0.310, 0.745, 0.925, "#d9e8f5", "Published criteria",
    "MOHW notification Annex 4\n(tiered determination rules)\n+ professional-society cutoffs")
box(0.360, 0.600, 0.745, 0.925, "#fdeecd", "Programmatic generation",
    "Boundary-value analysis ·\nvalue-ladder construction\n(threshold ±1–3 units, fillers)")
box(0.712, 0.968, 0.745, 0.925, "#fbe3ec", "Dual verification",
    "Independent rule engine:\n100% label agreement;\n0/6,321 violations (neg. control)", bfs=10.5)

# ---- middle row ----
box(0.124, 0.372, 0.495, 0.685, "#e2efdc", "Tier-classification set",
    "v1.0 · 144 cases · 20 items\n77 boundary (32 inclusive-\nthreshold) · 67 representative", bfs=10.5)
box(0.415, 0.645, 0.495, 0.685, "#e2efdc", "Value-ladder set",
    "v1.3 · 528 cases · 22 ladders\n6,321 ordered pairs\n(direction-aware; BMI split)", bfs=10.5)
box(0.730, 0.968, 0.495, 0.685, "#fbe3ec", "Confound audit",
    "v1.1→v1.2: Hb upper tail\nv1.2→v1.3: uric-acid lower\ntail — identified & removed", bfs=10.5)

# ---- bottom row ----
box(0.124, 0.467, 0.225, 0.425, "#e8e2f4", "LLM evaluation",
    "Claude Fable 5 · GPT-5.6 Sol\nzero-shot vs rule-grounded\n10 runs / model / condition")
box(0.520, 0.968, 0.150, 0.425, "#fdf9df", "Outcomes",
    "Grounding effect — run-level exact rank test\nMonotonicity violations — label-independent\n"
    "Test–retest reliability — flip, agreement, Fleiss κ\nSafety-critical errors — Wilson upper bound\n"
    "Stratified reporting: BMI vs non-BMI", bfs=10.5)

# ---- arrows ----
arrow((0.312, 0.835), (0.358, 0.835))                              # criteria -> generation
arrow((0.602, 0.835), (0.710, 0.835))                              # generation -> verification
ax.text(0.656, 0.851, "verify\nall labels", ha="center", va="bottom",
        fontsize=9, style="italic", linespacing=1.2)
arrow((0.400, 0.742), (0.278, 0.691), rad=0.25)                    # generation -> tier set
arrow((0.545, 0.742), (0.538, 0.691))                              # generation -> ladder set
arrow((0.845, 0.742), (0.852, 0.691), color=PURPLE)                # verification -> audit
arrow((0.727, 0.590), (0.650, 0.590), color=PURPLE)                # audit -> ladder set
ax.text(0.688, 0.574, "revise &\nre-verify", ha="center", va="top",
        fontsize=9, style="italic", color=PURPLE, linespacing=1.2)
arrow((0.248, 0.492), (0.278, 0.429))                              # tier set -> LLM eval
arrow((0.520, 0.492), (0.400, 0.429), rad=0.25)                    # ladder set -> LLM eval
arrow((0.470, 0.325), (0.517, 0.305))                              # LLM eval -> outcomes

plt.savefig("figure1_pipeline.png", dpi=200)
plt.savefig("figure1_pipeline.pdf")
print("saved figure1_pipeline.png / .pdf")
