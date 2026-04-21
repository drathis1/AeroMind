# AeroMind — Phase 3 Final Report

**Course:** Agentic Systems Studio · Track A · Technical Build  
**Team:** Dhiksha Rathis, Sai Karthik, Smridhi Patwari, Tina Sibbal  
**Repository commit at submission:** `3922b685e28444ad9f019db446dfd5573b20947e`  
**Phase 3 date:** April 2026

> Export this file to PDF (e.g. `pandoc docs/final_report.md -o
> docs/final_report.pdf`) before submitting on Canvas. All referenced paths
> are relative to the repository root.

---

## 1. Problem and user

**Problem.** Air cargo operations center workflows are fragmented across three
systems that must all agree before a flight departs: load optimization,
disruption rerouting, and regulatory compliance. Industry data shows a 62.7%
on-time delivery rate and more than $11B in annual losses concentrated in
exactly these three coordination points. Manual processes take 2–4 hours for
load planning, 2–6 hours for disruption response, and catch only ~40% of
compliance errors.

**Target user.** A cargo operations manager at an international freight
forwarder who must approve reroutes, load plans, and compliance documents
under time pressure. Secondary user: the compliance officer who needs an
auditable trail for every autonomous decision.

**Why this is an agentic problem.** Each operational domain (load, route,
compliance) has its own tools, data, and failure modes, and the *dependencies
between them* are conditional — a new booking touches load + compliance but
not routing; a weather alert touches routing first and only *conditionally*
triggers load + compliance. A single-agent pipeline cannot express those
conditional dependencies without re-implementing an orchestrator inside
itself. See README §"Why Multi-Agent? Why Not Simpler?" for the long form.

---

## 2. Architecture and design choices

The system is a LangGraph-based orchestrator with three specialist agents,
a shared governance layer, and a FastAPI + optional UI surface.

**Architecture diagram:** [`docs/architecture_diagram.png`](./architecture_diagram.png)
(Mermaid source at [`docs/architecture_diagram.mmd`](./architecture_diagram.mmd)).

**Roles**

| Role | Inputs | Outputs | Allowlisted tools |
|---|---|---|---|
| LoadIQ | manifest, aircraft config, hazmat classes | placements, weight/balance report, hazmat flags | weight_balance, hazmat_rules, aircraft_db, booking_write |
| ClearPath | weather, NOTAM, shipper SLA | ranked reroute options, booking amend proposal, handoff flag | weather_api, notam_api, route_optimizer, booking_write |
| CargoComply | shipment record, regulatory RAG, documents | compliance status, missing-doc list, pre-filled forms | pgvector_rag, cbp_feed, sanctions_check, doc_templates |

**Coordination logic (who starts, how handoffs happen, stopping conditions)**

- **Entry:** an ingested event (`NEW_BOOKING`, `MANIFEST_CHANGE`,
  `WEATHER_ALERT`, `NOTAM_FLAG`, `REROUTE_CONFIRMED`) lands in
  `aeromind/orchestrator/graph.py`.
- **First wave:** `routing.first_agents_for_event` deterministically picks
  which agents activate (e.g. NEW_BOOKING → LoadIQ + CargoComply; WEATHER_ALERT
  → ClearPath only).
- **Two-phase handoff:** if ClearPath sets `handoff.reroute_complete=true`,
  the orchestrator dispatches LoadIQ + CargoComply in parallel — the key
  architectural differentiator captured in trace
  [`trace_E2E02_weather_disruption.json`](../traces/trace_E2E02_weather_disruption.json).
- **Stopping conditions:** `CLOSED_CLEAN` (all agents done, no
  governance trips), `AWAITING_HUMAN` (any agent raised
  `escalation_required`), `BLAST_RADIUS_CAP` (autonomous commit counter
  tripped).
- **Human-in-the-loop:** gates open via `AWAITING_HUMAN` are resolvable
  through `POST /v1/gates/resolve`.

**Tools, memory, state**

- **Shared state.** PostgreSQL 16 + pgvector. All agents read/write through
  the orchestrator, never directly to each other. Prevents race conditions
  and gives a single point of audit.
- **Memory.** Shared state is workflow-scoped. Between workflows, the audit
  log and pgvector RAG index are the only persistent stores.
- **Tool allowlist.** `aeromind/tools/registry.py` assigns each agent a
  hard-coded tool set. Cross-agent tool calls raise `PermissionError`.

**Why this architecture over a simpler one.** A single-agent monolith
cannot meet the departure-window constraint (load re-optimization + compliance
re-check must run in parallel after a confirmed reroute), and a linear
pipeline cannot express conditional fan-out (NEW_BOOKING vs MANIFEST_CHANGE
activate different subsets). The three activation patterns with shared
downstream state are exactly what an orchestrated multi-agent graph solves.

