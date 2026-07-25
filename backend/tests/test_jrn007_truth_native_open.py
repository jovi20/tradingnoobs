import os
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import (
    AccountLedgerEntry,
    IdempotencyKey,
    Position,
    PositionEvent,
    TradeSourceState,
    TradingAccount,
    TradingPosition,
    User,
)
from services.auth_service import get_current_user


class TruthNativeOpenRouterTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
        )
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        self.user = User(
            email="jrn007@example.com",
            email_normalized="jrn007@example.com",
            hashed_password="hashed",
            public_id="jrn007-user",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        self.account = TradingAccount(
            user=self.user,
            public_id="jrn007-account",
            name="Journal account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add_all([self.user, self.account])
        self.db.commit()
        self.db.refresh(self.user)
        self.db.refresh(self.account)

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

    def payload(self, **overrides):
        payload = {
            "account_id": self.account.id,
            "symbol": "AAPL",
            "exchange_code": "NASDAQ",
            "asset_type": "STOCK",
            "direction": "LONG",
            "entry_price": "200",
            "quantity": "2",
            "entry_time": "2026-07-17T10:00:00+00:00",
            "asset_metadata": {
                "core_type": "STOCK",
                "market": "US",
                "currency": "USD",
                "instrument": "SPOT",
            },
        }
        payload.update(overrides)
        return payload

    def open(self, key, payload=None):
        return self.client.post(
            "/api/positions",
            headers={"Idempotency-Key": key},
            json=payload or self.payload(),
        )

    def test_open_requires_permanent_owner_scoped_idempotency_and_replays(self):
        missing = self.client.post("/api/positions", json=self.payload())
        self.assertEqual(missing.status_code, 422)

        first = self.open(
            "open-aapl-1",
            self.payload(fee_amount="1.25", fee_currency="USD"),
        )
        replay = self.open(
            "open-aapl-1",
            self.payload(fee_amount="1.25", fee_currency="USD"),
        )
        conflict = self.open(
            "open-aapl-1",
            self.payload(quantity="3", fee_amount="1.25", fee_currency="USD"),
        )

        self.assertEqual(first.status_code, 201, first.text)
        self.assertEqual(replay.status_code, 201, replay.text)
        self.assertEqual(replay.json(), first.json())
        self.assertEqual(conflict.status_code, 409, conflict.text)
        self.assertEqual(
            conflict.json()["detail"]["code"],
            "IDEMPOTENCY_KEY_REUSED",
        )

        self.db.expire_all()
        record = self.db.query(IdempotencyKey).one()
        event = self.db.query(PositionEvent).one()
        self.assertEqual(record.status, "COMPLETED")
        self.assertIsNone(record.expires_at)
        self.assertEqual(record.source_fact_public_id, event.public_id)
        self.assertEqual(
            self.account.trade_source_state,
            TradeSourceState.MANUAL.value,
        )
        self.assertEqual(self.db.query(Position).count(), 1)
        self.assertEqual(self.db.query(TradingPosition).count(), 1)
        fee_posting = self.db.query(AccountLedgerEntry).one()
        self.assertEqual(fee_posting.posting_kind, "TRADE_FEE")
        self.assertEqual(fee_posting.amount, Decimal("-1.25000000"))

    def test_opposite_side_is_independent_but_same_side_is_rejected(self):
        long_open = self.open("open-long")
        short_open = self.open(
            "open-short",
            self.payload(direction="SHORT"),
        )
        duplicate_long = self.open("open-long-again")

        self.assertEqual(long_open.status_code, 201, long_open.text)
        self.assertEqual(short_open.status_code, 201, short_open.text)
        self.assertEqual(duplicate_long.status_code, 409, duplicate_long.text)
        self.assertEqual(
            duplicate_long.json()["detail"]["code"],
            "OPEN_POSITION_EXISTS",
        )
        self.assertEqual(self.db.query(TradingPosition).count(), 2)

    def test_naive_dst_gap_and_fold_are_rejected_without_partial_writes(self):
        self.user.timezone = "America/New_York"
        self.db.commit()
        for key, entry_time, expected_code in (
            ("dst-gap", "2026-03-08T02:30:00", "NONEXISTENT_LOCAL_TIME"),
            ("dst-fold", "2026-11-01T01:30:00", "AMBIGUOUS_LOCAL_TIME"),
        ):
            with self.subTest(entry_time=entry_time):
                response = self.open(
                    key,
                    self.payload(entry_time=entry_time),
                )
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(response.json()["detail"]["code"], expected_code)

        self.assertEqual(self.db.query(Position).count(), 0)
        self.assertEqual(self.db.query(TradingPosition).count(), 0)
        self.assertEqual(self.db.query(IdempotencyKey).count(), 0)

    def test_source_bound_account_rejects_manual_open(self):
        self.account.trade_source_state = TradeSourceState.SOURCE_BOUND.value
        self.db.commit()
        response = self.open("source-bound")
        self.assertEqual(response.status_code, 409, response.text)
        self.assertEqual(
            response.json()["detail"]["code"],
            "SOURCE_BOUND_ACCOUNT",
        )
        self.assertEqual(self.db.query(Position).count(), 0)
        self.assertEqual(self.db.query(TradingPosition).count(), 0)

    def test_open_before_latest_same_side_terminal_is_rejected(self):
        opened = self.open("chronology-open")
        self.assertEqual(opened.status_code, 201, opened.text)
        truth_public_id = opened.json()["truth_position_public_id"]
        closed = self.client.post(
            f"/api/trading-positions/{truth_public_id}/events",
            headers={"Idempotency-Key": "chronology-close"},
            json={
                "event_type": "CLOSE",
                "quantity": "2",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-07-18T10:00:00+00:00",
            },
        )
        self.assertEqual(closed.status_code, 201, closed.text)

        backdated = self.open(
            "chronology-backdated",
            self.payload(entry_time="2026-07-16T10:00:00+00:00"),
        )
        self.assertEqual(backdated.status_code, 422, backdated.text)
        self.assertEqual(
            backdated.json()["detail"]["code"],
            "EVENT_CHRONOLOGY_VIOLATION",
        )
        self.assertEqual(self.db.query(TradingPosition).count(), 1)

    def test_projection_failure_rolls_back_every_open_fact(self):
        with patch(
            "services.truth_native_open_service.project_truth_accounting_to_legacy",
            side_effect=RuntimeError("projection failed"),
        ):
            with self.assertRaisesRegex(RuntimeError, "projection failed"):
                self.open("fault-injection")

        self.db.expire_all()
        for model in (
            Position,
            TradingPosition,
            PositionEvent,
            AccountLedgerEntry,
            IdempotencyKey,
        ):
            self.assertEqual(self.db.query(model).count(), 0)
        self.assertEqual(
            self.account.trade_source_state,
            TradeSourceState.CLEAN.value,
        )


if __name__ == "__main__":
    unittest.main()
