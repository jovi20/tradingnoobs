import os
import tempfile
import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import (
    AccountLedgerEntry,
    AccountLedgerEntryType,
    Position,
    PositionDirection,
    PositionStatus,
    TradeBatch,
    TradingAccount,
    Transaction,
    TransactionType,
    User,
)
from services.auth_service import get_current_user


class PublicIdNestedRouteTests(unittest.TestCase):
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
            email="nested@example.com",
            email_normalized="nested@example.com",
            hashed_password="hashed",
            public_id="user-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
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
            cash_balance=1000,
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
            status=PositionStatus.OPEN,
            total_quantity=1,
            opened_at=datetime.now(timezone.utc),
        )
        self.db.add(self.position)
        self.db.commit()
        self.db.refresh(self.position)

        self.transaction = Transaction(
            account_id=self.account.id,
            type=TransactionType.DEPOSIT,
            amount=100,
            currency="USD",
            date=datetime.now(timezone.utc),
            description="Seed cash",
        )
        self.db.add(self.transaction)
        self.db.commit()

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

    def test_account_transactions_routes_accept_account_public_id(self):
        list_response = self.client.get(f"/api/accounts/{self.account.public_id}/transactions")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        create_response = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            json={
                "type": "DEPOSIT",
                "amount": 50,
                "currency": "USD",
                "date": datetime.now(timezone.utc).isoformat(),
                "description": "Top up",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        self.assertEqual(create_response.json()["account_id"], self.account.id)

    def test_transaction_create_writes_account_ledger_entry(self):
        create_response = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            json={
                "type": "WITHDRAWAL",
                "amount": 25,
                "currency": "USD",
                "date": datetime.now(timezone.utc).isoformat(),
                "description": "Cash out",
            },
        )

        self.assertEqual(create_response.status_code, 200)
        payload = create_response.json()
        ledger_entry = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.transaction_id == payload["id"]
        ).one()
        self.assertEqual(ledger_entry.entry_type, AccountLedgerEntryType.WITHDRAWAL)
        self.assertEqual(float(ledger_entry.amount), -25.0)
        self.assertEqual(ledger_entry.currency, "USD")

        delete_response = self.client.delete(f"/api/transactions/{payload['public_id']}")

        self.assertEqual(delete_response.status_code, 200)
        self.assertEqual(
            self.db.query(AccountLedgerEntry).filter(
                AccountLedgerEntry.transaction_id == payload["id"]
            ).count(),
            0,
        )

    def test_transaction_create_rejects_transfer_and_non_usd_without_side_effects(self):
        before_transactions = self.db.query(Transaction).count()
        before_ledger = self.db.query(AccountLedgerEntry).count()

        transfer_response = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            json={
                "type": "TRANSFER_IN",
                "amount": 50,
                "currency": "USD",
                "date": datetime.now(timezone.utc).isoformat(),
            },
        )
        currency_response = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            json={
                "type": "DEPOSIT",
                "amount": 50,
                "currency": "USDT",
                "date": datetime.now(timezone.utc).isoformat(),
            },
        )

        self.assertEqual(transfer_response.status_code, 422)
        self.assertEqual(
            transfer_response.json()["detail"]["code"],
            "UNSUPPORTED_TRANSACTION_TYPE",
        )
        self.assertEqual(currency_response.status_code, 422)
        self.assertEqual(
            currency_response.json()["detail"]["code"],
            "UNSUPPORTED_RELEASE_CURRENCY",
        )
        self.assertEqual(self.db.query(Transaction).count(), before_transactions)
        self.assertEqual(self.db.query(AccountLedgerEntry).count(), before_ledger)

    def test_positions_check_open_accepts_account_public_id(self):
        response = self.client.get(
            f"/api/positions/check/NVDA?account_id={self.account.public_id}"
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["public_id"], self.position.public_id)
        self.assertEqual(payload["account_id"], self.account.id)


if __name__ == "__main__":
    unittest.main()
