# AeroMind — Phase 3 Final Report

**The AI Operations Brain for Air Cargo**

**Course:** Agentic Systems Studio · Track A: Technical Build
**Phase:** 3 — Final Product, Evidence, and Reflection
**Submission date:** April 2026
**Repository commit at submission:** `3922b685e28444ad9f019db446dfd5573b20947e`
**Repository:** `https://github.com/drathis1/AeroMind`

| Team member | Phase 3 area of ownership |
|---|---|
| Dhiksha Rathis | Agent architecture & orchestration (`graph.py`, `routing.py`, `state.py`), evaluation plan, governance tests |
| Sai Karthik | LoadIQ agent, tool registry & allowlist, FastAPI app, Docker Compose, evidence-capture scripts |
| Smridhi Patwari | ClearPath agent, prompt-injection filter, Next.js ops UI, interaction traces, README and this report |
| Tina Sibbal | CargoComply agent, LLM-as-judge, audit hash chain, PostgreSQL schema and governance views |

---

## Executive summary

AeroMind is a multi-agent AI platform that autonomously manages three critical
operations in air cargo logistics — real-time cargo load optimization,
disruption-driven flight rerouting, and regulatory compliance automation —
through a LangGraph-based central orchestrator coordinating three specialist
agents: **LoadIQ**, **ClearPath**, and **CargoComply**. Phase 3 delivers a
runnable end-to-end system with a governance layer (DG lock, blast-radius cap,
tool allowlist, prompt-injection sanitizer, audit hash chain, LLM-as-judge, and
human-in-the-loop gating), an evaluation evidence package covering eight
scenarios across all six evaluation dimensions, and two documented failure
cases where the orchestrator correctly contained unsafe autonomous actions.

| Phase 3 deliverable | Status | Evidence |
|---|---|---|
| Final artifact (runnable) | Delivered | `aeromind/`, `web/`, `docker-compose.yml`; 8/8 unit tests pass on clean checkout |
| Architecture diagram | Delivered | `docs/architecture_diagram.png` (Mermaid source at `.mmd`) |
| Eight completed evaluation scenarios | Delivered | `eval/test_cases.csv`, `eval/evaluation_results.csv`, `traces/` |
| Two failure cases with containment evidence | Delivered | `eval/failure_log.md`, `eval/failure_analysis.md` |
| Seven distinct governance controls | Delivered | DG lock, blast-radius, allowlist, injection filter, hash chain, LLM-as-judge, human gate |
| Individual reflections | Delivered | `phase_submissions/phase3/reflections/` (one per member) |
| AI usage disclosure | Delivered | `AI_USAGE.md` + `phase_submissions/phase3/ai_transcript_excerpts.md` |
| Representative outputs | Delivered | `outputs/sample_runs/` (8 captured responses) |
| 5-minute demo video | Link in `media/demo_video_link.txt` | (recorded separately) |

The report that follows walks through the problem and user (§1), the
architecture and why we chose it (§2), the implementation (§3), the evaluation
methodology (§4), the results (§5), the two failure cases in full narrative
form (§6), the governance and trust layer (§7), lessons learned and future
improvements (§8), team contributions (§9), and a reproduction appendix (§A).

---

## 1. Problem and user

### 1.1 The problem

The air cargo industry operates at a **62.7% on-time delivery rate** and loses
**more than $11B annually** to inefficiencies concentrated in three
coordination points: load planning, disruption response, and regulatory
compliance. Manual baselines for each:

| Problem | Industry baseline | AeroMind target |
|---|---|---|
| Load optimization time | 2–4 hours manual | < 5 minutes automated |
| Disruption response time | 2–6 hours reactive | < 30 minutes proactive |
| Compliance error detection rate | ~40% manual | > 90% automated |
| On-time delivery rate | 62.7% industry | > 80% in simulated scenarios |

The *fragmentation* is the issue — each of the three domains has its own tools,
data source, decision latency, and failure mode, and they all have to agree
before a flight departs. A single operator coordinating across three teams
under time pressure is the status quo that AeroMind replaces.

### 1.2 Target user

**Primary user:** A cargo operations manager at an international freight
forwarder who must approve reroutes, load plans, and compliance documents
under tight departure windows. This user currently opens three or four tabs
— weather, booking system, customs portal — and makes judgement calls with
incomplete information.

**Secondary user:** A compliance officer who needs an auditable, tamper-evident
trail for every autonomous decision the system makes. Their interaction with
the system is forensic: after the fact, can I reconstruct what happened, on
what evidence, and prove it wasn't altered?

**Tertiary user:** The ground crew receiving push notifications about load
plans. They never see the reasoning layer — they need a finalized,
human-approved plan delivered through existing notification rails.

### 1.3 Why this is an agentic problem

Three reasons a non-agentic solution fails:

1. **The three domains have distinct tool sets that do not compose into a
   single agent.** LoadIQ requires a weight/balance solver, hazmat rules
   database, and aircraft configuration lookup. ClearPath requires live
   weather, NOTAM feeds, and route optimization. CargoComply requires a
   pgvector RAG pipeline, sanctions screening, and document templates.
   Combining all of them into one agent produces an unmanageable context
   window and blurs accountability when something goes wrong.

2. **The dependencies between them are conditional.** A `NEW_BOOKING` event
   triggers LoadIQ and CargoComply in parallel but has nothing to do with
   routing. A `WEATHER_ALERT` triggers ClearPath first, and only
   *conditionally* triggers LoadIQ and CargoComply after a reroute is
   confirmed. A `MANIFEST_CHANGE` with no cargo type change triggers only
   LoadIQ. These are structurally different activation patterns with shared
   downstream state — exactly what an orchestrated multi-agent graph solves.

3. **The departure-window constraint rules out sequential pipelines.** When a
   reroute is confirmed, load re-optimization and compliance re-check must
   happen *in parallel*, not one after the other. A 90-minute departure
   window cannot afford sequential processing. A linear pipeline would need
   custom threading logic that reintroduces every coordination complexity
   the multi-agent orchestrator handles natively.

---

## 2. Architecture and design choices

### 2.1 System overview

AeroMind is organized in five layers. Data flows top-down from ingestion
through the orchestrator to the agent layer; shared state feeds back to the
orchestrator; escalations surface to the human interface layer. **Agents
never call each other directly** — all coordination passes through the
orchestrator via the shared state store. This is the single most important
architectural decision in the system: it prevents race conditions, gives
the system a single auditable point of control, and makes every safety
guarantee enforceable at exactly one place.

![AeroMind architecture](./architecture_diagram.png)

*Figure 1 — AeroMind architecture. Solid arrows = primary orchestration flow;
dashed = cross-agent handoff on confirmed reroute; red = escalation to human
interface; grey = async state feedback. Source: `docs/architecture_diagram.mmd`.*

### 2.2 Layer summary

