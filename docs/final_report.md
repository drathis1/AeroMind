# AeroMind — Phase 3 Final Report

**The AI Operations Brain for Air Cargo · Track A: Technical Build**

| Field | Value |
|---|---|
| Course | Agentic Systems Studio · Phase 3 — Final Product, Evidence, and Reflection |
| Submission date | April 2026 |
| Repository | `https://github.com/drathis1/AeroMind` |
| Submission tag | `v1.0-phase3-submission` (branch `main`) |

| Team member | Phase 3 area of ownership |
|---|---|
| Dhiksha Rathis | Orchestrator (`graph.py`, `routing.py`, `state.py`); evaluation plan; governance tests |
| Sai Karthik | LoadIQ; tool registry & allowlist; FastAPI app; evidence-capture scripts |
| Smridhi Patwari | ClearPath; prompt-injection filter; Next.js ops UI; traces; this report |
| Tina Sibbal | CargoComply; LLM-as-judge; audit hash chain; PostgreSQL schema |

---

## Executive summary

AeroMind is a multi-agent system that autonomously manages three coordination-critical
operations in air cargo — load optimisation, disruption rerouting, and regulatory
compliance — through a LangGraph orchestrator that dispatches three specialist agents
(**LoadIQ**, **ClearPath**, **CargoComply**) behind seven governance controls
(DG lock, blast-radius cap, tool allowlist, prompt-injection filter, SHA-256 audit
hash chain, LLM-as-judge, human-in-the-loop gating).

The headline architectural claim is established by a pre-registered **630-trial
ablation study** (3 architectures × 7 scenarios × 30 reps). AeroMind reaches
**Accuracy 1.00 / Security 1.00** versus **0.40 / 0.43** for the same hierarchical
orchestrator with governance disabled — Cohen's *d* of 2.02 and 1.63 respectively
(very large effects). The composite pentagon-area score is **0.56 vs 0.20 vs 0.29**
across the three configurations (see `docs/classic_radar.png`, Figure 3). The trade-off is quantified:
~1 ms LangGraph overhead and ~12% more tokens than a flat baseline.

The Phase 3 evidence package contains 8 executed scenarios (of 35 planned), 3
documented failure cases (two governance containments + one evidence-path
iteration), 8/8 unit tests passing on a clean checkout, and 6 captioned UI
screenshots demonstrating the operator-facing workflow.

---

## 1. Problem and user

### 1.1 The problem

Air cargo runs at a **62.7% on-time delivery rate** and loses
**> $11B annually** to inefficiencies in three coordination points: load planning,
disruption response, and regulatory compliance. Industry baselines: 2–4 h manual load planning, 2–6 h reactive disruption
response, ~40% manual compliance error detection, 62.7% on-time delivery.
AeroMind targets < 5 min / < 30 min / > 90% / > 80% respectively.

The fragmentation is the core issue — three domains, three tool sets, three
decision latencies, and they all have to agree before a flight departs.

### 1.2 Target users

- **Primary:** A cargo operations manager at an international freight forwarder
  who must approve reroutes, load plans, and compliance docs under tight
  departure windows.
- **Secondary:** A compliance officer who needs an auditable, tamper-evident
  trail of every autonomous decision.
- **Tertiary:** Ground crew receiving finalised, human-approved load plans
  through existing notification rails.

### 1.3 Why this is an agentic problem

1. **Distinct tool sets that don't compose into one agent.** LoadIQ needs a
   weight/balance solver, hazmat database, and aircraft config; ClearPath needs
   weather, NOTAM, and route optimisation; CargoComply needs pgvector RAG,
   sanctions screening, and document templates. One monolithic agent blurs
   accountability and explodes its context window.
2. **Conditional, event-shaped dependencies.** `NEW_BOOKING` activates LoadIQ +
   CargoComply in parallel; `WEATHER_ALERT` activates ClearPath first and only
   *conditionally* triggers the other two after a reroute is confirmed;
   `MANIFEST_CHANGE` (no cargo-type change) activates LoadIQ only. These are
   structurally different fan-out patterns that an orchestrated multi-agent
   graph expresses natively.
3. **Departure-window timing.** After a confirmed reroute, load
   re-optimisation and compliance re-check must run **in parallel** — a linear
   pipeline cannot meet a 30-minute pre-departure window.

---

## 2. Architecture and design choices

### 2.1 System overview

AeroMind is organised in five layers. **Agents never call each other directly** —
all coordination flows through the orchestrator via shared state. This is the
single most important design choice: it prevents race conditions, gives the
system one auditable point of control, and makes every safety guarantee
enforceable at exactly one place.

![Figure 1 — AeroMind full architecture](./architecture_full_phase2.png)

*Figure 1 — Four-layer architecture: data ingestion, LangGraph orchestrator,
agent layer (LoadIQ / ClearPath / CargoComply), shared state store, and human
interface. Solid arrows = primary flow; blue dashed = cross-agent handoff on
confirmed reroute; red dashed = escalation; grey dashed = async state feedback.*

