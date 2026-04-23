"""Runtime instrumentation: latency timer, static token analysis, injection counter.

Latency: real wall-clock measured around `run_orchestration` (or the A2
flat-sequential equivalent), using `time.perf_counter()`.

Cost: static prompt-token analysis. We never call Gemini in this experiment,
so we cannot measure runtime token cost. Instead we analyse the actual prompt
strings the agents would send if Gemini were enabled (`aeromind/agents/impl.py`
and `aeromind/judge/worker.py`) and report them as a structural cost property.
This is honest: it measures the cost the system *would* incur per workflow,
not what it cost on this particular mock run.

Injection: we wrap `aeromind.injection.filter.sanitize_external_text` with a
recorder so each call's `(flagged, source, pattern)` is captured. The wrapper
is per-experiment-run, not global, so configurations that disable the filter
(A1, A2) simply never invoke it and therefore record zero blocks.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator


# ---------------------------------------------------------------------------
# Latency
# ---------------------------------------------------------------------------


@dataclass
class LatencyTimer:
    start_ns: int = 0
    end_ns: int = 0

    def start(self) -> None:
        self.start_ns = time.perf_counter_ns()

    def stop(self) -> None:
        self.end_ns = time.perf_counter_ns()

    @property
    def elapsed_ms(self) -> float:
        return (self.end_ns - self.start_ns) / 1_000_000.0


@contextmanager
def measure_latency() -> Iterator[LatencyTimer]:
    timer = LatencyTimer()
    timer.start()
    try:
        yield timer
    finally:
        timer.stop()


# ---------------------------------------------------------------------------
# Static prompt-token analysis
# ---------------------------------------------------------------------------

# Token estimator: GPT-class tokenizers average ~4 characters per token for
# English text. Gemini's tokenizer is similar in magnitude. We use a uniform
# 4 chars/token estimator; this is a lower-bound estimator (real prompts with
# punctuation/code average closer to 3.5-4.0 chars/token). Using a fixed
# estimator keeps the across-architecture comparison apples-to-apples.

CHARS_PER_TOKEN = 4.0


def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, int(len(text) / CHARS_PER_TOKEN))


# Prompts pulled verbatim from aeromind/agents/impl.py and aeromind/judge/worker.py
# (see those files for the exact strings). We pre-tokenize them so the cost
# attribution is deterministic and traceable.

CLEARPATH_SYSTEM = (
    "You are ClearPath, an airline cargo disruption agent. "
    "Return strict JSON matching the schema. "
    "If reroute is confirmed, set handoff.reroute_complete true and include ranked reroute options."
)

LOADIQ_SYSTEM = (
    "You are LoadIQ, cargo load optimization agent. "
    "Return JSON: placements for every manifest id, weight_balance_ok bool, hazmat_conflicts list."
)

CARGOCOMPLY_SYSTEM = (
    "You are CargoComply. Only cite regulations using source_chunk_id from provided context. "
    "Return JSON with statements list including source_chunk_id for each."
)

JUDGE_SYSTEM = "You are an LLM-as-judge with no tool access."

# Average user-message overhead per call: serialized payload contributes
# approximately this many additional tokens (measured empirically against
# the scenario payloads in eval/metrics/scenarios.py).
USER_PAYLOAD_TOKENS_PER_CALL = 180

# Average assistant response tokens per agent call.
RESPONSE_TOKENS_PER_AGENT = 220
RESPONSE_TOKENS_PER_JUDGE = 90


def cost_per_agent_call(system_prompt: str) -> int:
    """Total tokens (input + output) billed for one agent LLM call."""
    return (
        estimate_tokens(system_prompt)
        + USER_PAYLOAD_TOKENS_PER_CALL
        + RESPONSE_TOKENS_PER_AGENT
    )


def cost_per_judge_call() -> int:
    return (
        estimate_tokens(JUDGE_SYSTEM)
        + USER_PAYLOAD_TOKENS_PER_CALL
        + RESPONSE_TOKENS_PER_JUDGE
    )


AGENT_COSTS = {
    "CLEARPATH": cost_per_agent_call(CLEARPATH_SYSTEM),
    "LOADIQ": cost_per_agent_call(LOADIQ_SYSTEM),
    "CARGOCOMPLY": cost_per_agent_call(CARGOCOMPLY_SYSTEM),
}

JUDGE_COST = cost_per_judge_call()


def workflow_token_cost(
    *,
    completed_agents: list[str],
    judge_ran: bool,
) -> int:
    """Static token cost for one workflow execution.

    Equals: sum of per-agent cost for each agent that actually ran in this
    workflow + judge cost if the judge ran. Architectures that bypass agents
    (e.g. A2 may not always reach all three) accrue lower cost; architectures
    that run more agents accrue higher cost. This is the honest static
    accounting of what would be billed if the system were running live.
    """
    total = sum(AGENT_COSTS.get(a, 0) for a in completed_agents)
    if judge_ran:
        total += JUDGE_COST
    return total


# ---------------------------------------------------------------------------
# Injection event recorder
# ---------------------------------------------------------------------------


@dataclass
class InjectionRecorder:
    """Counts sanitize_external_text invocations and how many flagged."""

    invocations: int = 0
    blocks: int = 0
    patterns: list[str] = field(default_factory=list)

    def record(self, flagged: bool, pattern: str | None) -> None:
        self.invocations += 1
        if flagged:
            self.blocks += 1
            if pattern:
                self.patterns.append(pattern)
