# AI Usage Disclosure — AeroMind (Phase 3)

**Course:** Agentic Systems Studio · Track A: Technical Build
**Team:** Dhiksha Rathis, Sai Karthik, Smridhi Patwari, Tina Sibbal
**Document date:** April 2026

This file records how generative-AI tools were used in the AeroMind project,
what we asked them to do, what we changed by hand, and what we verified
independently. It follows the course packet's AI Usage Log Template.

---

## Tools used

| Tool | Version / model | Where used |
|---|---|---|
| **Anthropic Claude** (via the Claude app and Cursor chat) | Claude Sonnet and Claude Opus tiers, April 2026 | Architecture brainstorming, Python scaffolding, writing drafts, failure-analysis narratives, pytest fixtures |
| **Cursor IDE** (agent and inline-edit modes) | Cursor 1.x (April 2026 build), backed by Anthropic Claude models | In-editor code generation, multi-file refactors, running commands, fixing lints, generating trace-capture and screenshot-rendering scripts |
| **Google Gemini** (`gemini-2.5-flash`) | `google-genai >= 1.0` SDK | *Runtime* component of the product itself — LLM-as-judge worker (`aeromind/judge/worker.py`) and optional agent LLM calls (`aeromind/llm/gemini_client.py`). Not used to author code or docs. |

We did **not** use any AI tool to generate course-required evaluation numbers
without running the actual code — every `PASS` in `eval/evaluation_results.csv`
comes from a real pytest run or a real trace capture.

---

## What we used AI for

### 1. Code scaffolding and refactors

- **Where:** `aeromind/orchestrator/graph.py`, `aeromind/orchestrator/routing.py`,
  `aeromind/agents/impl.py`, `aeromind/tools/registry.py`,
  `aeromind/audit/chain.py`, `aeromind/injection/filter.py`,
  `aeromind/judge/worker.py`, the FastAPI app (`aeromind/api/main.py`),
  and the Next.js demo UI under `web/`.
- **Prompting style:** We described the Phase-2 architecture (LangGraph
  orchestrator, three specialist agents, governance controls) and asked
  Claude / Cursor to produce a first draft of each module, one at a time.
- **Example prompts (paraphrased):**
  - *"Write a LangGraph `StateGraph` that routes an ingested event to
    first-wave agents from `first_agents_for_event`, runs one wave, applies
    the DG lock and blast-radius-cap guards, and returns `CLOSED_CLEAN`,
    `AWAITING_HUMAN`, or `BLAST_RADIUS_CAP`."*
  - *"Write a SHA-256 hash chain over audit rows with a `verify_chain` that
    returns `(False, 'broken at id=<n>')` on tamper."*
  - *"Write an async FastAPI route `POST /v1/workflows/run` that builds the
    default runners, invokes the orchestrator, and serializes the final
    state."*

### 2. Tests and evidence-capture scripts

- **Where:** `tests/test_orchestrator_unit.py`, `tests/test_phase3_controls.py`,
  `tests/test_audit_chain.py`, `eval/capture_traces.py`,
  `eval/render_screenshots.py`, `docs/render_architecture.py`.