| # | Layer | Contents | Role in system |
|---|---|---|---|
| 1 | Event ingestion | Weather / NOTAM feeds, airline booking events, shipper notes | Continuous monitoring; fires event to orchestrator when threshold crossed |
| 2 | Orchestrator (LangGraph) | Event router (`routing.py`), governance layer (`graph.py`), audit logger | Receives all events; decides which agent(s) to activate; enforces safety controls; closes workflows |
| 3 | Agent layer | LoadIQ · ClearPath · CargoComply | Each agent reads from and writes to shared state; no direct agent-to-agent calls |
| 4 | Shared state + evidence | PostgreSQL + pgvector RAG, LLM-as-judge, audit hash chain | Persistent state, post-hoc quality evaluation, tamper-evident trail |
| 5 | Human + API | FastAPI (`/v1/workflows/run`, `/v1/gates/resolve`, `/v1/governance/metrics`), Next.js ops dashboard | Receives escalations; ops manager approves or redirects; every decision logged |

### 2.3 Role definitions

| Role | Domain | Key inputs | Key outputs | Autonomy boundary |
|---|---|---|---|---|
| **LoadIQ** | Load optimization | Cargo manifest, aircraft type & ULD config, hazmat classifications, new aircraft on reroute | Optimized ULD load plan, weight & balance report, hazmat conflict flags, ground crew notification | AUTO: routine re-optimization. GATE: unsolvable constraints, unknown cargo type |
| **ClearPath** | Disruption rerouting | Live weather & NOTAM feeds, active bookings, shipper SLA | Disruption alert, ranked reroute options, amended booking, shipper notification, handoff to LoadIQ + CargoComply | AUTO: low-value domestic. GATE: >$500K, multi-country. NEVER: DG to unconfirmed country |
| **CargoComply** | Compliance & docs | Shipment record (origin, dest., HS code, value), regulatory RAG, existing shipper docs | Compliance status report, missing-doc checklist, pre-filled templates (AWB, EUR1, DG Declaration), shipper requests | AUTO: known trade lanes, template fill. GATE: novel lane, shipper unresponsive. NEVER: approve sanctions match |
| **Orchestrator** | Coordination & state | All agent outputs, human decisions, raw events | Routed task assignments, escalation alerts, audit log entries, shared state updates | Not an action agent — routes, arbitrates, and enforces escalation |

Each agent has a hard-coded tool allowlist (see §2.6). A LoadIQ attempt to
call `sanctions_check` raises `PermissionError` and is logged to
`governance_violations` — never silently dropped.

### 2.4 Coordination logic — who starts, how handoffs happen, when it stops

**Entry points.** The orchestrator accepts five event types, each routed
deterministically:

| Event | First activation | Follow-on | Notes |
|---|---|---|---|
| `WEATHER_ALERT` or `NOTAM_FLAG` | ClearPath only | LoadIQ + CargoComply (parallel) | Parallel activation **only** after ClearPath writes `reroute_complete=true` |
| `NEW_BOOKING` | LoadIQ + CargoComply (parallel) | — | Independent; neither depends on the other |
| `MANIFEST_CHANGE` (no cargo-type change) | LoadIQ only | — | CargoComply skipped unless `cargo_type_changed=true` |
| `MANIFEST_CHANGE` (cargo type to DG) | LoadIQ + CargoComply | — | Cargo-type change triggers full compliance re-check |
| `REROUTE_CONFIRMED` | LoadIQ + CargoComply (parallel) | — | Orchestrator reads `reroute_complete` flag from state before dispatch |

**Two-phase handoff — the architectural differentiator.** The core value of
the orchestrator is visible in `WEATHER_ALERT` flows. ClearPath runs first,
writes `reroute_complete=true` to shared state, and only then does the
orchestrator dispatch LoadIQ and CargoComply *in parallel*. A sequential
pipeline cannot express this without custom threading, and a single-agent
monolith cannot meet the parallel-after-reroute timing requirement.

```mermaid
sequenceDiagram
    autonumber
    participant Evt as Event
    participant Orc as Orchestrator
    participant CP as ClearPath
    participant LIQ as LoadIQ
    participant CC as CargoComply
    participant State as Shared State
    Evt->>Orc: WEATHER_ALERT (FRA-JFK, $48K, non-DG)
    Orc->>CP: dispatch (Phase 1, first_agents_for_event)
    CP->>CP: sanitize NOTAM · rank routes · select r1
    CP->>State: booking_write · reroute_complete=true
    State-->>Orc: flag detected
    Orc->>LIQ: dispatch (Phase 2, followon_after_clearpath)
    Orc->>CC: dispatch (Phase 2, parallel)
    LIQ-->>State: W&B pass · hazmat none · crew notify QUEUED
    CC-->>State: compliance PASS · grounded · 0 missing docs
    Orc->>Evt: CLOSED_CLEAN · 2 commits · audit chain valid
```

> If your Markdown viewer doesn't render Mermaid, a pre-rendered PNG of this
> sequence is available at [`docs/sequence_diagram.png`](sequence_diagram.png).

*Figure 2 — Two-phase handoff for a `WEATHER_ALERT` event. The first wave is
ClearPath only; the second wave (LoadIQ + CargoComply in parallel) is gated
on `reroute_complete` being written to shared state. This is the flow
captured verbatim in `traces/trace_E2E02_weather_disruption.json`.*

**Stopping conditions.** The orchestrator recognizes four terminal states:

| Final status | Trigger | Example |
|---|---|---|
| `CLOSED_CLEAN` | All required agents complete, no escalation flag, no governance trip | E2E-01 happy path |
| `AWAITING_HUMAN` | Any agent sets `escalation_required=true` | ESC-01 — LoadIQ unsolvable W&B constraint |
| `BLAST_RADIUS_CAP` | Cumulative autonomous commits would exceed cap | GOV-02 — cap set to 1, second commit halts graph |
| Graceful failure | No valid action possible (no viable reroute, unresolvable compliance) | Surfaced to human with all partial information |

### 2.5 Human intervention points

| Intervention point | Triggered by | Condition | What happens |
|---|---|---|---|
| Pre-execution gate | ClearPath / LoadIQ | Shipment >$500K, multi-country reroute, unsolvable load constraint | Workflow pauses; ops manager sees summary + approve/redirect via `POST /v1/gates/resolve` |
| Compliance hold | CargoComply | Sanctions match, novel trade lane, shipper unresponsive >24h | Shipment held; Zone 3 = immediate; compliance officer notified with full report |
| Manual override | Ops manager (any time) | Any workflow | Manager views full agent trace via `GET /v1/workflows/{id}/trace`; override logged with mandatory rationale |
| Post-action review | Ops manager (async) | Any completed workflow | LLM-as-judge flags out-of-pattern traces; summary card shows every agent action |

### 2.6 Tools, memory, and data design

**Tool registry and allowlist.** All tool calls are mediated by a central
`ToolRegistry` (`aeromind/tools/registry.py`). Every call passes through
`enforce_allowlist` before execution; denials are logged to
`governance_violations` and raise `PermissionError`.

