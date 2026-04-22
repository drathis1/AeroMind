# AI transcript excerpts — AeroMind Phase 3

This file holds representative Claude / Cursor prompt + response excerpts
referenced by [`../../AI_USAGE.md`](../../AI_USAGE.md). Complete session
transcripts are retained by each team member locally.

> These excerpts are **paraphrased / condensed** for readability. The full
> unedited transcripts are available on request.

---

## Excerpt 1 — Orchestrator skeleton

**Team member:** Dhiksha
**Tool:** Cursor (agent mode, backed by Claude)
**Goal:** First draft of `aeromind/orchestrator/graph.py`.

**Prompt (paraphrased):**
> Write a LangGraph `StateGraph` named `orchestrator_node` that:
> 1. Reads the event type and payload from state.
> 2. On the first tick, calls `first_agents_for_event` and puts the returned
>    agent IDs into `pending`.
> 3. On each tick, runs one wave of pending agents concurrently via
>    `run_agent_tick`, then applies the DG lock and blast-radius-cap
>    guards.
> 4. Returns `CLOSED_CLEAN`, `AWAITING_HUMAN`, or `BLAST_RADIUS_CAP`.

**What we changed manually:**
- Hardened the DG-lock block so it zeroes `meta["autonomous_commit"]`
  rather than raising.
- Changed the blast-radius comparator to a strict `>` so the boundary pair
  GOV-02 vs GOV-07 behaves correctly.
- Added the explicit `EventType.WEATHER_ALERT` follow-on branch that
  dispatches `LoadIQ + CargoComply` when ClearPath sets
  `handoff.reroute_complete=true`.

---

## Excerpt 2 — Audit hash chain

**Team member:** Tina
**Tool:** Claude.ai chat
**Goal:** SHA-256 chain with tamper detection.

**Prompt (paraphrased):**
> Write a Python module with `hash_entry(...)` and
> `verify_chain(rows)`. `hash_entry` must canonicalize the dict with sorted
> keys and compact separators before hashing. `verify_chain` must return
> `(True, None)` on a clean chain and `(False, "broken at id=<n>")` on any
> mismatch, including the empty-list case vacuously returning `(True, None)`.

**What we changed manually:**
- Added the `_canonical_json` helper and the explicit `separators=(",",":")`
  argument so Python's dict ordering across versions does not silently
  break hashes.
- Wrote the three unit tests (`test_hash_chain_verifies`,
  `test_tamper_detected`, and the empty-list edge case in
  `tests/test_audit_chain.py`).

---

## Excerpt 3 — Prompt-injection filter

**Team member:** Smridhi
**Tool:** Cursor (inline edit)
**Goal:** `aeromind/injection/filter.py`.

**Prompt (paraphrased):**
> Write a `sanitize_external_text(text, source)` that returns an
> `InjectionReport(flagged, redacted_text, pattern)` after checking a
> regex blocklist, a length cap (8,000 chars), and an anomalous-token
> heuristic (any whitespace-separated token longer than 120 chars).

**What we changed manually:**
- Tuned the blocklist patterns after running INJ-01 through INJ-05.
  Earlier drafts included `"override"` as a pattern, which fired false
  positives on legitimate NOTAM text ("override crew request"). Removed.
- Confirmed the 120-char token threshold does not redact normal airport
  codes or flight numbers.

---

## Excerpt 4 — Failure analysis prose

**Team member:** Sai
**Tool:** Claude.ai chat
**Goal:** First draft of `eval/failure_analysis.md`.

**Prompt (paraphrased):**
> I will paste the JSON from `traces/trace_GOV01_dg_lock.json` and
> `traces/trace_GOV02_blast_radius.json`. Write two failure-analysis
> sections, one per file, matching the structure: trigger, observed
> behavior, why it happened, severity, what changed after testing,
> residual risk.

**What we changed manually:**
- The AI's first draft said FL-001 ended in `AWAITING_HUMAN`. We checked
  the trace and saw the actual status was `CLOSED_CLEAN`. Rewrote the
  section to reflect the real behavior and added the "promote DG-lock
  firings into an explicit `AWAITING_HUMAN` gate" next-step under
  "Future improvements" in `docs/final_report.md`.
- The AI's severity labels were too alarmist ("Critical" for both); we
  retitled them to "High (safety)" and "Medium (runaway-automation
  containment)" to match the Phase-2 language.

---

## Excerpt 5 — Next.js demo UI scaffold

**Team member:** Smridhi
**Tool:** Cursor (agent mode)
**Goal:** Polished ops dashboard that talks to the FastAPI demo
endpoints.

**Prompt (paraphrased):**
> Create a Next.js 14 app-router dashboard under `web/` with a dark slate
> theme. Pages: `/dashboard` (stats + workflow list, 5s polling),
> `/orders/[id]` (agent timeline, shared state, escalation card). All data
> via `/api/demo/*`; use `next.config.js` to proxy to FastAPI on :8000.

**What we changed manually:**
- Rewrote `components/EscalationCard.tsx` so human-attention-needed workflows
  are the visually dominant element (full-width amber card, large CTA).
- Added the "AI decided" label on autonomous actions so ops users can
  distinguish agent commits from human ones at a glance.
- Replaced jargon codes (e.g. `DG_LOCK_BREACH`) with plain-English strings.

---

## Pattern across all excerpts

Every AI draft went through the same three steps before it shipped:

1. **Run it.** A module that would not execute or whose tests did not pass
   was discarded.
2. **Read it against the Phase-1 contract.** If the draft violated
   *"agents propose, the orchestrator commits"* (for example by letting
   an agent directly call another agent), it was rewritten.
3. **Back it with a test.** Every governance claim in the final report
   points to a regression test in `tests/` that is green in
   `eval/pytest_phase3_run.txt`.
