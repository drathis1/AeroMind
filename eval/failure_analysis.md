# Failure analysis — Phase 3

This document expands `eval/failure_log.md` with the required narrative. Both
failures are **containment events**: an unsafe or runaway autonomous action was
*attempted* by an agent and the orchestrator's governance layer *prevented it
from taking effect*. This is the core safety story of AeroMind.

Evidence files:

- `traces/trace_GOV01_dg_lock.json` — full orchestrator state dump
- `traces/trace_GOV02_blast_radius.json` — full orchestrator state dump
- `docs/screenshots/04_failure_GOV01_dg_lock.png` — screenshot summary
- `docs/screenshots/05_failure_GOV02_blast_radius.png` — screenshot summary
- `eval/pytest_phase3_run.txt` — regression tests backing both controls

---

## FL-001 — DG lock blocked an unsafe autonomous reroute commit

**Trigger.** A simulated `WEATHER_ALERT` event carrying a dangerous-goods
payload (`cargo_is_dg=true`, `reroute_new_country=true`, `dg_accepted=false`).
The ClearPath mock deliberately raised `booking_commit_requested=true` to
attempt an autonomous booking amendment.

**What happened (observed behavior).** The orchestrator's DG-lock guard in
`aeromind/orchestrator/graph.py` (lines 119–127) detected the unsafe combination
before the commit was persisted:

- `autonomous_commits` was held at **0** (zeroed, see
  `traces/trace_GOV01_dg_lock.json` line 83).
- The `messages` log recorded `dg_lock_blocked_commit` (line 86).
- No `booking_write` tool call was executed for ClearPath.
- The workflow still completed (`status=CLOSED_CLEAN`) because the downstream
  agents ran on the *proposed* plan, but the illegal external side-effect never
  happened.

**Why it happened.** This is the **intended governance behavior**. Production
rules in the project README make DG-to-new-country a Zone-3 situation that
requires explicit human DG acceptance. The orchestrator enforces that at the
commit boundary so no individual agent can route around it.

**Severity.** High (safety). In production this exact combination — dangerous
goods arriving in a country that has not confirmed DG acceptance — can lead to
cargo that cannot legally be offloaded.

**What changed after testing.**

- Regression test `tests/test_phase3_controls.py::test_dg_lock_zeros_commit_when_not_accepted`
  now captures this exact path; it is green in `eval/pytest_phase3_run.txt`.
- We added an explicit evidence trace (`traces/trace_GOV01_dg_lock.json`) and
  a screenshot-style evidence artifact so reviewers see both the *attempt* and
  the *containment* in one place.
- Observation: even though the DG lock correctly zeroed the commit, the
  workflow still closed `CLOSED_CLEAN` rather than being forced to
  `AWAITING_HUMAN`. This matches the implementation, but is softer than the
  language in the Phase-2 plan. Next-step improvement — raise an
  `AWAITING_HUMAN` gate whenever the DG lock fires, so a human explicitly
  acknowledges the suppressed commit before downstream autonomous actions
  continue.

**Residual risk.** A future code path that writes bookings outside of the
orchestrator's commit counter would bypass the DG lock. Mitigation: keep every
booking mutation behind the tool registry's `booking_write` allowlist (see
`registry.py`).

---

## FL-002 — Blast-radius cap halted a runaway autonomous chain

**Trigger.** A `NOTAM_FLAG` event with the global blast-radius cap lowered to
**1** via `config.settings.blast_radius_cap`. The ClearPath mock requested a
booking commit, and downstream agents were wired to request more commits
beyond the cap.

**What happened (observed behavior).** After ClearPath's single commit
(`autonomous_commits=1`, at cap), the orchestrator halted the workflow before
any follow-on commit ran:

- `status = "BLAST_RADIUS_CAP"` (see `traces/trace_GOV02_blast_radius.json`
  line 44).
- `blast_radius_halt = true` (line 43).
- `completed = ["CLEARPATH"]` only — LoadIQ and CargoComply were *not*
  scheduled.
- `messages` includes `blast_radius_cap` as the final marker.

**Why it happened.** The cap logic in `graph.py` (lines 130–145) uses a strict
`>` comparison against `autonomous_commits`, so once the cap is reached the
**next** requested commit terminates the graph. Boundary pair GOV-07 in the
Phase-2 evaluation plan confirms that *exactly* at cap the workflow passes, and
*cap + 1* halts — both sides of the boundary validated.

**Severity.** Medium (runaway-automation containment). Without this cap, a
misbehaving agent or corrupted LLM output could chain many autonomous writes.
This is not a user-facing safety incident on its own, but it is the main
defense against compounding small mistakes into a large one.

**What changed after testing.**

- Regression test
  `tests/test_phase3_controls.py::test_blast_radius_cap_second_wave`
  covers the halt path and is green in `eval/pytest_phase3_run.txt`.
- Trace `traces/trace_GOV02_blast_radius.json` captures the halting state so a
  reviewer can see that **no follow-on agent ran** after the cap tripped.
- Known limitation carried into the Phase-3 report: the cap is a *blunt*
  instrument — it counts every commit equally. A weighted version (notify ≠
  booking amendment) is listed under "Known Limitations" in the README.

**Residual risk.** If the cap is misconfigured (set very high), the safety net
weakens. Mitigation: the default is 15, and the value is surfaced via
`GET /v1/governance/metrics` so operators can audit it.

---

## Cross-cutting takeaway

Both failure cases show the same pattern: an agent *proposed* an unsafe action,
and the orchestrator refused to let it take effect. That is the contract we
promised in Phase 1 — *agents propose, the orchestrator commits* — and both
tests and traces are evidence that the contract holds.
