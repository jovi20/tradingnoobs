from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import (
    AccountLedgerEntry,
    IdempotencyKey,
    ImportRow,
    ImportSession,
    PositionEvent,
    TradeSourceState,
    TradingAccount,
    TradingPosition,
    Transaction,
    TransactionType,
    User,
)
from services.auth_service import get_current_user
from services.account_ledger_service import sync_opening_balance_to_account_ledger


HEADER = (
    "asset_type,market,exchange_code,symbol,instrument_type,direction,"
    "action,timestamp,price,quantity,currency,commission,fee_currency,"
    "reason,note\n"
)


def row(
    *,
    symbol: str = "AAPL",
    direction: str = "LONG",
    action: str = "OPEN",
    timestamp: str = "2026-07-25T10:00:00+00:00",
    price: str = "200",
    quantity: str = "2",
    commission: str = "1.25",
) -> str:
    return (
        f"STOCK,US,NASDAQ,{symbol},SPOT,{direction},{action},{timestamp},"
        f"{price},{quantity},USD,{commission},USD,imported,note\n"
    )


class JRN012GenericImportConfirmTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.previous_temp_root = os.environ.get("TRADINGNOOBS_IMPORT_TMP_DIR")
        os.environ["TRADINGNOOBS_IMPORT_TMP_DIR"] = self.temp_dir.name
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
            email="jrn012@example.com",
            email_normalized="jrn012@example.com",
            hashed_password="hashed",
            public_id="jrn012-user",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        self.other_user = User(
            email="jrn012-other@example.com",
            email_normalized="jrn012-other@example.com",
            hashed_password="hashed",
            public_id="jrn012-other-user",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        self.account = TradingAccount(
            user=self.user,
            public_id="jrn012-account",
            name="Bootstrap account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.other_account = TradingAccount(
            user=self.other_user,
            public_id="jrn012-other-account",
            name="Other account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add_all(
            [self.user, self.other_user, self.account, self.other_account]
        )
        self.db.commit()
        self.db.refresh(self.user)
        self.db.refresh(self.other_user)
        self.db.refresh(self.account)
        self.current_user = self.user

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.current_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.client.close()
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        if self.previous_temp_root is None:
            os.environ.pop("TRADINGNOOBS_IMPORT_TMP_DIR", None)
        else:
            os.environ["TRADINGNOOBS_IMPORT_TMP_DIR"] = self.previous_temp_root
        self.temp_dir.cleanup()

    def upload(
        self,
        content: str,
        *,
        key: str = "upload-1",
        account_public_id: str | None = None,
    ) -> dict:
        response = self.client.post(
            "/api/positions/import/upload",
            headers={"Idempotency-Key": key},
            data={
                "account_id": account_public_id or self.account.public_id,
                "adapter_kind": "GENERIC_BOOTSTRAP",
            },
            files={"file": ("trades.csv", content.encode())},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def confirm(
        self,
        session: dict,
        *,
        selected: list[str] | None = None,
        key: str = "confirm-1",
    ):
        return self.client.post(
            "/api/positions/import/confirm",
            headers={"Idempotency-Key": key},
            json={
                "session_public_id": session["session_public_id"],
                "selected_row_public_ids": (
                    selected
                    if selected is not None
                    else [item["public_id"] for item in session["rows"]]
                ),
            },
        )

    def test_confirm_replays_multiple_lifecycles_and_persists_response(self):
        preview = self.upload(
            HEADER
            + row(action="OPEN", quantity="3")
            + row(action="REDUCE", quantity="1", timestamp="2026-07-25T11:00:00Z")
            + row(action="CLOSE", quantity="2", timestamp="2026-07-25T12:00:00Z")
            + row(action="OPEN", quantity="4", timestamp="2026-07-25T13:00:00Z")
            + row(
                symbol="AAPL",
                direction="SHORT",
                action="OPEN",
                quantity="5",
                timestamp="2026-07-25T10:30:00Z",
            )
        )
        response = self.confirm(preview)
        replay = self.confirm(preview)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(replay.status_code, 200, replay.text)
        self.assertEqual(replay.json(), response.json())
        payload = response.json()
        self.assertEqual(payload["status"], "COMPLETED")
        self.assertEqual(payload["selected_row_count"], 5)
        self.assertEqual(payload["position_count"], 3)
        self.assertEqual(payload["event_count"], 5)
        self.assertGreaterEqual(payload["posting_count"], 5)
        self.db.expire_all()
        self.assertEqual(self.db.query(TradingPosition).count(), 3)
        self.assertEqual(self.db.query(PositionEvent).count(), 5)
        self.assertEqual(
            self.db.get(TradingAccount, self.account.id).trade_source_state,
            TradeSourceState.MANUAL.value,
        )
        persisted = self.db.query(ImportSession).filter(
            ImportSession.public_id == preview["session_public_id"]
        ).one()
        self.assertEqual(persisted.status, "COMPLETED")
        self.assertIsNotNone(persisted.confirm_idempotency_id)
        self.assertTrue(
            all(
                item.applied_position_public_id and item.applied_event_public_id
                for item in self.db.query(ImportRow).filter(
                    ImportRow.session_id == persisted.id
                )
            )
        )
        record = self.db.get(IdempotencyKey, persisted.confirm_idempotency_id)
        self.assertIsNone(record.expires_at)
        self.assertEqual(record.response_json, payload)

        other_key = self.confirm(preview, key="confirm-2")
        self.assertEqual(other_key.status_code, 409, other_key.text)
        self.assertEqual(
            other_key.json()["detail"]["code"],
            "IMPORT_SESSION_ALREADY_CONSUMED",
        )

    def test_noop_consumes_only_session_and_keeps_account_clean(self):
        first = self.upload(HEADER + row())
        noop = self.confirm(first, selected=[])
        self.assertEqual(noop.status_code, 200, noop.text)
        self.assertEqual(noop.json()["status"], "COMPLETED_NOOP")
        self.db.expire_all()
        self.assertEqual(self.db.query(TradingPosition).count(), 0)
        self.assertEqual(
            self.db.get(TradingAccount, self.account.id).trade_source_state,
            TradeSourceState.CLEAN.value,
        )

        second = self.upload(HEADER + row(symbol="MSFT"), key="upload-2")
        completed = self.confirm(second, key="confirm-2")
        self.assertEqual(completed.status_code, 200, completed.text)
        self.assertEqual(completed.json()["status"], "COMPLETED")
        third = self.upload(HEADER + row(symbol="GOOG"), key="upload-3")
        rejected = self.confirm(third, key="confirm-3")
        self.assertEqual(rejected.status_code, 409, rejected.text)
        self.assertEqual(
            rejected.json()["detail"]["code"],
            "GENERIC_BOOTSTRAP_NOT_ELIGIBLE",
        )

    def test_selection_must_form_complete_prefix_and_rows_are_owner_bound(self):
        preview = self.upload(
            HEADER
            + row(action="OPEN", quantity="3")
            + row(action="CLOSE", quantity="3", timestamp="2026-07-25T11:00:00Z")
        )
        close_only = self.confirm(preview, selected=[preview["rows"][1]["public_id"]])
        self.assertEqual(close_only.status_code, 422, close_only.text)
        self.assertEqual(
            close_only.json()["detail"]["code"],
            "IMPORT_LIFECYCLE_ORPHAN_EVENT",
        )
        self.assertEqual(self.db.query(TradingPosition).count(), 0)
        self.db.expire_all()
        persisted = self.db.query(ImportSession).filter(
            ImportSession.public_id == preview["session_public_id"]
        ).one()
        self.assertEqual(persisted.status, "PREVIEW_READY")
        self.assertIsNone(persisted.confirm_idempotency_id)

        self.current_user = self.other_user
        other_preview = self.upload(
            HEADER + row(symbol="MSFT"),
            key="other-upload",
            account_public_id=self.other_account.public_id,
        )
        foreign_row = self.confirm(
            other_preview,
            selected=[preview["rows"][0]["public_id"]],
            key="other-confirm",
        )
        self.assertEqual(foreign_row.status_code, 404, foreign_row.text)
        self.assertEqual(
            foreign_row.json()["detail"]["code"],
            "IMPORT_ROW_NOT_FOUND",
        )

    def test_non_opening_financial_history_and_non_clean_state_are_rejected(self):
        self.db.add(
            Transaction(
                account_id=self.account.id,
                type=TransactionType.DEPOSIT,
                amount=10,
                currency="USD",
                date=datetime.now(timezone.utc),
            )
        )
        self.db.commit()
        preview = self.upload(HEADER + row())
        rejected = self.confirm(preview)
        self.assertEqual(rejected.status_code, 409, rejected.text)
        self.assertEqual(
            rejected.json()["detail"]["code"],
            "GENERIC_BOOTSTRAP_NOT_ELIGIBLE",
        )
        self.db.query(Transaction).delete()
        self.db.get(TradingAccount, self.account.id).trade_source_state = (
            TradeSourceState.MANUAL.value
        )
        self.db.commit()
        rejected_state = self.confirm(preview, key="confirm-2")
        self.assertEqual(rejected_state.status_code, 409, rejected_state.text)

    def test_opening_balance_only_and_selected_valid_rows_are_allowed(self):
        self.account.initial_balance = 1000
        sync_opening_balance_to_account_ledger(self.db, account=self.account)
        self.db.commit()
        preview = self.upload(
            HEADER
            + row(action="OPEN", quantity="1")
            + row(action="ADD", quantity="1", timestamp="2026-07-25T11:00:00Z")
            + row(action="ADD", quantity="1", timestamp="2026-07-25T11:00:00Z")
            + row(
                symbol="INVALID SYMBOL",
                action="OPEN",
                timestamp="2026-07-25T12:00:00Z",
            )
        )
        selected = [
            item["public_id"] for item in preview["rows"] if item["is_valid"]
        ]
        response = self.confirm(preview, selected=selected)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["event_count"], 3)
        self.assertEqual(response.json()["position_count"], 1)

    def test_stale_preview_and_duplicate_selection_are_rejected(self):
        preview = self.upload(HEADER + row())
        duplicated = self.confirm(
            preview,
            selected=[
                preview["rows"][0]["public_id"],
                preview["rows"][0]["public_id"],
            ],
        )
        self.assertEqual(duplicated.status_code, 422, duplicated.text)
        self.assertEqual(
            duplicated.json()["detail"]["code"],
            "DUPLICATE_IMPORT_ROW_SELECTION",
        )
        persisted_row = self.db.query(ImportRow).filter(
            ImportRow.public_id == preview["rows"][0]["public_id"]
        ).one()
        persisted_row.normalized_values_json = {
            **persisted_row.normalized_values_json,
            "quantity": "999",
        }
        self.db.commit()
        stale = self.confirm(preview, key="confirm-stale")
        self.assertEqual(stale.status_code, 409, stale.text)
        self.assertEqual(
            stale.json()["detail"]["code"],
            "STALE_IMPORT_PREVIEW",
        )

    def test_expired_cross_owner_and_fault_all_roll_back(self):
        preview = self.upload(
            HEADER
            + row(action="OPEN", quantity="3")
            + row(action="CLOSE", quantity="3", timestamp="2026-07-25T11:00:00Z")
        )
        self.current_user = self.other_user
        hidden = self.confirm(preview)
        self.assertEqual(hidden.status_code, 404, hidden.text)
        hidden_without_key = self.client.post(
            "/api/positions/import/confirm",
            json={
                "session_public_id": preview["session_public_id"],
                "selected_row_public_ids": [],
            },
        )
        self.assertEqual(hidden_without_key.status_code, 404, hidden_without_key.text)
        self.current_user = self.user

        with patch(
            "services.generic_import_confirm_service.append_truth_trade_event",
            side_effect=RuntimeError("injected replay failure"),
        ):
            with self.assertRaises(RuntimeError):
                self.confirm(preview)
        self.db.expire_all()
        self.assertEqual(self.db.query(TradingPosition).count(), 0)
        self.assertEqual(self.db.query(PositionEvent).count(), 0)
        self.assertEqual(self.db.query(AccountLedgerEntry).count(), 0)
        persisted = self.db.query(ImportSession).filter(
            ImportSession.public_id == preview["session_public_id"]
        ).one()
        self.assertEqual(persisted.status, "PREVIEW_READY")
        self.assertIsNone(persisted.confirm_idempotency_id)

        persisted.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        self.db.commit()
        expired = self.confirm(preview, key="confirm-expired")
        self.assertEqual(expired.status_code, 410, expired.text)
        self.assertEqual(
            self.db.get(ImportSession, persisted.id).status,
            "EXPIRED",
        )