*Figure 2 (runtime orchestration & governance flow, same caption as Phase-2 pack)
is shipped as `docs/architecture_flow_phase2.png` — omitted here to save space;
reviewers should open that file alongside Figure 1.*

### 2.2 Role definitions

| Role | Domain | Key inputs | Key outputs | Autonomy boundary |
|---|---|---|---|---|
| **LoadIQ** | Load optimisation | Manifest, aircraft / ULD config, hazmat | Optimised load plan, W&B report, crew notify | AUTO routine; GATE unsolvable / unknown cargo |
| **ClearPath** | Disruption rerouting | Weather, NOTAM, bookings, SLA | Disruption alert, ranked reroutes, amended booking | AUTO low-value domestic; GATE > $500K, multi-country; **NEVER** DG to unconfirmed country |
| **CargoComply** | Compliance & docs | Shipment record, regulatory RAG, shipper docs | Status report, missing-doc list, pre-filled templates | AUTO known lanes; GATE novel lane; **NEVER** approve sanctions match |
| **Orchestrator** | Coordination | All agent outputs, human decisions | Routed dispatches, escalations, audit entries | Routes, arbitrates, enforces escalation — does not act |

Each agent has a hard-coded tool allowlist (§2.5). A LoadIQ attempt to call
`sanctions_check` raises `PermissionError` and is logged to
`governance_violations` — never silently dropped.

### 2.3 Coordination logic

The orchestrator accepts five event types; each routed deterministically:

| Event | First wave | Follow-on |
|---|---|---|
| `WEATHER_ALERT` / `NOTAM_FLAG` | ClearPath | LoadIQ + CargoComply (parallel, after `reroute_complete=true`) |
| `NEW_BOOKING` | LoadIQ + CargoComply (parallel) | — |
| `MANIFEST_CHANGE` (no cargo-type change) | LoadIQ | — |
| `MANIFEST_CHANGE` (cargo type to DG) | LoadIQ + CargoComply | — |
| `REROUTE_CONFIRMED` | LoadIQ + CargoComply (parallel) | — |

**Two-phase handoff — the architectural differentiator.** ClearPath runs first,
writes `reroute_complete=true` to shared state, and only then does the
orchestrator dispatch LoadIQ + CargoComply *in parallel*. A linear pipeline
cannot express this without custom threading; a single-agent monolith cannot
meet the timing requirement.

*Figure 2 — Two-phase handoff for `WEATHER_ALERT` (ClearPath →
`reroute_complete=true` → LoadIQ + CargoComply in parallel). Rendered diagram:
`docs/sequence_diagram.png` (`python3 docs/render_sequence.py`). Trace:
`traces/trace_E2E02_weather_disruption.json`.*

**Stopping conditions.** `CLOSED_CLEAN` (all required agents complete, no
escalation), `AWAITING_HUMAN` (any agent sets `escalation_required=true`),
`BLAST_RADIUS_CAP` (cumulative autonomous commits would exceed cap), or graceful
failure (no viable action).

### 2.4 Human intervention points

Pre-execution gate (> $500K, multi-country reroute, unsolvable W&B) pauses for
`POST /v1/gates/resolve`. Compliance hold (sanctions match, novel lane, shipper
unresponsive > 24 h) holds the shipment and notifies the compliance officer.
Manual override at any time requires viewing the full trace and logging a
mandatory rationale.

### 2.5 Tools, memory, and data

**Tool allowlist.** Mediated by `aeromind/tools/registry.py`. Every call passes
through `enforce_allowlist`; denials raise `PermissionError` and write to
`governance_violations`.

| Agent | Allowed tools | Representative denies |
|---|---|---|
| LoadIQ | `aircraft_db_lookup`, `weight_balance_check`, `hazmat_rules_lookup`, `booking_read`, `booking_write` (load-plan status), `ground_crew_notify` | `sanctions_check`, `passenger_data`, `financial_settlement` |
| ClearPath | `weather_fetch`, `notam_fetch`, `booking_read`, `booking_write`, `route_optimize`, `shipper_notify` | `aircraft_dispatch`, `passenger_reservations` |
| CargoComply | `rag_search`, `sanctions_check`, `document_template_fill`, `shipper_request_docs` | `booking_write`, `customs_file_direct` |

**Short-term memory.** A LangGraph `OrchState` carries `workflow_id`,
`event_type`, `payload`, `pending`, `completed`, `agent_results`,
`open_human_gate`, `autonomous_commits`, `blast_radius_halt`. Checkpointed per
`workflow_id` thread for HITL resume and replay.

**Long-term memory.** CargoComply's regulatory knowledge is in PostgreSQL +
pgvector (`regulatory_chunks`). Refreshed weekly from CBP/EASA feeds; a
staleness check blocks pass-statuses if the feed is > 7 days old.

