"""Render a clean AeroMind architecture diagram as PNG using matplotlib.

Output: docs/architecture_diagram.png
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch

OUT = Path(__file__).resolve().parent / "architecture_diagram.png"

NAVY = "#1B4D3E"
SLATE = "#2F3E4D"
SAND = "#F4E8D1"
BRICK = "#8C2A1E"
AMBER = "#C77A2E"
TEAL = "#2F8F8F"
INK = "#111111"


def box(ax, x, y, w, h, text, *, face=SAND, edge=SLATE, text_color=INK, fontsize=10, weight="normal"):
    rect = mpatches.FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=0.15",
        linewidth=1.4,
        edgecolor=edge,
        facecolor=face,
    )
    ax.add_patch(rect)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=text_color,
        fontweight=weight,
        wrap=True,
    )


def band(ax, x, y, w, h, label, *, color):
    ax.add_patch(
        mpatches.FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.2",
            linewidth=1.0,
            edgecolor=color,
            facecolor="white",
            alpha=0.0,
        )
    )
    ax.text(
        x + 0.15,
        y + h - 0.28,
        label,
        ha="left",
        va="top",
        fontsize=10,
        color=color,
        fontweight="bold",
    )


def arrow(ax, x0, y0, x1, y1, *, color=SLATE, style="-|>", label=None, lw=1.3, ls="-"):
    ap = FancyArrowPatch(
        (x0, y0),
        (x1, y1),
        arrowstyle=style,
        mutation_scale=14,
        color=color,
        linewidth=lw,
        linestyle=ls,
    )
    ax.add_patch(ap)
    if label:
        ax.text((x0 + x1) / 2, (y0 + y1) / 2 + 0.08, label, ha="center", fontsize=8, color=color)


def main() -> None:
    fig, ax = plt.subplots(figsize=(13.5, 9.2), dpi=180)
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    ax.text(
        7,
        9.65,
        "AeroMind — Multi-Agent Air Cargo Orchestration",
        ha="center",
        fontsize=16,
        fontweight="bold",
        color=NAVY,
    )
    ax.text(
        7,
        9.3,
        "Track A · Phase 3 · LangGraph orchestrator + three specialist agents + governance layer",
        ha="center",
        fontsize=10,
        color=SLATE,
    )

    band(ax, 0.2, 7.7, 13.6, 1.3, "Layer 1 · Event ingestion (untrusted external feeds)", color=SLATE)
    box(ax, 0.6, 8.0, 3.8, 0.8, "Weather / NOTAM feeds", face="#EAF4F2", edge=SLATE)
    box(ax, 5.1, 8.0, 3.8, 0.8, "Airline booking events", face="#EAF4F2", edge=SLATE)
    box(ax, 9.6, 8.0, 3.8, 0.8, "Shipper notes / customs", face="#EAF4F2", edge=SLATE)

    band(ax, 0.2, 5.3, 13.6, 2.2, "Layer 2 · Orchestrator + Governance", color=NAVY)
    box(
        ax,
        0.8,
        5.9,
        6.0,
        1.3,
        "Event router (LangGraph)\n• routing.first_agents_for_event\n• two-phase handoff on reroute_complete\n• stopping conditions + escalation routing",
        face="#E4EFEA",
        edge=NAVY,
        fontsize=9.5,
    )
    box(
        ax,
        7.1,
        5.9,
        6.1,
        1.3,
        "Governance layer\n• DG lock (graph.py:119–127)\n• Blast-radius cap (graph.py:130–145)\n• Tool allowlist (registry.py)\n• Injection filter (filter.py)\n• Audit hash chain (chain.py)",
        face="#FFF0E0",
        edge=BRICK,
        fontsize=9.5,
    )

    band(ax, 0.2, 2.9, 13.6, 2.2, "Layer 3 · Agents (propose only; commits gated by Layer 2)", color=TEAL)
    box(
        ax,
        0.8,
        3.2,
        4.0,
        1.5,
        "LoadIQ\nLoad optimization\n• ULD placements\n• weight/balance\n• hazmat rules",
        face="#E6F1F1",
        edge=TEAL,
        fontsize=9.5,
    )
    box(
        ax,
        5.0,
        3.2,
        4.0,
        1.5,
        "ClearPath\nDisruption rerouting\n• ranked reroute options\n• weather / NOTAM analysis\n• booking amend proposal",
        face="#E6F1F1",
        edge=TEAL,
        fontsize=9.5,
    )
    box(
        ax,
        9.2,
        3.2,
        4.0,
        1.5,
        "CargoComply\nRegulatory compliance\n• pgvector RAG retrieval\n• sanctions screening\n• document generation",
        face="#E6F1F1",
        edge=TEAL,
        fontsize=9.5,
    )

    band(ax, 0.2, 0.4, 13.6, 2.3, "Layer 4 · Shared state + evidence + human", color=AMBER)
    box(ax, 0.8, 1.1, 3.2, 1.2, "PostgreSQL\n+ pgvector (RAG)", face="#FBEFD8", edge=AMBER, fontsize=9.5)
    box(
        ax,
        4.3,
        1.1,
        3.2,
        1.2,
        "LLM-as-judge\nheuristic + Gemini\n→ mandatory_human_review",
        face="#FBEFD8",
        edge=AMBER,
        fontsize=9.5,
    )
    box(ax, 7.8, 1.1, 2.6, 1.2, "Audit log\n(SHA-256 chain)", face="#FBEFD8", edge=AMBER, fontsize=9.5)
    box(
        ax,
        10.7,
        1.1,
        2.5,
        1.2,
        "FastAPI + Ops UI\n/v1/gates/resolve\n/v1/governance/*",
        face="#FBEFD8",
        edge=AMBER,
        fontsize=9.5,
    )

    arrow(ax, 2.5, 8.0, 3.8, 7.25)
    arrow(ax, 7.0, 8.0, 7.0, 7.25)
    arrow(ax, 11.5, 8.0, 10.2, 7.25)

    arrow(ax, 3.8, 5.9, 2.8, 4.7, label="NEW_BOOKING / MANIFEST_CHANGE")
    arrow(ax, 4.6, 5.9, 7.0, 4.7, label="WEATHER / NOTAM")
    arrow(ax, 5.2, 5.9, 11.2, 4.7, label="NEW_BOOKING w/ DG or cargo_type_changed")

    arrow(
        ax,
        7.0,
        3.2,
        4.8,
        5.9,
        color=TEAL,
        ls="--",
        label="reroute_complete → follow-on wave",
    )

    arrow(ax, 2.8, 3.2, 2.4, 2.3, color=BRICK)
    arrow(ax, 7.0, 3.2, 5.9, 2.3, color=BRICK)
    arrow(ax, 11.2, 3.2, 9.1, 2.3, color=BRICK)

    arrow(ax, 12.0, 5.9, 12.0, 2.3, color=AMBER, ls=":", label="escalation →\nhuman gate")
    arrow(ax, 12.0, 1.1, 6.0, 5.9, color=AMBER, ls=":", label="resolve gate → resume")

    legend = [
        mpatches.Patch(facecolor="#E4EFEA", edgecolor=NAVY, label="Orchestrator"),
        mpatches.Patch(facecolor="#FFF0E0", edgecolor=BRICK, label="Governance controls"),
        mpatches.Patch(facecolor="#E6F1F1", edgecolor=TEAL, label="Agents"),
        mpatches.Patch(facecolor="#FBEFD8", edgecolor=AMBER, label="Shared state & human"),
    ]
    ax.legend(handles=legend, loc="lower left", bbox_to_anchor=(0.0, -0.02), ncol=4, frameon=False, fontsize=9)

    plt.tight_layout()
    fig.savefig(OUT, dpi=200, bbox_inches="tight", facecolor="white")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