| Agent | Allowed tools | Representative denies | Policy hooks |
|---|---|---|---|
| LoadIQ | `aircraft_db_lookup`, `weight_balance_check`, `hazmat_rules_lookup`, `booking_read`, `booking_write` (load plan status), `ground_crew_notify` | `sanctions_check`, `passenger_data`, `financial_settlement` | `ground_crew_notify` blocked if Zone 2/3 gate open |
| ClearPath | `weather_fetch`, `notam_fetch`, `booking_read`, `booking_write`, `route_optimize`, `shipper_notify` | `aircraft_dispatch`, `passenger_reservations`, `financial_settlement` | **DG lock:** `booking_write` blocked if `cargo_is_dg=true` + `reroute_new_country=true` + `dg_accepted=false` |
| CargoComply | `rag_search`, `sanctions_check`, `document_template_fill`, `shipper_request_docs` | `booking_write`, `customs_file_direct`, `financial_data` | Every compliance statement must include `source_chunk_id` from pgvector retrieval |

**Short-term (workflow) memory.** A LangGraph `OrchState` carries the complete
workflow context within a run: `workflow_id`, `event_type`, `payload`,
`pending`, `completed`, `agent_results`, `open_human_gate`,
`autonomous_commits`, `blast_radius_halt`. The state is checkpointed per
`workflow_id` thread, which makes HITL resume and replay possible.

**Long-term (retrieval) memory.** CargoComply's regulatory knowledge is stored
in PostgreSQL with pgvector embeddings (`regulatory_chunks` table). The
knowledge base is refreshed weekly from CBP/EASA feeds. A staleness check
runs before every CargoComply dispatch: if the feed timestamp is >7 days old,
CargoComply is blocked from issuing pass statuses and raises a
data-staleness alert.

**Persistent tables** (`aeromind/db/sql/001_init.sql`):

| Table | Purpose | Key fields |
|---|---|---|
| `workflows` | Workflow metadata and counters | `workflow_id`, `event_type`, `status`, `autonomous_commits`, `blast_radius_halt` |
| `orchestrator_events` | Correlated orchestration events | `event_type` (e.g. `DG_LOCK_BREACH_ATTEMPT`), `payload` JSONB |
| `human_gates` | Open and resolved human approvals | `gate_id`, `status`, `approve_continue`, `rationale` |
| `audit_log` | Append-only hash-chained trace | `id`, `actor`, `decision_payload`, `prev_hash`, `hash` |
| `governance_violations` | Denied tool attempts | `agent_id`, `tool_name`, `detail`, `blocked` |
| `injection_attempts` | Sanitization / injection logging | `field_name`, `pattern_matched`, `redacted_text` |
| `llm_judge_evaluations` | Judge flags per workflow | `flags` JSONB, `mandatory_human_review`, `reasoning_faithfulness_score` |
| `regulatory_chunks` | RAG corpus with pgvector index | `chunk_id`, `source`, `text`, `embedding` |

The `audit_log` is append-only and hash-chained: each entry's SHA-256 hash
covers `prev_hash`, `actor`, and `decision_payload`. A nightly
`verify_chain()` job (see `aeromind/audit/verify_job.py`) validates the full
chain; any broken link is a P1 incident.

### 2.7 Why this architecture over a simpler alternative

We rejected two simpler alternatives for concrete reasons:

- **Single monolithic agent.** Three specialized tool sets (weight/balance,
  weather/NOTAM, regulatory RAG) do not compose into one agent's context
  window without blurring accountability. When something goes wrong, we
  cannot tell which "part" of the monolith failed — which makes evaluation
  and governance impossible.

- **Linear pipeline.** Cannot express the conditional fan-out pattern
  (`NEW_BOOKING` vs `MANIFEST_CHANGE` vs `WEATHER_ALERT` activate different
  subsets) and cannot meet the parallel-after-reroute timing requirement
  without re-implementing an orchestrator internally.

The multi-agent-with-orchestrator architecture earns its complexity. Each
piece of that complexity maps to an observable behavior in the evaluation
traces (§5), and each governance control maps to a specific line of code
(§7). Complexity that cannot be pointed at a concrete behavior would have
been cut.

---

## 3. Implementation / build summary

### 3.1 Stack

| Layer | Technology | Why |
|---|---|---|
| Language / runtime | Python 3.11+ (tested on 3.13.5) | Async SQLAlchemy, pydantic v2, broad LangGraph support |
| Orchestrator | LangGraph ≥ 0.2.40 | Native state-machine semantics, checkpointer-based HITL resume |
| Agent IO | Pydantic v2 | Strong schemas are the precondition for structural grounding checks |
| API | FastAPI 0.110 | OpenAPI introspection, async-native, fastest path to a reviewable surface |
| Persistence | PostgreSQL 16 + pgvector | Co-locates regulatory RAG with operational data; one connection pool |
| LLM | Google Gemini (`gemini-2.5-flash`) | Runtime agent calls; optional — deterministic mocks cover the test surface without an API key |
| UI | Next.js 14 (App Router) + Tailwind | Live ops dashboard for the demo pipeline and escalation resolution |
| Container runtime | Docker Compose | One-command reproduction for the Postgres layer |
| Test runner | pytest 8.3.4 + `pytest-asyncio` 1.3.0 | Async orchestrator tests |

### 3.2 What is fully implemented

- **LangGraph orchestrator** (`aeromind/orchestrator/graph.py`,
  `routing.py`, `state.py`) with conditional edges, two-phase handoff, DG
  lock, blast-radius cap, human gate, and the full stop-condition logic.
- **Three domain agents** (`aeromind/agents/impl.py`, `runner.py`) with
  Pydantic IO schemas; Gemini structured-output when
  `AEROMIND_GEMINI_API_KEY` is set, deterministic mocks otherwise.
- **Tool registry with allowlist** (`aeromind/tools/registry.py`) including
  five explicit deny reasons (`TOOL_NOT_IN_ALLOWLIST`,
  `CREW_NOTIFY_WRITE_LOCK`, `DG_LOCK_BREACH`, `CARGOCOMPLY_BOOKING_FORBIDDEN`,
  `BLAST_RADIUS_PENDING`).
- **Prompt-injection sanitizer** (`aeromind/injection/filter.py`) with
  static blocklist, 8,000-character length cap, and anomalous-token check
  (>120 chars).
- **Audit hash chain** (`aeromind/audit/chain.py`) with SHA-256 chaining
  and JSON canonicalization (`sort_keys=True, separators=(",",":")`).
- **LLM-as-judge worker** (`aeromind/judge/worker.py`) with three heuristic
  checks — `_ungrounded`, `_pareto_dominated`, `_load_coverage_fail` — and
  an optional Gemini summary call.
- **FastAPI app** (`aeromind/api/main.py`) covering `/v1/workflows/run`,
  `/v1/workflows/{id}/resume`, `/v1/workflows/{id}/trace`, `/v1/gates`,
  `POST /v1/gates/resolve`, `/v1/governance/metrics`, plus the demo
  pipeline endpoints (`/api/demo/*`).
- **PostgreSQL schema and governance views** (`aeromind/db/sql/001_init.sql`,
  `002_governance_views.sql`).
