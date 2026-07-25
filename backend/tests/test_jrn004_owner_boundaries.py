import os
import tempfile
import unittest
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import create_app
from models import (
    AccountLedgerEntry,
    AccountLedgerEntryType,
    AssetMaster,
    BatchType,
    DailySummary,
    JournalEntry,
    Position,
    PositionDirection,
    PositionEvent,
    PositionEventType,
    PositionStatus,
    Strategy,
    TradeBatch,
    TradeInstrument,
    TradeInstrumentType,
    TradingAccount,
    TradingPosition,
    TradingPositionSide,
    TradingPositionStatus,
    Transaction,
    TransactionType,
    User,
)
from release_profile import ReleaseProfile
from services.account_ledger_service import (
    sync_dividend_event_to_account_ledger,
    sync_transaction_to_account_ledger,
)
from services.auth_service import get_current_user
from services.legacy_truth_sync_service import sync_legacy_position_to_truth


@dataclass(frozen=True)
class OwnerBoundaryProbe:
    method: str
    path: str
    json: dict | None = None


def assert_owner_boundary_probes(
    test: unittest.TestCase,
    client: TestClient,
    probes: tuple[OwnerBoundaryProbe, ...],
    *,
    forbidden_values: tuple[str, ...],
) -> None:
    for probe in probes:
        response = client.request(probe.method, probe.path, json=probe.json)
        test.assertEqual(
            response.status_code,
            404,
            f"{probe.method} {probe.path}: {response.text}",
        )
        for value in forbidden_values:
            test.assertNotIn(value, response.text)


