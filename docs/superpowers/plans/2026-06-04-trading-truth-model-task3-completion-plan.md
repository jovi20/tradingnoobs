# Trading Truth Model Task 3 Completion Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the remaining Task 3 truth-model gate so new trading writes, imports, and V1 APIs use `TradingPosition / PositionEvent / AccountLedgerEntry` instead of legacy `Position / TradeBatch`.

**Architecture:** Keep legacy `/api/positions` readable until frontend hard cutover, but stop expanding it and publish new `/api/v1/trading-positions` contracts with public IDs. Extend the existing accounting service as the only write path for position lifecycle, decision-quality fields, ledger entries, outbox events, and idempotent import/job triggers.

**Tech Stack:** FastAPI, SQLAlchemy ORM, Alembic, SQLite test harness, Decimal accounting, pytest, FastAPI TestClient.

---

## Files And Responsibilities

- Modify `backend/models.py`: add decision-quality columns to `PositionEvent`, add optional event link to `AccountLedgerEntry`, and add `JobDefinition`, `JobRun`, `JobRunEvent`, and `IdempotencyKey`.
- Modify `backend/services/trading_accounting_service.py`: accept decision-quality fields, calculate unrealized PnL with FIFO remaining lots, and record dividends, fees, and cash adjustments as ledger truth.
- Create `backend/services/job_service.py`: centralize idempotency key claims and visible job-run records.
- Modify `backend/services/import_service.py`: route imported rows through `TradingAccountingService` rather than creating legacy `Position / TradeBatch`.
- Modify `backend/schemas.py`: add V1 trading truth DTOs that expose `public_id`, lifecycle fields, trust-ready decision fields, event refs, and ledger refs.
- Create `backend/routers/trading_positions.py`: publish `/api/v1/trading-positions` create/list/detail/event and ledger adjustment endpoints.
- Modify `backend/main.py`: include the V1 trading router without changing legacy `/api/positions`.
- Create `backend/alembic/versions/20260604_0003_trading_task3_completion.py`: add decision fields, event-linked ledger, job tables, and idempotency keys.
- Modify tests under `backend/tests/`: prove red-green behavior for decision fields, ledger extensions, idempotent jobs/import, V1 API shape, and migration smoke.
- Modify `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`: mark Task 3 only after verification proves the full gate.

---

### Task 3E: Decision-Quality Fields On Events

**Files:**
- Modify: `backend/tests/test_trading_accounting_service.py`
- Modify: `backend/models.py`
- Modify: `backend/services/trading_accounting_service.py`

- [x] **Step 1: Write failing decision-field test**

Add a test that opens a position with `edge_source`, `disconfirming_evidence`, `invalidation_rule`, `expected_holding_period`, `planned_exit_rule`, `sizing_rationale`, and `checklist_snapshot`, then asserts the opening `PositionEvent` exposes those fields as first-class columns.

- [x] **Step 2: Run decision-field test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_open_position_records_decision_quality_fields_on_event -q`

Expected: FAIL because `PositionEvent.edge_source` and related fields do not exist.

- [x] **Step 3: Add model and service support**

Add nullable columns to `PositionEvent` and thread optional keyword arguments through `TradingAccountingService.open_position()` into `_record_position_event()`.

- [x] **Step 4: Run decision-field test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_open_position_records_decision_quality_fields_on_event -q`

Expected: PASS.

---

### Task 3F: Ledger Truth For Dividends, Fees, And Adjustments

**Files:**
- Modify: `backend/tests/test_trading_accounting_service.py`
- Modify: `backend/models.py`
- Modify: `backend/services/trading_accounting_service.py`

- [x] **Step 1: Write failing ledger-extension test**

Add a test that calls `record_dividend()`, `record_fee()`, and `record_cash_adjustment()` and asserts they create `AccountLedgerEntry` rows with entry types `DIVIDEND`, `FEE`, and `CASH_ADJUSTMENT`, signed cash amounts, optional position linkage, and related outbox events.

- [x] **Step 2: Run ledger-extension test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_dividend_fee_and_cash_adjustment_are_ledger_truth -q`

Expected: FAIL because the accounting service methods do not exist.

- [x] **Step 3: Implement ledger extension methods**

Add `record_dividend()`, `record_fee()`, and `record_cash_adjustment()` to `TradingAccountingService`, plus optional `related_position_event_id` on `AccountLedgerEntry` for event-linked cash movements.

- [x] **Step 4: Run ledger-extension test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_dividend_fee_and_cash_adjustment_are_ledger_truth -q`

Expected: PASS.

---

### Task 3G: FIFO Unrealized PnL Boundary

**Files:**
- Modify: `backend/tests/test_trading_accounting_service.py`
- Modify: `backend/services/trading_accounting_service.py`

- [x] **Step 1: Write failing unrealized-PnL test**

Add a test that opens and partially reduces a long position, then calls `calculate_unrealized_pnl(position_public_id, current_price=Decimal("125"), fx_rate=Decimal("1"))` and asserts the remaining FIFO lots produce gross and net unrealized PnL without changing realized ledger state.

