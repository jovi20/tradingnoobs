from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import (
    AccountingHealth,
    AccountingReconciliationCase,
    AccountLedgerEntry,
    AccountLedgerEntryType,
    AssetMaster,
    LedgerPostingKind,
    PositionEvent,
    PositionEventType,
    TradeInstrument,
    TradeInstrumentType,
    TradingAccount,
    TradingPosition,
    TradingPositionSide,
    TradingPositionStatus,
    Transaction,
    User,
)
from services.auth_service import get_current_user
from services.account_ledger_service import (
    AccountingReconciliationRequiredError,
    LedgerPostingConflictError,
    calculate_account_cash_balance_read_model,
    require_accounting_healthy,
    sync_opening_balance_to_account_ledger,
    sync_trade_event_postings,
)
from services.account_reconciliation_service import (
    apply_compensating_repair,
    preview_account_reconciliation,
)
from services.trading_position_write_service import (
    replay_truth_position_accounting,
)


class JRN006AppendOnlyLedgerTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(f"sqlite:///{self.db_path}")
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.SessionLocal()

        self.user = User(
            public_id="jrn006-user",
            email="jrn006@example.com",
            email_normalized="jrn006@example.com",
            hashed_password="hash",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        self.account = TradingAccount(
            public_id="jrn006-account",
            user=self.user,
            name="JRN-006",
            broker="MANUAL",
            currency="USD",
            initial_balance=Decimal("100"),
            cash_balance=Decimal("9999"),
            accounting_health=AccountingHealth.HEALTHY.value,
            is_active=True,
        )
        asset = AssetMaster(
            public_id="jrn006-asset",
            canonical_code="NASDAQ:AAPL:USD",
            display_symbol="AAPL",
            name="Apple",
            asset_type="EQUITY",
            quote_currency="USD",
            status="ACTIVE",
        )
        instrument = TradeInstrument(
            public_id="jrn006-instrument",
            asset=asset,
            instrument_type=TradeInstrumentType.SPOT,
            display_name="AAPL",
            contract_symbol="AAPL",
            status="ACTIVE",
        )
        self.position = TradingPosition(
            public_id="jrn006-position",
            user=self.user,
            account=self.account,
            instrument=instrument,
            status=TradingPositionStatus.OPEN,
            side=TradingPositionSide.LONG,
            opened_at=datetime(2026, 7, 25, 9, 30, tzinfo=timezone.utc),
            base_currency="USD",
            cost_basis_method="FIFO",
        )
        self.db.add_all([self.user, self.account, asset, instrument, self.position])
        self.db.commit()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        os.remove(self.db_path)

    def test_trade_event_emits_gross_and_fee_postings_and_replays_identically(self):
        sync_opening_balance_to_account_ledger(self.db, account=self.account)
        event = PositionEvent(
            public_id="jrn006-close",
            user_id=self.user.id,
            position_id=self.position.id,
            account_id=self.account.id,
            instrument_id=self.position.instrument_id,
            event_type=PositionEventType.CLOSE,
            event_time=datetime(2026, 7, 25, 10, 0, tzinfo=timezone.utc),
            quantity=Decimal("1"),
            price=Decimal("11"),
            currency="USD",
            fee_amount=Decimal("0.25"),
            fee_currency="USD",
            fx_rate_to_account_ccy=Decimal("1"),
            realized_pnl_gross=Decimal("1"),
            realized_pnl_net=Decimal("0.65"),
        )
        self.db.add(event)
        self.db.flush()

        first = sync_trade_event_postings(
            self.db,
            event=event,
            position=self.position,
        )
        replay = sync_trade_event_postings(
            self.db,
            event=event,
            position=self.position,
        )

        self.assertEqual([entry.id for entry in replay], [entry.id for entry in first])
        self.assertEqual(
            [(entry.posting_kind, entry.amount) for entry in first],
            [
                (LedgerPostingKind.REALIZED_GROSS.value, Decimal("1.00000000")),
                (LedgerPostingKind.TRADE_FEE.value, Decimal("-0.25000000")),
            ],
        )
        self.assertEqual(
            calculate_account_cash_balance_read_model(
                self.db,
                account=self.account,
            ),
            Decimal("100.75000000"),
        )

        event.realized_pnl_gross = Decimal("2")
        with self.assertRaises(LedgerPostingConflictError):
            sync_trade_event_postings(
                self.db,
                event=event,
                position=self.position,
            )

    def test_production_replay_satisfies_every_trade_golden_vector(self):
        vectors_path = (
            Path(__file__).parent
            / "fixtures"
            / "jrn005_accounting_golden_vectors_v1.json"
        )
        vectors = json.loads(vectors_path.read_text(encoding="utf-8"))
        instrument = self.position.instrument

        for vector_index, vector in enumerate(vectors["trade_vectors"], start=1):
            account = TradingAccount(
                public_id=f"jrn006-vector-account-{vector_index}",
                user_id=self.user.id,
                name=vector["id"],
                broker="MANUAL",
                currency="USD",
                initial_balance=Decimal(vector["opening_balance"]),
                accounting_health=AccountingHealth.HEALTHY.value,
                is_active=True,
            )
            position = TradingPosition(
                public_id=f"jrn006-vector-position-{vector_index}",
                user_id=self.user.id,
                account=account,
                instrument_id=instrument.id,
                status=TradingPositionStatus.OPEN,
                side=TradingPositionSide(vector["side"]),
                opened_at=datetime(
                    2026,
                    7,
                    vector_index,
                    9,
                    30,
                    tzinfo=timezone.utc,
                ),
                base_currency="USD",
                cost_basis_method="FIFO",
            )
            self.db.add_all([account, position])
            self.db.flush()
            sync_opening_balance_to_account_ledger(self.db, account=account)
            events = []
            for sequence_no, item in enumerate(vector["events"], start=1):
                event = PositionEvent(
                    public_id=f"{vector['id']}-{item['id']}",
                    user_id=self.user.id,
                    position_id=position.id,
                    account_id=account.id,
                    instrument_id=instrument.id,
                    event_type=PositionEventType(item["type"]),
                    event_time=datetime(
                        2026,
                        7,
                        vector_index,
                        9,
                        30 + sequence_no,
                        tzinfo=timezone.utc,
                    ),
                    sequence_no=sequence_no,
                    quantity=Decimal(item["quantity"]),
                    price=Decimal(item["price"]),
                    currency="USD",
                    fee_amount=Decimal(item["fee"]),
                    fee_currency="USD",
                    fx_rate_to_account_ccy=Decimal("1"),
                )
                events.append(event)
                self.db.add(event)
            self.db.flush()

            replay_truth_position_accounting(self.db, position=position)

            expected_summary = vector["expected_summary"]
            self.assertEqual(
                position.quantity_opened,
                Decimal(expected_summary["quantity_opened"]),
            )
            self.assertEqual(
                position.quantity_closed,
                Decimal(expected_summary["quantity_closed"]),
            )
            self.assertEqual(
                position.realized_pnl_gross,
                Decimal(expected_summary["realized_gross"]),
            )
            self.assertEqual(
                position.realized_pnl_net,
                Decimal(expected_summary["realized_net"]),
            )
            self.assertEqual(
                position.total_fees,
                Decimal(expected_summary["total_fees"]),
            )
            for event, expected in zip(
                events,
                vector["expected_events"],
                strict=True,
            ):
                self.assertEqual(
                    event.realized_pnl_gross,
                    Decimal(expected["realized_gross"]),
                )
                self.assertEqual(
                    event.realized_pnl_net,
                    Decimal(expected["realized_net"]),
                )

            actual_postings = self.db.query(AccountLedgerEntry).filter(
                AccountLedgerEntry.position_id == position.id,
            ).order_by(AccountLedgerEntry.id.asc()).all()
            self.assertEqual(
                [
                    (
                        entry.source_fact_public_id.rsplit("-", 1)[-1],
                        entry.posting_kind,
                        format(entry.amount, "f"),
                    )
                    for entry in actual_postings
                ],
                [
                    (
                        item["source"],
                        item["kind"],
                        format(Decimal(item["amount"]), "f"),
                    )
                    for item in vector["expected_postings"]
                ],
                vector["id"],
            )
            self.assertEqual(
                calculate_account_cash_balance_read_model(
                    self.db,
                    account=account,
                ),
                Decimal(expected_summary["journal_balance"]),
            )

    def test_orm_guard_rejects_update_and_delete(self):
        entry = sync_opening_balance_to_account_ledger(
            self.db,
            account=self.account,
        )
        self.db.commit()

        entry.amount = Decimal("101")
        with self.assertRaisesRegex(ValueError, "append-only"):
            self.db.flush()
        self.db.rollback()

        entry = self.db.get(AccountLedgerEntry, entry.id)
        self.db.delete(entry)
        with self.assertRaisesRegex(ValueError, "append-only"):
            self.db.flush()

    def test_balance_never_falls_back_to_cash_balance(self):
        self.account.initial_balance = None
        self.db.commit()
        self.assertEqual(
            calculate_account_cash_balance_read_model(
                self.db,
                account=self.account,
            ),
            Decimal("0"),
        )

    def test_reconciliation_required_blocks_financial_mutation(self):
        self.account.accounting_health = (
            AccountingHealth.RECONCILIATION_REQUIRED.value
        )
        self.db.commit()
        with self.assertRaises(AccountingReconciliationRequiredError):
            require_accounting_healthy(self.account)

    def test_audited_compensation_resolves_case_and_restores_health(self):
        legacy = AccountLedgerEntry(
            public_id="legacy-ledger-entry",
            user_id=self.user.id,
            account_id=self.account.id,
            entry_type=AccountLedgerEntryType.REALIZED_PNL,
            source_fact_public_id="legacy-ledger-entry",
            posting_kind=LedgerPostingKind.LEGACY_UNRESOLVED.value,
            occurred_at=datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc),
            currency="USD",
            amount=Decimal("12"),
            amount_account_ccy=Decimal("12"),
            fx_rate_to_account_ccy=Decimal("1"),
            source="LEGACY_BACKFILL",
        )
        self.db.add(legacy)
        self.db.flush()
        case = AccountingReconciliationCase(
            public_id="reconciliation-case",
            user_id=self.user.id,
            account_id=self.account.id,
            original_ledger_entry_id=legacy.id,
            status="OPEN",
            issue_code="LEGACY_UNRESOLVED_POSTINGS",
            details_json={"ledger_entry_public_id": legacy.public_id},
        )
        self.account.accounting_health = (
            AccountingHealth.RECONCILIATION_REQUIRED.value
        )
        self.db.add(case)
        self.db.commit()

        preview = preview_account_reconciliation(
            self.db,
            account=self.account,
        )
        self.assertFalse(preview.can_mark_healthy)
        self.assertEqual(
            [item.code for item in preview.divergences],
            ["LEGACY_UNRESOLVED_POSTING"],
        )

        compensation = apply_compensating_repair(
            self.db,
            case=case,
            actor_user_id=self.user.id,
            reason="Verified duplicate legacy net posting",
        )
        self.db.commit()
        self.assertEqual(
            compensation.posting_kind,
            LedgerPostingKind.COMPENSATING_REVERSAL.value,
        )
        self.assertEqual(compensation.amount, Decimal("-12.00000000"))
        self.assertEqual(case.status, "RESOLVED")
        self.assertEqual(
            self.account.accounting_health,
            AccountingHealth.HEALTHY.value,
        )
        self.assertTrue(
            preview_account_reconciliation(
                self.db,
                account=self.account,
            ).can_mark_healthy
        )