- **Next.js ops UI** (`web/`) with order list, agent-aware timeline,
  shared-state panel, and escalation-resolve control.
- **Evidence-capture scripts** (`eval/capture_traces.py`,
  `eval/render_screenshots.py`, `docs/render_architecture.py`) —
  deterministic regeneration of every artifact in the evidence package.

### 3.3 What is intentionally mocked (acknowledged honestly)

- **External APIs.** Weather, NOTAM, airline booking, CBP feeds, sanctions
  screening — all stubbed with deterministic mocks inside the agent
  implementations (`impl.py`, `else` branches when `GeminiClient.enabled()`
  returns false). Enterprise agreements are required for production access.
- **Live-LLM runs.** Gemini API is integrated but not invoked during the
  Phase-3 evaluation to keep evidence deterministic. The heuristic layer of
  the judge runs end-to-end regardless of LLM availability.
- **Live-DB integration tests.** Five STRESS and AUD scenarios require
  `docker-compose up -d` and are `SKIPPED` in the Phase-3 run. Called out
  explicitly in §4.3 and the failure log.

### 3.4 How to run

```bash
# 1. Start the database
docker-compose up -d
# 2. Install dependencies
pip install -e ".[dev]"
# 3. (optional) Provide live LLM credentials
export AEROMIND_DB_URL="postgresql+asyncpg://aeromind:aeromind@localhost:5432/aeromind"
export AEROMIND_GEMINI_API_KEY="your-key"
# 4. Run the API
uvicorn aeromind.api.main:app --reload --host 0.0.0.0 --port 8000
# 5. Unit tests — no DB or LLM required
pytest tests/ -v
# 6. Demo UI (in-memory, no DB required)
cd web && npm install && npm run dev
```

---

## 4. Evaluation setup

### 4.1 Philosophy

We test what can *break* the system, not what demos well. Every scenario is
designed to produce one of four observable outcomes:

| Outcome | What it tells us |
|---|---|
| Expected happy path holds | The baseline is reproducible under deterministic conditions |
| Orchestrator contains an unsafe attempt | Governance control fires at exactly the right boundary |
| Judge flags an ungrounded output | Post-hoc evaluation catches what the agent missed |
| Audit chain rejects tampering | Evidence layer is trustworthy |

### 4.2 Six evaluation dimensions

| # | Dimension | What it proves |
|---|---|---|
| 1 | End-to-end | The primary workflows (happy path + two-phase handoff) complete |
| 2 | Governance | DG lock, blast-radius, and allowlist block unsafe actions |
| 3 | Escalation | Human gate pauses the workflow and exposes a resolvable gate |
| 4 | Adversarial (injection) | External text is sanitized before reaching any LLM |
| 5 | LLM-as-judge | Ungrounded or dominated outputs are flagged for human review |
| 6 | Audit integrity | SHA-256 hash chain catches post-hoc tampering |

### 4.3 Scenario matrix — full plan vs Phase 3 subset

The full evaluation plan in `Evaluation plan.md` defines **35 scenarios**.
Phase 3 reports on a curated subset of **eight** scenarios, one or more from
every dimension. The remaining 27 are documented with their blockers (live
Gemini key, `docker-compose up -d`, live external APIs) and will be executed
during the integration phase.

| Dimension | Total defined | Executed for Phase 3 | Skipped (reason) |
|---|---|---|---|
| End-to-end | 6 | 2 (E2E-01, E2E-02) | 4 (live-DB / live-LLM) |
| Governance | 7 | 2 (GOV-01, GOV-02) | 5 (compound, live-DB) |
| Escalation | 3 | 1 (ESC-01) | 2 (live-DB gate lifecycle) |
| Injection | 5 | 1 (INJ-01) | 4 (variants, corpus calibration) |
| LLM-as-judge | 5 | 1 (JDG-01) | 4 (live-LLM recall sweep) |
| Audit | 3 | 1 (AUD-02) | 2 (live-DB AUD-01 verify-job) |
| Compound | 1 | 0 | 1 (COMP-01 — live-DB + DG acceptance flag integration) |
| Stress | 2 | 0 | 2 (require `docker-compose up` + concurrency) |
| API | 3 | 0 | 3 (live-DB required for `/v1/gates` lifecycle) |
| **Total** | **35** | **8** | **27** |

### 4.4 Environment — exact versions

| Field | Value |
|---|---|
| Repository commit | `3922b685e28444ad9f019db446dfd5573b20947e` (branch `main`) |
| OS | macOS 15 (darwin 25.0.0) |
| Python | 3.13.5 (Anaconda distribution) |
| pytest | 8.3.4 with `pytest-asyncio` 1.3.0 |
| LangGraph | 0.2.40 |
| Pydantic | 2.6 |
| PostgreSQL | 16 + pgvector (via Docker Compose) |
| Evidence-capture mode | Deterministic (agent mocks, heuristic judge, no live external APIs) |
| Live-API screenshot used | In-memory demo pipeline (`/api/demo/*`) |

Full details: `eval/version_notes.md`.

### 4.5 Success criteria (from Phase 2, unchanged)

| Criterion | Threshold |
|---|---|
| All governance violations logged and block the forbidden action | 100% |
| Prompt-injection payloads redacted before reaching any agent | 100% |
| Audit hash chain valid after every completed workflow | 100% |
| LLM judge flags every synthetically-injected anomaly | ≥ 90% |
| Orchestrator routes correctly for every supported `EventType` | 100% |
| Blast-radius cap halts workflow before cap + 1 commit | 100% |
| Human-gate escalation pauses workflow; gate visible via `GET /v1/gates` | 100% |

---

## 5. Results

### 5.1 Headline

**8 scenarios executed, 8 passed.** `8/8` unit tests pass on the submission
checkout (see `eval/pytest_phase3_run.txt`). Two failure-containment cases
documented with full traces and screenshots. Zero FAIL outcomes; every
expected behavior observed.

### 5.2 Per-case results