- [x] **Step 2: Run unrealized-PnL test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_unrealized_pnl_uses_remaining_fifo_lots_without_mutating_position -q`

Expected: FAIL because `calculate_unrealized_pnl()` does not exist.

- [x] **Step 3: Implement read-only unrealized calculation**

Add `calculate_unrealized_pnl()` returning gross/net Decimal values from remaining FIFO lots, close price, and FX rate. Do not write `PositionEvent`, `AccountLedgerEntry`, or `OutboxEvent`.

- [x] **Step 4: Run unrealized-PnL test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_unrealized_pnl_uses_remaining_fifo_lots_without_mutating_position -q`

Expected: PASS.

---

### Task 3H: Job And Idempotency Foundation

**Files:**
- Create: `backend/tests/test_job_service.py`
- Create: `backend/services/job_service.py`
- Modify: `backend/models.py`

- [x] **Step 1: Write failing idempotent job test**

Create a test that enqueues the same `scope/key` twice and asserts one `IdempotencyKey`, one `JobRun`, and a second call returning the existing job instead of duplicating work.

- [x] **Step 2: Run idempotent job test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_job_service.py::test_enqueue_job_reuses_existing_run_for_same_idempotency_key -q`

Expected: FAIL because `services.job_service` does not exist.

- [x] **Step 3: Implement job/idempotency models and service**

Add `JobDefinition`, `JobRun`, `JobRunEvent`, and `IdempotencyKey` models. Implement `JobService.enqueue_job()` with a `(scope, key)` uniqueness check and visible `QUEUED` job run records.

- [x] **Step 4: Run idempotent job test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_job_service.py::test_enqueue_job_reuses_existing_run_for_same_idempotency_key -q`

Expected: PASS.

---

### Task 3I: Import Writes To Trading Truth Model

**Files:**
- Create: `backend/tests/test_import_truth_model.py`
- Modify: `backend/services/import_service.py`

- [x] **Step 1: Write failing import cutover test**

Create a test that calls `ImportService._save_trade()` for an ENTRY row and an EXIT row, then asserts no legacy `Position` or `TradeBatch` rows were created while `TradingPosition`, `PositionEvent`, `AccountLedgerEntry`, and `OutboxEvent` rows exist.

- [x] **Step 2: Run import cutover test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_import_truth_model.py::test_import_save_trade_writes_trading_truth_model_not_legacy_batches -q`

Expected: FAIL because `_save_trade()` still writes legacy `Position / TradeBatch`.

- [x] **Step 3: Route import through accounting service**

Change `_save_trade()` to find open `TradingPosition` by user/account/symbol, call `open_position()` for entry rows, call `reduce_position()` or `close_position()` for exit rows, and stop importing `Position` or `TradeBatch`.

- [x] **Step 4: Run import cutover test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_import_truth_model.py::test_import_save_trade_writes_trading_truth_model_not_legacy_batches -q`

Expected: PASS.

---

### Task 3J: V1 Trading Truth API

**Files:**
- Create: `backend/tests/test_trading_positions_api.py`
- Modify: `backend/schemas.py`
- Create: `backend/routers/trading_positions.py`
- Modify: `backend/main.py`

- [x] **Step 1: Write failing V1 API test**

Create a FastAPI `TestClient` test that overrides `get_db`, authenticates with a user `public_id` token, posts to `/api/v1/trading-positions`, and asserts the response exposes `public_id`, `events`, `ledger_entries`, decision-quality fields, and no top-level internal integer `id`.

- [x] **Step 2: Run V1 API test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_positions_api.py::test_create_v1_trading_position_returns_public_contract -q`

Expected: FAIL because `/api/v1/trading-positions` does not exist.

- [x] **Step 3: Implement schemas and router**

Add V1 schemas and router endpoints for create, list, detail, add, reduce, close, dividend, fee, and cash adjustment. Include router in `main.py`. Keep legacy `/api/positions` untouched except for no new work.

- [x] **Step 4: Run V1 API test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_positions_api.py::test_create_v1_trading_position_returns_public_contract -q`

Expected: PASS.

---

### Task 3K: Migration And Gate Verification

**Files:**
- Create: `backend/alembic/versions/20260604_0003_trading_task3_completion.py`
- Modify: `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`
- Modify: `docs/superpowers/plans/2026-06-04-trading-truth-model-task3-completion-plan.md`

- [x] **Step 1: Add Alembic migration**

Create revision `20260604_0003` that adds `PositionEvent` decision fields, `AccountLedgerEntry.related_position_event_id`, `job_definitions`, `job_runs`, `job_run_events`, and `idempotency_keys`.

- [x] **Step 2: Run full backend tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests -q`

Expected: PASS.

- [x] **Step 3: Run Alembic smoke and upgrade**

Run: `cd backend && ../.venv/bin/alembic -c alembic.ini current`

Expected: command exits 0.

Run: `cd backend && env DATABASE_URL=sqlite:////private/tmp/tradingnoobs_alembic_task3_completion_verify.db ../.venv/bin/alembic -c alembic.ini upgrade head`

Expected: migrations `20260604_0001`, `20260604_0002`, and `20260604_0003` execute.

- [x] **Step 4: Update top-level sequencing plan**

Mark Task 3 items complete only if tests prove the full gate: V1 truth-model API, import cutover, ledger extensions, FIFO realized/unrealized boundaries, decision-quality fields, outbox, job model, and idempotency.

- [x] **Step 5: Review diff**

Run: `git diff --check`

Expected: no output.
