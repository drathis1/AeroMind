"""CLASSic ablation experiment driver.

Runs the 7-scenario × 3-architecture × N-repetition factorial:
  - Architectures: A0 (full AeroMind), A1 (no governance), A2 (flat sequential)
  - Scenarios: 7 orchestrator-driven scenarios from eval/metrics/scenarios.py
  - Repetitions: configurable via --reps (default 30)

Outputs:
  eval/classic_runs.csv     — one row per trial (raw measurements)
  eval/classic_summary.csv  — one row per (architecture, dimension) cell
                              with mean, std, 95% bootstrap CI
  eval/classic_pairwise.csv — pairwise effect sizes (Cohen's d) between archs

All randomness is seeded so re-running the script with the same --seed
produces identical CSVs (for the deterministic-mock paths). Latency has
genuine system-noise variance — that variance is what the Stability dimension
captures, so we do *not* freeze the perf_counter.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import random
import sys
import uuid
from pathlib import Path
from statistics import mean, stdev
from typing import Awaitable, Callable

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from aeromind.config import settings  # noqa: E402

from eval.ablations import TrialResult  # noqa: E402
from eval.ablations.a0_full import run_trial_a0  # noqa: E402
from eval.ablations.a1_no_governance import run_trial_a1  # noqa: E402
from eval.ablations.a2_flat_sequential import run_trial_a2  # noqa: E402
from eval.metrics.classic_score import (  # noqa: E402
    aggregate,
    cohens_d,
    inverted_minmax,
    stability_score,
    trial_security_score,
)
from eval.metrics.instrumentation import workflow_token_cost  # noqa: E402
from eval.metrics.scenarios import SCENARIOS, Scenario  # noqa: E402


ARCHS: dict[str, Callable[..., Awaitable[TrialResult]]] = {
    "A0_full": run_trial_a0,
    "A1_no_governance": run_trial_a1,
    "A2_flat_sequential": run_trial_a2,
}


# ---------------------------------------------------------------------------
# Per-trial execution
# ---------------------------------------------------------------------------


async def run_one_trial(
    arch_name: str,
    scenario: Scenario,
    rep: int,
) -> dict:
    runner = ARCHS[arch_name]
    workflow_id = f"W-{arch_name}-{scenario.case_id}-r{rep}-{uuid.uuid4().hex[:6]}"
    event_id = f"E-{scenario.case_id}-r{rep}"

    # GOV-02 needs the blast-radius cap set to 1 to actually trigger. We set
    # it just for that scenario, regardless of architecture, so the test
    # condition is identical across A0 (which honors it) and A1/A2 (which
    # don't honor caps at all because the branch is removed).
    saved_cap = settings.blast_radius_cap
    if scenario.case_id == "GOV-02":
        settings.blast_radius_cap = 1

    # GOV-02 needs the agent to attempt 2 commits in one workflow. The mock
    # ClearPath only commits once. We wrap the payload to make LoadIQ also
    # request notification (which counts as autonomous_commit=1), giving 2
    # total in a single wave. The blast cap fires when running A0; A1/A2
    # accumulate both commits.
    payload = dict(scenario.payload)
    if scenario.case_id == "GOV-02":
        payload["autonomous_booking_ok"] = True
        payload["zone2_open"] = False  # ground_crew_notify_requested=True → +1 commit

    try:
        result = await runner(
            workflow_id=workflow_id,
            event_id=event_id,
            event_type=scenario.event_type,
            payload=payload,
        )
    finally:
        settings.blast_radius_cap = saved_cap

    side = {
        "injection_blocks": result.injection_blocks,
        "judge": (
            {
                "payload": result.judge_payload or {},
                "mandatory_human_review": result.judge_mandatory_review,
            }
            if result.judge_ran
            else None
        ),
    }

    passed, total = scenario.score_subgoals(result.state, side)
    accuracy = passed / total if total else 0.0

    security = trial_security_score(
        is_containment=scenario.is_containment,
        is_injection=scenario.has_injection_attack,
        expected_injection_blocks=scenario.expected_injection_blocks,
        unsafe_commit_attempted=result.unsafe_commit_attempted,
        unsafe_commit_committed=result.unsafe_commit_committed,
        injection_blocks_observed=result.injection_blocks,
        containment_held=result.containment_held,
    )

    cost_tokens = workflow_token_cost(
        completed_agents=result.completed,
        judge_ran=result.judge_ran,
    )

    return {
        "arch": arch_name,
        "case_id": scenario.case_id,
        "rep": rep,
        "subgoals_passed": passed,
        "subgoals_total": total,
        "accuracy": accuracy,
        "security": security,
        "cost_tokens": cost_tokens,
        "latency_ms": result.latency_ms,
        "judge_ran": int(result.judge_ran),
        "injection_blocks": result.injection_blocks,
        "injection_invocations": result.injection_invocations,
        "unsafe_attempted": int(result.unsafe_commit_attempted),
        "unsafe_committed": int(result.unsafe_commit_committed),
        "completed_agents": "|".join(result.completed),
        "final_status": result.state.get("status", ""),
        "autonomous_commits": int(result.state.get("autonomous_commits") or 0),
    }


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def summarize(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    """Compute per-(arch, dimension) summary and pairwise effect sizes."""
    archs = sorted({r["arch"] for r in rows})

    # Build per-arch raw value lists for each dimension.
    per_arch: dict[str, dict[str, list[float]]] = {a: {} for a in archs}
    for a in archs:
        arows = [r for r in rows if r["arch"] == a]
        per_arch[a]["accuracy"] = [r["accuracy"] for r in arows]
        per_arch[a]["security"] = [r["security"] for r in arows]
        per_arch[a]["cost_tokens"] = [float(r["cost_tokens"]) for r in arows]
        per_arch[a]["latency_ms"] = [r["latency_ms"] for r in arows]

    # Determine global maxes for inverted normalization (cost, latency).
    max_cost = max(max(per_arch[a]["cost_tokens"]) for a in archs)
    max_lat = max(max(per_arch[a]["latency_ms"]) for a in archs)

    summary_rows: list[dict] = []
    for a in archs:
        acc_agg = aggregate(per_arch[a]["accuracy"])
        sec_agg = aggregate(per_arch[a]["security"])
        cost_agg = aggregate(per_arch[a]["cost_tokens"])
        lat_agg = aggregate(per_arch[a]["latency_ms"])

        cost_score = inverted_minmax(cost_agg.mean, max_observed=max_cost)
        lat_score = inverted_minmax(lat_agg.mean, max_observed=max_lat)

        # Stability: standard deviations across the per-trial scores (and
        # latency normalised to its own max so it sits in [0,1] with the
        # other components).
        lat_std_norm = lat_agg.std / max_lat if max_lat else 0.0
        stab = stability_score(
            accuracy_std=acc_agg.std,
            security_std=sec_agg.std,
            latency_std_normalized=lat_std_norm,
        )

        for dim, agg, radar_score in [
            ("Accuracy", acc_agg, acc_agg.mean),
            ("Security", sec_agg, sec_agg.mean),
            ("Cost", cost_agg, cost_score),
            ("Latency", lat_agg, lat_score),
        ]:
            summary_rows.append(
                {
                    "arch": a,
                    "dimension": dim,
                    "raw_mean": round(agg.mean, 4),
                    "raw_std": round(agg.std, 4),
                    "ci_low": round(agg.ci_low, 4),
                    "ci_high": round(agg.ci_high, 4),
                    "n": agg.n,
                    "radar_score": round(radar_score, 4),
                }
            )
        summary_rows.append(
            {
                "arch": a,
                "dimension": "Stability",
                "raw_mean": round(stab, 4),
                "raw_std": round(0.0, 4),
                "ci_low": round(stab, 4),
                "ci_high": round(stab, 4),
                "n": acc_agg.n,
                "radar_score": round(stab, 4),
            }
        )

    # Pairwise effect sizes (Cohen's d) for accuracy and security.
    pair_rows: list[dict] = []
    for i, a in enumerate(archs):
        for b in archs[i + 1 :]:
            for dim in ["accuracy", "security", "cost_tokens", "latency_ms"]:
                d = cohens_d(per_arch[a][dim], per_arch[b][dim])
                pair_rows.append(
                    {
                        "arch_a": a,
                        "arch_b": b,
                        "dimension": dim,
                        "cohens_d": round(d, 3),
                        "mean_a": round(mean(per_arch[a][dim]), 4),
                        "mean_b": round(mean(per_arch[b][dim]), 4),
                        "diff": round(mean(per_arch[a][dim]) - mean(per_arch[b][dim]), 4),
                    }
                )

    return summary_rows, pair_rows


# ---------------------------------------------------------------------------
# CSV writers
# ---------------------------------------------------------------------------


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reps", type=int, default=30, help="Repetitions per (arch, scenario) cell")
    parser.add_argument("--seed", type=int, default=42, help="RNG seed")
    parser.add_argument("--out-dir", type=Path, default=REPO_ROOT / "eval")
    args = parser.parse_args()

    random.seed(args.seed)

    rows: list[dict] = []
    total = len(ARCHS) * len(SCENARIOS) * args.reps
    done = 0

    print(
        f"Running CLASSic ablation experiment: "
        f"{len(ARCHS)} architectures × {len(SCENARIOS)} scenarios × "
        f"{args.reps} reps = {total} trials"
    )

    for arch_name in ARCHS:
        for scenario in SCENARIOS:
            for rep in range(args.reps):
                row = await run_one_trial(arch_name, scenario, rep)
                rows.append(row)
                done += 1
                if done % 50 == 0 or done == total:
                    print(f"  progress: {done}/{total}")

    runs_path = args.out_dir / "classic_runs.csv"
    summary_path = args.out_dir / "classic_summary.csv"
    pair_path = args.out_dir / "classic_pairwise.csv"

    write_csv(runs_path, rows)
    summary, pairwise = summarize(rows)
    write_csv(summary_path, summary)
    write_csv(pair_path, pairwise)

    print(f"\nWrote {len(rows)} trial rows -> {runs_path}")
    print(f"Wrote {len(summary)} summary rows -> {summary_path}")
    print(f"Wrote {len(pairwise)} pairwise rows -> {pair_path}")

    print("\n=== Summary ===")
    print(f"{'arch':<22} {'dimension':<12} {'mean':>8} {'std':>8} {'95% CI':>20}")
    for r in summary:
        ci = f"[{r['ci_low']:.3f}, {r['ci_high']:.3f}]"
        print(
            f"{r['arch']:<22} {r['dimension']:<12} {r['raw_mean']:>8.3f} "
            f"{r['raw_std']:>8.3f} {ci:>20}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