class JRN006MigrationGuardTests(unittest.TestCase):
    def test_sqlite_migration_installs_database_append_only_guard(self):
        repo_root = Path(__file__).resolve().parents[2]
        fd, raw_path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        path = Path(raw_path)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{path}"
        env["PYTHONPATH"] = str(repo_root / "backend")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "backend/alembic.ini",
                "upgrade",
                "head",
            ],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

        with sqlite3.connect(path) as connection:
            connection.execute(
                """
                INSERT INTO users (
                    public_id, email, email_normalized, hashed_password,
                    status, is_active, role
                ) VALUES ('u1', 'u1@example.com', 'u1@example.com',
                          'hash', 'ACTIVE', 1, 'user')
                """
            )
            user_id = connection.execute(
                "SELECT id FROM users WHERE public_id = 'u1'"
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO trading_accounts (
                    public_id, user_id, name, broker, currency, is_active,
                    accounting_health
                ) VALUES (
                    'a1', ?, 'A1', 'MANUAL', 'USD', 1,
                    'ACCOUNTING_HEALTHY'
                )
                """,
                (user_id,),
            )
            account_id = connection.execute(
                "SELECT id FROM trading_accounts WHERE public_id = 'a1'"
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO account_ledger_entries (
                    public_id, user_id, account_id, entry_type,
                    source_fact_public_id, posting_kind, occurred_at,
                    currency, amount, amount_account_ccy,
                    fx_rate_to_account_ccy
                ) VALUES (
                    'l1', ?, ?, 'DEPOSIT', 'fact-1', 'DEPOSIT',
                    '2026-07-25T10:00:00Z', 'USD', 10, 10, 1
                )
                """,
                (user_id, account_id),
            )
            connection.commit()

            with self.assertRaisesRegex(
                sqlite3.IntegrityError,
                "append-only",
            ):
                connection.execute(
                    "UPDATE account_ledger_entries SET amount = 11 "
                    "WHERE public_id = 'l1'"
                )
            with self.assertRaisesRegex(
                sqlite3.IntegrityError,
                "append-only",
            ):
                connection.execute(
                    "DELETE FROM account_ledger_entries "
                    "WHERE public_id = 'l1'"
                )


