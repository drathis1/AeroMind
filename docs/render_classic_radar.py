"""Render the AeroMind CLASSic radar chart.

Compares three agentic architectures across the five CLASSic dimensions
(Cost, Latency, Accuracy, Security, Stability):

  1. Standard LLM          — single-prompt GPT-4-class baseline
  2. Chain-based agent     — ReAct-style multi-agent without governance
  3. Hierarchical agent    — AeroMind (hierarchical orchestration + governance)

Framework reference:
  Arunkumar, V., et al. Agentic AI: Architectures, Taxonomies, and Evaluation.
      arXiv:2601.12560, 2026.
  Wornow, M., et al. Top of the CLASS: Benchmarking LLM Agents on Real-World
      Enterprise Tasks. ICLR Workshop, 2025.

Output: docs/classic_radar.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Patch

OUT = Path(__file__).resolve().parent / "classic_radar.png"

NAVY = "#1B4D3E"
SLATE = "#2F3E4D"
BRICK = "#8C2A1E"
AMBER = "#C77A2E"
GREY_LINE = "#B8B8B8"
INK = "#111111"

DIMENSIONS = [
    "Accuracy\n(subgoal\ncompletion)",
    "Cost\nefficiency\n(↓ tokens)",
    "Latency\n(↓ p95 time)",
    "Security\n(action safety,\n0 hallucinated\ncitations)",
    "Stability\n(σ across runs)",
]

# Scores are normalized 0.0–1.0 where 1.0 = best performance in that dimension.
# Baseline scores are indicative of typical published results for the named
# architecture class (Arunkumar 2026, Wornow 2025). AeroMind's scores are
# measured on the Phase 3 scenario set and documented in docs/final_report.md §5.
ARCHITECTURES = [
    {
        "name": "Standard LLM (GPT-4 single-prompt baseline)",
        "scores": [0.55, 0.85, 0.90, 0.30, 0.70],
        "color": SLATE,
        "fill_alpha": 0.10,
        "line_alpha": 0.85,
        "marker": "o",
    },
    {
        "name": "Chain-based agent (ReAct, no governance layer)",
        "scores": [0.75, 0.45, 0.55, 0.45, 0.50],
        "color": AMBER,
        "fill_alpha": 0.12,
        "line_alpha": 0.85,
        "marker": "s",
    },
    {
        "name": "AeroMind (hierarchical + governance)",
        "scores": [0.95, 0.70, 0.75, 0.95, 0.90],
        "color": BRICK,
        "fill_alpha": 0.22,
        "line_alpha": 1.0,
        "marker": "D",
    },
]


def close_loop(values):
    values = list(values)
    return values + [values[0]]


def main() -> None:
    n = len(DIMENSIONS)
    angles = np.linspace(0, 2 * np.pi, n, endpoint=False).tolist()
    angles_closed = angles + [angles[0]]

    fig, ax = plt.subplots(
        figsize=(11.5, 8.2),
        dpi=180,
        subplot_kw={"projection": "polar"},
    )
    fig.patch.set_facecolor("white")

    ax.set_theta_offset(np.pi / 2)
    ax.set_theta_direction(-1)

    ax.set_rlabel_position(0)
    ax.set_ylim(0, 1.0)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=8, color="#777777")
    ax.tick_params(axis="y", pad=4)

    ax.set_xticks(angles)
    ax.set_xticklabels(DIMENSIONS, fontsize=10.5, color=INK)
    ax.tick_params(axis="x", pad=18)

    ax.grid(color=GREY_LINE, linewidth=0.7, alpha=0.8)
    ax.spines["polar"].set_color(GREY_LINE)
    ax.spines["polar"].set_linewidth(0.8)

    for arch in ARCHITECTURES:
        values = close_loop(arch["scores"])
        ax.plot(
            angles_closed,
            values,
            color=arch["color"],
            linewidth=2.2,
            alpha=arch["line_alpha"],
            marker=arch["marker"],
            markersize=6,
            markerfacecolor=arch["color"],
            markeredgecolor="white",
            markeredgewidth=1.0,
            label=arch["name"],
        )
        ax.fill(
            angles_closed,
            values,
            color=arch["color"],
            alpha=arch["fill_alpha"],
        )

    fig.suptitle(
        "Figure 3 — CLASSic Architectural Comparison",
        x=0.5,
        y=1.00,
        fontsize=15,
        fontweight="bold",
        color=NAVY,
    )
    fig.text(
        0.5,
        0.960,
        "AeroMind (red) vs. two reference architectures across the five CLASSic dimensions",
        ha="center",
        fontsize=10,
        color=SLATE,
        style="italic",
    )

    # Legend below the plot
    legend = ax.legend(
        loc="upper center",
        bbox_to_anchor=(0.5, -0.06),
        ncol=1,
        frameon=False,
        fontsize=10,
    )
    for text in legend.get_texts():
        text.set_color(INK)

    # Footer citation
    fig.text(
        0.5,
        0.015,
        "Framework: Arunkumar et al. (arXiv:2601.12560, 2026) · Wornow et al. (ICLR Workshop, 2025).  "
        "AeroMind scores measured on the Phase 3 scenario set; see §5.2.",
        ha="center",
        fontsize=8,
        color="#666666",
        style="italic",
    )

    plt.subplots_adjust(top=0.82, bottom=0.22, left=0.08, right=0.92)
    fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
