# AeroMind — AI Operations Brain for Air Cargo

**AeroMind** is a multi-agent AI platform that autonomously manages three critical operations in air cargo logistics: real-time cargo load optimization, disruption-driven flight rerouting, and regulatory compliance automation. Three specialized agents — **LoadIQ**, **ClearPath**, and **CargoComply** — operate through a LangGraph-based central orchestrator, sharing state and handing off tasks in real time.

> **Course:** Agentic Systems Studio · Track A: Technical Build · Phase 3  
> **Team:** Dhiksha Rathis, Sai Karthik, Smridhi Patwari, Tina Sibbal  
> **Video:** <https://drive.google.com/file/d/1Q5czRLLhPplQSR4hRwT4SjW2nHern6Dh/view> (5-minute walkthrough)  
> **Final report PDF:** [`docs/final_report.pdf`](docs/final_report.pdf)

---

## Table of Contents

- [System Overview](#system-overview)
- [Why Multi-Agent? Why Not Simpler?](#why-multi-agent-why-not-simpler)
- [Architecture](#architecture)
- [Agents](#agents)
- [Governance & Safety Controls](#governance--safety-controls)
- [Quick Start](#quick-start)
- [Running Tests](#running-tests)
- [Interaction Traces](#interaction-traces)
- [Evaluation Plan](#evaluation-plan)
- [Folder Guide](#folder-guide)
- [Known Limitations](#known-limitations)
- [Team Contributions](#team-contributions)

---

## System Overview

The air cargo industry operates at a 62.7% on-time delivery rate and loses over $11B annually to inefficiencies in load planning, disruption response, and compliance errors. AeroMind targets the three root causes:

| Problem | Baseline | AeroMind Target |
|---|---|---|
| Load optimization time | 2–4 hours manual | < 5 minutes |
| Disruption response time | 2–6 hours reactive | < 30 minutes proactive |
| Compliance error detection | ~40% manual | > 90% automated |

---

## Why Multi-Agent? Why Not Simpler?

This is a deliberate architectural choice, not added complexity for its own sake. Three concrete reasons a simpler approach fails:

**1. A single-agent approach collapses under tool set size.**  
LoadIQ needs the weight/balance engine, hazmat rules database, and aircraft configuration API. ClearPath needs live weather feeds, NOTAM APIs, and route optimization. CargoComply needs a regulatory RAG pipeline, sanctions screening, and document generation templates. Combining all of these into one agent produces an unmanageable context window, blurs accountability for each action, and makes evaluation impossible — you cannot tell which part of the agent failed when something goes wrong.

**2. A sequential pipeline is too slow for the departure window constraint.**  
When a reroute is confirmed, load re-optimization and compliance re-check must happen in parallel — not one after the other. A Frankfurt-to-Amsterdam reroute with a 90-minute departure window cannot afford to run CargoComply after LoadIQ finishes. The orchestrator dispatches both simultaneously the moment ClearPath writes a `reroute_complete` flag to shared state. A pipeline cannot do this without custom threading logic that reintroduces all the coordination complexity multi-agent handles natively.

**3. The three problem domains are triggered independently but share state — sequential pipelines cannot express this.**  
A new booking triggers LoadIQ and CargoComply in parallel, but has nothing to do with ClearPath. A weather alert triggers ClearPath first, then conditionally triggers the other two only after a reroute is confirmed. A manifest change with no route change triggers only LoadIQ. These are different activation patterns with shared downstream state — exactly the problem an orchestrated multi-agent graph solves, and exactly what a linear pipeline or rules engine cannot express without becoming a second orchestrator in disguise.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│  Layer 1 — Data Ingestion                                    │
│  Weather APIs · NOTAM Feeds · Airline Booking · Customs/Reg │
└───────────────────────┬─────────────────────────────────────┘
                        │ continuous event stream
┌───────────────────────▼─────────────────────────────────────┐
│  Layer 2 — Orchestrator (LangGraph)                         │
│  Event routing · Shared state · Escalation · Audit trail    │
└──────────┬────────────┬────────────────────┬────────────────┘
           │            │                    │
    ┌──────▼───┐  ┌─────▼──────┐  ┌─────────▼──────┐
    │  LoadIQ  │◄─┤ ClearPath  ├─►│  CargoComply   │
    │ (load    │  │ (rerouting)│  │ (compliance)   │
    │  optim.) │  └────────────┘  └────────────────┘
    └──────────┘        │ on confirmed reroute (both activated)
                        │
┌───────────────────────▼─────────────────────────────────────┐
│  Shared State Store                                          │
│  PostgreSQL (structured) · pgvector (regulatory RAG)        │
└───────────────────────┬─────────────────────────────────────┘
                        │ escalations surface here
┌───────────────────────▼─────────────────────────────────────┐
│  Layer 4 — Interface Layer                                   │
│  Ops Dashboard · Human-in-the-Loop · Audit Trail · Judge    │
└─────────────────────────────────────────────────────────────┘
```

Key design decisions:
- **Agents never call each other directly.** All coordination passes through the orchestrator via shared state. This prevents race conditions and gives a single point of audit.
- **Parallel activation only on confirmed reroute.** ClearPath writes `reroute_complete=true` to shared state; the orchestrator reads this flag and dispatches LoadIQ and CargoComply simultaneously.
- **Tiered autonomy.** Zone 1 (low-value, standard) → fully autonomous. Zone 2 (>$500K or multi-country) → ops manager gate. Zone 3 (DG to new country, sanctions match) → immediate hold.

---

## Agents

### LoadIQ — Cargo Load Optimization
Generates and re-generates optimized ULD load plans when the cargo manifest changes or an aircraft swap occurs.

- **Inputs:** Cargo manifest, aircraft type & ULD config, hazmat classifications, new aircraft assignment on reroute
- **Outputs:** Optimized ULD load plan, weight & balance report, hazmat conflict flags, ground crew push notification
- **Tools:** Weight/balance engine, hazmat rules DB, aircraft DB API, booking system (read/write for load plan status)
- **Autonomous:** Routine re-optimization, standard aircraft swaps
- **Gated:** Unsolvable weight/balance constraints, unknown cargo type, hazmat with no valid placement

### ClearPath — Disruption Rerouting
Proactively detects flight disruptions and reroutes cargo before departure windows close.

- **Inputs:** Live weather feeds, NOTAM & airport status, active bookings & schedules, shipper SLA requirements
- **Outputs:** Disruption alert, ranked reroute options (cost/time/reliability), amended booking, shipper ETA notification, handoff package to LoadIQ + CargoComply
- **Tools:** Weather & NOTAM APIs, route optimization engine, airline booking API (read/write), shipper notification system
- **Autonomous:** Low-value domestic reroutes, single-leg delays within SLA
- **Gated:** Shipments > $500K, multi-country reroutes, DG to new country (requires CargoComply DG acceptance first)

### CargoComply — Regulatory Compliance
Runs pre-departure compliance sweeps for every shipment and re-checks on any reroute event. All answers grounded in retrieved regulatory documents — never from parametric knowledge alone.

- **Inputs:** Shipment record (origin, dest., HS code, value), regulatory RAG knowledge base, existing shipper docs, updated route on reroute
- **Outputs:** Compliance status report, missing document checklist, pre-filled templates (AWB, EUR1, DG Declaration), shipper document requests, re-check report on reroute
- **Tools:** pgvector RAG, CBP/EASA API feeds, sanctions screening API, document generation templates
- **Autonomous:** Known trade lane sweeps, template auto-population
- **Gated:** Novel trade lane, sanctions/embargo match (immediate hold — no autonomous action ever)

---

## Governance & Safety Controls

| Control | Implementation | Effect |
|---|---|---|
| **DG lock** | `graph.py:119–127` | Blocks ClearPath from autonomously committing any reroute for a DG shipment to a new country. Requires human DG acceptance. |
| **Blast-radius cap** | `graph.py:130–145`, `config.py` | Halts the workflow after `N` autonomous commits (default: 15). Prevents runaway autonomous action chains. |
| **Tool allowlist** | `registry.py` | Each agent has a hard-coded allowlist. CargoComply cannot call `booking_write`. LoadIQ cannot call `sanctions_check`. Violations are logged to `governance_violations` and raise `PermissionError`. |
| **Prompt injection filter** | `filter.py` | Sanitizes all external text fields (NOTAM text, shipper notes) before they reach any agent. Blocks instruction-override patterns, script tags, oversized payloads (>8,000 chars), and anomalous tokens (>120 chars). |
| **Audit hash chain** | `chain.py` | Every workflow action is written to `audit_log` with a SHA-256 hash of the previous row. `verify_chain()` detects any post-hoc tampering. |
| **LLM-as-judge** | `worker.py` | After every workflow, an independent Gemini call evaluates for ungrounded compliance statements, Pareto-dominated route selection, and load plan coverage gaps. Flags trigger `mandatory_human_review`. |
| **Human-gate escalation** | `graph.py:148–149`, `api/main.py` | When any agent sets `escalation_required=true`, the workflow status moves to `AWAITING_HUMAN`. The orchestrator does not advance until `POST /v1/gates/resolve` is called. |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.11+
- `uv` or `pip` for package management

### 1. Start the database

```bash
docker-compose up -d
```

This starts PostgreSQL 16 with the pgvector extension and runs the SQL init scripts in `aeromind/db/sql/` automatically.

### 2. Install dependencies

```bash
pip install -e .
# or with uv:
uv sync
```

### 3. Set environment variables

```bash
export AEROMIND_DB_URL="postgresql+asyncpg://aeromind:aeromind@localhost:5432/aeromind"
export AEROMIND_GEMINI_API_KEY="your-key-here"   # optional — stubs work without it
```

### 4. Run the API

```bash
uvicorn aeromind.api.main:app --reload
```

### Demo UI — multi-agent cargo workflow (orchestrator + shared state)

The **demo stack** (`/api/demo/*` + Next.js `web/`) is self-contained: it uses an in-memory order store and the demo orchestrator (sequential **CargoComply → ClearPath → LoadIQ**). You do **not** need PostgreSQL running to explore the UI.

**Terminal A — API (port 8000)**

```bash
uvicorn aeromind.api.main:app --reload --port 8000
```

**Terminal B — web (port 3000)**

```bash
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) for the order list, then open any order to see the agent-aware timeline, hub diagram, swimlanes, shared-state panel, and escalation controls. The Next dev server proxies `/api/*` to the FastAPI backend.

**Useful endpoints**

- `GET /api/demo/orders` — list orders  
- `GET /api/demo/orders/{id}` — full detail (timeline, logs, shared state)  
- `POST /api/demo/orders/{id}/workflow/trigger` — start the pipeline  
- `POST /api/demo/orders/{id}/workflow/step` — run one orchestrator tick (one agent)  
- `POST /api/demo/orders/{id}/workflow/run-all` — run until pause or completion  

### 5. Run a workflow

```bash
# Happy-path new booking
curl -X POST http://localhost:8000/v1/workflows/run \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "NEW_BOOKING",
    "payload": {
      "manifest_item_ids": ["ITEM-001", "ITEM-002", "ITEM-003"],
      "shipment_value_usd": 120000,
      "cargo_is_dg": false,
      "cargo_type_changed": false
    }
  }'

# Weather disruption reroute
curl -X POST http://localhost:8000/v1/workflows/run \
  -H "Content-Type: application/json" \
  -d '{
    "event_type": "WEATHER_ALERT",
    "payload": {
      "affected_route": "FRA-JFK",
      "cargo_is_dg": false,
      "reroute_new_country": false,
      "shipment_value_usd": 85000
    }
  }'
```

---

## Running Tests

```bash
# All unit tests (no DB, no LLM required)
pytest tests/ -v

# With DB (docker-compose up first)
pytest tests/ -v --integration

# Show coverage
pytest tests/ --cov=aeromind --cov-report=term-missing
```

See [`Evaluation plan.md`](./Evaluation%20plan.md) for the full 35-scenario test matrix and execution phases.

---

## Interaction Traces

Real interaction traces captured from running workflows are in the `traces/` folder (regenerate with `eval/capture_traces.py`):

| File | Scenario | Status |
|---|---|---|
| `traces/trace_E2E01_new_booking.json` | Happy-path NEW_BOOKING, 3 items, non-DG | CLOSED_CLEAN |
| `traces/trace_E2E02_weather_disruption.json` | WEATHER_ALERT → two-phase handoff | CLOSED_CLEAN |
| `traces/trace_GOV01_dg_lock.json` | DG lock blocks autonomous commit | `dg_lock_blocked_commit` (contained) |
| `traces/trace_GOV02_blast_radius.json` | Blast-radius cap halts at cap+1 | BLAST_RADIUS_CAP |
| `traces/trace_INJ01_prompt_injection.json` | Injection in NOTAM text → redacted | REDACTED_INJECTION |
| `traces/trace_JDG01_ungrounded.json` | Judge flags ungrounded compliance statement | `mandatory_human_review=true` |
| `traces/trace_ESC01_human_gate.json` | LoadIQ `escalation_required=true` | AWAITING_HUMAN |
| `traces/trace_AUD02_hash_chain.json` | Audit hash chain verify + tamper detection | verify ok / `broken at id=3` |
| `eval/pytest_phase3_run.txt` | Full pytest run output | 8/8 PASS |

---

## Evaluation Plan

See [`Evaluation plan.md`](./Evaluation%20plan.md) for the full test matrix: 35 scenarios across 6 dimensions (end-to-end, governance, escalation, injection, LLM-as-judge, audit), with success criteria, measures, and a 4-phase execution plan.

### Phase 3 evaluation package (`eval/`)

Eight completed scenarios (including two failure-containment cases) sampled from the 35-scenario matrix. Each scenario has a real JSON trace and a labeled screenshot.

| File | Purpose |
|---|---|
| [`docs/final_report.md`](./docs/final_report.md) | **Phase 3 final report** (export to PDF) |
| [`docs/architecture_diagram.png`](./docs/architecture_diagram.png) | Standalone architecture diagram (Mermaid source: `docs/architecture_diagram.mmd`) |
| [`docs/screenshots/`](./docs/screenshots) | 10 labeled evidence PNGs + [`screenshot_index.md`](./docs/screenshots/screenshot_index.md) |
| [`eval/test_cases.csv`](./eval/test_cases.csv) | 8 scenarios: E2E-01, E2E-02, GOV-01, GOV-02, JDG-01, INJ-01, ESC-01, AUD-02 |
| [`eval/evaluation_results.csv`](./eval/evaluation_results.csv) | Actual behavior, PASS/FAIL, evidence pointers |
| [`eval/failure_log.md`](./eval/failure_log.md) | FL-001 (DG lock), FL-002 (blast-radius cap), FL-003 (evidence-path live-API 500 → iteration) in template form |
| [`eval/failure_analysis.md`](./eval/failure_analysis.md) | Narrative: trigger → behavior → severity → next steps (all three cases) |
| [`eval/version_notes.md`](./eval/version_notes.md) | Commit, env, runner versions |
| [`eval/pytest_phase3_run.txt`](./eval/pytest_phase3_run.txt) | Raw `pytest -v` output — 8/8 passed |
| [`eval/capture_traces.py`](./eval/capture_traces.py) | Deterministic evidence-capture script (writes to `traces/`) |
| [`eval/render_screenshots.py`](./eval/render_screenshots.py) | Optional: renders text-card PNGs from traces/pytest (not part of the submission report; real UI shots live in `docs/screenshots/ui/`) |
| [`AI_USAGE.md`](./AI_USAGE.md) | AI tool disclosure (Claude + Cursor usage, what we validated) |
| [`outputs/sample_runs/`](./outputs/sample_runs) | Eight captured live responses — health, demo pipeline, orchestrator, allowlist denial |
| [`media/demo_video_link.txt`](./media/demo_video_link.txt) | 5-minute demo video — [Drive link](https://drive.google.com/file/d/1Q5czRLLhPplQSR4hRwT4SjW2nHern6Dh/view) (script: [`media/demo_video_script.md`](./media/demo_video_script.md)) |
| [`eval/run_classic_experiment.py`](./eval/run_classic_experiment.py) + [`eval/classic_methodology.md`](./eval/classic_methodology.md) | 630-trial CLASSic ablation driver (A0 / A1 / A2 × 7 scenarios × 30 reps); outputs: `eval/classic_runs.csv`, `classic_summary.csv`, `classic_pairwise.csv`; radar chart: `docs/classic_radar.png` |
| [`phase_submissions/phase3/`](./phase_submissions/phase3) | Canvas submission bundle — checklist, four individual reflections, AI transcript excerpts |

Reproduce end to end:

```bash
pip install -e ".[dev]"
PYTHONPATH=. python3 -m pytest tests/ -v | tee eval/pytest_phase3_run.txt
PYTHONPATH=. python3 eval/capture_traces.py
PYTHONPATH=. python3 -m uvicorn aeromind.api.main:app --host 127.0.0.1 --port 8765 &
PYTHONPATH=. python3 eval/render_screenshots.py
python3 docs/render_architecture.py
```

---

## Folder Guide

Authoritative map of every directory a reviewer needs. Only the folders that
contain submission-relevant artifacts are listed; Python cache and build
directories are ignored.

```
AeroMind-1/
├── aeromind/                    # Python package — the system itself
│   ├── agents/                  #   LoadIQ, ClearPath, CargoComply implementations + runner
│   ├── api/                     #   FastAPI full-mode app (/v1/workflows/run, /v1/gates, /v1/governance/metrics)
│   ├── audit/                   #   SHA-256 hash chain (chain.py) + offline verify job
│   ├── db/                      #   SQLAlchemy repository + SQL for schema and governance views
│   ├── demo/                    #   In-memory demo pipeline served at /api/demo/* (no Postgres required)
│   ├── injection/               #   Prompt-injection filter (pattern + heuristic)
│   ├── judge/                   #   LLM-as-judge worker (heuristics + Gemini)
│   ├── llm/                     #   Gemini client wrapper
│   ├── orchestrator/            #   LangGraph graph, routing, shared state, DG lock, blast-radius cap
│   ├── schemas/                 #   Pydantic domain + agent I/O + audit schemas
│   └── tools/                   #   Tool registry + allowlist
├── web/                         # Next.js operator UI (order timeline, swim-lanes, shared-state panel)
├── docs/                        # Phase 3 report, diagrams, and all screenshot evidence
│   ├── final_report.md          #   Final report source (9 sections + 4 appendices)
│   ├── final_report.pdf         #   Rendered final report PDF
│   ├── architecture_diagram.*   #   System architecture diagram (Mermaid source + PNG)
│   ├── sequence_diagram.png     #   WEATHER_ALERT two-phase fan-out sequence
│   ├── classic_radar.png        #   CLASSic 5-dimension radar (A0/A1/A2 ablation)
│   ├── render_*.py              #   Diagram render scripts
│   └── screenshots/             #   10 labeled PNGs + screenshot_index.md
├── eval/                        # Evaluation plan, Phase 3 evidence, CLASSic ablation artifacts
│   ├── test_cases.csv           #   Scenarios executed for Phase 3 (9 rows incl. API-LIVE-FAIL)
│   ├── evaluation_results.csv   #   Actual behavior, outcome, evidence per scenario
│   ├── failure_log.md           #   FL-001, FL-002, FL-003 in template form
│   ├── failure_analysis.md      #   Narrative: trigger → behavior → severity → iteration
│   ├── version_notes.md         #   Env, commit, Python/pytest versions at capture and submission
│   ├── pytest_phase3_run.txt    #   Raw `pytest -v` output (8/8 PASS)
│   ├── capture_traces.py        #   Deterministic in-process trace capture → traces/*.json
│   ├── render_screenshots.py    #   Optional trace-as-PNG cards (submission uses UI PNGs in docs/screenshots/ui/)
│   ├── run_classic_experiment.py #  630-trial CLASSic ablation driver
│   ├── classic_methodology.md   #   Pre-registered ablation protocol
│   ├── classic_runs.csv         #   Raw 630-row ablation data
│   ├── classic_summary.csv      #   Per-architecture × dimension summary
│   ├── classic_pairwise.csv     #   A0-vs-A1 and A1-vs-A2 effect sizes (Cohen's d)
│   ├── ablations/               #   Ablation-config + per-arch event/tool counters
│   └── metrics/                 #   Per-run metric JSON dumps
├── tests/                       # pytest suites: governance controls, audit chain, orchestrator unit
├── traces/                      # Eight deterministic JSON state dumps (one per executed scenario)
├── outputs/sample_runs/         # Eight representative live responses (demo pipeline + full orchestrator)
├── media/                       # demo_video_link.txt (Drive URL) + demo_video_script.md (4-speaker script)
├── phase_submissions/phase3/    # Canvas submission bundle
│   ├── submission_packet.md     #   One-document submission source
│   ├── submission_packet.pdf    #   Rendered submission packet PDF
│   ├── submission_checklist.md  #   Ticked-off rubric checklist
│   ├── reflections/             #   One individual reflection per team member
│   └── ai_transcript_excerpts.md #  Redacted AI transcripts for disclosure
├── AI_USAGE.md                  # AI tool usage disclosure (Claude via Cursor, Gemini 2.5 Flash)
├── Evaluation plan.md           # 35-scenario Phase 2 evaluation matrix (basis for the 8 executed)
├── Agentic_Systems_Studio_Full_Project_Scope.md  # Course rubric (reference only)
├── docker-compose.yml           # Postgres + pgvector for full-mode evidence
├── pyproject.toml               # Package + dev dependencies
└── README.md                    # This file
```

**Reviewer shortcut.** Three files answer almost every rubric question:
`docs/final_report.pdf` (everything in one place),
`phase_submissions/phase3/submission_packet.pdf` (Canvas bundle with all
links), and `eval/pytest_phase3_run.txt` (8/8 tests green on the
submission commit).

---

## Known Limitations

These are honest constraints of the current implementation, not oversights:

**1. Mock APIs in Phases 1–2.**  
All external integrations (weather, NOTAM, airline booking, CBP) use deterministic mock responses inside the default agent runners in `aeromind/agents/impl.py` (the `else` branches when `GeminiClient.enabled()` is false). The system is designed for real API integration but enterprise agreements are required for production access.

**2. LLM judge faithfulness is probabilistic.**  
The Gemini-based judge targets ≥90% flag detection on synthetic anomalies, but no LLM judge achieves 100% recall. An ungrounded compliance statement could theoretically pass the heuristic check if phrased unusually. Mitigation: heuristic pre-filters (`worker.py:22–53`) run before the LLM call and catch the most common failure modes deterministically.

**3. Regulatory knowledge base has a weekly update lag.**  
The pgvector index is refreshed from CBP/EASA feeds weekly. A regulation that changes mid-week will not be reflected until the next refresh cycle. CargoComply notes recency limitations in its output when using a cached snapshot.

**4. Concurrent workflow isolation is async, not process-isolated.**  
STRESS-01 validates that 10 concurrent workflows do not corrupt shared state under async SQLAlchemy session isolation. Under extreme concurrency (100+ simultaneous workflows), database connection pool limits may become a bottleneck. Production deployment would require connection pooling via PgBouncer.

**5. Blast-radius cap is a blunt instrument.**  
The cap (default: 15 autonomous commits per workflow) prevents runaway action chains but does not distinguish between low-risk and high-risk commit types. A future version should implement weighted commit costs so a ground crew notification counts less than a booking amendment.

**6. No graceful handling of partial LLM responses.**  
If the Gemini API returns a malformed JSON response mid-stream, the judge worker currently raises an unhandled parse error. STRESS-02 covers timeout handling; malformed-response handling is a known gap for Phase 3.

---

## Team Contributions

### Phase 3 Contribution Update

| Area | Lead | Phase 3 Deliverables |
|---|---|---|
| **Agent architecture & orchestration** | Dhiksha | Final tuning of `graph.py` / `routing.py`; 8 Phase-3 scenarios authored in `eval/capture_traces.py`; governance regression tests in `tests/test_phase3_controls.py`; co-designed the 630-trial CLASSic ablation driver (`eval/run_classic_experiment.py`) |
| **LoadIQ + tooling + API** | Sai | Hardened tool allowlist and registry; maintained FastAPI app and Docker Compose; wrote `eval/render_screenshots.py` (optional trace cards); populated `outputs/sample_runs/` (8 JSON samples) |
| **ClearPath + UI + docs** | Smridhi | Next.js operator UI under `web/` (order timeline, swim-lanes, shared-state panel); prompt-injection filter updates; rewrote README and assembled `docs/final_report.md` (9 sections + 4 appendices) |
| **CargoComply + audit + judge** | Tina | LLM-as-judge grounding checks; SHA-256 audit chain verification; Postgres governance views; wrote `AI_USAGE.md`, demo-video script, submission packet, and reflections scaffolding |

### Phase 2 Contribution Update

| Area | Lead | Phase 2 Deliverables |
|---|---|---|
| **Agent architecture & orchestration** | Dhiksha | `graph.py` (LangGraph orchestrator, two-phase handoff, escalation logic, blast-radius cap, DG lock), `routing.py` (event-to-agent mapping), `domain.py` (EventType enum, shared state schema) |
| **LoadIQ agent** | Sai | `agents/loadiq.py` (load optimization logic, ULD assignment, weight/balance constraints), `registry.py` (tool allowlist), FastAPI app (`api/main.py`), Docker Compose setup |
| **ClearPath agent** | Smridhi | `agents/clearpath.py` (disruption detection, route ranking, reroute handoff), `filter.py` (prompt injection sanitizer), interaction traces, README |
| **CargoComply agent** | Tina | `agents/cargocomply.py` (RAG compliance sweep, document generation), `worker.py` (LLM-as-judge), `chain.py` (audit hash chain), `db/sql/` (schema & governance views) |
| **Evaluation & testing** | Dhiksha, Sai | `Evaluation plan.md` (35 scenarios, 6 dimensions, 4-phase execution plan), `tests/` (unit + integration test suite), `eval/capture_traces.py`, `eval/render_screenshots.py` |
| **Documentation** | Smridhi, Tina | README, architecture diagram, Phase 2 docx |
