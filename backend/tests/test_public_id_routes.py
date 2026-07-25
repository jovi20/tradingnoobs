import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import (
    AccountLedgerEntry,
    AccountLedgerEntryType,
    LedgerPostingKind,
    Position,
    PositionDirection,
    PositionStatus,
    TradingAccount,
    User,
)
from services.account_ledger_service import sync_opening_balance_to_account_ledger
from services.auth_service import get_current_user


class PublicIdRouteTests(unittest.TestCase):
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
            email="publicid@example.com",
            email_normalized="publicid@example.com",
            hashed_password="hashed",
            public_id="user-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        self.account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-public-id",
            name="IBKR Main",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(self.account)
        self.db.commit()
        self.db.refresh(self.account)

        self.position = Position(
            user_id=self.user.id,
            account_id=self.account.id,
            public_id="pos-public-id",
            symbol="NVDA",
            exchange="NASDAQ",
            direction=PositionDirection.LONG,
            status=PositionStatus.CLOSED,
            total_quantity=1,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )
        self.db.add(self.position)
        self.db.commit()
        self.db.refresh(self.position)

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

    def test_accounts_list_and_get_include_and_accept_public_id(self):
        list_response = self.client.get("/api/accounts")
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        self.assertEqual(payload[0]["public_id"], "acct-public-id")

        get_response = self.client.get("/api/accounts/acct-public-id")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["id"], self.account.id)
        self.assertEqual(get_response.json()["public_id"], "acct-public-id")

    def test_account_read_does_not_call_market_data_or_claim_nav(self):
        self.account.cash_balance = Decimal("1000")
        self.db.add_all(
            [
                Position(
                    user_id=self.user.id,
                    account_id=self.account.id,
                    public_id="pos-account-long",
                    symbol="LONGX",
                    exchange="NASDAQ",
                    direction=PositionDirection.LONG,
                    status=PositionStatus.OPEN,
                    total_quantity=Decimal("2"),
                    average_entry_price=Decimal("100"),
                    opened_at=datetime.now(timezone.utc),
                ),
                Position(
                    user_id=self.user.id,
                    account_id=self.account.id,
                    public_id="pos-account-short",
                    symbol="SHORTX",
                    exchange="NASDAQ",
                    direction=PositionDirection.SHORT,
                    status=PositionStatus.OPEN,
                    total_quantity=Decimal("3"),
                    average_entry_price=Decimal("50"),
                    opened_at=datetime.now(timezone.utc),
                ),
            ]
        )
        self.db.commit()

        get_response = self.client.get("/api/accounts/acct-public-id")

        self.assertEqual(get_response.status_code, 200)
        payload = get_response.json()
        self.assertEqual(Decimal(str(payload["journal_balance"])), Decimal("0"))
        for legacy_or_market_field in (
            "cash_balance",
            "current_balance",
            "market_value",
            "total_equity",
        ):
            self.assertNotIn(legacy_or_market_field, payload)

    def test_account_cash_balance_prefers_ledger_derived_read_model(self):
        self.account.initial_balance = Decimal("1000")
        self.account.cash_balance = Decimal("9999")
        sync_opening_balance_to_account_ledger(self.db, account=self.account)
        self.db.add(
            AccountLedgerEntry(
                public_id="ledger-cash-out",
                user_id=self.user.id,
                account_id=self.account.id,
                entry_type=AccountLedgerEntryType.WITHDRAWAL,
                source_fact_public_id="withdrawal-fact",
                posting_kind=LedgerPostingKind.WITHDRAWAL.value,
                occurred_at=datetime.now(timezone.utc),
                currency="USD",
                amount=Decimal("-25"),
                amount_account_ccy=Decimal("-25"),
                source="TEST",
            )
        )
        self.db.commit()

        get_response = self.client.get("/api/accounts/acct-public-id")

        self.assertEqual(get_response.status_code, 200)
        payload = get_response.json()
        self.assertEqual(Decimal(str(payload["journal_balance"])), Decimal("975"))
        self.assertNotIn("cash_balance", payload)
        self.assertNotIn("total_equity", payload)

    def test_account_create_and_update_reject_non_usd_currency(self):
        create_response = self.client.post(
            "/api/accounts",
            headers={"Idempotency-Key": "opening-ledger-account"},
            json={
                "name": "Unsupported Currency",
                "broker": "IBKR",
                "currency": "USDT",
            },
        )

        self.assertEqual(create_response.status_code, 422)
        self.assertEqual(
            create_response.json()["detail"]["code"],
            "UNSUPPORTED_RELEASE_CURRENCY",
        )
        self.assertEqual(
            self.db.query(TradingAccount).filter(
                TradingAccount.name == "Unsupported Currency"
            ).count(),
            0,
        )

        update_response = self.client.patch(
            "/api/accounts/acct-public-id",
            json={"currency": "HKD"},
        )

        self.assertEqual(update_response.status_code, 422)
        self.assertEqual(self.account.currency, "USD")

    def test_account_create_writes_opening_balance_ledger_entry(self):
        create_response = self.client.post(
            "/api/accounts",
            headers={"Idempotency-Key": "cash-adjustment-account"},
            json={
                "name": "Opening Ledger",
                "broker": "IBKR",
                "currency": "USD",
                "initial_balance": "1000",
            },
        )

        self.assertEqual(create_response.status_code, 201)
        payload = create_response.json()
        ledger_entry = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.account_id == payload["id"],
            AccountLedgerEntry.source == "OPENING_BALANCE",
        ).one()
        self.assertEqual(ledger_entry.entry_type, AccountLedgerEntryType.CASH_ADJUSTMENT)
        self.assertEqual(ledger_entry.amount, Decimal("1000"))
        self.assertEqual(Decimal(str(payload["journal_balance"])), Decimal("1000"))
        created_account = self.db.get(TradingAccount, payload["id"])
        self.assertFalse(created_account.hard_delete_eligible)

    def test_account_metadata_update_rejects_cash_balance_mutation(self):
        create_response = self.client.post(
            "/api/accounts",
            headers={"Idempotency-Key": "cash-adjustment-account"},
            json={
                "name": "Cash Adjustment",
                "broker": "IBKR",
                "currency": "USD",
                "initial_balance": "1000",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        account_public_id = create_response.json()["public_id"]

        update_response = self.client.patch(
            f"/api/accounts/{account_public_id}",
            json={"name": "Renamed Account", "cash_balance": "1200"},
        )

        self.assertEqual(update_response.status_code, 422)
        account_id = create_response.json()["id"]
        ledger_entry_count = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.account_id == account_id,
            AccountLedgerEntry.source == "MANUAL_CASH_ADJUSTMENT",
        ).count()
        self.assertEqual(ledger_entry_count, 0)

        get_response = self.client.get(f"/api/accounts/{account_public_id}")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["name"], "Cash Adjustment")
        self.assertEqual(
            Decimal(str(get_response.json()["journal_balance"])),
            Decimal("1000"),
        )
        self.assertNotIn("cash_balance", get_response.json())

    def test_account_delete_hard_deletes_only_empty_and_archives_history(self):
        empty = self.client.post(
            "/api/accounts",
            json={"name": "Empty", "broker": "IBKR", "currency": "USD"},
        )
        self.assertEqual(empty.status_code, 201)
        empty_public_id = empty.json()["public_id"]
        self.assertEqual(
            self.client.delete(f"/api/accounts/{empty_public_id}").status_code,
            204,
        )
        self.assertEqual(
            self.client.get(f"/api/accounts/{empty_public_id}").status_code,
            404,
        )

        historical_body = {
            "name": "Historical",
            "broker": "IBKR",
            "currency": "USD",
            "initial_balance": "1000",
        }
        headers = {"Idempotency-Key": "historical-opening"}
        historical = self.client.post(
            "/api/accounts",
            headers=headers,
            json=historical_body,
        )
        replay = self.client.post(
            "/api/accounts",
            headers=headers,
            json=historical_body,
        )
        self.assertEqual(replay.json(), historical.json())
        historical_public_id = historical.json()["public_id"]
        historical_id = historical.json()["id"]
        reversal_body = {
            "occurred_at": (
                datetime.now(timezone.utc) + timedelta(days=1)
            ).isoformat(),
            "reason": "Opening balance entered twice",
        }
        reversal_headers = {
            "Idempotency-Key": "historical-opening-reversal",
            "X-Request-ID": "request-opening-reversal",
        }
        reversal = self.client.post(
            f"/api/accounts/{historical_public_id}/opening-balance/reverse",
            headers=reversal_headers,
            json=reversal_body,
        )
        reversal_replay = self.client.post(
            f"/api/accounts/{historical_public_id}/opening-balance/reverse",
            headers=reversal_headers,
            json=reversal_body,
        )
        self.assertEqual(reversal.status_code, 201)
        self.assertEqual(reversal_replay.json(), reversal.json())
        self.assertEqual(
            Decimal(str(reversal.json()["journal_balance"])),
            Decimal("0"),
        )
        self.db.expire_all()
        historical_account = self.db.get(TradingAccount, historical_id)
        self.assertFalse(historical_account.hard_delete_eligible)
        self.assertEqual(
            self.client.delete(f"/api/accounts/{historical_public_id}").status_code,
            204,
        )
        archived = self.client.get(f"/api/accounts/{historical_public_id}")
        self.assertEqual(archived.status_code, 200)
        self.assertFalse(archived.json()["is_active"])
        replay_after_archive = self.client.post(
            f"/api/accounts/{historical_public_id}/opening-balance/reverse",
            headers=reversal_headers,
            json=reversal_body,
        )
        self.assertEqual(replay_after_archive.json(), reversal.json())
        self.assertEqual(
            self.db.query(AccountLedgerEntry).filter(
                AccountLedgerEntry.account_id == historical_id
            ).count(),
            2,
        )

    def test_positions_list_and_get_include_and_accept_public_id(self):
        list_response = self.client.get("/api/positions")
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        self.assertEqual(payload[0]["public_id"], "pos-public-id")
        self.assertNotIn("current_price", payload[0])
        self.assertNotIn("unrealized_pnl", payload[0])

        get_response = self.client.get("/api/positions/pos-public-id")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["id"], self.position.id)
        self.assertEqual(get_response.json()["public_id"], "pos-public-id")
        self.assertNotIn("current_price", get_response.json())
        self.assertNotIn("unrealized_pnl", get_response.json())


if __name__ == "__main__":
    unittest.main()
