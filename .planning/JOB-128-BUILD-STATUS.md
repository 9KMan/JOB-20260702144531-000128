# JOB-128 Build Status — 2026-07-03

**Status:** PARTIAL — committed but build is not green.

## What's committed (this push)

24 untracked files added to `feat/composio-connectors`:

- FastAPI app: `src/api/main.py`, `src/api/routes/{health,ingestion}.py`, `src/api/models/schemas.py`
- Pipeline runner: `run_pipeline.py`, `run_pipeline.sh`
- Tests: `tests/test_api.py`, `tests/test_etl.py`, `tests/test_bigquery.py`
- Build monitoring: `gsd-execute-plan.py`, `monitor_build.sh`, `_send_hb.py`
- Telegram health/poller helpers: `tg_bot.py`, `tg_health.py`, `.tg_offset`
- Planning: `.planning/{STATE,REQUIREMENTS,ROADMAP,ACCEPTANCE_CRITERIA}.md`, `.planning/JOB-128-REWORK-followup.md`, `.planning/phases/01-foundation/01-PLAN.md`
- Ops notes: `deploy-notes/2026-07-03-job128-investigation.md`

## What is NOT working (must fix before final delivery)

1. **Missing dep `pydantic_settings`** — `src/api/main.py` imports `from src.core.config import settings`,
   which does `from pydantic_settings import BaseSettings`. Not in `requirements.txt`.
   Add: `pydantic-settings>=2.0`.
2. **Test fixture bug** — `tests/test_api.py` uses a `client` fixture that is never defined.
   `pytest-flask` is auto-injecting (wrong plugin — this is FastAPI, not Flask) and the
   `app` fixture it expects doesn't exist. Add an `app`/`client` fixture in `tests/conftest.py`
   using `httpx.ASGITransport`.
3. **`tests/conftest.py` is for Composio** — the existing conftest mocks Composio env vars,
   which is wrong for this app. Needs to be either split or rewritten.
4. **Tests never run green** — see `tests/test_api.py:11` for the failure shape.
5. **`requirements.txt` is incomplete** — missing `pydantic-settings`, plus `google-cloud-bigquery`,
   `apache-airflow`, `beautifulsoup4`, `pandas` will all need to be installed to actually run the
   ETL path.

## What does work

- `python -m py_compile` on `src/api/main.py`, `src/api/routes/*.py`, `src/api/models/schemas.py`,
  `run_pipeline.py`, `gsd-execute-plan.py` — all pass (syntax only).
- `run_pipeline.py` imports cleanly; `WebhookProcessor` and `ETLService` classes are present
  with `main()` entrypoint.

## Branch state

- Local: `feat/composio-connectors` (HEAD at `ae41fd0`)
- This commit: adds the 24 files listed above
- Target repo: `9KMan/JOB-20260702144531-000128`
- Target branch pushed: `feat/composio-connectors` (did NOT touch `master`)

## Recommended next steps

1. `pip install -r requirements.txt` (after adding `pydantic-settings`)
2. Fix `tests/conftest.py` to expose a FastAPI `app` fixture and a `client` AsyncClient
3. Drop or disable `pytest-flask` in `pyproject.toml`/`requirements-dev.txt`
4. Re-run `pytest tests/ -v` — should pass
5. Then push a follow-up commit and update the JOB-128 status to BUILT