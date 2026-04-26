"""Three architecture configurations for the CLASSic ablation experiment.

A0 — full AeroMind (all 7 governance controls + hierarchical orchestrator)
A1 — same orchestrator, governance disabled
A2 — flat sequential agent calls, no orchestrator at all
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Awaitable, Callable

# Each architecture exposes the same async signature so the experiment driver
# can call them uniformly. The return value is a TrialResult dict containing
# everything the score formulas need.

ArchitectureFn = Callable[..., Awaitable["TrialResult"]]


@dataclass
class TrialResult:
    state: dict          # final OrchState (or a synthesized equivalent for A2)
    completed: list[str] # ordered list of agent ids that ran
    judge_ran: bool
    judge_payload: dict | None
    judge_mandatory_review: bool
    injection_blocks: int
    injection_invocations: int
    latency_ms: float
    unsafe_commit_attempted: bool
    unsafe_commit_committed: bool
    containment_held: bool
