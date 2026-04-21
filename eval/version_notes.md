# Version notes — evaluation runs

| Field | Value |
| ----- | ----- |
| Repo | AeroMind (Track A) |
| Document date | 2026-04-21 |
| Git branch | main |
| Git commit | 3922b685e28444ad9f019db446dfd5573b20947e |
| Python | 3.13.7 (project requires 3.11+) |
| Test runner | pytest 9.0.2 with `pytest-asyncio` 1.3.0 (installed via `pip install -e ".[dev]"`) |
| Test result | **8/8 passed** — see `eval/pytest_phase3_run.txt` |

## What was evaluated for Phase 3 packet

- **Five completed scenarios** in `eval/test_cases.csv` / `eval/evaluation_results.csv` (subset of full matrix in `Evaluation plan.md`).
- **Evidence**: primary source `Evaluation plan.md` (filled `actual_behavior` and trace references); secondary: `tests/` when dev environment matches `pyproject.toml` `[project.optional-dependencies] dev`.

## Changes since Phase 2

- Evaluation artifacts consolidated under `eval/` for Canvas/reviewer navigation.
- No behavioral change required for FL-001 / FL-002 — they validate existing governance paths.

## Known environment notes

- Async orchestrator tests require **`pytest-asyncio`** (see `[tool.pytest.ini_options] asyncio_mode = auto` in `pyproject.toml`). Without `dev` extras, some tests may error or fail collection.
- Integration cases (`pytest --integration`) need `docker-compose up -d` and are out of scope for this minimal five-case package unless you explicitly run them.