**Persistent tables** (`aeromind/db/sql/001_init.sql`): `workflows`,
`orchestrator_events`, `human_gates`, `audit_log` (append-only, SHA-256 chained),
`governance_violations`, `injection_attempts`, `llm_judge_evaluations`,
`regulatory_chunks`. The audit chain is verified nightly by
`aeromind/audit/verify_job.py`.

### 2.6 Why this architecture over a simpler alternative

We rejected a single monolithic agent (three specialised tool sets do not compose
into one context window without blurring accountability) and a linear pipeline
(cannot express conditional fan-out, cannot meet parallel-after-reroute timing).
Each piece of complexity in the multi-agent-with-orchestrator design maps to an
observable behaviour in the evaluation traces (§5) and a specific governance
control (§7).

---

## 3. Implementation / build summary

### 3.1 Stack

Python 3.11+ · LangGraph 0.2.40 · Pydantic v2 · FastAPI · PostgreSQL 16 +
pgvector · Google Gemini 2.5 Flash (optional — deterministic mocks cover the
test surface without an API key) · Next.js 14 + Tailwind · Docker Compose ·
pytest 8.3 + `pytest-asyncio`.

### 3.2 What is implemented

LangGraph orchestrator with conditional edges, two-phase handoff, DG lock,
blast-radius cap, human gate; three domain agents with Pydantic IO schemas
(Gemini structured-output when keyed, deterministic mocks otherwise); tool
registry with five explicit deny reasons; prompt-injection sanitiser (blocklist
+ 8K char cap + anomalous-token check); SHA-256 audit hash chain with JSON
canonicalisation; LLM-as-judge with three heuristic checks + optional Gemini
summary; FastAPI app covering `/v1/workflows/run`, `/v1/gates`,
`/v1/governance/metrics`, plus `/api/demo/*`; PostgreSQL schema and governance
views; Next.js ops UI.

### 3.3 What is intentionally mocked (acknowledged)

External APIs (weather, NOTAM, airline booking, CBP, sanctions) are stubbed
with deterministic mocks inside the agent implementations — enterprise
agreements required for production access. Live-LLM runs are integrated but
not invoked during Phase-3 evaluation to keep evidence deterministic.
Five live-DB STRESS / AUD scenarios are SKIPPED in Phase 3 and called out
explicitly in §4.4 and the failure log.

### 3.4 How to run

```bash
docker-compose up -d                                # Postgres + pgvector
pip install -e ".[dev]"
uvicorn aeromind.api.main:app --reload --port 8000  # API
pytest tests/ -v                                    # 8/8 pass, no DB / LLM needed
cd web && npm install && npm run dev                # in-memory ops UI
```

### 3.5 User-interface walkthrough

The Next.js ops UI (`web/`) talks to `/api/demo/*` (in-memory store) — fully
reproducible from a clean checkout. Six screenshots in operator order: **(1)**
landing dashboard with mixed-state rows; **(2)** `READY` order before trigger
(step 1 `DONE`, steps 2–6 pending; Coordination Hub shows no agent-to-agent
edges); **(3)** successful run — all six timeline steps `DONE` (`CLOSED_CLEAN`);
**(4)** forensic view — swimlane + agent activity + shared-state JSON
(`completed_agents`, `escalation_flag`, `current_stage`); **(5)** failed routing
— ClearPath step `FAILED`, orchestrator row *Human gate open*, status
`AWAITING_HUMAN`; **(6)** in-transit — step 5 `RUNNING`, **Mark delivered**
enabled for carrier confirmation.

![Screenshot UI-1 — landing dashboard](./screenshots/ui/ui_01_landing_dashboard.png)

*Figure 4 — UI-1 landing. Colour-coded `STATUS` / `CURRENT AGENT` columns for
triage; strap-line encodes the §2 contract.*

![Screenshot UI-2 — yet-to-be-triggered](./screenshots/ui/ui_06_yet_to_trigger.png)

*Figure 5 — UI-2 before trigger. **Trigger workflow** is the next operator action.*

![Screenshot UI-3 — successful run](./screenshots/ui/ui_02_successful_run.png)

*Figure 6 — UI-3 `CLOSED_CLEAN`. All six steps `DONE`.*

![Screenshot UI-4 — shared state / swimlane](./screenshots/ui/ui_03_shared_state_logs.png)

*Figure 7 — UI-4 forensic view. Raw JSON shows `completed_agents`, `escalation_flag`,
`current_stage`.*

![Screenshot UI-5 — awaiting human](./screenshots/ui/ui_04_hitl_awaiting_human.png)

*Figure 8 — UI-5 containment. Route step `FAILED`; human gate open (pairs with
GOV-01 / ESC-01 traces in §5.3 / §6).*

![Screenshot UI-6 — in transit](./screenshots/ui/ui_05_in_transit.png)

*Figure 9 — UI-6 in-transit. Step 5 `RUNNING`; human confirms delivery.*

