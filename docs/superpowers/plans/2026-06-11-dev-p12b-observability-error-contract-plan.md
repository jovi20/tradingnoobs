# P12B Observability Error Contract Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make backend error responses and logs operationally useful by wiring stable error codes, request IDs, and structured logging into the app.

**Architecture:** Keep existing routers and status codes stable, but add a shared HTTP exception handler that wraps errors in a predictable envelope. Use a small logging helper instead of broad logging framework churn, then replace only high-value business-path `print()` calls in this lane.

**Tech Stack:** FastAPI, Starlette exception handlers, Python `logging`, existing `unittest` suite, existing `observability.py` middleware.

---

## Files Likely To Touch

Backend:
- `backend/observability.py`
- `backend/main.py`
- `backend/tests/test_observability.py`
- `backend/routers/admin.py`
- `backend/routers/dashboard.py`
- `backend/routers/positions.py`
- `backend/services/import_service.py`
- `backend/services/llm_service.py`
- `backend/services/market_data_service.py`

Docs:
- `docs/TODO.md`
- `docs/DEVELOPER_GUIDE.md`
- `docs/superpowers/plans/2026-06-11-dev-p12b-observability-error-contract-plan.md`

---

## Task 1: Add Error Envelope Contract

**Goal:** HTTP errors return a stable shape with code, message, status, and request id.

- [x] Write failing tests in `backend/tests/test_observability.py`:
  - a `404` raised from `/api/trading-positions/example` returns `{"error": {"code": "TRADING_POSITIONS_NOT_FOUND", "message": "...", "request_id": "...", "status_code": 404}}`.
  - the response preserves `X-Request-ID`.
  - validation errors keep `422` and use `VALIDATION_REQUEST_INVALID`.
- [x] Run `cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_observability.py` and confirm the new tests fail before implementation.
- [x] Implement in `backend/observability.py`:
  - store request id on `request.state.request_id` in middleware.
  - add `infer_error_namespace(path: str)`.
  - add `build_error_response_payload(...)`.
  - add `add_error_handlers(app)`.
  - add handlers for `HTTPException`, Starlette `HTTPException`, and `RequestValidationError`.
- [x] Wire `add_error_handlers(app)` in `backend/main.py` after `add_observability_middleware(app)`.
- [x] Run `cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_observability.py` and confirm it passes.
- [x] Commit with `feat: add backend error response contract`.

P12B Task 1 result:
- Backend HTTP errors now return a compatibility-preserving payload with top-level `detail` plus a stable `error` envelope containing `code`, `message`, `request_id`, and `status_code`.
- Request IDs are stored on `request.state.request_id` by the observability middleware and reused by exception handlers.
- Validation errors use the stable `VALIDATION_REQUEST_INVALID` code.
- Route-scoped HTTP errors infer namespace from `/api/<namespace>/...`; for example, trading position 404s produce `TRADING_POSITIONS_NOT_FOUND`.

Verification log:
- RED backend: `../.venv313/bin/python -m unittest discover -s tests -p test_observability.py` failed because `add_error_handlers` did not exist.
- GREEN targeted backend: `../.venv313/bin/python -m unittest discover -s tests -p test_observability.py` ran 6 tests OK.
- P12B Task 1 bridge compatibility: `../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py` ran 9 tests OK.
- P12B Task 1 lifecycle compatibility: `../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py` ran 25 tests OK.
- P12B Task 1 OpenAPI compatibility: `../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py` ran 3 tests OK.
- Commit: `cda1a3f feat: add backend error response contract`.

Verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_observability.py
```

---

## Task 2: Add Structured Logging Helper

**Goal:** provide a lightweight structured logging path before replacing broad `print()` usage.

- [x] Write failing tests in `backend/tests/test_observability.py`:
  - `get_structured_logger("market_data")` returns a logger named `tradingnoobs.market_data`.
  - `log_event(logger, "warning", "quote_failed", symbol="MSFT")` emits a log message containing `event=quote_failed` and `symbol=MSFT`.
- [x] Run `cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_observability.py` and confirm the logging tests fail.
- [x] Implement in `backend/observability.py`:
  - `get_structured_logger(namespace: str)`.
  - `log_event(logger, level: str, event: str, **fields)`.
- [x] Run `cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_observability.py` and confirm it passes.
- [ ] Commit with `feat: add structured logging helper`.

P12B Task 2 result:
- Added `get_structured_logger(namespace)` with the `tradingnoobs.<namespace>` naming convention.
- Added `log_event(logger, level, event, **fields)` with stable `key=value` output sorted by field name.

Verification log:
- RED backend: `../.venv313/bin/python -m unittest discover -s tests -p test_observability.py` failed because `get_structured_logger` did not exist.
- GREEN targeted backend: `../.venv313/bin/python -m unittest discover -s tests -p test_observability.py` ran 8 tests OK.

Verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_observability.py
```

---

## Task 3: Replace High-Value Business Print Calls

**Goal:** remove noisy production-path prints from trading, dashboard, import, market data, and LLM services while leaving CLI ops prints alone.

- [ ] Write a failing static test in `backend/tests/test_observability.py` that rejects `print(` usage in:
  - `backend/routers/admin.py`
  - `backend/routers/dashboard.py`
  - `backend/routers/positions.py`
  - `backend/services/import_service.py`
  - `backend/services/llm_service.py`
  - `backend/services/market_data_service.py`
- [ ] Run `cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_observability.py` and confirm it fails on existing `print()` calls.
- [ ] Replace those prints with `get_structured_logger(...)` and `log_event(...)`.
- [ ] Leave CLI and ops scripts unchanged in this task.
- [ ] Run `cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_observability.py` and confirm it passes.
- [ ] Commit with `chore: replace business prints with structured logs`.

Verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_observability.py
```

---

## Task 4: P12B Completion Gate

- [ ] Backend observability tests pass.
- [ ] Backend full tests pass.
- [ ] Frontend typecheck passes.
- [ ] Frontend lint passes.
- [ ] Frontend Node tests pass.
- [ ] `git diff --check` passes.
- [ ] `docs/TODO.md` marks P12B completed or lists precise remaining blockers.

Final verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
cd ../frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
node --experimental-strip-types --test tests/*.test.mts
cd ..
git diff --check
git status --short --branch
```

---

## Stop Conditions

- Stop before changing the public response shape for successful API responses.
- Stop before rewriting every router exception into custom exception classes.
- Stop if tests show frontend code depends on raw `detail` error payloads and needs a compatibility adapter.
- Stop before changing CLI/ops `print()` output, because those commands use stdout as their interface.
