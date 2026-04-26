# Version notes — evaluation runs

| Field | Value |
| ----- | ----- |
| Repo | AeroMind (Track A) |
| Document date | 2026-04-25 |
| Git branch at submission | `phase-3` |
| Git commit at evidence capture | `3922b685e28444ad9f019db446dfd5573b20947e` (the commit under which `pytest_phase3_run.txt` and all JSON traces were produced) |
| Git commit at submission (docs + PDF export) | `e7e7783748a9aaa75682a0378f4eb4bd52a88e1e` (docs-only; re-runs of `eval/capture_traces.py` reproduce identical traces) |
| Python (evidence capture) | 3.13.5 (project requires 3.11+) |
| Test runner (evidence capture) | pytest 8.3.4 with `pytest-asyncio` 1.3.0 (installed via `pip install -e ".[dev]"`) |
| Test result | **8/8 passed** — see `eval/pytest_phase3_run.txt` |

## What was evaluated for Phase 3 packet

- **Eight completed scenarios** in `eval/test_cases.csv` / `eval/evaluation_results.csv` (E2E-01, E2E-02, GOV-01, GOV-02, JDG-01, INJ-01, ESC-01, AUD-02 — covers all six in-house evaluation dimensions). Subset of the 35-scenario matrix in `Evaluation plan.md`.
- **630-trial CLASSic ablation** (`eval/run_classic_experiment.py`, outputs in `eval/classic_runs.csv` / `classic_summary.csv` / `classic_pairwise.csv`): 7 scenarios × 3 architectures (A0 full / A1 no-governance / A2 flat sequential) × 30 repetitions. Methodology pre-registered in `eval/classic_methodology.md`.
- **Evidence**: primary source `docs/final_report.md` §5 and `eval/evaluation_results.csv`; JSON traces in `traces/`; PNG evidence in `docs/screenshots/` (10 PNGs, indexed in `screenshot_index.md`); unit-test log in `eval/pytest_phase3_run.txt`.

## Changes since Phase 2

- Evaluation artifacts consolidated under `eval/` for Canvas/reviewer navigation.
- No behavioral change required for FL-001 / FL-002 — they validate existing governance paths.

## Known environment notes

- Async orchestrator tests require **`pytest-asyncio`** (see `[tool.pytest.ini_options] asyncio_mode = auto` in `pyproject.toml`). Without `dev` extras, some tests may error or fail collection.
- Integration cases (`pytest --integration`) need `docker-compose up -d` and are out of scope for this minimal five-case package unless you explicitly run them.