---

## 3. Implementation / build summary

- **Language & runtime.** Python 3.11+ (tested on 3.13.7); LangGraph ≥ 0.2.40.
- **Web.** FastAPI app at `aeromind/api/main.py`; in-memory demo pipeline under
  `aeromind/demo/` so reviewers can exercise the multi-agent timeline without
  Postgres.
- **Persistence.** PostgreSQL + pgvector via Docker Compose (`docker-compose.yml`).
- **Governance code.** DG lock and blast-radius cap in
  `aeromind/orchestrator/graph.py`; allowlist in
  `aeromind/tools/registry.py`; injection sanitizer in
  `aeromind/injection/filter.py`; audit hash chain in
  `aeromind/audit/chain.py`; LLM-as-judge in `aeromind/judge/worker.py`.
- **Testing.** `tests/` with async orchestrator tests,
  governance regression tests, and audit-chain tests.
- **Evidence scripts.** `eval/capture_traces.py` drives every scenario through
  the real orchestrator and writes JSON; `eval/render_screenshots.py` renders
  labeled PNGs into `docs/screenshots/`.

Reproduce (see README for the full version):

```bash
pip install -e ".[dev]"
PYTHONPATH=. python3 -m pytest tests/ -v | tee eval/pytest_phase3_run.txt
PYTHONPATH=. python3 eval/capture_traces.py
PYTHONPATH=. python3 -m uvicorn aeromind.api.main:app --host 127.0.0.1 --port 8765 &
PYTHONPATH=. python3 eval/render_screenshots.py
```

---

## 4. Evaluation setup

**Philosophy.** Test what can break the system, not what demos well. We
sampled eight scenarios from the 35-scenario matrix in
[`Evaluation plan.md`](../Evaluation%20plan.md), covering all six test
dimensions (end-to-end, governance, escalation, injection, LLM-as-judge,
audit).

**Environment.** See [`eval/version_notes.md`](../eval/version_notes.md).
All evidence was produced on macOS + Python 3.13.7, with pytest 9.0.2 +
pytest-asyncio 1.3.0. Runs are deterministic (agent mocks and heuristic
judge). The live-API screenshot used the in-memory demo pipeline.

**Test matrix (subset submitted for Phase 3 package)**

| case_id | dimension | source evidence |
|---|---|---|
| E2E-01 | end-to-end baseline | `traces/trace_E2E01_new_booking.json`, screenshot 02 |
| E2E-02 | two-phase handoff | `traces/trace_E2E02_weather_disruption.json`, screenshot 03 |
| GOV-01 | DG lock containment | `traces/trace_GOV01_dg_lock.json`, screenshot 04 |
| GOV-02 | blast-radius cap halt | `traces/trace_GOV02_blast_radius.json`, screenshot 05 |
| JDG-01 | judge ungrounded flag | `traces/trace_JDG01_ungrounded.json`, screenshot 06 |
| INJ-01 | prompt-injection filter | `traces/trace_INJ01_prompt_injection.json`, screenshot 07 |
| ESC-01 | human-gate escalation | `traces/trace_ESC01_human_gate.json`, screenshot 08 |
| AUD-02 | audit hash-chain tamper | `traces/trace_AUD02_hash_chain.json`, screenshot 09 |

**Measures.** Pass/fail, governance-violation count, audit-chain validity,
human-gate triggered, agents completed, blast_radius_halt. Latency and cost
are not in this submission (the evidence is produced from deterministic mocks;
Gemini latency/cost will be added when we run the live-LLM phase).

---

## 5. Results

**Headline:** 8 passing unit tests; 8 evaluation scenarios with matching JSON
traces and screenshots; two contained failure cases with observable
containment in the traces.

**Per-case result summary** (full machine-readable table in
[`eval/evaluation_results.csv`](../eval/evaluation_results.csv)):

| case_id | outcome | one-line result |
|---|---|---|
| E2E-01 | PASS | Status `CLOSED_CLEAN`; LoadIQ + CargoComply both complete |
| E2E-02 | PASS | Two-phase: ClearPath first, then LoadIQ + CargoComply parallel |
| GOV-01 | PASS (containment) | DG lock zeroed unsafe commit; `dg_lock_blocked_commit` in messages; booking write never executed |
| GOV-02 | PASS (containment) | Status `BLAST_RADIUS_CAP`; `blast_radius_halt=true`; follow-on agents never ran |
| JDG-01 | PASS | Judge flagged `ungrounded_compliance=true`, `mandatory_human_review=true` |
| INJ-01 | PASS | Blocklist / length / token-length payloads flagged; benign text passes unmodified |
| ESC-01 | PASS | Status `AWAITING_HUMAN`; `open_human_gate=true`; orchestrator does not advance |
| AUD-02 | PASS | Clean chain verified `(True, None)`; tampered row rejected with `broken at id=3` |