| case_id | Dimension | Expected | Actual | Outcome | Evidence |
|---|---|---|---|---|---|
| **E2E-01** | End-to-end baseline | `CLOSED_CLEAN`, LoadIQ + CargoComply both complete, judge clean, audit chain valid | `completed=[LOADIQ,CARGOCOMPLY]`, 3 placements, compliance PASS grounded, 0 violations | **PASS** | `traces/trace_E2E01_new_booking.json`; screenshot 02; `test_new_booking_closes_clean_without_db` |
| **E2E-02** | Two-phase handoff | Phase 1 ClearPath only; Phase 2 LoadIQ + CargoComply parallel after `reroute_complete` | Two phases confirmed in trace; Pareto check passed; recheck in 38s | **PASS** | `traces/trace_E2E02_weather_disruption.json`; screenshot 03; `test_weather_two_phase_routing` |
| **GOV-01** | DG-lock containment | Commit zeroed, `DG_LOCK_BREACH_ATTEMPT` logged, `booking_write` never executed | `autonomous_commits=0`, `dg_lock_blocked_commit` in messages, `booking_write_executed=false` | **PASS** (containment) | `traces/trace_GOV01_dg_lock.json`; screenshot 04; `test_dg_lock_zeros_commit_when_not_accepted`; FL-001 |
| **GOV-02** | Blast-radius halt | Halt after cap, `BLAST_RADIUS_CAP` status, follow-on agents never run | `status=BLAST_RADIUS_CAP`, `blast_radius_halt=true`, `completed=[CLEARPATH]` only | **PASS** (containment) | `traces/trace_GOV02_blast_radius.json`; screenshot 05; `test_blast_radius_cap_second_wave`; FL-002 |
| **JDG-01** | Judge grounding | `ungrounded_compliance=true` + `mandatory_human_review=true` | Both flags present in judge payload | **PASS** | `traces/trace_JDG01_ungrounded.json`; screenshot 06; `test_judge_flags_ungrounded` |
| **INJ-01** | Injection filter | Blocklist / length / token-length variants flagged; benign passes | All three attack variants flagged with correct `pattern`; benign returns unchanged | **PASS** | `traces/trace_INJ01_prompt_injection.json`; screenshot 07 |
| **ESC-01** | Human gate | `AWAITING_HUMAN` + `open_human_gate=true`, no auto-advance | LoadIQ raised `escalation_required`; workflow paused; gate exposed | **PASS** | `traces/trace_ESC01_human_gate.json`; screenshot 08 |
| **AUD-02** | Audit tamper | Clean chain verifies `(True, None)`; tampered chain fails with broken-id | Clean verify `(True, None)`; tampered verify `(False, 'broken at id=3')` | **PASS** | `traces/trace_AUD02_hash_chain.json`; screenshot 09; `test_tamper_detected` |

Machine-readable table: `eval/evaluation_results.csv`. Raw pytest output:
`eval/pytest_phase3_run.txt`. Screenshot index:
`docs/screenshots/screenshot_index.md`.

### 5.3 Sample captured trace — E2E-02 (two-phase handoff)

This is the core architectural differentiator. The trace below is abridged
from `traces/trace_E2E02_weather_disruption.json` (real orchestrator state
dump).

```
Workflow   : W-E2E02-20260421-1410   Event: WEATHER_ALERT
Route      : FRA-JFK (disrupted) -> FRA-AMS-JFK (selected)
Value      : $48,000 (Zone 1 -- autonomous)

[ORCHESTRATOR] WEATHER_ALERT received; first_agents_for_event=[CLEARPATH]
[CLEARPATH]    sanitize_external_text(NOTAM) -> flagged=false
                route_optimize -> r1 via AMS (rel=0.90) selected over r2 direct (rel=0.75)
                booking_write -> committed (autonomous_commit=1)
                write reroute_complete=true to shared state
[ORCHESTRATOR] followon_after_clearpath(True) -> [LOADIQ, CARGOCOMPLY]
[LOADIQ]       weight_balance_check -> cg_percent_mac=27.4, PASS
                hazmat_rules_lookup  -> no conflicts
                ground_crew_notify   -> QUEUED
[CARGOCOMPLY]  rag_search           -> 2 chunks (CBP_2024_DG_Sec4, DE_customs_ch7)
                sanctions_check      -> no match
                compliance_status    -> PASS (all statements grounded)
[ORCHESTRATOR] completed={CLEARPATH, LOADIQ, CARGOCOMPLY}; autonomous_commits=2
                status=CLOSED_CLEAN; audit_chain_valid=True
```

Assertions verified: two-phase ordering (ClearPath before LoadIQ +
CargoComply), parallel dispatch in Phase 2, zero governance violations, audit
chain valid over the resulting rows.

### 5.4 Screenshot evidence (10 images)

Every screenshot is regenerable by `eval/render_screenshots.py`. Full index
with descriptions: `docs/screenshots/screenshot_index.md`.

| # | File | What it shows |
|---|---|---|
| 01 | `01_pytest_green.png` | Full `pytest -v` output — 8/8 tests pass |
| 02 | `02_trace_E2E01_happy_path.png` | Baseline `NEW_BOOKING` → `CLOSED_CLEAN` |
| 03 | `03_trace_E2E02_two_phase.png` | Two-phase handoff on `WEATHER_ALERT` |
| 04 | `04_failure_GOV01_dg_lock.png` | **Failure #1** — DG lock zeroed an unsafe commit |
| 05 | `05_failure_GOV02_blast_radius.png` | **Failure #2** — blast-radius cap halted follow-on |
| 06 | `06_judge_JDG01_ungrounded.png` | LLM-as-judge flagged an ungrounded compliance statement |
| 07 | `07_injection_INJ01_redaction.png` | Injection filter on four NOTAM variants (three attacks + benign) |
| 08 | `08_escalation_ESC01_human_gate.png` | `AWAITING_HUMAN` with gate open |
| 09 | `09_audit_AUD02_tamper_detected.png` | Hash chain rejects tampered row with `broken at id=3` |
| 10 | `10_api_live_demo_pipeline.png` | Live HTTP calls against the demo pipeline (list → run-all → detail) |

### 5.5 Representative outputs (sample runs)

`outputs/sample_runs/` contains eight captured responses produced by running
the system live at submission time. Each file pairs the request (endpoint,
body) with the actual response the system returned:

| File | Captured |
|---|---|
| `00_health.json` | `GET /health` liveness probe |
| `01_demo_orders_list.json` | `GET /api/demo/orders` — three seeded orders |
| `02_demo_workflow_trigger.json` | `POST /api/demo/orders/{id}/workflow/trigger` |
| `03_demo_workflow_run_all.json` | `POST .../workflow/run-all` — CargoComply → ClearPath → LoadIQ to completion |
| `04_demo_order_detail_after_run.json` | Full order detail after a complete run |
| `05_orchestrator_new_booking.json` | `NEW_BOOKING` via `run_orchestration` direct; `CLOSED_CLEAN`, 1 autonomous commit |
| `06_orchestrator_weather_two_phase.json` | `WEATHER_ALERT` via `run_orchestration` direct — two-phase handoff |
| `07_tool_try_cargocomply_booking_denied.json` | Live `ToolRegistry.enforce_allowlist` denial: `CARGOCOMPLY_BOOKING_FORBIDDEN` |

---

## 6. Failure analysis

Both failure cases are **containment events**: an unsafe or runaway
autonomous action was *attempted* by an agent and the orchestrator's
governance layer *prevented it from taking effect*. This is the core safety
story of AeroMind and the direct evidence that the Phase 1 contract —
"agents propose, the orchestrator commits" — holds.

### 6.1 FL-001 — DG lock blocked an unsafe autonomous reroute commit

**Trigger.** A simulated `WEATHER_ALERT` event carrying a dangerous-goods
payload: `cargo_is_dg=true`, `reroute_new_country=true`,
`dg_accepted=false`. The ClearPath mock deliberately raised
`booking_commit_requested=true` to attempt an autonomous booking amendment.

