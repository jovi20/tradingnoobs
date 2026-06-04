# Trading Truth Model Task 3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the minimum trading truth-model slice: `AssetMaster / TradeInstrument / TradingPosition / PositionEvent / AccountLedgerEntry / OutboxEvent` plus FIFO realized PnL.

**Architecture:** Add the new truth model alongside legacy `Position / TradeBatch` first. Route and page migration waits until the service-level lifecycle is tested. The domain service writes position events, ledger entries, and outbox events in one database transaction.

**Tech Stack:** FastAPI backend, SQLAlchemy ORM, SQLite test harness, Alembic migration baseline, Decimal accounting, pytest.

---

## Files And Responsibilities

- Create `backend/tests/test_trading_accounting_service.py`: proves FIFO matching and lifecycle service behavior.
- Create `backend/services/trading_accounting_service.py`: centralizes open/add/reduce/close accounting, FIFO lots, ledger writes, and outbox writes.
- Modify `backend/models.py`: add `AssetMaster`, `TradeInstrument`, `TradingPosition`, `PositionEvent`, `AccountLedgerEntry`, and `OutboxEvent`.
- Modify `backend/schemas.py`: add enums/read DTO shells only if required by tests; do not replace legacy API DTOs yet.
- Modify `backend/alembic/versions/20260604_0001_platform_baseline.py`: add new truth-model tables if they are part of the same hard-cutover baseline, or create a new `20260604_0002_trading_truth_model.py` migration if the baseline has already shipped.
- Modify `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`: mark Task 3 items complete only after tests and migration smoke pass.

---

### Task 3A: FIFO Accounting Unit

**Files:**
- Create: `backend/tests/test_trading_accounting_service.py`
- Create: `backend/services/trading_accounting_service.py`

- [x] **Step 1: Write failing FIFO test**

Create `backend/tests/test_trading_accounting_service.py`:

```python
from decimal import Decimal

from services.trading_accounting_service import FifoLot, match_fifo


def test_match_fifo_realizes_pnl_from_oldest_lots_first():
    lots = [
        FifoLot(quantity=Decimal("10"), price=Decimal("100"), fee=Decimal("1.00")),
        FifoLot(quantity=Decimal("5"), price=Decimal("110"), fee=Decimal("0.50")),
    ]

    result = match_fifo(lots, close_quantity=Decimal("12"), close_price=Decimal("120"), close_fee=Decimal("1.20"))

    assert result.realized_pnl_gross == Decimal("220.00")
    assert result.realized_pnl_net == Decimal("217.60")
    assert result.remaining_lots == [
        FifoLot(quantity=Decimal("3"), price=Decimal("110"), fee=Decimal("0.30")),
    ]
```

- [x] **Step 2: Run FIFO test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_match_fifo_realizes_pnl_from_oldest_lots_first -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'services.trading_accounting_service'`.

- [x] **Step 3: Implement minimal FIFO helper**

Create `backend/services/trading_accounting_service.py` with immutable `FifoLot`, `FifoMatchResult`, and `match_fifo()`.

- [x] **Step 4: Run FIFO test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_match_fifo_realizes_pnl_from_oldest_lots_first -q`

Expected: PASS.

---

### Task 3B: Truth Model Tables

**Files:**
- Modify: `backend/models.py`
- Modify: `backend/tests/test_trading_accounting_service.py`

- [x] **Step 1: Write failing model-shape test**

Add to `backend/tests/test_trading_accounting_service.py`:

```python
from models import AccountLedgerEntry, AssetMaster, OutboxEvent, PositionEvent, TradeInstrument, TradingPosition


def test_truth_model_tables_are_registered():
    assert AssetMaster.__tablename__ == "asset_master"
    assert TradeInstrument.__tablename__ == "trade_instruments"
    assert TradingPosition.__tablename__ == "trading_positions"
    assert PositionEvent.__tablename__ == "position_events"
    assert AccountLedgerEntry.__tablename__ == "account_ledger_entries"
    assert OutboxEvent.__tablename__ == "outbox_events"
```

- [x] **Step 2: Run model-shape test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_truth_model_tables_are_registered -q`

Expected: FAIL because the new models do not exist.

- [x] **Step 3: Add minimal ORM models**

Add SQLAlchemy models with `public_id`, user/account/instrument links, lifecycle fields, event fields, ledger fields, and outbox payload/status fields.

- [x] **Step 4: Run model-shape test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_truth_model_tables_are_registered -q`