- **How used:** We described each scenario (e.g. "DG lock must zero the
  commit when `dg_accepted=false`") and let the AI draft the pytest, then we
  ran it, read the failures, and iterated until it matched the behavior we
  wanted the orchestrator to have.

### 3. Documentation drafts

- **Where:** `README.md`, `docs/final_report.md`, `eval/failure_analysis.md`,
  `eval/version_notes.md`, `docs/screenshots/screenshot_index.md`, and the
  Phase-2 / Phase-3 narratives.
- **How used:** We fed the AI the actual code, traces, and test results and
  asked it to produce the long-form prose. Every factual claim
  (file paths, line numbers, test names, trace outcomes) was manually
  cross-checked against the repository before commit.

### 4. Architecture diagram

- **Where:** `docs/architecture_diagram.mmd` and
  `docs/render_architecture.py`.
- **How used:** Claude drafted the Mermaid source; we hand-edited the
  node labels until they matched the roles defined in `routing.py` and the
  governance controls in `graph.py`, then rendered the `.png` locally.

---

## What we changed manually

- **All hand-tuned behavior in `aeromind/orchestrator/graph.py`.** The
  two-phase handoff, the DG-lock guard (lines 119–127), the blast-radius
  comparator (`>`, line 131), the escalation path, and the conditional
  `CLOSED_CLEAN` branches were edited by hand to match the Phase-1 contract
  *"agents propose, the orchestrator commits."* Earlier AI drafts used a
  looser comparator and did not zero the commit on DG lock.
- **Tool allowlist in `aeromind/tools/registry.py`.** The specific denies
  (`CARGOCOMPLY_BOOKING_FORBIDDEN`, `CREW_NOTIFY_WRITE_LOCK`,
  `DG_LOCK_BREACH`) were written by the team after reviewing the
  Phase-2 threat model; AI drafts did not include these specific names or
  the zone-based logic.
- **`aeromind/injection/filter.py`** — the blocklist patterns and the
  token-length heuristic (120 chars) were tuned by hand after running the
  INJ-01 through INJ-05 scenarios and watching which patterns produced
  false positives on real NOTAM text.
- **README structural edits.** The AI produced a long first draft; we
  rewrote the *"Why Multi-Agent? Why Not Simpler?"* section by hand so the
  three justifications matched the actual code paths rather than generic
  multi-agent claims.
- **Failure-analysis honesty edit.** The AI's first draft of FL-001 claimed
  the workflow ended in `AWAITING_HUMAN`. We traced this against
  `traces/trace_GOV01_dg_lock.json` and saw the actual status was
  `CLOSED_CLEAN`; the analysis was rewritten to record the gap and add it
  as a next-step improvement.

---

## What we independently verified

- **`pytest tests/ -v` was run locally** before each submission checkpoint.
  The captured output in `eval/pytest_phase3_run.txt` is from a real run
  (8/8 passed).
- **Every trace under `traces/`** is produced by `eval/capture_traces.py`
  driving the real orchestrator code — it is not LLM-generated JSON.
- **Every screenshot under `docs/screenshots/`** is rendered by
  `eval/render_screenshots.py` from either real pytest output or real JSON
  state dumps. They were not edited, hand-drawn, or AI-generated as images.
- **Every file-path / line-number citation** in `README.md` and
  `docs/final_report.md` was clicked through in the repository before the
  document was committed.
- **Every governance control** referenced in the final report has a
  corresponding regression test in `tests/` (green in
  `eval/pytest_phase3_run.txt`) — we did not trust the AI's prose claim
  until a test backed it up.
- **The demo UI in `web/`** was loaded locally (`npm run dev` on port 3000,
  FastAPI on port 8000) and the end-to-end flow (list → trigger → run-all
  → detail) was exercised by hand before we used screenshots from it.

---

## Things we did *not* use AI for

- Running the actual tests.
- Capturing the actual traces.
- Recording the 5-minute demo video.
- The individual contribution reflections in
  `phase_submissions/phase3/reflections/` (each team member wrote their
  own).
- Choosing the problem domain, the target user, or the three-agent split.
  Those design decisions came from the team in Phase 1 and were not
  generated.

---

## Prompt and transcript archive

Representative Claude / Cursor prompts and responses referenced above are
excerpted in
[`phase_submissions/phase3/ai_transcript_excerpts.md`](./phase_submissions/phase3/ai_transcript_excerpts.md).
Complete session transcripts are retained by each team member locally and
are available on request.

---

## Responsibility statement

Every team member listed on the submission packet has reviewed this
disclosure and accepts responsibility for the accuracy and appropriateness
of all AI-assisted material that appears in the AeroMind submission. Where
the AI produced a draft, a named team member verified it against the code
and evidence in this repository before it shipped.