Screenshot index: [`docs/screenshots/screenshot_index.md`](./screenshots/screenshot_index.md).
Raw pytest output: [`eval/pytest_phase3_run.txt`](../eval/pytest_phase3_run.txt).

---

## 6. Failure analysis

Full narratives live in
[`eval/failure_analysis.md`](../eval/failure_analysis.md); summary here.

**FL-001 — DG lock blocked an unsafe autonomous reroute commit (screenshot 04).**
Trigger: DG shipment, reroute to new country, `dg_accepted=false`, ClearPath
attempts autonomous booking commit. Observed: `autonomous_commits` held at 0,
`dg_lock_blocked_commit` written to messages, booking_write never called.
Severity: High (safety). Iteration: added the regression test
`test_dg_lock_zeros_commit_when_not_accepted`; recorded the honest gap that
the current graph closes `CLOSED_CLEAN` instead of forcing `AWAITING_HUMAN`
in this path, and logged it as a next-step improvement.

**FL-002 — Blast-radius cap halted a runaway autonomous chain (screenshot 05).**
Trigger: `blast_radius_cap=1`, agents request a second autonomous commit.
Observed: `status=BLAST_RADIUS_CAP`, `blast_radius_halt=true`, only ClearPath
in `completed`. Severity: Medium (runaway automation). Iteration: regression
test `test_blast_radius_cap_second_wave`; boundary pair GOV-07 validates the
strict `>` operator.

**Cross-cutting takeaway.** Every failure in the Phase 3 package shows the
same pattern: an agent *proposed* an unsafe action and the orchestrator
refused to commit it. That is the Phase 1 contract — *agents propose, the
orchestrator commits* — and the traces are direct evidence the contract
holds.

---

## 7. Governance, trust, and responsible behavior

Five controls are exercised in the Phase 3 evidence package:

1. **DG lock** (`graph.py:119–127`) — FL-001 trace.
2. **Blast-radius cap** (`graph.py:130–145`) — FL-002 trace.
3. **Tool allowlist** (`registry.py`) —
   `tests/test_phase3_controls.py::test_allowlist_blocks_cargocomply_booking`.
4. **Prompt-injection sanitizer** (`filter.py`) — INJ-01 trace.
5. **Audit hash chain** (`chain.py`) — AUD-02 trace; clean chain verifies,
   tampered chain fails with `broken at id=3`.
6. **LLM-as-judge** (`worker.py`) — JDG-01 trace flags ungrounded compliance
   statements for mandatory human review.

**Trust posture.** Compliance claims without a retrieved source chunk never
pass autonomously; booking writes never happen outside of the tool registry;
every autonomous action is recorded in the SHA-256-chained audit log.

---

## 8. Lessons learned and future improvements

**Lessons learned**

- *Containment matters more than cleverness.* The strongest rubric evidence is
  not the happy-path run; it is the moment the orchestrator refuses to act.
- *Honesty beats polish.* We kept the GOV-01 gap (DG lock does not currently
  force `AWAITING_HUMAN`) in the write-up rather than restating Phase 2's
  more ambitious language.
- *Evaluation scripts are worth the same as tests.* `eval/capture_traces.py`
  and `eval/render_screenshots.py` let us regenerate every piece of evidence
  deterministically, which avoided a scramble at submission time.

**Future improvements** (prioritized)

1. Promote every DG-lock firing into an explicit `AWAITING_HUMAN` gate so a
   human acknowledges the suppressed commit before downstream autonomous
   actions continue.
2. Weighted blast-radius cap: a crew notification costs less than a booking
   amendment (noted as Known Limitation #5 in README).
3. Live-LLM evaluation pass: run E2E-01, E2E-02, JDG-05 with Gemini and
   report latency p50/p95 + token cost.
4. Stress + integration pass: `docker-compose up -d && pytest --integration`
   covering STRESS-01, STRESS-02, AUD-01 with live DB.
5. Graceful handling of malformed Gemini JSON (Known Limitation #6).

---

## Appendix A — where to find everything

- Code: `aeromind/` + `tests/`
- Evidence: `eval/`, `traces/`, `docs/screenshots/`
- Architecture: `docs/architecture_diagram.png` + `.mmd`
- Phase 2 detail: `Agentic Phase 2.docx`, `Evaluation plan.md`
- Individual reflections: `phase_submissions/phase3/reflections/`
- Submission packet PDF: `phase_submissions/phase3/submission_packet.pdf`
  (to be assembled at submission time)
- AI usage disclosure: `AI_USAGE.md`
- Video link (once recorded): `media/demo_video_link.txt`
