import os
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import (
    AccountLedgerEntry,
    AccountLedgerEntryType,
    AssetMetadata,
    BatchType,
    Position,
    PositionEvent,
    PositionEventType,
    PositionDirection,
    PositionStatus,
    TradeBatch,
    TradingAccount,
    User,
)
from services.auth_service import get_current_user
from services.legacy_truth_sync_service import sync_legacy_position_to_truth


class TradingPositionLifecycleRouterTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()

        self.user = User(
            email="lifecycle@example.com",
            email_normalized="lifecycle@example.com",
            hashed_password="hashed",
            public_id="user-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _seed_synced_position(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-public-id",
            name="IBKR Main",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)

        metadata = AssetMetadata(
            symbol="AAPL",
            name="Apple Inc.",
            core_type="STOCK",
            market="US",
            currency="USD",
            instrument="Spot",
        )
        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(account)

        legacy_position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="legacy-position",
            symbol="AAPL",
            exchange="NASDAQ",
            asset_type="EQUITY",
            direction=PositionDirection.LONG,
            status=PositionStatus.CLOSED,
            total_quantity=Decimal("0"),
            average_entry_price=Decimal("185"),
            realized_pnl=Decimal("180"),
            opened_at=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 5, 16, 0, tzinfo=timezone.utc),
            trade_review="Held plan well.",
            checklist_responses={"pre_market": True, "risk_check": False},
            asset_metadata_symbol="AAPL",
        )
        self.db.add(legacy_position)
        self.db.commit()
        self.db.refresh(legacy_position)

        self.db.add_all([
            TradeBatch(
                public_id="batch-open",
                position_id=legacy_position.id,
                type=BatchType.ENTRY,
                price=Decimal("180"),
                quantity=Decimal("5"),
                time=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
                reason="Initial breakout entry",
                emotion="Confident",
                confidence=4,
            ),
            TradeBatch(
                public_id="batch-add",
                position_id=legacy_position.id,
                type=BatchType.ENTRY,
                price=Decimal("190"),
                quantity=Decimal("5"),
                time=datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc),
                reason="Added on continuation",
                emotion="Focused",
                confidence=4,
            ),
            TradeBatch(
                public_id="batch-close",
                position_id=legacy_position.id,
                type=BatchType.EXIT,
                price=Decimal("203"),
                quantity=Decimal("10"),
                time=datetime(2026, 4, 5, 16, 0, tzinfo=timezone.utc),
                reason="Take profit",
                emotion="Calm",
                confidence=5,
                pnl=Decimal("180"),
            ),
        ])
        self.db.commit()

        return sync_legacy_position_to_truth(self.db, legacy_position.id)

    def _seed_open_synced_position(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-open-public-id",
            name="IBKR Open",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)

        metadata = AssetMetadata(
            symbol="MSFT",
            name="Microsoft",
            core_type="STOCK",
            market="US",
            currency="USD",
            instrument="Spot",
        )
        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(account)

        legacy_position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="legacy-open-position",
            symbol="MSFT",
            exchange="NASDAQ",
            asset_type="EQUITY",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=Decimal("5"),
            average_entry_price=Decimal("180"),
            realized_pnl=Decimal("0"),
            opened_at=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
            trade_review="",
            checklist_responses={"pre_market": True},
            asset_metadata_symbol="MSFT",
        )
        self.db.add(legacy_position)
        self.db.commit()
        self.db.refresh(legacy_position)

        self.db.add(
            TradeBatch(
                public_id="batch-open-msft",
                position_id=legacy_position.id,
                type=BatchType.ENTRY,
                price=Decimal("180"),
                quantity=Decimal("5"),
                time=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
                reason="Initial trend entry",
                emotion="Prepared",
                confidence=4,
            )
        )
        self.db.commit()

        return sync_legacy_position_to_truth(self.db, legacy_position.id)

    def test_lifecycle_route_returns_position_summary_and_thread(self):
        truth_position = self._seed_synced_position()

        response = self.client.get(f"/api/trading-positions/{truth_position.public_id}/lifecycle")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["position_summary"]["public_id"], truth_position.public_id)
        self.assertEqual(payload["data"]["position_summary"]["status"], "CLOSED")
        self.assertEqual(payload["data"]["position_summary"]["pnl_basis"]["cost_basis_method"], "FIFO")
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "ADD", "CLOSE"])
        self.assertEqual(payload["data"]["thesis_block"]["thesis"], "Initial breakout entry")
        cash_effects = payload["data"]["ledger_summary"]["cash_effects"]
        self.assertEqual(len(cash_effects), 1)
        self.assertEqual(cash_effects[0]["entry_type"], "REALIZED_PNL")
        self.assertEqual(float(cash_effects[0]["amount"]), 180.0)
        self.assertEqual(cash_effects[0]["currency"], "USD")

    def test_lifecycle_route_rejects_internal_numeric_id(self):
        truth_position = self._seed_synced_position()

        response = self.client.get(f"/api/trading-positions/{truth_position.id}/lifecycle")

        self.assertEqual(response.status_code, 404)

    def test_event_narrative_patch_updates_truth_event_and_returns_lifecycle(self):
        truth_position = self._seed_synced_position()
        opening_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.OPEN,
        ).one()

        response = self.client.patch(
            f"/api/trading-positions/{truth_position.public_id}/events/{opening_event.public_id}",
            json={
                "reason": "Updated breakout thesis",
                "emotion": "Focused",
                "confidence": 5,
                "thesis": "Breakout continuation after earnings reset",
                "invalidation_rule": "Lose prior day low",
                "planned_exit_rule": "Scale out above 2R",
                "sizing_rationale": "Half risk until confirmation",
                "checklist_snapshot": {"pre_market": True, "risk_check": True},
                "note": "Narrative-only truth event update.",
            },
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["meta"]["source"], "MANUAL")
        self.assertEqual(payload["data"]["position_summary"]["public_id"], truth_position.public_id)
        self.assertEqual(payload["data"]["thesis_block"]["thesis"], "Breakout continuation after earnings reset")
        self.assertEqual(payload["data"]["thesis_block"]["invalidation_rule"], "Lose prior day low")
        self.assertEqual(payload["data"]["thesis_block"]["planned_exit_rule"], "Scale out above 2R")
        self.assertEqual(payload["data"]["thesis_block"]["sizing_rationale"], "Half risk until confirmation")
        checklist = payload["data"]["thesis_block"]["checklist_snapshot"]
        self.assertEqual(checklist, [
            {"label": "pre_market", "checked": True},
            {"label": "risk_check", "checked": True},
        ])
        first_node = payload["data"]["lifecycle_thread"]["nodes"][0]
        self.assertEqual(first_node["node_public_id"], opening_event.public_id)
        self.assertEqual(first_node["summary"], "Updated breakout thesis")
        self.assertEqual(first_node["emotion"], "Focused")
        self.assertEqual(first_node["confidence"], 5)

        self.db.expire_all()
        persisted = self.db.query(PositionEvent).filter(PositionEvent.id == opening_event.id).one()
        self.assertEqual(persisted.reason, "Updated breakout thesis")
        self.assertEqual(persisted.thesis, "Breakout continuation after earnings reset")
        self.assertEqual(persisted.checklist_snapshot, {"pre_market": True, "risk_check": True})

    def test_event_narrative_patch_rejects_internal_event_id(self):
        truth_position = self._seed_synced_position()
        opening_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.OPEN,
        ).one()

        response = self.client.patch(
            f"/api/trading-positions/{truth_position.public_id}/events/{opening_event.id}",
            json={"reason": "Should not accept numeric ids"},
        )

        self.assertEqual(response.status_code, 404)

    def test_dividend_event_write_creates_truth_event_and_ledger_entry(self):
        truth_position = self._seed_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/dividends",
            json={
                "amount": "12.50",
                "currency": "USD",
                "occurred_at": "2026-04-04T12:00:00+00:00",
                "note": "Quarterly dividend",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["meta"]["source"], "MANUAL")
        self.assertEqual(Decimal(str(payload["data"]["ledger_summary"]["total_dividends"])), Decimal("12.5"))

        dividend_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.DIVIDEND,
        ).one()
        self.assertEqual(dividend_event.gross_amount, Decimal("12.50000000"))
        self.assertEqual(dividend_event.note, "Quarterly dividend")

        ledger_entry = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.position_event_id == dividend_event.id,
        ).one()
        self.assertEqual(ledger_entry.entry_type, AccountLedgerEntryType.DIVIDEND)
        self.assertEqual(ledger_entry.amount, Decimal("12.50000000"))
        self.assertEqual(ledger_entry.currency, "USD")

    def test_manual_adjustment_event_write_creates_adjustment_event_and_ledger_entry(self):
        truth_position = self._seed_open_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/adjustments",
            json={
                "amount": "-7.25",
                "currency": "USD",
                "occurred_at": "2026-04-04T12:00:00+00:00",
                "note": "Broker cash correction",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["meta"]["source"], "MANUAL")
        self.assertEqual(Decimal(str(payload["data"]["ledger_summary"]["total_adjustments"])), Decimal("-7.25"))
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_net"])), Decimal("0"))
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "MANUAL_ADJUSTMENT"])

        adjustment_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.MANUAL_ADJUSTMENT,
        ).one()
        self.assertTrue(adjustment_event.is_adjustment)
        self.assertEqual(adjustment_event.gross_amount, Decimal("-7.25000000"))
        self.assertEqual(adjustment_event.note, "Broker cash correction")

        ledger_entry = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.position_event_id == adjustment_event.id,
        ).one()
        self.assertEqual(ledger_entry.entry_type, AccountLedgerEntryType.CASH_ADJUSTMENT)
        self.assertEqual(ledger_entry.amount, Decimal("-7.25000000"))
        self.assertEqual(ledger_entry.currency, "USD")

    def test_trade_event_write_replays_fifo_and_creates_realized_pnl_ledger_entry(self):
        truth_position = self._seed_open_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "REDUCE",
                "quantity": "2",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
                "fee_amount": "1.00",
                "reason": "Scale out into strength",
                "emotion": "Calm",
                "confidence": 5,
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["meta"]["source"], "MANUAL")
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_gross"])), Decimal("60"))
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_net"])), Decimal("59"))
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["total_fees"])), Decimal("1"))
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "REDUCE"])

        self.db.expire_all()
        trade_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.REDUCE,
        ).one()
        self.assertEqual(trade_event.quantity, Decimal("2.00000000"))
        self.assertEqual(trade_event.price, Decimal("210.00000000"))
        self.assertEqual(trade_event.fee_amount, Decimal("1.00000000"))
        self.assertEqual(trade_event.realized_pnl_gross, Decimal("60.00000000"))
        self.assertEqual(trade_event.realized_pnl_net, Decimal("59.00000000"))

        ledger_entry = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.position_event_id == trade_event.id,
        ).one()
        self.assertEqual(ledger_entry.entry_type, AccountLedgerEntryType.REALIZED_PNL)
        self.assertEqual(ledger_entry.amount, Decimal("59.00000000"))
        self.assertEqual(ledger_entry.currency, "USD")

    def test_trade_event_write_add_replays_fifo_without_cash_ledger_entry(self):
        truth_position = self._seed_open_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "ADD",
                "quantity": "3",
                "price": "190",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
                "reason": "Add on continuation",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["meta"]["source"], "MANUAL")
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_gross"])), Decimal("0"))
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_net"])), Decimal("0"))
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "ADD"])

        self.db.expire_all()
        add_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.ADD,
        ).one()
        self.assertEqual(add_event.quantity, Decimal("3.00000000"))
        self.assertEqual(add_event.price, Decimal("190.00000000"))
        self.assertEqual(add_event.realized_pnl_gross, Decimal("0E-8"))
        self.assertEqual(add_event.realized_pnl_net, Decimal("0E-8"))
        self.assertEqual(
            self.db.query(AccountLedgerEntry).filter(AccountLedgerEntry.position_event_id == add_event.id).count(),
            0,
        )

    def test_trade_event_reverse_latest_event_preserves_audit_trail_and_replays_fifo(self):
        truth_position = self._seed_open_synced_position()
        reduce_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "REDUCE",
                "quantity": "2",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
                "fee_amount": "1.00",
                "reason": "Scale out into strength",
            },
        )
        self.assertEqual(reduce_response.status_code, 201)

        self.db.expire_all()
        reduce_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.REDUCE,
        ).one()

        reverse_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events/{reduce_event.public_id}/reverse",
            json={
                "occurred_at": "2026-04-04T12:00:00+00:00",
                "note": "Broker correction: reduction did not fill",
            },
        )

        self.assertEqual(reverse_response.status_code, 201)
        payload = reverse_response.json()
        self.assertEqual(payload["meta"]["source"], "MANUAL")
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_gross"])), Decimal("0"))
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_net"])), Decimal("0"))
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "REDUCE", "REVERSAL"])
        reversal_node = payload["data"]["lifecycle_thread"]["nodes"][-1]
        self.assertEqual(reversal_node["reverses_event_public_id"], reduce_event.public_id)
        cash_effects = payload["data"]["ledger_summary"]["cash_effects"]
        self.assertEqual([entry["entry_type"] for entry in cash_effects], ["REALIZED_PNL", "REALIZED_PNL"])
        self.assertEqual(Decimal(str(cash_effects[0]["amount"])), Decimal("59.0"))
        self.assertEqual(Decimal(str(cash_effects[1]["amount"])), Decimal("-59.0"))

        self.db.expire_all()
        reversal_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.REVERSAL,
        ).one()
        self.assertTrue(reversal_event.is_adjustment)
        self.assertEqual(reversal_event.reverses_event_id, reduce_event.id)
        self.assertEqual(reversal_event.realized_pnl_net, Decimal("-59.00000000"))
        reversal_ledger = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.position_event_id == reversal_event.id,
        ).one()
        self.assertEqual(reversal_ledger.entry_type, AccountLedgerEntryType.REALIZED_PNL)
        self.assertEqual(reversal_ledger.amount, Decimal("-59.00000000"))

    def test_trade_event_reverse_rejects_open_event_until_void_semantics_exist(self):
        truth_position = self._seed_open_synced_position()
        open_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.OPEN,
        ).one()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events/{open_event.public_id}/reverse",
            json={
                "occurred_at": "2026-04-04T12:00:00+00:00",
                "note": "Attempt to void opening event",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("OPEN events cannot be reversed", response.json()["detail"])
        self.db.expire_all()
        self.assertEqual(
            self.db.query(PositionEvent).filter(
                PositionEvent.position_id == truth_position.id,
                PositionEvent.event_type == PositionEventType.REVERSAL,
            ).count(),
            0,
        )

    def test_trade_event_reverse_rejects_non_latest_active_trade_event(self):
        truth_position = self._seed_open_synced_position()
        reduce_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "REDUCE",
                "quantity": "1",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
            },
        )
        self.assertEqual(reduce_response.status_code, 201)
        add_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "ADD",
                "quantity": "1",
                "price": "200",
                "currency": "USD",
                "occurred_at": "2026-04-04T15:30:00+00:00",
            },
        )
        self.assertEqual(add_response.status_code, 201)

        self.db.expire_all()
        reduce_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.REDUCE,
        ).one()
        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events/{reduce_event.public_id}/reverse",
            json={"occurred_at": "2026-04-05T12:00:00+00:00"},
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("Only the latest active trade event can be reversed", response.json()["detail"])

    def test_trade_event_reverse_rejects_duplicate_reversal(self):
        truth_position = self._seed_open_synced_position()
        reduce_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "REDUCE",
                "quantity": "2",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
                "fee_amount": "1.00",
            },
        )
        self.assertEqual(reduce_response.status_code, 201)
        self.db.expire_all()
        reduce_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.REDUCE,
        ).one()

        first_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events/{reduce_event.public_id}/reverse",
            json={"occurred_at": "2026-04-04T12:00:00+00:00"},
        )
        self.assertEqual(first_response.status_code, 201)
        second_response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events/{reduce_event.public_id}/reverse",
            json={"occurred_at": "2026-04-05T12:00:00+00:00"},
        )

        self.assertEqual(second_response.status_code, 422)
        self.assertIn("already been reversed", second_response.json()["detail"])

    def test_trade_event_write_close_marks_position_closed_and_writes_ledger_entry(self):
        truth_position = self._seed_open_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "CLOSE",
                "quantity": "5",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
                "fee_amount": "1.00",
                "reason": "Exit full position",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["data"]["position_summary"]["status"], "CLOSED")
        self.assertEqual(payload["data"]["review_status"], "CLOSED_PENDING_REVIEW")
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_gross"])), Decimal("150"))
        self.assertEqual(Decimal(str(payload["data"]["position_summary"]["realized_pnl_net"])), Decimal("149"))
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "CLOSE"])

        self.db.expire_all()
        close_event = self.db.query(PositionEvent).filter(
            PositionEvent.position_id == truth_position.id,
            PositionEvent.event_type == PositionEventType.CLOSE,
        ).one()
        ledger_entry = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.position_event_id == close_event.id,
        ).one()
        self.assertEqual(ledger_entry.entry_type, AccountLedgerEntryType.REALIZED_PNL)
        self.assertEqual(ledger_entry.amount, Decimal("149.00000000"))

    def test_trade_event_write_rejects_partial_close_without_mutating_events(self):
        truth_position = self._seed_open_synced_position()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "CLOSE",
                "quantity": "2",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("CLOSE event quantity must equal remaining open quantity", response.json()["detail"])

        self.db.expire_all()
        events = self.db.query(PositionEvent).filter(PositionEvent.position_id == truth_position.id).all()
        self.assertEqual([event.event_type for event in events], [PositionEventType.OPEN])

    def test_trade_event_write_rejects_add_on_closed_position_without_mutating_events(self):
        truth_position = self._seed_synced_position()
        original_events = self.db.query(PositionEvent).filter(PositionEvent.position_id == truth_position.id).count()

        response = self.client.post(
            f"/api/trading-positions/{truth_position.public_id}/events",
            json={
                "event_type": "ADD",
                "quantity": "1",
                "price": "205",
                "currency": "USD",
                "occurred_at": "2026-04-06T15:30:00+00:00",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertIn("Cannot append trade events to a closed trading position", response.json()["detail"])

        self.db.expire_all()
        events = self.db.query(PositionEvent).filter(PositionEvent.position_id == truth_position.id).all()
        self.assertEqual(len(events), original_events)
        self.assertEqual([event.event_type for event in events], [
            PositionEventType.OPEN,
            PositionEventType.ADD,
            PositionEventType.CLOSE,
        ])


if __name__ == "__main__":
    unittest.main()