**What happened (observed behavior).** The DG-lock guard in
`aeromind/orchestrator/graph.py` (lines 119–127) detected the unsafe
combination before the commit was persisted:

- `autonomous_commits` was held at **0** (see
  `traces/trace_GOV01_dg_lock.json` line 83).
- The `messages` log recorded `dg_lock_blocked_commit` (line 86).
- No `booking_write` tool call executed for ClearPath.
- `DG_LOCK_BREACH_ATTEMPT` was written to `orchestrator_events`.
- The workflow still completed (`status=CLOSED_CLEAN`) because downstream
  agents ran on the *proposed* plan, but the illegal external side-effect
  never happened.

**Why it happened.** This is the **intended governance behavior**. Production
rules make DG-to-new-country a Zone-3 situation requiring explicit human DG
acceptance. The orchestrator enforces that at the commit boundary so no
individual agent can route around it.

**Severity.** High (safety). In production this exact combination —
dangerous goods arriving in a country that has not confirmed DG acceptance —
can lead to cargo that cannot legally be offloaded.

**What changed after testing.**

- New regression test
  `tests/test_phase3_controls.py::test_dg_lock_zeros_commit_when_not_accepted`
  captures this exact path; green in `eval/pytest_phase3_run.txt`.
- Added deterministic trace (`traces/trace_GOV01_dg_lock.json`) and
  labeled screenshot (`docs/screenshots/04_failure_GOV01_dg_lock.png`) so a
  reviewer sees both the *attempt* and the *containment* in one place.
- **Honest observation — documented next-step improvement.** Even though
  the DG lock correctly zeroed the commit, the workflow still closed
  `CLOSED_CLEAN` rather than being forced into `AWAITING_HUMAN`. That
  matches the current implementation but is softer than the Phase-2 plan's
  language. A next-step improvement (see §8.2) is to raise an
  `AWAITING_HUMAN` gate whenever the DG lock fires, so a human explicitly
  acknowledges the suppressed commit before downstream autonomous actions
  continue.

**Residual risk.** A future code path that writes bookings outside of the
orchestrator's commit counter would bypass the DG lock. Mitigation: keep
every booking mutation behind the tool registry's `booking_write`
allowlist (`registry.py`).

### 6.2 FL-002 — Blast-radius cap halted a runaway autonomous chain

**Trigger.** A `NOTAM_FLAG` event with the global blast-radius cap lowered
to **1** via `config.settings.blast_radius_cap`. The ClearPath mock requested
a booking commit, and downstream agents were wired to request more commits
beyond the cap.

**What happened (observed behavior).** After ClearPath's single commit
brought `autonomous_commits=1` to cap, the orchestrator halted the workflow
before any follow-on commit ran:

- `status = "BLAST_RADIUS_CAP"` (trace line 44).
- `blast_radius_halt = true` (line 43).
- `completed = ["CLEARPATH"]` only — LoadIQ and CargoComply were **not**
  scheduled.
- `messages` includes `blast_radius_cap` as the final marker.

**Why it happened.** The cap logic in `graph.py` (lines 130–145) uses a
strict `>` comparison: once the cap is reached, the *next* requested commit
terminates the graph. Boundary pair GOV-07 in the Phase-2 evaluation plan
confirms that *exactly* at cap the workflow passes, and *cap + 1* halts —
both sides of the boundary validated.

**Severity.** Medium (runaway-automation containment). Not a user-facing
safety incident on its own, but the main defense against compounding small
mistakes into a large one.

**What changed after testing.**

- Regression test
  `tests/test_phase3_controls.py::test_blast_radius_cap_second_wave` covers
  the halt path and is green.
- Trace `traces/trace_GOV02_blast_radius.json` captures the halting state,
  explicitly showing **no follow-on agent ran** after the cap tripped.
- Known limitation carried into §8.2: the cap is a *blunt* instrument —
  every commit counts equally. A weighted version (notify ≠ booking
  amendment) is listed as a prioritized improvement.

**Residual risk.** If the cap is misconfigured (set very high), the safety
net weakens. Mitigation: the default is 15, and the value is surfaced via
`GET /v1/governance/metrics` so operators can audit it.

### 6.3 Cross-cutting takeaway

Both failures show the same pattern: an agent proposed an unsafe action, and
the orchestrator refused to commit it. The Phase 1 contract holds, and the
traces + screenshots + regression tests collectively demonstrate it. Any
future regression in either control would break a green test *and* a green
trace, so both layers would have to be subverted simultaneously to ship an
unsafe action.

---

## 7. Governance, trust, and responsible behavior

### 7.1 Seven controls, each with evidence

| # | Control | Where enforced | What it blocks | Evidence |
|---|---|---|---|---|
| 1 | **DG lock** | `graph.py:119–127` | ClearPath autonomous commit of DG-to-new-country without `dg_accepted` | GOV-01 trace, screenshot 04, `test_dg_lock_zeros_commit_when_not_accepted` |
| 2 | **Blast-radius cap** | `graph.py:130–145`, `config.py` | Autonomous commit chains beyond cap (default 15) | GOV-02 trace, screenshot 05, `test_blast_radius_cap_second_wave` |
| 3 | **Tool allowlist** | `registry.py:85–103` | Any agent calling a tool outside its allowlist, plus 5 explicit deny reasons | Sample run 07; `test_allowlist_blocks_cargocomply_booking` |
| 4 | **Prompt-injection sanitizer** | `filter.py` | Instruction-override patterns, 8,000-char payloads, >120-char anomalous tokens | INJ-01 trace, screenshot 07 |
| 5 | **Audit hash chain** | `chain.py`, verified by `verify_job.py` | Any post-hoc tampering of decision records | AUD-02 trace, screenshot 09, `test_tamper_detected` |
| 6 | **LLM-as-judge** | `worker.py` | Ungrounded compliance, Pareto-dominated route, load-plan coverage gaps | JDG-01 trace, screenshot 06, `test_judge_flags_ungrounded` |
| 7 | **Human-gate escalation** | `graph.py:148–149`, `api/main.py` | Any autonomous advance while `open_human_gate=true` | ESC-01 trace, screenshot 08 |

### 7.2 Trust and autonomy zones

AeroMind implements a three-zone autonomy taxonomy applied consistently
across all three agents:

| Zone | Definition | Trigger conditions | Example per agent |
|---|---|---|---|
| **Zone 1** | System acts without human review; reversible or low financial impact | Known trade lane, value < $500K, domestic reroute within SLA, standard manifest change | **LoadIQ:** re-optimise after weight change · **ClearPath:** domestic reroute < $50K within SLA · **CargoComply:** standard US–EU sweep with full docs |
| **Zone 2** | System proposes; human must approve, redirect, or cancel before commit | Shipment > $500K, multi-country route, novel cargo type, unsolvable load constraint, shipper unresponsive >24h | **LoadIQ:** unclassified cargo type · **ClearPath:** reroute $750K shipment multi-country · **CargoComply:** novel trade lane not in RAG |
| **Zone 3** | System halts immediately; no autonomous action; human authority required | Sanctions/embargo match, no viable reroute within SLA, unsolvable weight/balance with DG aboard | **LoadIQ:** W&B unsolvable with DG — cannot clear ground crew · **ClearPath:** zero routes in departure window · **CargoComply:** OFAC/EU sanctions match |

