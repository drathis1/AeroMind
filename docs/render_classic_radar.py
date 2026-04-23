"""Render the CLASSic radar chart from the experimental results in
`eval/classic_summary.csv`.

This script is fully data-driven: it reads the measured radar_score column
for each (architecture, dimension) pair and plots them. There are no
hard-coded scores. To regenerate after re-running the experiment:

    python eval/run_classic_experiment.py --reps 30
    python docs/render_classic_radar.py
"""

from __future__ import annotations

import csv
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

REPO_ROOT = Path(__file__).resolve().parent.parent
SUMMARY_CSV = REPO_ROOT / "eval" / "classic_summary.csv"
OUTPUT_PNG = REPO_ROOT / "docs" / "classic_radar.png"

DIMENSIONS = ["Accuracy", "Cost", "Latency", "Security", "Stability"]

ARCH_DISPLAY = {
    "A0_full": ("AeroMind (A0 — full)", "#1f77b4", 2.5, 1.0),
    "A1_no_governance": ("A1 — Hierarchical, no governance", "#d62728", 1.8, 0.85),
    "A2_flat_sequential": ("A2 — Flat sequential, no governance", "#2ca02c", 1.5, 0.85),
}


def load_radar_scores(path: Path) -> dict[str, dict[str, float]]:
    out: dict[str, dict[str, float]] = {}
    with path.open() as f:
        for row in csv.DictReader(f):
            arch = row["arch"]
            dim = row["dimension"]
            score = float(row["radar_score"])
            out.setdefault(arch, {})[dim] = score
    return out


def plot_radar(scores: dict[str, dict[str, float]], out_path: Path) -> None:
    angles = np.linspace(0, 2 * np.pi, len(DIMENSIONS), endpoint=False).tolist()
    angles += angles[:1]

    fig, ax = plt.subplots(figsize=(9, 9), subplot_kw=dict(polar=True))

    for arch_key, (label, color, lw, alpha) in ARCH_DISPLAY.items():
        arch_scores = scores.get(arch_key)
        if not arch_scores:
            continue
        values = [arch_scores.get(d, 0.0) for d in DIMENSIONS]
        values += values[:1]
        ax.plot(angles, values, linewidth=lw, color=color, label=label, alpha=alpha)
        ax.fill(angles, values, color=color, alpha=0.10)

    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(DIMENSIONS, fontsize=14, fontweight="bold")

    ax.set_ylim(0, 1.05)
    ax.set_yticks([0.2, 0.4, 0.6, 0.8, 1.0])
    ax.set_yticklabels(["0.2", "0.4", "0.6", "0.8", "1.0"], fontsize=10, color="#555")
    ax.grid(color="#cccccc", linestyle=":", linewidth=0.7)
    ax.spines["polar"].set_color("#888888")

    plt.subplots_adjust(top=0.84, bottom=0.20)
    fig.suptitle(
        "AeroMind on the CLASSic framework",
        fontsize=18,
        fontweight="bold",
        y=0.99,
    )
    fig.text(
        0.5,
        0.945,
        "Measured ablation: 7 scenarios × 3 architectures × 30 repetitions = 630 trials",
        ha="center",
        fontsize=11,
        color="#444",
    )

    legend = ax.legend(
        loc="lower center",
        bbox_to_anchor=(0.5, -0.22),
        ncol=1,
        fontsize=11,
        frameon=True,
        edgecolor="#aaa",
    )
    for text in legend.get_texts():
        text.set_color("#222")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(out_path, dpi=180, bbox_inches="tight")
    print(f"Wrote radar chart -> {out_path}")


def main() -> int:
    if not SUMMARY_CSV.exists():
        print(
            f"ERROR: {SUMMARY_CSV} not found. Run "
            f"`python eval/run_classic_experiment.py --reps 30` first.",
            file=sys.stderr,
        )
        return 1
    scores = load_radar_scores(SUMMARY_CSV)
    plot_radar(scores, OUTPUT_PNG)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
