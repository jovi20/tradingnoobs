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
    BatchType,
    IdempotencyKey,
    LedgerPostingKind,
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
from services.legacy_truth_sync_service import (
    sync_legacy_position_to_truth,
    validate_legacy_instrument_identity,
)


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
            asset_type="STOCK",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=1,
            opened_at=datetime.now(timezone.utc),
        )
        self.db.add(self.position)
        self.db.commit()
        self.db.refresh(self.position)
        self._seed_truth_identity(self.position, market="US")

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

    def _seed_truth_identity(self, position: Position, *, market: str) -> None:
        self.db.add(
            TradeBatch(
                public_id=f"batch-{position.public_id}",
                position_id=position.id,
                type=BatchType.ENTRY,
                price=1,
                quantity=position.total_quantity,
                time=position.opened_at,
            )
        )
        self.db.commit()
        identity = validate_legacy_instrument_identity(
            position_asset_type=position.asset_type,
            account_currency=self.account.currency,
            symbol=position.symbol,
            exchange_code=position.exchange,
            metadata_core_type=position.asset_type,
            metadata_market=market,
            metadata_currency=self.account.currency,
            metadata_instrument="SPOT",
        )
        sync_legacy_position_to_truth(
            self.db,
            position.id,
            expected_identity=identity,
        )
        self.db.expire_all()

    def test_account_transactions_routes_accept_account_public_id(self):
        list_response = self.client.get(f"/api/accounts/{self.account.public_id}/transactions")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(len(list_response.json()), 1)

        create_response = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            headers={"Idempotency-Key": "public-account-deposit"},
            json={
                "type": "DEPOSIT",
                "amount": 50,
                "currency": "USD",
                "date": datetime.now(timezone.utc).isoformat(),
                "description": "Top up",
            },
        )
        self.assertEqual(create_response.status_code, 201)
        self.assertEqual(create_response.json()["account_id"], self.account.id)

    def test_transaction_create_writes_account_ledger_entry(self):
        create_response = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            headers={"Idempotency-Key": "public-account-withdrawal"},
            json={
                "type": "WITHDRAWAL",
                "amount": 25,
                "currency": "USD",
                "date": datetime.now(timezone.utc).isoformat(),
                "description": "Cash out",
            },
        )

        self.assertEqual(create_response.status_code, 201)
        payload = create_response.json()
        ledger_entry = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.transaction_id == payload["id"]
        ).one()
        self.assertEqual(ledger_entry.entry_type, AccountLedgerEntryType.WITHDRAWAL)
        self.assertEqual(float(ledger_entry.amount), -25.0)
        self.assertEqual(ledger_entry.currency, "USD")

        delete_response = self.client.delete(f"/api/transactions/{payload['public_id']}")

        self.assertEqual(delete_response.status_code, 405)
        self.assertEqual(
            delete_response.json()["detail"]["code"],
            "FINANCIAL_FACT_IMMUTABLE",
        )
        self.assertEqual(
            self.db.query(AccountLedgerEntry).filter(
                AccountLedgerEntry.transaction_id == payload["id"]
            ).count(),
            1,
        )
        self.assertEqual(
            self.db.query(Transaction).filter(
                Transaction.id == payload["id"]
            ).count(),
            1,
        )

    def test_each_cash_transaction_type_creates_and_reverses_with_derived_sign(self):
        cases = (
            ("DEPOSIT", LedgerPostingKind.DEPOSIT, Decimal("12.00000000")),
            ("WITHDRAWAL", LedgerPostingKind.WITHDRAWAL, Decimal("-12.00000000")),
            ("INTEREST", LedgerPostingKind.INTEREST, Decimal("12.00000000")),
            ("FEE", LedgerPostingKind.ACCOUNT_FEE, Decimal("-12.00000000")),
        )

        for index, (transaction_type, posting_kind, expected_amount) in enumerate(cases):
            with self.subTest(transaction_type=transaction_type):
                created = self.client.post(
                    f"/api/accounts/{self.account.public_id}/transactions",
                    headers={"Idempotency-Key": f"{transaction_type.lower()}-create"},
                    json={
                        "type": transaction_type,
                        "amount": "12",
                        "currency": "USD",
                        "date": f"2026-07-25T12:{index:02d}:00+00:00",
                    },
                )
                self.assertEqual(created.status_code, 201, created.text)
                original = self.db.query(Transaction).filter(
                    Transaction.public_id == created.json()["public_id"]
                ).one()
                original_entry = self.db.query(AccountLedgerEntry).filter(
                    AccountLedgerEntry.transaction_id == original.id
                ).one()
                self.assertEqual(original.amount, expected_amount)
                self.assertEqual(original_entry.posting_kind, posting_kind.value)
                self.assertEqual(original_entry.amount, expected_amount)

                reversed_response = self.client.post(
                    f"/api/transactions/{original.public_id}/reverse",
                    headers={
                        "Idempotency-Key": f"{transaction_type.lower()}-reverse",
                        "X-Request-ID": f"{transaction_type.lower()}-reverse-request",
                    },
                    json={
                        "occurred_at": f"2026-07-25T13:{index:02d}:00+00:00",
                        "reason": f"Correct {transaction_type.lower()}",
                    },
                )
                self.assertEqual(
                    reversed_response.status_code,
                    201,
                    reversed_response.text,
                )
                reversal = self.db.query(Transaction).filter(
                    Transaction.public_id == reversed_response.json()["public_id"]
                ).one()
                reversal_entry = self.db.query(AccountLedgerEntry).filter(
                    AccountLedgerEntry.transaction_id == reversal.id
                ).one()
                self.assertEqual(reversal.amount, -expected_amount)
                self.assertEqual(reversal.reverses_transaction_id, original.id)
                self.assertEqual(
                    reversal_entry.posting_kind,
                    LedgerPostingKind.COMPENSATING_REVERSAL.value,
                )
                self.assertEqual(reversal_entry.amount, -expected_amount)
                self.assertEqual(
                    reversal_entry.reverses_ledger_entry_id,
                    original_entry.id,
                )

    def test_financial_transaction_idempotency_and_reversal_are_permanent(self):
        body = {
            "type": "WITHDRAWAL",
            "amount": 25,
            "currency": "USD",
            "date": "2026-07-25T12:00:00+00:00",
            "description": "Cash out",
        }
        missing = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            json=body,
        )
        self.assertEqual(missing.status_code, 422)
        self.assertEqual(missing.json()["detail"]["code"], "IDEMPOTENCY_KEY_REQUIRED")

        headers = {"Idempotency-Key": "cash-withdrawal-retry"}
        first = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            headers=headers,
            json=body,
        )
        replay = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            headers=headers,
            json=body,
        )
        conflict = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            headers=headers,
            json={**body, "amount": 26},
        )
        self.assertEqual(first.status_code, 201)
        self.assertEqual(replay.json(), first.json())
        self.assertEqual(conflict.status_code, 409)
        self.assertEqual(conflict.json()["detail"]["code"], "IDEMPOTENCY_KEY_REUSED")

        original_public_id = first.json()["public_id"]
        reversal_body = {
            "occurred_at": "2026-07-25T13:00:00+00:00",
            "reason": "Duplicate broker cash record",
        }
        reversal_headers = {
            "Idempotency-Key": "cash-withdrawal-reversal",
            "X-Request-ID": "request-cash-reversal",
        }
        reversal = self.client.post(
            f"/api/transactions/{original_public_id}/reverse",
            headers=reversal_headers,
            json=reversal_body,
        )
        reversal_replay = self.client.post(
            f"/api/transactions/{original_public_id}/reverse",
            headers=reversal_headers,
            json=reversal_body,
        )
        duplicate_reversal = self.client.post(
            f"/api/transactions/{original_public_id}/reverse",
            headers={"Idempotency-Key": "different-reversal-key"},
            json=reversal_body,
        )
        self.assertEqual(reversal.status_code, 201)
        self.assertEqual(reversal_replay.json(), reversal.json())
        self.assertEqual(duplicate_reversal.status_code, 409)
        self.assertEqual(
            duplicate_reversal.json()["detail"]["code"],
            "FINANCIAL_FACT_ALREADY_REVERSED",
        )
        self.assertEqual(
            reversal.json()["reverses_transaction_public_id"],
            original_public_id,
        )
        self.assertEqual(reversal.json()["request_id"], "request-cash-reversal")

        self.db.expire_all()
        idempotency_rows = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.key.in_(
                ["cash-withdrawal-retry", "cash-withdrawal-reversal"]
            )
        ).all()
        self.assertEqual(len(idempotency_rows), 2)
        self.assertTrue(all(row.expires_at is None for row in idempotency_rows))
        self.assertTrue(all(row.source_fact_public_id for row in idempotency_rows))
        reversal_entry = self.db.query(AccountLedgerEntry).filter(
            AccountLedgerEntry.posting_kind
            == LedgerPostingKind.COMPENSATING_REVERSAL.value,
        ).one()
        self.assertEqual(float(reversal_entry.amount), 25.0)
        self.assertIsNotNone(reversal_entry.reverses_ledger_entry_id)

        self.assertEqual(
            self.client.delete(
                f"/api/accounts/{self.account.public_id}"
            ).status_code,
            204,
        )
        replay_after_archive = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            headers=headers,
            json=body,
        )
        reversal_after_archive = self.client.post(
            f"/api/transactions/{original_public_id}/reverse",
            headers=reversal_headers,
            json=reversal_body,
        )
        new_after_archive = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            headers={"Idempotency-Key": "new-after-archive"},
            json={**body, "description": "Must fail"},
        )
        self.assertEqual(replay_after_archive.json(), first.json())
        self.assertEqual(reversal_after_archive.json(), reversal.json())
        self.assertEqual(new_after_archive.status_code, 409)
        self.assertEqual(
            new_after_archive.json()["detail"]["code"],
            "ACCOUNT_ARCHIVED",
        )

    def test_transaction_create_rejects_transfer_and_non_usd_without_side_effects(self):
        before_transactions = self.db.query(Transaction).count()
        before_ledger = self.db.query(AccountLedgerEntry).count()

        transfer_response = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            headers={"Idempotency-Key": "disabled-transfer"},
            json={
                "type": "TRANSFER_IN",
                "amount": 50,
                "currency": "USD",
                "date": datetime.now(timezone.utc).isoformat(),
            },
        )
        currency_response = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            headers={"Idempotency-Key": "unsupported-currency"},
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
            "/api/positions/check/open",
            params={
                "account_id": self.account.public_id,
                "symbol": " nvda ",
                "exchange_code": " nasdaq ",
                "direction": "LONG",
                "asset_type": "STOCK",
                "market": "US",
                "instrument_type": "SPOT",
                "quote_currency": "USD",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["public_id"], self.position.public_id)
        self.assertEqual(payload["account_id"], self.account.id)

        for changes in (
            {"exchange_code": "NYSE"},
            {"direction": "SHORT"},
            {"asset_type": "CRYPTO", "market": "CRYPTO"},
        ):
            params = {
                "account_id": self.account.public_id,
                "symbol": "NVDA",
                "exchange_code": "NASDAQ",
                "direction": "LONG",
                "asset_type": "STOCK",
                "market": "US",
                "instrument_type": "SPOT",
                "quote_currency": "USD",
            }
            params.update(changes)
            mismatch = self.client.get("/api/positions/check/open", params=params)
            self.assertEqual(mismatch.status_code, 200, mismatch.text)
            self.assertIsNone(mismatch.json())

    def test_positions_check_open_accepts_symbol_with_path_separator_as_query_data(self):
        crypto_position = Position(
            user_id=self.user.id,
            account_id=self.account.id,
            public_id="crypto-pos-public-id",
            symbol="BTC/USD",
            exchange="COINBASE",
            asset_type="CRYPTO",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=1,
            opened_at=datetime.now(timezone.utc),
        )
        self.db.add(crypto_position)
        self.db.commit()
        self._seed_truth_identity(crypto_position, market="CRYPTO")

        response = self.client.get(
            "/api/positions/check/open",
            params={
                "account_id": self.account.public_id,
                "symbol": "BTC/USD",
                "exchange_code": "COINBASE",
                "direction": "LONG",
                "asset_type": "CRYPTO",
                "market": "CRYPTO",
                "instrument_type": "SPOT",
                "quote_currency": "USD",
            },
        )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["public_id"], crypto_position.public_id)


if __name__ == "__main__":
    unittest.main()