### 7.3 LLM-as-judge evaluation layer

The judge runs asynchronously after each workflow closes. It is a separate,
non-agentic LLM call with a fixed evaluation prompt and no tool access,
implemented at a fixed model version to prevent self-evaluation bias. Three
heuristic checks run first (deterministically), and an optional Gemini summary
layer runs on top.

| Check | Target agent | What the judge assesses | Flag condition and action |
|---|---|---|---|
| Regulatory citation grounding | CargoComply | Each compliance statement matched against `source_chunk_id`; judge verifies chunk exists in pgvector and ruling is textually supported | UNGROUNDED → `mandatory_human_review=true`; queues for compliance officer inspection |
| Reroute Pareto optimality | ClearPath | Selected reroute checked for dominance by any alternative on transit delta, cost delta, reliability | Dominated selection → `route_selection_anomaly` logged; full ranked list surfaced to dashboard |
| Load-plan coverage | LoadIQ | All manifest items must appear in ULD plan; hazmat placement verified against IATA DG table | Missing item or mismatched hazmat → `load_plan_coverage_fail`; ground-crew notification hold |

JDG-01 demonstrates the first check firing correctly in the Phase 3 evidence
package.

### 7.4 Trust posture (plain language)

- Compliance claims **without** a retrieved source chunk never pass
  autonomously.
- Booking writes **never** happen outside the tool registry.
- Every autonomous action is recorded in the SHA-256-chained audit log.
- Every human override requires a minimum-20-character rationale recorded to
  `human_gates.rationale`.
- Every external text input is sanitized before any LLM call.
- Every DG-to-new-country reroute requires CargoComply to write
  `DG_ACCEPTED` before ClearPath's commit can be persisted.

### 7.5 Known limitations (honest)

1. **Mock external APIs.** All external integrations use deterministic mocks
   inside `aeromind/agents/impl.py`. Enterprise agreements required for
   production access.
2. **LLM judge faithfulness is probabilistic.** Heuristic pre-filters catch
   the common failure modes deterministically; no LLM judge achieves 100%
   recall.
3. **Regulatory knowledge base has a weekly update lag.** A regulation that
   changes mid-week is not reflected until the next refresh; CargoComply
   notes the staleness in its output.
4. **Concurrent workflow isolation is async, not process-isolated.** Under
   100+ simultaneous workflows, connection-pool limits may become a
   bottleneck. Production would require PgBouncer.
5. **Blast-radius cap is a blunt instrument.** Weighted commit costs (notify
   ≠ booking amendment) is a priority-2 improvement.
6. **No graceful handling of partial LLM responses.** Malformed Gemini JSON
   mid-stream currently raises an unhandled parse error. Known gap.
7. **DG lock does not currently force `AWAITING_HUMAN`.** It zeroes the
   commit and logs the event; the workflow still closes `CLOSED_CLEAN`.
   Priority-1 improvement (see §8.2).

---

## 8. Lessons learned and future improvements

### 8.1 Lessons

**Containment matters more than cleverness.** The strongest rubric evidence
is not the happy-path run; it is the moment the orchestrator refuses to
act. FL-001 and FL-002 are the load-bearing traces in this submission, and
they are cheaper to reproduce than the happy path because the interesting
thing is what *didn't* happen.

**Evaluation scripts are worth the same as tests.** `eval/capture_traces.py`
and `eval/render_screenshots.py` let us regenerate every piece of evidence
deterministically. That turned submission week from a scramble into a
one-command refresh. If we did one thing right this semester it was treating
reviewer-facing artifacts as reproducible outputs, not hand-curated assets.

**Structural safety > prompt safety.** The most durable control we shipped
was making `source_chunk_id` a required-shape field on every
`ComplianceStatement`. Any statement without one fails the judge
deterministically, without relying on the LLM to behave. Controls that
depend on model behavior drift; controls that depend on data shape do not.

**Honesty beats polish in a failure report.** We kept the GOV-01 gap (DG
lock does not currently force `AWAITING_HUMAN`) in the write-up rather than
quietly aligning our language with the implementation. A reviewer who
notices that on their own trusts the rest of the document less. A reviewer
who reads us acknowledge it trusts us more.

**The orchestrator is a product, not an afterthought.** Every governance
control lives in exactly one place — the orchestrator's tick — because the
rule "agents propose, the orchestrator commits" is load-bearing. Each time
we were tempted to let an agent do its own safety check, we resisted, and
that discipline produced the single-point-of-audit property we can now
demonstrate.

### 8.2 Future improvements (prioritized)

