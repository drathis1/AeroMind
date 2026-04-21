# AI Usage Disclosure — AeroMind

This file discloses every AI assistant used during Phase 3 of the project
(scoping, prototyping, evaluation, documentation). We describe *what* we
asked for, *what we changed by hand*, and *what we verified independently*.

All generative AI outputs that shipped in the submission were reviewed by at
least one team member against the actual repository. No AI output was accepted
verbatim without verification.

---

## Tools used

### 1. Anthropic Claude (Opus 4.7) via the Cursor IDE agent
**Version / date**: Cursor agent, April 21, 2026.

**What we used it for**
- Drafting the Phase 3 **evaluation package**: `eval/test_cases.csv`,
  `eval/evaluation_results.csv`, `eval/failure_log.md`,
  `eval/failure_analysis.md`, `eval/version_notes.md`.
- Writing the evidence scripts `eval/capture_traces.py` and
  `eval/render_screenshots.py`, which drive the real orchestrator and the
  live FastAPI to produce JSON traces and PNG screenshots.
- Drafting `docs/final_report.md`, `docs/screenshots/screenshot_index.md`,
  this `AI_USAGE.md`, and updates to `README.md`.
- Rendering the standalone `docs/architecture_diagram.png` with matplotlib
  (agent wrote the script `docs/render_architecture.py`).

**Representative prompt excerpts** (full transcript in appendix below)
- "we are done with phase 1 and 2 of this project, now only the evals part
  is left for phase 3 … plan out firstly how to do evals and then how to
  split in two?"
- "ok can u complete this then? make sure u get everything include
  screenshotting evidence."
- "ok can u double check against the rubric to see if what we have will
  get me 100/100? check each and every line."

**What we changed manually after the AI output**
- Corrected the narrative for FL-001 after reading
  `traces/trace_GOV01_dg_lock.json`: the DG lock zeroed the autonomous
  commit but the workflow still closed `CLOSED_CLEAN` rather than moving
  to `AWAITING_HUMAN`. We kept this honest observation in
  `eval/failure_analysis.md` and flagged the improvement as a next step
  rather than letting the AI restate Phase 2's more ambitious language.
- Switched the live-API screenshot target from `/v1/workflows/run` (needs
  Postgres) to the `/api/demo/*` endpoints (in-memory) so the screenshot
  reflects what a reviewer can actually run without Docker.
- Re-ran `pytest` and regenerated all PNGs on our own laptop to confirm the
  8/8 result; committed the freshly-dated `eval/pytest_phase3_run.txt`.

**What we verified independently**
- `pytest tests/ -v` on our machine — matched the 8/8 green output in
  `eval/pytest_phase3_run.txt`.
- Every evidence path in `eval/evaluation_results.csv` exists on disk.
- Trace JSON fields referenced in `eval/failure_analysis.md`
  (`autonomous_commits`, `messages`, `blast_radius_halt`, `status`) were
  verified against `traces/*.json`.
- Architecture diagram code references (`graph.py:119–127`, `graph.py:130–145`,
  `registry.py`, `filter.py`, `chain.py`) were checked against the actual
  source files.

### 2. Google Gemini 2.5 Flash (only when `AEROMIND_GEMINI_API_KEY` is set)
**Version**: `gemini-2.5-flash` via `google-genai` ≥ 1.0.

**What we used it for**
- Runtime LLM-as-judge summaries inside `aeromind/judge/worker.py`. When no
  API key is set, the judge falls back to deterministic heuristics and all
  Phase 3 evidence in this repo was produced via the heuristic path
  (see `trace_JDG01_ungrounded.json`).

**What we changed manually**
- We kept all rule-based judge checks (`_ungrounded`, `_pareto_dominated`,
  `_load_coverage_fail`) as deterministic pre-filters so the LLM is not the
  sole gate for `mandatory_human_review`.

**What we verified independently**
- JDG-01 was run without the API key to prove the heuristic-only path
  fires correctly.

---

## Appendix — transcripts and full prompt/response

Full prompt and response transcripts for the Cursor Claude session that
produced the Phase 3 evaluation package are preserved in the team's
chat history. A cleaned copy is stored at
`phase_submissions/phase3/ai_transcript_excerpts.md` (excerpts only, lightly
redacted for clarity). We can provide the full original on request.

Per course policy, we accept responsibility for the accuracy and
appropriateness of all AI-assisted content in this submission.
