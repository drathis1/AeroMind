"""Render the AeroMind two-phase handoff sequence diagram as a clean PNG.

Output: docs/sequence_diagram.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

OUT = Path(__file__).resolve().parent / "sequence_diagram.png"

NAVY = "#1B4D3E"
SLATE = "#2F3E4D"
SAND = "#F4E8D1"
BRICK = "#8C2A1E"
AMBER = "#C77A2E"
TEAL = "#2F8F8F"
INK = "#111111"
GREY = "#888888"

ACTORS = [
    ("Event\n(WEATHER_ALERT)", "#EAF4F2", SLATE),
    ("Orchestrator\n(LangGraph)", "#E4EFEA", NAVY),
    ("ClearPath", "#E6F1F1", TEAL),
    ("LoadIQ", "#E6F1F1", TEAL),
    ("CargoComply", "#E6F1F1", TEAL),
    ("Shared state\n(DB + audit)", "#FBEFD8", AMBER),
]


def actor_header(ax, x, y, w, h, text, face, edge):
    ax.add_patch(
        FancyBboxPatch(
            (x - w / 2, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.1",
            linewidth=1.4,
            edgecolor=edge,
            facecolor=face,
        )
    )
    ax.text(
        x,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=10,
        color=INK,
        fontweight="bold",
    )


def lifeline(ax, x, top, bottom):
    ax.plot([x, x], [top, bottom], color=GREY, lw=1.0, ls=(0, (4, 3)))


def message(ax, x0, x1, y, label, *, color=SLATE, style="-|>", dashed=False, note=None):
    ls = "--" if dashed else "-"
    ap = FancyArrowPatch(
        (x0, y),
        (x1, y),
        arrowstyle=style,
        mutation_scale=12,
        color=color,
        linewidth=1.5,
        linestyle=ls,
    )
    ax.add_patch(ap)
    mid = (x0 + x1) / 2
    ax.text(mid, y + 0.12, label, ha="center", va="bottom", fontsize=9, color=color)
    if note:
        ax.text(mid, y - 0.18, note, ha="center", va="top", fontsize=7.5, color=GREY, style="italic")


def self_message(ax, x, y, label, *, color=TEAL):
    w = 0.45
    ap = FancyArrowPatch(
        (x, y),
        (x, y - 0.35),
        connectionstyle=f"arc3,rad=-1.3",
        arrowstyle="-|>",
        mutation_scale=10,
        color=color,
        linewidth=1.3,
    )
    ax.add_patch(ap)
    ax.text(x + 0.35, y - 0.18, label, ha="left", va="center", fontsize=9, color=color)


def phase_band(ax, x0, x1, y0, y1, label, color, *, label_y=None):
    ax.add_patch(
        mpatches.Rectangle(
            (x0, y0),
            x1 - x0,
            y1 - y0,
            linewidth=0,
            facecolor=color,
            alpha=0.08,
        )
    )
    # Phase label is placed just ABOVE the band in the gap between bands
    # so it cannot overlap any arrow or lifeline.
    tab_y = (label_y if label_y is not None else y1) + 0.02
    # Small colored stripe on the left as a visual anchor.
    ax.add_patch(
        mpatches.Rectangle(
            (x0 + 0.05, tab_y + 0.05),
            0.25,
            0.18,
            linewidth=0,
            facecolor=color,
        )
    )
    ax.text(
        x0 + 0.40,
        tab_y + 0.14,
        label,
        ha="left",
        va="center",
        fontsize=9.2,
        color=color,
        fontweight="bold",
    )


def step(ax, x, y, n):
    ax.add_patch(
        mpatches.Circle((x, y), 0.13, facecolor=NAVY, edgecolor="white", linewidth=1.2, zorder=5)
    )
    ax.text(x, y, str(n), ha="center", va="center", fontsize=8, color="white", fontweight="bold", zorder=6)


def main() -> None:
    fig, ax = plt.subplots(figsize=(14, 8.5), dpi=180)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(
        7,
        9.7,
        "Figure 2 — Two-phase handoff for a WEATHER_ALERT event",
        ha="center",
        fontsize=14,
        fontweight="bold",
        color=NAVY,
    )
    ax.text(
        7,
        9.35,
        "Phase 1: ClearPath runs alone.   Phase 2: LoadIQ + CargoComply run in parallel once reroute_complete=true is observed.",
        ha="center",
        fontsize=9.5,
        color=SLATE,
    )

    xs = [1.3, 3.5, 5.7, 8.0, 10.2, 12.6]
    header_y = 8.55
    header_h = 0.55
    life_top = header_y
    life_bottom = 0.55

    for x, (text, face, edge) in zip(xs, ACTORS):
        actor_header(ax, x, header_y, 1.9, header_h, text, face, edge)
        lifeline(ax, x, life_top, life_bottom)

    phase_band(ax, 0.2, 13.8, 6.00, 8.10, "Phase 1 — first_agents_for_event → ClearPath", NAVY)
    phase_band(ax, 0.2, 13.8, 2.75, 5.85, "Phase 2 — followon_after_clearpath → LoadIQ ∥ CargoComply", TEAL)
    phase_band(ax, 0.2, 13.8, 0.45, 2.60, "Closeout — orchestrator commits + audit chain verification", AMBER)

    step_x = 0.35

    y = 7.55
    step(ax, step_x, y, 1)
    message(ax, xs[0], xs[1], y, "WEATHER_ALERT  (FRA–JFK, value $48K, non-DG)", color=SLATE)

    y = 7.05
    step(ax, step_x, y, 2)
    message(ax, xs[1], xs[2], y, "dispatch(ClearPath)", color=NAVY, note="routing.first_agents_for_event()")

    y = 6.55
    step(ax, step_x, y, 3)
    self_message(ax, xs[2], y, "sanitize NOTAM · rank reroute options · select r1", color=TEAL)

    y = 6.15
    step(ax, step_x, y, 4)
    message(ax, xs[2], xs[5], y, "booking_write · reroute_complete = true", color=TEAL)

    y = 5.40
    step(ax, step_x, y, 5)
    message(ax, xs[5], xs[1], y, "flag observed", color=AMBER, dashed=True, note="graph.py: two-phase gate")

    y = 4.80
    step(ax, step_x, y, 6)
    message(ax, xs[1], xs[3], y, "dispatch(LoadIQ)", color=NAVY, note="followon_after_clearpath()")

    y = 4.20
    step(ax, step_x, y, 7)
    message(ax, xs[1], xs[4], y, "dispatch(CargoComply) — parallel", color=NAVY)

    y = 3.60
    step(ax, step_x, y, 8)
    message(ax, xs[3], xs[5], y, "W&B pass · hazmat none · crew-notify QUEUED", color=TEAL, dashed=True)

    y = 3.00
    step(ax, step_x, y, 9)
    message(ax, xs[4], xs[5], y, "compliance PASS · grounded · 0 missing docs", color=TEAL, dashed=True)

    y = 2.15
    step(ax, step_x, y, 10)
    message(ax, xs[5], xs[1], y, "2 autonomous commits written · hash-chain extended", color=AMBER, dashed=True)

    y = 1.55
    step(ax, step_x, y, 11)
    message(ax, xs[1], xs[0], y, "CLOSED_CLEAN · audit chain valid · 0 escalations", color=NAVY)

    ax.text(
        7,
        0.75,
        "Captured verbatim in traces/trace_E2E02_weather_disruption.json",
        ha="center",
        fontsize=9,
        color=GREY,
        style="italic",
    )

    legend = [
        mpatches.Patch(facecolor=NAVY, edgecolor=NAVY, label="Orchestrator message"),
        mpatches.Patch(facecolor=TEAL, edgecolor=TEAL, label="Agent work / state write"),
        mpatches.Patch(facecolor=AMBER, edgecolor=AMBER, label="State / audit response"),
        mpatches.Patch(facecolor=SLATE, edgecolor=SLATE, label="External event"),
    ]
    ax.legend(
        handles=legend,
        loc="lower center",
        bbox_to_anchor=(0.5, -0.04),
        ncol=4,
        frameon=False,
        fontsize=9,
    )

    plt.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