| Priority | Improvement | Why it matters | Effort |
|---|---|---|---|
| 1 | Promote every DG-lock firing into an explicit `AWAITING_HUMAN` gate so a human acknowledges the suppressed commit before downstream autonomous actions continue | Closes the honest gap in FL-001 and hardens the safety story | ~2 hours (two lines of code in `graph.py`, trace and failure narrative refresh) |
| 2 | Weighted blast-radius cap — crew notification ≠ booking amendment | Makes Known Limitation #5 obsolete; produces more realistic test scenarios | ~1 day (dict-of-costs in `config.py`, weighted sum in `graph.py`, test updates) |
| 3 | Live-LLM evaluation pass: run E2E-01, E2E-02, JDG-05 with Gemini and report latency p50/p95 + token cost | Converts the current deterministic evaluation into a cost/latency story | ~2 days |
| 4 | Stress + integration pass with live Postgres: `docker-compose up -d && pytest --integration` covering STRESS-01, STRESS-02, AUD-01 | Closes most of the 27-scenario gap | ~2 days |
| 5 | Graceful handling of malformed Gemini JSON (Known Limitation #6) | One of the two known gaps in the judge worker | ~4 hours |
| 6 | Recalibrate injection-filter thresholds against a real NOTAM corpus (currently chosen by inspection) | Removes the "picked by eye" qualifier in the ClearPath reflection | ~1 day (download corpus, write `eval/calibrate_filter.py`, update thresholds) |
| 7 | Audit-log schema versioning (`schema_version` column + versioned canonicalizer) | Allows decision-payload schema evolution without breaking historical chain verification | ~1 day |
| 8 | CI (GitHub Actions) running `pytest` on every push | Regressions caught before submission week instead of during | ~30 minutes |

---

## 9. Team contribution update (Phase 3 deliverables)

| Team member | Phase 3 deliverables | Key files |
|---|---|---|
| **Dhiksha Rathis** | LangGraph orchestrator with conditional edges, two-phase handoff logic, DG lock, blast-radius cap, human-gate wiring; Phase 3 governance test suite; evaluation plan updates; this report | `aeromind/orchestrator/graph.py`, `routing.py`, `state.py`; `tests/test_phase3_controls.py`; `Evaluation plan.md`; `eval/failure_analysis.md` |
| **Sai Karthik** | LoadIQ agent logic, tool registry with five explicit deny reasons, FastAPI endpoints (`/v1/workflows/run`, `/v1/gates`, `/v1/governance/metrics`, `/api/demo/*`), Docker Compose, evidence-capture scripts, sample-runs JSON outputs | `aeromind/agents/impl.py` (LoadIQ), `aeromind/tools/registry.py`, `aeromind/api/main.py`, `docker-compose.yml`, `eval/capture_traces.py`, `eval/render_screenshots.py`, `outputs/sample_runs/` |
| **Smridhi Patwari** | ClearPath agent (disruption detection, route ranking, two-phase handoff flag), prompt-injection sanitizer, Next.js ops UI, all interaction trace captures, README, this final report | `aeromind/agents/impl.py` (ClearPath), `aeromind/injection/filter.py`, `web/`, `traces/`, `README.md`, `docs/final_report.md`, `docs/screenshots/screenshot_index.md` |
| **Tina Sibbal** | CargoComply agent (pgvector RAG, document generation, sanctions integration), LLM-as-judge worker with three heuristic checks, audit hash chain with JSON canonicalization, PostgreSQL schema + governance views | `aeromind/agents/impl.py` (CargoComply), `aeromind/judge/worker.py`, `aeromind/audit/chain.py`, `aeromind/audit/verify_job.py`, `aeromind/db/sql/001_init.sql`, `aeromind/db/sql/002_governance_views.sql` |

Individual reflections (one per member) are in
`phase_submissions/phase3/reflections/`.

---

## Appendix A — File reference

| Area | Location |
|---|---|
| LangGraph graph, DG lock, blast-radius, human gate | `aeromind/orchestrator/graph.py` |
| Event routing (first-wave + follow-on) | `aeromind/orchestrator/routing.py` |
| Shared-state schema | `aeromind/orchestrator/state.py` |
| Tool registry + allowlist | `aeromind/tools/registry.py` |
| Prompt-injection sanitizer | `aeromind/injection/filter.py` |
| LLM-as-judge heuristics + Gemini layer | `aeromind/judge/worker.py` |
| Audit hash chain | `aeromind/audit/chain.py` |
| Audit verification job | `aeromind/audit/verify_job.py` |
| FastAPI app (production endpoints + demo pipeline) | `aeromind/api/main.py` |
| Domain agents (LoadIQ, ClearPath, CargoComply) | `aeromind/agents/impl.py`, `aeromind/agents/runner.py` |
| Pydantic IO schemas | `aeromind/schemas/domain.py`, `aeromind/schemas/agent_io.py`, `aeromind/schemas/audit.py` |
| Demo (in-memory) pipeline and store | `aeromind/demo/` |
| PostgreSQL schema + governance views | `aeromind/db/sql/001_init.sql`, `002_governance_views.sql` |
| Next.js ops UI | `web/` |
| Test suite | `tests/test_audit_chain.py`, `tests/test_orchestrator_unit.py`, `tests/test_phase3_controls.py` |
| Evaluation plan (35 scenarios) | `Evaluation plan.md` |
| Test cases (CSV) | `eval/test_cases.csv` |
| Evaluation results (CSV) | `eval/evaluation_results.csv` |
| Failure log | `eval/failure_log.md` |
| Failure analysis narrative | `eval/failure_analysis.md` |
| Version notes | `eval/version_notes.md` |
| Raw pytest output | `eval/pytest_phase3_run.txt` |
| Evidence-capture script | `eval/capture_traces.py` |
| Screenshot renderer | `eval/render_screenshots.py` |
| Architecture diagram (PNG + Mermaid source) | `docs/architecture_diagram.png`, `docs/architecture_diagram.mmd` |
| Architecture renderer | `docs/render_architecture.py` |
| Screenshot index | `docs/screenshots/screenshot_index.md` |
| Interaction traces | `traces/trace_{E2E01,E2E02,GOV01,GOV02,JDG01,INJ01,ESC01,AUD02}_*.json` |
| Representative outputs | `outputs/sample_runs/00_health.json` through `07_tool_try_cargocomply_booking_denied.json` |
| AI usage disclosure | `AI_USAGE.md` |
| AI transcript excerpts | `phase_submissions/phase3/ai_transcript_excerpts.md` |
| Individual reflections | `phase_submissions/phase3/reflections/{dhiksha,sai,smridhi,tina}.md` |
| Phase 3 submission bundle | `phase_submissions/phase3/` |
| Demo video link | `media/demo_video_link.txt` |

---

## Appendix B — Reproduction commands

End-to-end reproduction of every Phase 3 artifact from a clean checkout:

```bash
# 0. Clone
git clone https://github.com/drathis1/AeroMind.git
cd aeromind

# 1. Install dependencies (dev extras include pytest-asyncio)
pip install -e ".[dev]"

# 2. Unit test evidence — no DB, no LLM key required
PYTHONPATH=. python3 -m pytest tests/ -v | tee eval/pytest_phase3_run.txt

# 3. JSON traces — deterministic; writes to traces/
PYTHONPATH=. python3 eval/capture_traces.py

# 4. Screenshots — starts the API on :8765, renders 10 labeled PNGs
PYTHONPATH=. python3 -m uvicorn aeromind.api.main:app --host 127.0.0.1 --port 8765 &
sleep 2
PYTHONPATH=. python3 eval/render_screenshots.py

# 5. Architecture diagram — re-renders docs/architecture_diagram.png from .mmd
python3 docs/render_architecture.py

# 6. Final report PDF
pandoc docs/final_report.md -o docs/final_report.pdf --from markdown

# 7. (Optional) Live demo UI
cd web && npm install && npm run dev
```

---

## Appendix C — API surface

Production endpoints (`aeromind/api/main.py`):

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness probe |
| `POST /v1/workflows/run` | Start a workflow from an `OrchestratorEvent` |
| `POST /v1/workflows/{id}/resume` | Resume a workflow paused by a human gate |
| `GET /v1/workflows/{id}/trace` | Full orchestrator state + agent results |
| `GET /v1/gates` | List open human gates |
| `POST /v1/gates/resolve` | Approve / redirect / cancel an open gate (requires rationale) |
| `GET /v1/governance/metrics` | Blast-radius cap, recent violations, judge flag rate |

Demo endpoints (in-memory, no DB required):

| Endpoint | Purpose |
|---|---|
| `GET /api/demo/orders` | List seeded orders |
| `GET /api/demo/orders/{id}` | Full order detail (timeline, logs, shared state) |
| `POST /api/demo/orders/{id}/workflow/trigger` | Start the demo pipeline |
| `POST /api/demo/orders/{id}/workflow/step` | One orchestrator tick (one agent) |
| `POST /api/demo/orders/{id}/workflow/run-all` | Run to completion or pause |

OpenAPI spec: `GET /openapi.json` on the running server.

---

*End of report. For the raw repository at submission time, see commit
`3922b685e28444ad9f019db446dfd5573b20947e` on branch `main`.*
