# Screenshot index — Phase 3 evaluation evidence

All images in this folder are generated from **real runs** of the AeroMind
codebase — live pytest output, JSON state dumps from
`eval/capture_traces.py`, or live API requests against
`uvicorn aeromind.api.main:app`. Regenerate with
`eval/render_screenshots.py` (see the "How to regenerate" section).

| screenshot_file | what_it_shows | why_it_matters | where_it_is_discussed_in_the_report |
|---|---|---|---|
| `01_pytest_green.png` | Full `pytest -v` output: 8/8 tests pass (audit chain, two orchestration tests, four Phase-3 governance tests) | Single-glance evidence that the build under test is healthy before evaluation | Final report §5 Results; raw: `eval/pytest_phase3_run.txt` |
| `02_trace_E2E01_happy_path.png` | Orchestrator state for case E2E-01 (NEW_BOOKING → LoadIQ + CargoComply → `CLOSED_CLEAN`) | Baseline multi-agent run, placements + grounded compliance, no judge flags | §5 Results; trace `traces/trace_E2E01_new_booking.json` |
| `03_trace_E2E02_two_phase.png` | Orchestrator state for E2E-02 (WEATHER_ALERT → ClearPath first, then LoadIQ + CargoComply in parallel) | Validates the two-phase handoff that is the core architectural differentiator | §2 Architecture; trace `traces/trace_E2E02_weather_disruption.json` |
| `04_failure_GOV01_dg_lock.png` | **Failure containment #1** — DG-lock zeroed an autonomous commit and prevented a booking write on a DG-to-new-country reroute | Core safety guarantee: unsafe proposals are caught at the orchestrator commit boundary | §6 Failure analysis FL-001; `eval/failure_analysis.md`; trace `traces/trace_GOV01_dg_lock.json` |
| `05_failure_GOV02_blast_radius.png` | **Failure containment #2** — Blast-radius cap halted the workflow at cap + 1; follow-on agents did not run | Runaway-automation defense; confirms strict `>` comparator and the halt state | §6 Failure analysis FL-002; `eval/failure_analysis.md`; trace `traces/trace_GOV02_blast_radius.json` |
| `06_judge_JDG01_ungrounded.png` | LLM-as-judge flagged an ungrounded compliance statement; `mandatory_human_review=true` | Shows the evidence / trust layer: compliance claims without a source chunk are surfaced for humans | §7 Governance; trace `traces/trace_JDG01_ungrounded.json` |
| `07_injection_INJ01_redaction.png` | `sanitize_external_text` on four NOTAM payloads: blocklist match, length cap, anomalous token, benign | Defends the untrusted-external-text boundary; verifies no false positives on normal ops text | §7 Governance; trace `traces/trace_INJ01_prompt_injection.json` |
| `08_escalation_ESC01_human_gate.png` | LoadIQ raises `escalation_required`; workflow pauses with `AWAITING_HUMAN` and `open_human_gate=true` | Validates the human-in-the-loop stopping condition and gate lifecycle entry | §7 Governance; trace `traces/trace_ESC01_human_gate.json` |
| `09_audit_AUD02_tamper_detected.png` | Clean 4-row hash chain verifies; tampered row rejected with `broken at id=3` | Audit integrity: SHA-256 chain catches post-hoc manipulation | §7 Governance; trace `traces/trace_AUD02_hash_chain.json` |
| `10_api_live_demo_pipeline.png` | Live HTTP calls against the in-memory demo pipeline (list orders → run-all → fetch detail; CargoComply → ClearPath → LoadIQ) | End-to-end proof that the API + orchestrator + agents wire together outside of unit tests | §3 Implementation walkthrough |

## How to regenerate

```bash
cd <repo>
pip install -e ".[dev]"
PYTHONPATH=. python3 eval/capture_traces.py
PYTHONPATH=. python3 -m uvicorn aeromind.api.main:app --host 127.0.0.1 --port 8765 &
PYTHONPATH=. python3 eval/render_screenshots.py
python3 docs/render_architecture.py
```

All scripts are deterministic given the current agent mocks and will overwrite
the images above.