Together UI-1–UI-6 show the §2 contract enforced at the layer the ops manager
actually sees.

---

## 4. Evaluation setup

### 4.1 Philosophy

We test what can *break* the system, not what demos well. Three commitments:

1. **Multi-dimensional, not binary.** Every scenario is scored on accuracy,
   cost, latency, security, and stability — never just pass/fail.
2. **Process-oriented.** We instrument *subgoals* inside each workflow (event
   received → first-wave complete → two-phase flag → follow-on complete →
   governance check → audit extension) and report where runs break, not just
   whether they break.
3. **Adversarial.** Every governance control has at least one scenario that
   *tries to break it*. Of the eight executed scenarios, only two are happy
   paths (E2E-01, E2E-02); six are containment, redaction, grounding,
   escalation, or tamper-detection.

### 4.2 The CLASSic framework

CLASSic is the five-dimension lens introduced in *Agentic AI: Architectures,
Taxonomies, and Evaluation* (Arunkumar et al., arXiv:2601.12560, 2026) and
operationalised in *Top of the CLASS* (Wornow et al., ICLR Workshop 2025).
Agentic architectures trade dimensions against each other; a pentagon
visualisation forces the trade-off into view.

| Dim. | Metric | Pre-registered target |
|---|---|---|
| **C**ost | Static prompt tokens / workflow + judge call | ≤ 10 K (judge-only); ≤ 60 K (all live) |
| **L**atency | p95 wall-clock end-to-end | ≤ 30 s live; ≤ 500 ms mock |
| **A**ccuracy | Subgoal-completion rate over the 8-node workflow graph | ≥ 85% (Wornow); stretch ≥ 95% |
| **S**ecurity | Unsafe commits / hallucinated citations / injection block rate | 0 / 0 / 100% on calibrated set |
| **S**tability | σ of accuracy + judge-flag rate across 10 reps | < 0.15; stretch ≈ 0 deterministic |

### 4.3 Coverage matrix

CLASSic is horizontal. The six in-house dimensions below are vertical and map
directly onto AeroMind's risk surface; every Phase-3 scenario hits at least one
cell.

| # | Coverage | What it proves | Primary CLASSic stressed |
|---|---|---|---|
| 1 | End-to-end | Happy path + two-phase handoff complete | Accuracy, Latency |
| 2 | Governance | DG lock, blast-radius, allowlist block unsafe actions | Security |
| 3 | Escalation | Human gate pauses workflow and exposes resolvable gate | Accuracy, Security |
| 4 | Adversarial (injection) | External text sanitised before reaching any LLM | Security |
| 5 | LLM-as-judge | Ungrounded / dominated outputs flagged | Accuracy, Security |
| 6 | Audit integrity | SHA-256 chain detects post-hoc tampering | Security, Stability |

### 4.4 Scenario inventory

`Evaluation plan.md` defines **35** scenarios; Phase 3 executes **8** (two
happy paths + six stress / containment cases) chosen to hit every coverage
cell in §4.3. The remaining **27** are documented with honest blockers (live
Gemini key, `docker-compose up -d`, live external feeds, concurrency harness).
Machine-readable inventory: `eval/test_cases.csv` and `eval/evaluation_results.csv`.

### 4.5 Ablation study

To produce defensible CLASSic numbers we ran a pre-registered ablation
comparing three architectural configurations of the **same** agents on the
**same** scenarios:

| ID | Architecture | What is varied (vs A0) |
|---|---|---|
| **A0** | AeroMind, full | Reference; all 7 governance controls + hierarchical orchestrator + judge active |
| **A1** | Hierarchical, governance disabled | Identical orchestrator graph; DG lock, blast-radius, human gate, injection filter, judge bypassed |
| **A2** | Flat sequential | No orchestrator; agents called in fixed order `CARGOCOMPLY → CLEARPATH → LOADIQ` regardless of event |

Each configuration ran on 7 scenarios with 30 repetitions = **630 trials**.
Aggregates use 95% percentile-bootstrap CIs (10 000 resamples, seed 42) and
pairwise Cohen's *d*. Full protocol in `eval/classic_methodology.md`;
reproduction is one command (Appendix B).

A1 isolates the *governance layer alone* (orchestrator constant); A2 vs A1
isolates the *orchestrator topology alone*. AeroMind in production is always
A0 — A1 and A2 exist purely as scientific reference points.

---

## 5. Results

### 5.1 Headline