class JRN004OwnerBoundaryTests(unittest.TestCase):
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

        self.owner = self._user("owner@example.com", "owner-public-id")
        self.foreign = self._user("foreign@example.com", "foreign-public-id")
        self.db.add_all([self.owner, self.foreign])
        self.db.commit()
        self.db.refresh(self.owner)
        self.db.refresh(self.foreign)

        self.owner_account = TradingAccount(
            user_id=self.owner.id,
            public_id="owner-account-public-id",
            name="Owner account",
            broker="MANUAL",
            currency="USD",
            cash_balance=Decimal("0"),
            is_active=True,
        )
        self.foreign_account = TradingAccount(
            user_id=self.foreign.id,
            public_id="foreign-account-public-id",
            name="Foreign account",
            broker="MANUAL",
            currency="USD",
            cash_balance=Decimal("0"),
            is_active=True,
        )
        self.foreign_strategy = Strategy(
            user_id=self.foreign.id,
            name="Foreign strategy",
            checklist_items=[],
            symbols=[],
        )
        self.db.add_all(
            [self.owner_account, self.foreign_account, self.foreign_strategy]
        )
        self.db.commit()
        for row in (
            self.owner_account,
            self.foreign_account,
            self.foreign_strategy,
        ):
            self.db.refresh(row)

        self.foreign_daily = DailySummary(
            user_id=self.foreign.id,
            date=date(2026, 7, 24),
            summary="foreign daily private text",
        )
        self.foreign_journal = JournalEntry(
            user_id=self.foreign.id,
            date=date(2026, 7, 24),
            content="foreign journal private text",
        )
        self.foreign_transaction = Transaction(
            public_id="foreign-transaction-public-id",
            account_id=self.foreign_account.id,
            type=TransactionType.DEPOSIT,
            amount=Decimal("100"),
            currency="USD",
            date=datetime(2026, 7, 24, 9, 0, tzinfo=timezone.utc),
            description="foreign transaction private text",
        )
        self.foreign_position = Position(
            public_id="foreign-position-public-id",
            user_id=self.foreign.id,
            account_id=self.foreign_account.id,
            strategy_id=self.foreign_strategy.id,
            symbol="FOREIGN",
            exchange="NASDAQ",
            asset_type="EQUITY",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=Decimal("1"),
            average_entry_price=Decimal("10"),
            opened_at=datetime(2026, 7, 24, 9, 30, tzinfo=timezone.utc),
        )
        self.db.add_all(
            [
                self.foreign_daily,
                self.foreign_journal,
                self.foreign_transaction,
                self.foreign_position,
            ]
        )
        self.db.flush()
        self.foreign_batch = TradeBatch(
            public_id="foreign-batch-public-id",
            position_id=self.foreign_position.id,
            type=BatchType.ENTRY,
            price=Decimal("10"),
            quantity=Decimal("1"),
            time=datetime(2026, 7, 24, 9, 30, tzinfo=timezone.utc),
        )
        self.db.add(self.foreign_batch)

        asset = AssetMaster(
            canonical_code="US:OWNER",
            display_symbol="OWNER",
            name="Owner asset",
            asset_type="STOCK",
            quote_currency="USD",
            status="ACTIVE",
            metadata_json={},
        )
        self.db.add(asset)
        self.db.flush()
        instrument = TradeInstrument(
            asset_id=asset.id,
            instrument_type=TradeInstrumentType.SPOT,
            display_name="OWNER",
            contract_symbol="OWNER",
            status="ACTIVE",
        )
        self.db.add(instrument)
        self.db.flush()
        self.owner_truth = TradingPosition(
            public_id="owner-truth-public-id",
            user_id=self.owner.id,
            account_id=self.owner_account.id,
            instrument_id=instrument.id,
            status=TradingPositionStatus.OPEN,
            side=TradingPositionSide.LONG,
            opened_at=datetime(2026, 7, 24, 9, 30, tzinfo=timezone.utc),
            base_currency="USD",
            cost_basis_method="FIFO",
            quantity_opened=Decimal("1"),
            quantity_closed=Decimal("0"),
        )
        self.foreign_truth = TradingPosition(
            public_id="foreign-truth-public-id",
            user_id=self.foreign.id,
            account_id=self.foreign_account.id,
            instrument_id=instrument.id,
            strategy_id=self.foreign_strategy.id,
            status=TradingPositionStatus.OPEN,
            side=TradingPositionSide.LONG,
            opened_at=datetime(2026, 7, 24, 9, 30, tzinfo=timezone.utc),
            base_currency="USD",
            cost_basis_method="FIFO",
            quantity_opened=Decimal("1"),
            quantity_closed=Decimal("0"),
        )
        self.db.add_all([self.owner_truth, self.foreign_truth])
        self.db.flush()
        self.owner_event = self._event(
            "owner-event-public-id",
            self.owner,
            self.owner_account,
            self.owner_truth,
            instrument,
        )
        self.foreign_event = self._event(
            "foreign-event-public-id",
            self.foreign,
            self.foreign_account,
            self.foreign_truth,
            instrument,
        )
        self.db.add_all([self.owner_event, self.foreign_event])
        self.db.add(
            AccountLedgerEntry(
                public_id="cross-owner-ledger-public-id",
                user_id=self.foreign.id,
                account_id=self.owner_account.id,
                entry_type=AccountLedgerEntryType.CASH_ADJUSTMENT,
                occurred_at=datetime(2026, 7, 24, 10, 0, tzinfo=timezone.utc),
                currency="USD",
                amount=Decimal("999"),
                amount_account_ccy=Decimal("999"),
                fx_rate_to_account_ccy=Decimal("1"),
                source="CORRUPT_CROSS_OWNER_FIXTURE",
            )
        )
        self.db.add(
            AccountLedgerEntry(
                public_id="cross-account-transaction-ledger-public-id",
                user_id=self.owner.id,
                account_id=self.owner_account.id,
                transaction_id=self.foreign_transaction.id,
                entry_type=AccountLedgerEntryType.DEPOSIT,
                occurred_at=datetime(2026, 7, 24, 10, 1, tzinfo=timezone.utc),
                currency="USD",
                amount=Decimal("777"),
                amount_account_ccy=Decimal("777"),
                fx_rate_to_account_ccy=Decimal("1"),
                source="CORRUPT_CROSS_ACCOUNT_TRANSACTION_FIXTURE",
            )
        )
        self.db.commit()

        self.app = create_app(ReleaseProfile.JOURNAL_BASELINE)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.owner

        self.app.dependency_overrides[get_db] = override_get_db
        self.app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
        os.remove(self.db_path)

    @staticmethod
    def _user(email: str, public_id: str) -> User:
        return User(
            email=email,
            email_normalized=email,
            hashed_password="hashed",
            public_id=public_id,
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )

    @staticmethod
    def _event(public_id, user, account, position, instrument) -> PositionEvent:
        return PositionEvent(
            public_id=public_id,
            user_id=user.id,
            position_id=position.id,
            account_id=account.id,
            instrument_id=instrument.id,
            event_type=PositionEventType.OPEN,
            event_time=datetime(2026, 7, 24, 9, 30, tzinfo=timezone.utc),
            quantity=Decimal("1"),
            price=Decimal("10"),
            currency="USD",
            input_source="MANUAL",
        )

    def test_foreign_current_resources_are_hidden_for_public_and_internal_ids(self):
        probes = (
            OwnerBoundaryProbe("GET", f"/api/accounts/{self.foreign_account.public_id}"),
            OwnerBoundaryProbe("GET", f"/api/accounts/{self.foreign_account.id}"),
            OwnerBoundaryProbe(
                "PATCH",
                f"/api/accounts/{self.foreign_account.public_id}",
                {"description": "stolen"},
            ),
            OwnerBoundaryProbe("DELETE", f"/api/accounts/{self.foreign_account.id}"),
            OwnerBoundaryProbe("GET", f"/api/strategies/{self.foreign_strategy.id}"),
            OwnerBoundaryProbe(
                "PATCH",
                f"/api/strategies/{self.foreign_strategy.id}",
                {"description": "stolen"},
            ),
            OwnerBoundaryProbe(
                "GET",
                f"/api/accounts/{self.foreign_account.public_id}/transactions",
            ),
            OwnerBoundaryProbe(
                "DELETE",
                f"/api/transactions/{self.foreign_transaction.public_id}",
            ),
            OwnerBoundaryProbe(
                "DELETE",
                f"/api/transactions/{self.foreign_transaction.id}",
            ),
            OwnerBoundaryProbe("GET", f"/api/positions/{self.foreign_position.public_id}"),
            OwnerBoundaryProbe("GET", f"/api/positions/{self.foreign_position.id}"),
            OwnerBoundaryProbe(
                "GET",
                f"/api/positions/{self.foreign_position.public_id}/batches",
            ),
            OwnerBoundaryProbe(
                "PATCH",
                f"/api/positions/batches/{self.foreign_batch.public_id}",
                {"price": "11"},
            ),
            OwnerBoundaryProbe(
                "GET",
                f"/api/trading-positions/{self.foreign_truth.public_id}/lifecycle",
            ),
            OwnerBoundaryProbe(
                "PATCH",
                (
                    f"/api/trading-positions/{self.owner_truth.public_id}/events/"
                    f"{self.foreign_event.public_id}/narrative"
                ),
                {"note": "stolen"},
            ),
            OwnerBoundaryProbe("GET", "/api/daily/2026-07-24"),
            OwnerBoundaryProbe(
                "PATCH",
                f"/api/journal/{self.foreign_journal.id}",
                {"content": "stolen"},
            ),
            OwnerBoundaryProbe("DELETE", f"/api/journal/{self.foreign_journal.id}"),
        )
        counts_before = {
            model: self.db.query(model).count()
            for model in (
                TradingAccount,
                Strategy,
                Transaction,
                Position,
                TradeBatch,
                TradingPosition,
                PositionEvent,
                DailySummary,
                JournalEntry,
            )
        }

        assert_owner_boundary_probes(
            self,
            self.client,
            probes,
            forbidden_values=(
                "Foreign account",
                "Foreign strategy",
                "FOREIGN",
                "foreign daily private text",
                "foreign journal private text",
                "foreign transaction private text",
            ),
        )

        self.db.expire_all()
        self.assertEqual(
            {model: self.db.query(model).count() for model in counts_before},
            counts_before,
        )
        self.assertNotEqual(self.foreign_account.description, "stolen")
        self.assertNotEqual(self.foreign_strategy.description, "stolen")
        self.assertNotEqual(self.foreign_journal.content, "stolen")

    def test_lists_exports_and_account_ledger_read_model_do_not_leak_foreign_rows(self):
        self.db.add(
            Position(
                public_id="mixed-list-position-public-id",
                user_id=self.owner.id,
                account_id=self.owner_account.id,
                strategy_id=self.foreign_strategy.id,
                symbol="MIXEDPRIVATE",
                exchange="NASDAQ",
                asset_type="EQUITY",
                direction=PositionDirection.LONG,
                status=PositionStatus.OPEN,
                total_quantity=Decimal("1"),
                average_entry_price=Decimal("10"),
                opened_at=datetime(2026, 7, 24, 9, 30, tzinfo=timezone.utc),
            )
        )
        self.db.commit()

        accounts = self.client.get("/api/accounts")
        strategies = self.client.get("/api/strategies")
        positions = self.client.get("/api/positions")
        journals = self.client.get("/api/journal")
        daily = self.client.get("/api/daily")
        export = self.client.get("/api/positions/export/csv")
        dashboard = self.client.get("/api/dashboard/stats")
        timeline = self.client.get("/api/timeline/home")
        owner_account = self.client.get(
            f"/api/accounts/{self.owner_account.public_id}"
        )

        for response in (
            accounts,
            strategies,
            positions,
            journals,
            daily,
            export,
            dashboard,
            timeline,
            owner_account,
        ):
            self.assertEqual(response.status_code, 200, response.text)
            self.assertNotIn("Foreign account", response.text)
            self.assertNotIn("Foreign strategy", response.text)
            self.assertNotIn("FOREIGN", response.text)
            self.assertNotIn("MIXEDPRIVATE", response.text)
            self.assertNotIn("foreign journal private text", response.text)
        self.assertEqual(owner_account.json()["journal_balance"], "0")
        self.assertEqual(dashboard.json()["total_trades"], 0)

    def test_direct_batch_ids_fail_closed_for_cross_owner_strategy_graph(self):
        mixed_position = Position(
            public_id="mixed-batch-position-public-id",
            user_id=self.owner.id,
            account_id=self.owner_account.id,
            strategy_id=self.foreign_strategy.id,
            symbol="MIXEDBATCH",
            exchange="NASDAQ",
            asset_type="EQUITY",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=Decimal("1"),
            average_entry_price=Decimal("10"),
            opened_at=datetime(2026, 7, 24, 9, 30, tzinfo=timezone.utc),
        )
        self.db.add(mixed_position)
        self.db.flush()
        mixed_batch = TradeBatch(
            public_id="mixed-batch-public-id",
            position_id=mixed_position.id,
            type=BatchType.ENTRY,
            price=Decimal("10"),
            quantity=Decimal("1"),
            time=datetime(2026, 7, 24, 9, 30, tzinfo=timezone.utc),
        )
        self.db.add(mixed_batch)
        self.db.commit()

        probes = (
            OwnerBoundaryProbe(
                "PATCH",
                f"/api/positions/batches/{mixed_batch.public_id}",
                {"price": "99"},
            ),
            OwnerBoundaryProbe(
                "PATCH",
                f"/api/positions/batches/{mixed_batch.id}",
                {"price": "99"},
            ),
        )
        assert_owner_boundary_probes(
            self,
            self.client,
            probes,
            forbidden_values=("MIXEDBATCH",),
        )

        self.db.expire_all()
        self.assertEqual(
            self.db.query(TradeBatch).filter(TradeBatch.id == mixed_batch.id).one().price,
            Decimal("10"),
        )

    def test_position_create_rejects_foreign_strategy_without_side_effects(self):
        counts_before = {
            model: self.db.query(model).count()
            for model in (
                Position,
                TradeBatch,
                TradingPosition,
                PositionEvent,
                AccountLedgerEntry,
            )
        }
        response = self.client.post(
            "/api/positions",
            headers={"Idempotency-Key": "foreign-strategy-open"},
            json={
                "account_id": self.owner_account.id,
                "strategy_id": self.foreign_strategy.id,
                "symbol": "MIXED",
                "exchange_code": "NASDAQ",
                "asset_type": "EQUITY",
                "direction": "LONG",
                "entry_price": "10",
                "quantity": "1",
                "entry_time": "2026-07-24T09:30:00+00:00",
                "asset_metadata": {
                    "core_type": "STOCK",
                    "market": "US",
                    "currency": "USD",
                    "instrument": "SPOT",
                },
            },
        )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertEqual(response.json()["detail"], "Strategy not found")
        self.assertEqual(
            {model: self.db.query(model).count() for model in counts_before},
            counts_before,
        )

    def test_legacy_truth_sync_rejects_cross_owner_strategy(self):
        mixed_position = Position(
            public_id="mixed-owner-position-public-id",
            user_id=self.owner.id,
            account_id=self.owner_account.id,
            strategy_id=self.foreign_strategy.id,
            symbol="MIXED",
            exchange="NASDAQ",
            asset_type="EQUITY",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=Decimal("1"),
            average_entry_price=Decimal("10"),
            opened_at=datetime(2026, 7, 24, 9, 30, tzinfo=timezone.utc),
        )
        self.db.add(mixed_position)
        self.db.commit()

        with self.assertRaisesRegex(ValueError, "strategy .* different owners"):
            sync_legacy_position_to_truth(self.db, mixed_position.id)

        self.assertEqual(
            self.client.get(
                f"/api/positions/{mixed_position.public_id}"
            ).status_code,
            404,
        )
        self.assertEqual(
            self.db.query(TradingPosition).filter(
                TradingPosition.public_id != self.owner_truth.public_id,
                TradingPosition.public_id != self.foreign_truth.public_id,
            ).count(),
            0,
        )

    def test_truth_lifecycle_fails_closed_for_cross_owner_nested_event(self):
        self.owner_event.user_id = self.foreign.id
        self.db.commit()

        response = self.client.get(
            f"/api/trading-positions/{self.owner_truth.public_id}/lifecycle"
        )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertNotIn(self.owner_event.public_id, response.text)
        self.assertEqual(
            self.db.query(PositionEvent).filter(
                PositionEvent.public_id == self.owner_event.public_id
            ).one().user_id,
            self.foreign.id,
        )

    def test_truth_lifecycle_fails_closed_for_cross_position_reversal_reference(self):
        self.db.execute(
            text(
                "UPDATE position_events "
                "SET reverses_event_id = :foreign_event_id "
                "WHERE id = :owner_event_id"
            ),
            {
                "foreign_event_id": self.foreign_event.id,
                "owner_event_id": self.owner_event.id,
            },
        )
        self.db.commit()

        response = self.client.get(
            f"/api/trading-positions/{self.owner_truth.public_id}/lifecycle"
        )

        self.assertEqual(response.status_code, 404, response.text)
        self.assertNotIn(self.foreign_event.public_id, response.text)

    def test_ledger_writers_reject_cross_owner_nested_graphs(self):
        ledger_count = self.db.query(AccountLedgerEntry).count()

        with self.assertRaisesRegex(ValueError, "different owners"):
            sync_transaction_to_account_ledger(
                self.db,
                transaction=self.foreign_transaction,
                account=self.owner_account,
            )

        self.owner_event.user_id = self.foreign.id
        self.db.flush()
        with self.assertRaisesRegex(ValueError, "owner graph is inconsistent"):
            sync_dividend_event_to_account_ledger(
                self.db,
                event=self.owner_event,
            )

        self.db.rollback()
        self.assertEqual(self.db.query(AccountLedgerEntry).count(), ledger_count)

    def test_legacy_import_routes_remain_deny_only(self):
        for method, path in (
            ("POST", "/api/positions/import/upload"),
            ("POST", "/api/positions/import/confirm"),
            ("GET", "/api/positions/import/template"),
        ):
            response = self.client.request(method, path)
            self.assertEqual(response.status_code, 404, response.text)
            self.assertEqual(response.json()["detail"]["code"], "FEATURE_DISABLED")