class JRN006AccountingHealthApiTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)
        self.db = self.SessionLocal()
        self.user = User(
            public_id="jrn006-api-user",
            email="jrn006-api@example.com",
            email_normalized="jrn006-api@example.com",
            hashed_password="hash",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        self.account = TradingAccount(
            public_id="jrn006-api-account",
            user=self.user,
            name="Needs reconciliation",
            broker="MANUAL",
            currency="USD",
            accounting_health=(
                AccountingHealth.RECONCILIATION_REQUIRED.value
            ),
            is_active=True,
        )
        self.db.add_all([self.user, self.account])
        self.db.commit()

        def override_get_db():
            session = self.SessionLocal()
            try:
                yield session
            finally:
                session.close()

        async def override_get_current_user():
            return self.user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
        os.remove(self.db_path)

    def test_degraded_account_is_visible_but_mutation_and_trusted_metrics_are_blocked(self):
        account_response = self.client.get(
            f"/api/accounts/{self.account.public_id}"
        )
        self.assertEqual(account_response.status_code, 200)
        self.assertFalse(account_response.json()["journal_balance_trusted"])
        self.assertEqual(
            account_response.json()["accounting_health"],
            AccountingHealth.RECONCILIATION_REQUIRED.value,
        )

        dashboard_response = self.client.get("/api/dashboard/stats")
        self.assertEqual(dashboard_response.status_code, 200)
        dashboard = dashboard_response.json()
        self.assertTrue(dashboard["accounting_degraded"])
        self.assertFalse(
            dashboard["account_balances"][0]["journal_balance_trusted"]
        )
        self.assertEqual(dashboard["journal_balance"], 0)

        mutation = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            headers={"Idempotency-Key": "degraded-account-deposit"},
            json={
                "type": "DEPOSIT",
                "amount": "10",
                "currency": "USD",
                "date": "2026-07-25T10:00:00Z",
            },
        )
        self.assertEqual(mutation.status_code, 409)
        self.assertEqual(
            mutation.json()["detail"]["code"],
            "ACCOUNTING_RECONCILIATION_REQUIRED",
        )
        self.assertEqual(self.db.query(Transaction).count(), 0)
        self.assertEqual(self.db.query(AccountLedgerEntry).count(), 0)

    def test_posting_failure_rolls_back_source_fact(self):
        self.account.accounting_health = AccountingHealth.HEALTHY.value
        self.db.commit()
        with patch(
            "routers.transactions.sync_transaction_to_account_ledger",
            side_effect=LedgerPostingConflictError("injected conflict"),
        ):
            response = self.client.post(
                f"/api/accounts/{self.account.public_id}/transactions",
                headers={"Idempotency-Key": "posting-failure-deposit"},
                json={
                    "type": "DEPOSIT",
                    "amount": "10",
                    "currency": "USD",
                    "date": "2026-07-25T10:00:00Z",
                },
            )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(self.db.query(Transaction).count(), 0)
        self.assertEqual(self.db.query(AccountLedgerEntry).count(), 0)