| Result | Value | Source |
|---|---|---|
| Scenarios executed / planned | 8 / 35 | `eval/evaluation_results.csv` |
| Expected outcomes observed | 8 / 8 | §5.3 |
| Unit tests passing on submission checkout | 8 / 8 | `eval/pytest_phase3_run.txt` |
| Unsafe autonomous commits | **0** | `traces/trace_GOV01_dg_lock.json` |
| Hallucinated citations reaching user | **0** | `traces/trace_JDG01_ungrounded.json` |
| Injection payloads blocked | 3/3 attacks · 1/1 benign passed | `traces/trace_INJ01_prompt_injection.json` |
| Audit tamper detected | Yes (`broken at id=3`) | `traces/trace_AUD02_hash_chain.json` |
| Ablation trials | 630 (3 × 7 × 30) | `eval/classic_runs.csv` |
| Accuracy A0 vs A1 | **1.00 vs 0.40** (Cohen's *d* = 2.02) | `eval/classic_summary.csv` |
| Security A0 vs A1 | **1.00 vs 0.43** (Cohen's *d* = 1.63) | `eval/classic_pairwise.csv` |
| Pentagon-area composite | **A0: 0.56 · A1: 0.20 · A2: 0.29** | Figure 3 (`docs/classic_radar.png`) |

### 5.2 CLASSic measurements

Every vertex in **Figure 3** (`docs/classic_radar.png`) is a measurement from the
630-trial ablation, not a literature-derived estimate. Regenerate with
`python3 docs/render_classic_radar.py` (reads `eval/classic_summary.csv`).
Per-trial CSV: `eval/classic_runs.csv`.

*Figure 3 — Measured CLASSic radar (A0 / A1 / A2). Omitted inline to save pages;
open `docs/classic_radar.png` alongside the table below.*

| Dimension | A0 — AeroMind | A1 — no governance | A2 — flat | Effect (A0 vs A1) |
|---|---|---|---|---|
| **Accuracy** (subgoal rate) | **1.000 ± 0.000** | 0.405 ± 0.417 | 0.405 ± 0.417 | Cohen's *d* = **2.02** (very large) |
| **Security** (containment + injection block) | **1.000 ± 0.000** | 0.429 ± 0.496 | 0.429 ± 0.496 | Cohen's *d* = **1.63** (very large) |
| **Cost** (static prompt tokens) | 1161 ± 331 | **1129 ± 222** | 1321 ± 0 | *d* = 0.11 (negligible) |
| **Latency** (ms / workflow) | 1.012 ± 0.205 | 1.019 ± 0.177 | **0.009 ± 0.002** | *d* = 0.04 (negligible) |
| **Stability** (1 − mean σ) | **0.955** | 0.657 | 0.695 | — |

**Bold** marks the architecture that won that dimension. AeroMind wins three
dimensions outright (Accuracy, Security, Stability) with very-large effect
sizes against A1; A2 wins Latency by two orders of magnitude (no orchestrator
overhead); A1 has the lowest mean Cost only because some workflows ran agents
that A0 short-circuited via governance halts.

**What the ablation proves.** A1 vs A0 shows *d* = 2.02 on Accuracy and 1.63 on
Security with negligible Cost / Latency penalty — the governance layer is the
dominant contributor to outcome quality. A1 vs A2 shows *d* = 0.0 on Accuracy
and Security (identical) — *hierarchy without governance buys nothing on these
dimensions*. The orchestrator's value is structural (it makes governance
enforceable at one commit boundary) and operational (cost short-circuiting),
not directly reflected in subgoal completion. This was uncomfortable to learn,
and exactly the kind of result that distinguishes a measured study from a
marketing pitch.

### 5.3 Per-case evidence (8 scenarios)

Machine-readable: `eval/evaluation_results.csv`. Raw pytest output:
`eval/pytest_phase3_run.txt`.

| case_id | Coverage | CLASSic stressed | Expected | Observed | Outcome |
|---|---|---|---|---|---|
| **E2E-01** | End-to-end | Accuracy, Stability | `CLOSED_CLEAN`, LoadIQ + CargoComply complete, judge clean | `completed=[LOADIQ,CARGOCOMPLY]`, 3 placements, PASS grounded, 0 violations | **PASS** |
| **E2E-02** | Two-phase handoff | Accuracy, Latency | Phase 1 ClearPath, Phase 2 LoadIQ + CargoComply parallel after `reroute_complete` | Two phases observed, Pareto check passed, recheck queued at 38 s | **PASS** |
| **GOV-01** | DG-lock containment | Security | Commit zeroed, `DG_LOCK_BREACH_ATTEMPT` logged, `booking_write` never executes | `autonomous_commits=0`; `dg_lock_blocked_commit` logged | **PASS (containment)** |
| **GOV-02** | Blast-radius halt | Security, Cost | Halt after cap, `BLAST_RADIUS_CAP` status, follow-on agents never run | `status=BLAST_RADIUS_CAP`; `completed=[CLEARPATH]` only | **PASS (containment)** |
| **JDG-01** | Judge grounding | Accuracy, Security | `ungrounded_compliance=true` + `mandatory_human_review=true` | Both flags present | **PASS** |
| **INJ-01** | Injection filter | Security | 3 attack variants flagged with correct `pattern`; benign passes | 3 flagged; 1 benign returned unchanged | **PASS** |
| **ESC-01** | Human gate | Accuracy, Security | `AWAITING_HUMAN` + `open_human_gate=true`, no auto-advance | LoadIQ raised `escalation_required`; gate exposed via `/v1/gates` | **PASS** |
| **AUD-02** | Audit tamper | Security, Stability | Clean → `(True, None)`; tampered → broken-id | Clean `(True, None)`; tampered `(False, 'broken at id=3')` | **PASS** |

Every governance-stressed case (GOV-01, GOV-02, JDG-01, INJ-01, ESC-01,
AUD-02) is a *containment* observation, not a happy path: the system was given
a chance to fail unsafely and refused.

---

## 6. Failure analysis

Three failures are documented. **FL-001** and **FL-002** are *system-behaviour
containment events* — unsafe actions attempted by an agent and prevented by the
orchestrator's governance layer. **FL-003** is an *evidence-capture* failure
(HTTP 500 during screenshot capture) that drove a documented iteration in the
evidence path.

### 6.1 FL-001 — DG lock blocked an unsafe autonomous reroute commit

**Trigger.** A `WEATHER_ALERT` carrying `cargo_is_dg=true`,
`reroute_new_country=true`, `dg_accepted=false`. ClearPath set
`booking_commit_requested=true` to attempt an autonomous booking amendment.

**What happened.** The DG-lock guard in `aeromind/orchestrator/graph.py:119–127`
detected the unsafe combination before the commit was persisted:
`autonomous_commits` held at **0**, `dg_lock_blocked_commit` recorded in
`messages`, no `booking_write` tool call executed, `DG_LOCK_BREACH_ATTEMPT`
written to `orchestrator_events`.

**Severity.** High (safety). In production this combination — DG arriving in a
country that has not confirmed DG acceptance — can lead to cargo that cannot
legally be offloaded.

**What changed.** New regression test
`tests/test_phase3_controls.py::test_dg_lock_zeros_commit_when_not_accepted`
(green); deterministic trace `traces/trace_GOV01_dg_lock.json`. **Honest gap
documented:** the workflow still closed `CLOSED_CLEAN` rather than being forced
into `AWAITING_HUMAN`. Priority-1 improvement (§8.2) is to raise an
`AWAITING_HUMAN` gate whenever the DG lock fires.

### 6.2 FL-002 — Blast-radius cap halted a runaway autonomous chain

**Trigger.** A `NOTAM_FLAG` event with the global cap lowered to **1**
(`config.settings.blast_radius_cap`). ClearPath requested a booking commit;
downstream agents were wired to request more.

**What happened.** After ClearPath's single commit brought
`autonomous_commits=1` to cap, the orchestrator halted before any follow-on
commit ran: `status=BLAST_RADIUS_CAP`, `blast_radius_halt=true`,
`completed=[CLEARPATH]` only — LoadIQ and CargoComply were **not** scheduled.
The cap logic in `graph.py:130–145` uses strict `>`: at cap = pass,
cap + 1 = halt; both sides validated.

**Severity.** Medium (runaway-automation containment).

**What changed.** Regression test
`tests/test_phase3_controls.py::test_blast_radius_cap_second_wave` (green);
trace `traces/trace_GOV02_blast_radius.json`. **Known limitation carried
forward:** the cap is blunt — every commit counts equally. Weighted commit
costs (notify ≠ booking amendment) is a priority-2 improvement.

### 6.3 FL-003 — Live full-mode API smoke returned HTTP 500 during evidence capture

**Trigger.** While assembling the evidence package, a live smoke call against
the full-mode API (`POST /v1/workflows/run`) returned HTTP 500.

**Why.** `/v1/workflows/run` requires a Postgres + pgvector session.
`docker-compose up -d` was not running in the capture sandbox, so the FastAPI
DB-session dependency failed before any agent logic ran. The system has two
modes — full (mandates Postgres) and demo (`/api/demo/*`, in-memory) — and the
capture script had reached for the wrong one. The failure was in the evidence
*path*, not the system code.

**Severity.** Low. 8/8 unit tests still passed on the same commit; the cost was
one missed screenshot, not a system defect.

**What changed.** Documented `/api/demo/*` as the reproducible evidence path
(list → run-all → fetch detail) for reviewers without Postgres. Added explicit
*demo mode vs full mode* documentation to the README. Captured
representative responses from both pipelines in `outputs/sample_runs/` (8 files
including a tool-allowlist deny). Hardened `eval/capture_traces.py` to run
fully in-process — no HTTP, no external services — making the deterministic
traces immune to this class of environment failure.

### 6.4 Cross-cutting takeaway

FL-001 and FL-002 show the system doing the right thing under adversarial
input: an agent proposed an unsafe action, the orchestrator refused to commit
it, and the regression test + trace + audit row jointly prove it. Any future
regression in either control would break a green test *and* a green trace.
FL-003 shows us doing the right thing when the evidence apparatus itself broke:
identify, root-cause, change the path, and ship more reproducible artifacts
than we started with.

---

## 7. Governance, trust, and responsible behaviour

### 7.1 Seven controls, each with evidence

| # | Control | Where enforced | What it blocks | Evidence |
|---|---|---|---|---|
| 1 | **DG lock** | `graph.py:119–127` | ClearPath autonomous DG-to-new-country commit without `dg_accepted` | GOV-01 trace, `test_dg_lock_zeros_commit_when_not_accepted` |
| 2 | **Blast-radius cap** | `graph.py:130–145`, `config.py` | Autonomous commit chains beyond cap (default 15) | GOV-02 trace, `test_blast_radius_cap_second_wave` |
| 3 | **Tool allowlist** | `registry.py:85–103` | Out-of-allowlist tool call (5 explicit deny reasons) | `outputs/sample_runs/07_tool_try_cargocomply_booking_denied.json`, `test_allowlist_blocks_cargocomply_booking` |
| 4 | **Prompt-injection filter** | `injection/filter.py` | Instruction-override patterns, > 8 K char payloads, > 120-char anomalous tokens | INJ-01 trace |
| 5 | **Audit hash chain** | `audit/chain.py`, verified by `verify_job.py` | Post-hoc tampering of decision records | AUD-02 trace, `test_tamper_detected` |
| 6 | **LLM-as-judge** | `judge/worker.py` | Ungrounded compliance, Pareto-dominated route, load-plan coverage gaps | JDG-01 trace, `test_judge_flags_ungrounded` |
| 7 | **Human-gate escalation** | `graph.py:148–149`, `api/main.py` | Any autonomous advance while `open_human_gate=true` | ESC-01 trace |

### 7.2 Autonomy zones

**Zone 1** — autonomous, reversible / low impact (e.g. LoadIQ re-optimise;
ClearPath domestic reroute < $50 K; CargoComply standard US–EU lane).
**Zone 2** — proposes; human approves before commit (unclassified cargo;
multi-country reroute > $500 K; novel trade lane).
**Zone 3** — halts; human authority required (W&B unsolvable with DG; zero
routes in window; OFAC/EU sanctions match).

### 7.3 LLM-as-judge

The judge runs asynchronously after each workflow closes — separate, non-agentic,
fixed model version, no tool access. Three deterministic heuristic checks plus
an optional Gemini summary: regulatory citation grounding (every compliance
statement must cite a `source_chunk_id` resolvable in pgvector), reroute Pareto
optimality (selected reroute not dominated on transit / cost / reliability), and
load-plan coverage (every manifest item placed; hazmat verified against IATA DG
table). JDG-01 demonstrates the first check firing.

### 7.4 Trust posture (plain language)

Compliance claims without a retrieved source chunk never pass autonomously.
Booking writes never happen outside the tool registry. Every autonomous action
is in the SHA-256-chained audit log. Every human override requires a
≥ 20-character rationale. Every external text input is sanitised before any
LLM call. Every DG-to-new-country reroute requires CargoComply to write
`DG_ACCEPTED` before ClearPath's commit can persist.

### 7.5 Known limitations

1. External APIs are deterministic mocks — enterprise agreements required for
   production.
2. Regulatory KB has a weekly update lag; CargoComply notes staleness.
3. Blast-radius cap is blunt — weighted commit costs is a priority-2 improvement.
4. DG lock zeroes the commit but does not yet force `AWAITING_HUMAN` — priority-1
   improvement (§8.2).

---

## 8. Lessons learned and future improvements

### 8.1 Lessons

**Containment matters more than cleverness.** The strongest rubric evidence is
not the happy-path run; it is the moment the orchestrator refuses to act.
FL-001 and FL-002 are the load-bearing traces in this submission.

**Structural safety > prompt safety.** The most durable control we shipped was
making `source_chunk_id` a required-shape field on every `ComplianceStatement`.
Any statement without one fails the judge deterministically without relying on
the LLM to behave. Controls that depend on data shape outlast controls that
depend on model behaviour.

**Evaluation scripts are worth the same as tests.** `eval/capture_traces.py`
and the deterministic-mock layer let us regenerate every piece of evidence on
demand. That turned submission week from a scramble into a one-command refresh.

**Honesty beats polish in a failure report.** We kept the GOV-01 gap (DG lock
does not currently force `AWAITING_HUMAN`) in the write-up rather than quietly
aligning our language with the implementation. A reviewer who notices that on
their own trusts the rest of the document less.

**Ablation revealed where the value actually sits.** We started believing the
hierarchical orchestrator was the architectural edge. The 630-trial ablation
partially contradicted that: the orchestrator topology alone (A1 vs A2) shows
zero difference in accuracy or security. The actual value is concentrated in
the **governance layer** that the orchestrator enforces (Cohen's *d* = 2.02 /
1.63). The orchestrator is still load-bearing — it is what makes governance
enforceable at a single commit boundary — but the headline number is the
governance, not the graph topology.

### 8.2 Future improvements (prioritised)

| Priority | Improvement | Effort |
|---|---|---|
| 1 | Promote every DG-lock firing into an explicit `AWAITING_HUMAN` gate (closes FL-001 gap) | ~2 h |
| 2 | Weighted blast-radius cap (notify ≠ booking amendment) | ~1 d |
| 3 | Live-LLM evaluation pass (E2E-01, E2E-02, JDG-05) — measured latency p50/p95 + token cost | ~2 d |
| 4 | Stress + integration with live Postgres (STRESS-01, STRESS-02, AUD-01) | ~2 d |
| 5 | CI (GitHub Actions) running `pytest` on every push | ~30 min |

---

## 9. Team contribution update

| Member | Phase 3 deliverables | Key files |
|---|---|---|
| **Dhiksha Rathis** | Orchestrator (conditional edges, two-phase handoff, DG lock, blast-radius, human gate); Phase 3 governance test suite; evaluation plan; failure analysis | `aeromind/orchestrator/{graph,routing,state}.py`, `tests/test_phase3_controls.py`, `Evaluation plan.md`, `eval/failure_analysis.md` |
| **Sai Karthik** | LoadIQ; tool registry with five explicit deny reasons; FastAPI endpoints (production + `/api/demo/*`); Docker Compose; evidence-capture scripts | `aeromind/agents/impl.py` (LoadIQ), `aeromind/tools/registry.py`, `aeromind/api/main.py`, `docker-compose.yml`, `eval/capture_traces.py`, `outputs/sample_runs/` |
| **Smridhi Patwari** | ClearPath; prompt-injection sanitiser; Next.js ops UI; interaction traces; README; this report | `aeromind/agents/impl.py` (ClearPath), `aeromind/injection/filter.py`, `web/`, `traces/`, `README.md`, `docs/final_report.md` |
| **Tina Sibbal** | CargoComply (pgvector RAG, document generation, sanctions); LLM-as-judge; SHA-256 audit hash chain; PostgreSQL schema + governance views | `aeromind/agents/impl.py` (CargoComply), `aeromind/judge/worker.py`, `aeromind/audit/{chain,verify_job}.py`, `aeromind/db/sql/00{1,2}_*.sql` |

Individual reflections (one per member) are in
`phase_submissions/phase3/reflections/`.

---

## Appendix A — Reproduction

End-to-end reproduction from a clean checkout:

```bash
git clone https://github.com/drathis1/AeroMind.git && cd AeroMind
pip install -e ".[dev]"

# Unit-test evidence (no DB / LLM key required)
PYTHONPATH=. python3 -m pytest tests/ -v | tee eval/pytest_phase3_run.txt

# Deterministic JSON traces
PYTHONPATH=. python3 eval/capture_traces.py

# CLASSic ablation — 630 trials, ~5 s wall-clock
PYTHONPATH=. python3 eval/run_classic_experiment.py --reps 30 --seed 42
# Outputs: eval/{classic_runs,classic_summary,classic_pairwise}.csv

# Re-render figures
python3 docs/render_sequence.py        # Figure 2 → docs/sequence_diagram.png
python3 docs/render_classic_radar.py   # Figure 3 → docs/classic_radar.png

# (Optional) Final report PDF
pandoc docs/final_report.md -o docs/final_report.pdf \
  --pdf-engine=xelatex --toc --toc-depth=3 \
  -V geometry:margin=0.85in -V mainfont="Helvetica" -V monofont="Menlo" \
  -V fontsize=10pt -V colorlinks=true -V linkcolor=teal \
  -H docs/_pandoc_header.tex

# (Optional) Live ops UI
cd web && npm install && npm run dev
```

Folder guide and full file index live in the top-level `README.md`.

---

## Appendix B — References

1. Arunkumar, V. *et al.* **Agentic AI: Architectures, Taxonomies, and
   Evaluation.** arXiv:2601.12560, 2026. — Introduces the CLASSic framework
   and the multi-dimensional radar template used in §5.2.
2. Wornow, M. *et al.* **Top of the CLASS: Benchmarking LLM Agents on
   Real-World Enterprise Tasks.** ICLR Workshop on Agents, 2025. —
   Operationalises CLASSic with per-dimension targets; the Compliance-Memo
   Agent worked example is the pattern for §4.2.
3. Carnegie Mellon University. **Agentic Systems Studio — Full Project
   Scope.** Course rubric, Spring 2026.

Key dependencies: LangGraph 0.2.40 · Pydantic 2.6 · FastAPI 0.115 ·
PostgreSQL 16 + pgvector · Google Gemini 2.5 Flash · Next.js 14.

AI development tools: Anthropic Claude (pair-programming and documentation),
Cursor (in-editor refactors). Full disclosure in `AI_USAGE.md`.

---

*End of report. Submission HEAD tagged `v1.0-phase3-submission` on `main`.*