Expected: PASS.

---

### Task 3C: Lifecycle Service Minimum Slice

**Files:**
- Modify: `backend/tests/test_trading_accounting_service.py`
- Modify: `backend/services/trading_accounting_service.py`

- [x] **Step 1: Write failing lifecycle service test**

Add to `backend/tests/test_trading_accounting_service.py`:

```python
from datetime import datetime, timezone
from decimal import Decimal

from models import AccountLedgerEntry, OutboxEvent, PositionEvent, TradingPosition
from services.trading_accounting_service import TradingAccountingService


def test_open_add_reduce_close_writes_events_ledger_and_outbox(db_session):
    service = TradingAccountingService(db_session)
    opened_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    position = service.open_position(
        user_id=1,
        account_id=1,
        symbol="AAPL",
        side="LONG",
        quantity=Decimal("10"),
        price=Decimal("100"),
        fee=Decimal("1.00"),
        event_time=opened_at,
        thesis="Breakout setup",
    )
    service.add_to_position(
        position_public_id=position.public_id,
        quantity=Decimal("5"),
        price=Decimal("110"),
        fee=Decimal("0.50"),
        event_time=opened_at,
    )
    service.reduce_position(
        position_public_id=position.public_id,
        quantity=Decimal("12"),
        price=Decimal("120"),
        fee=Decimal("1.20"),
        event_time=opened_at,
    )
    service.close_position(
        position_public_id=position.public_id,
        quantity=Decimal("3"),
        price=Decimal("115"),
        fee=Decimal("0.30"),
        event_time=opened_at,
    )

    stored_position = db_session.query(TradingPosition).filter_by(public_id=position.public_id).one()
    events = db_session.query(PositionEvent).filter_by(position_id=stored_position.id).order_by(PositionEvent.event_time).all()
    ledger_entries = db_session.query(AccountLedgerEntry).filter_by(related_position_id=stored_position.id).all()
    outbox_events = db_session.query(OutboxEvent).filter_by(aggregate_public_id=stored_position.public_id).all()

    assert stored_position.status == "CLOSED"
    assert stored_position.quantity_opened == Decimal("15.00000000")
    assert stored_position.quantity_closed == Decimal("15.00000000")
    assert stored_position.realized_pnl_gross == Decimal("235.00000000")
    assert stored_position.realized_pnl_net == Decimal("232.00000000")
    assert [event.event_type for event in events] == ["OPEN", "ADD", "REDUCE", "CLOSE"]
    assert len(ledger_entries) == 4
    assert len(outbox_events) == 4
```

- [x] **Step 2: Run lifecycle test and verify RED**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_open_add_reduce_close_writes_events_ledger_and_outbox -q`

Expected: FAIL because `TradingAccountingService` is not implemented.

- [x] **Step 3: Implement minimal service**

Implement `open_position()`, `add_to_position()`, `reduce_position()`, and `close_position()` with FIFO matching, ledger entries, and outbox events.

- [x] **Step 4: Run lifecycle test and verify GREEN**

Run: `cd backend && ../.venv/bin/python -m pytest tests/test_trading_accounting_service.py::test_open_add_reduce_close_writes_events_ledger_and_outbox -q`

Expected: PASS.

---

### Task 3D: Migration And Plan Verification

**Files:**
- Create or modify: `backend/alembic/versions/20260604_0002_trading_truth_model.py`
- Modify: `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`

- [x] **Step 1: Add migration for truth-model tables**

Create a migration that creates asset, instrument, trading position, event, ledger, and outbox tables for SQLite tests and PostgreSQL schemas.

Note: `outbox_events` was already created by baseline revision `20260604_0001`; revision `20260604_0002` adds the missing asset, instrument, position, event, and ledger tables without duplicating outbox.

- [x] **Step 2: Run backend tests**

Run: `cd backend && ../.venv/bin/python -m pytest tests -q`

Expected: PASS.

- [x] **Step 3: Run Alembic smoke**

Run: `cd backend && ../.venv/bin/alembic -c alembic.ini current`

Expected: command exits 0.

- [x] **Step 4: Update top-level sequencing plan**

Mark Task 3 complete only after the service tests prove open/add/reduce/close, FIFO realized PnL, ledger writes, and outbox writes.

- [x] **Step 5: Review diff**

Run: `git diff --check`

Expected: no output.
