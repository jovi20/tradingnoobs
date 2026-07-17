import os
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from app_config.release_contract import ReleaseContractViolation
from models import (
    AccountLedgerEntry,
    AccountLedgerEntryType,
    AssetMaster,
    AssetMetadata,
    BatchType,
    Position,
    PositionDirection,
    PositionStatus,
    PositionEvent,
    PositionEventType,
    TradeBatch,
    TradeInstrument,
    TradeInstrumentType,
    TradingAccount,
    TradingPosition,
    TradingPositionSide,
    TradingPositionStatus,
    User,
)
from services.legacy_truth_sync_service import (
    sync_all_legacy_positions_to_truth,
    sync_legacy_position_to_truth,
    validate_legacy_instrument_identity,
)


class LegacyTruthSyncTests(unittest.TestCase):
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

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _seed_legacy_position(
        self,
        *,
        email: str = "legacy@example.com",
        user_public_id: str = "user-public-id",
        account_public_id: str = "acct-public-id",
        position_public_id: str = "legacy-position",
        symbol: str = "AAPL",
        position_opened_at: datetime | None = None,
        position_closed_at: datetime | None = None,
        realized_pnl: Decimal = Decimal("180"),
    ):
        user = self.db.query(User).filter(User.email_normalized == email).first()
        if not user:
            user = User(
                email=email,
                email_normalized=email,
                hashed_password="hashed",
                public_id=user_public_id,
                status="ACTIVE",
                is_active=True,
                role="user",
            )
            self.db.add(user)
            self.db.commit()
            self.db.refresh(user)

        account = TradingAccount(
            user_id=user.id,
            public_id=account_public_id,
            name="IBKR Main",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)

        metadata = AssetMetadata(
            symbol=symbol,
            name=f"{symbol} Inc.",
            core_type="STOCK",
            market="US",
            currency="USD",
            instrument="Spot",
        )
        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(account)

        position = Position(
            user_id=user.id,
            account_id=account.id,
            public_id=position_public_id,
            strategy_id=None,
            symbol=symbol,
            exchange="NASDAQ",
            asset_type="EQUITY",
            direction=PositionDirection.LONG,
            status=PositionStatus.CLOSED,
            total_quantity=Decimal("0"),
            average_entry_price=Decimal("185"),
            realized_pnl=realized_pnl,
            opened_at=position_opened_at or datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
            closed_at=position_closed_at or datetime(2026, 4, 5, 16, 0, tzinfo=timezone.utc),
            trade_review="Held plan well.",
            checklist_responses={"pre_market": True, "risk_check": False},
            asset_metadata_symbol=symbol,
        )
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)

        batches = [
            TradeBatch(
                public_id=f"{position_public_id}-batch-open",
                position_id=position.id,
                type=BatchType.ENTRY,
                price=Decimal("180"),
                quantity=Decimal("5"),
                time=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
                reason="Initial breakout entry",
                emotion="Confident",
                confidence=4,
            ),
            TradeBatch(
                public_id=f"{position_public_id}-batch-add",
                position_id=position.id,
                type=BatchType.ENTRY,
                price=Decimal("190"),
                quantity=Decimal("5"),
                time=datetime(2026, 4, 2, 10, 0, tzinfo=timezone.utc),
                reason="Added on continuation",
                emotion="Focused",
                confidence=4,
            ),
            TradeBatch(
                public_id=f"{position_public_id}-batch-close",
                position_id=position.id,
                type=BatchType.EXIT,
                price=Decimal("203"),
                quantity=Decimal("10"),
                time=position.closed_at,
                reason="Take profit",
                emotion="Calm",
                confidence=5,
                pnl=realized_pnl,
            ),
        ]
        self.db.add_all(batches)
        self.db.commit()
        return position

    def _expected_identity(self, position: Position):
        self.db.refresh(position)
        metadata = position.asset_metadata
        return validate_legacy_instrument_identity(
            position_asset_type=position.asset_type,
            account_currency=position.trading_account.currency,
            symbol=position.symbol,
            exchange_code=position.exchange,
            metadata_core_type=metadata.core_type if metadata else None,
            metadata_market=metadata.market if metadata else None,
            metadata_currency=metadata.currency if metadata else None,
            metadata_instrument=metadata.instrument if metadata else None,
        )

    def test_sync_legacy_position_creates_truth_position_and_events(self):
        legacy_position = self._seed_legacy_position()

        truth_position = sync_legacy_position_to_truth(
            self.db,
            legacy_position.id,
            expected_identity=self._expected_identity(legacy_position),
        )

        self.assertIsInstance(truth_position, TradingPosition)
        self.assertEqual(truth_position.status, TradingPositionStatus.CLOSED)
        self.assertEqual(truth_position.side, TradingPositionSide.LONG)
        self.assertEqual(float(truth_position.quantity_opened), 10.0)
        self.assertEqual(float(truth_position.quantity_closed), 10.0)
        self.assertEqual(float(truth_position.avg_open_price), 185.0)
        self.assertEqual(float(truth_position.avg_close_price), 203.0)
        self.assertEqual(float(truth_position.realized_pnl_gross), 180.0)
        self.assertEqual(float(truth_position.realized_pnl_net), 180.0)

        instrument = self.db.query(TradeInstrument).one()
        self.assertEqual(instrument.instrument_type, TradeInstrumentType.SPOT)
        self.assertEqual(instrument.contract_symbol, "AAPL")

        events = self.db.query(PositionEvent).order_by(PositionEvent.event_time.asc()).all()
        self.assertEqual(len(events), 3)
        self.assertEqual(
            [event.event_type for event in events],
            [PositionEventType.OPEN, PositionEventType.ADD, PositionEventType.CLOSE],
        )
        self.assertEqual(events[0].checklist_snapshot["pre_market"], True)
        self.assertEqual(events[0].thesis, "Initial breakout entry")
        self.assertEqual(events[2].realized_pnl_net, Decimal("180"))

        ledger_entries = self.db.query(AccountLedgerEntry).order_by(AccountLedgerEntry.occurred_at.asc()).all()
        self.assertEqual(len(ledger_entries), 1)
        self.assertEqual(ledger_entries[0].entry_type, AccountLedgerEntryType.REALIZED_PNL)
        self.assertEqual(ledger_entries[0].position_event_id, events[2].id)
        self.assertEqual(ledger_entries[0].amount, Decimal("180"))
        self.assertEqual(ledger_entries[0].currency, "USD")

    def test_sync_legacy_position_is_idempotent(self):
        legacy_position = self._seed_legacy_position()

        first = sync_legacy_position_to_truth(
            self.db,
            legacy_position.id,
            expected_identity=self._expected_identity(legacy_position),
        )
        second = sync_legacy_position_to_truth(self.db, legacy_position.id)

        self.assertEqual(first.id, second.id)
        self.assertEqual(self.db.query(TradingPosition).count(), 1)
        self.assertEqual(self.db.query(TradeInstrument).count(), 1)
        self.assertEqual(self.db.query(PositionEvent).count(), 3)
        self.assertEqual(self.db.query(AccountLedgerEntry).count(), 1)

    def test_sync_rejects_nonconforming_metadata_before_canonical_writes(self):
        legacy_position = self._seed_legacy_position()
        metadata = self.db.query(AssetMetadata).filter(AssetMetadata.symbol == "AAPL").one()
        metadata.currency = "HKD"
        self.db.commit()

        with self.assertRaises(ReleaseContractViolation) as raised:
            sync_legacy_position_to_truth(self.db, legacy_position.id)

        self.assertEqual(raised.exception.code, "UNSUPPORTED_RELEASE_CURRENCY")
        self.assertEqual(self.db.query(TradingPosition).count(), 0)
        self.assertEqual(self.db.query(TradeInstrument).count(), 0)

    def test_sync_rejects_missing_account_before_any_truth_writes(self):
        legacy_position = self._seed_legacy_position()
        legacy_position.account_id = 999999
        self.db.commit()

        with self.assertRaisesRegex(ValueError, "Trading account 999999.*not found"):
            sync_legacy_position_to_truth(self.db, legacy_position.id)

        for model in (
            AssetMaster,
            TradeInstrument,
            TradingPosition,
            PositionEvent,
            AccountLedgerEntry,
        ):
            with self.subTest(model=model.__name__):
                self.assertEqual(self.db.query(model).count(), 0)

    def test_sync_rejects_foreign_owner_account_before_any_truth_writes(self):
        legacy_position = self._seed_legacy_position()
        foreign_user = User(
            email="foreign-sync-owner@example.com",
            email_normalized="foreign-sync-owner@example.com",
            hashed_password="hashed",
            public_id="foreign-sync-owner",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(foreign_user)
        self.db.commit()
        foreign_account = TradingAccount(
            user_id=foreign_user.id,
            public_id="foreign-sync-account",
            name="Foreign account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(foreign_account)
        self.db.commit()
        legacy_position.account_id = foreign_account.id
        self.db.commit()

        with self.assertRaisesRegex(ValueError, "have different owners"):
            sync_legacy_position_to_truth(self.db, legacy_position.id)

        for model in (
            AssetMaster,
            TradeInstrument,
            TradingPosition,
            PositionEvent,
            AccountLedgerEntry,
        ):
            with self.subTest(model=model.__name__):
                self.assertEqual(self.db.query(model).count(), 0)

    def test_sync_legacy_position_derives_truth_pnl_from_fifo_events(self):
        legacy_position = self._seed_legacy_position(realized_pnl=Decimal("999"))

        truth_position = sync_legacy_position_to_truth(
            self.db,
            legacy_position.id,
            expected_identity=self._expected_identity(legacy_position),
        )

        events = self.db.query(PositionEvent).order_by(PositionEvent.event_time.asc()).all()
        ledger_entries = self.db.query(AccountLedgerEntry).order_by(AccountLedgerEntry.occurred_at.asc()).all()
        self.assertEqual(float(truth_position.realized_pnl_gross), 180.0)
        self.assertEqual(float(truth_position.realized_pnl_net), 180.0)
        self.assertEqual(events[2].realized_pnl_gross, Decimal("180"))
        self.assertEqual(events[2].realized_pnl_net, Decimal("180"))
        self.assertEqual(ledger_entries[0].amount, Decimal("180"))

    def test_sync_all_legacy_positions_reports_created_summary(self):
        first_position = self._seed_legacy_position(
            email="batch@example.com",
            user_public_id="user-batch",
            account_public_id="acct-batch-1",
            position_public_id="legacy-pos-1",
            symbol="AAPL",
            realized_pnl=Decimal("180"),
        )
        second_position = self._seed_legacy_position(
            email="batch@example.com",
            user_public_id="user-batch",
            account_public_id="acct-batch-2",
            position_public_id="legacy-pos-2",
            symbol="MSFT",
            position_opened_at=datetime(2026, 4, 2, 9, 30, tzinfo=timezone.utc),
            position_closed_at=datetime(2026, 4, 6, 16, 0, tzinfo=timezone.utc),
            realized_pnl=Decimal("90"),
        )

        summary = sync_all_legacy_positions_to_truth(
            self.db,
            expected_identities={
                first_position.id: self._expected_identity(first_position),
                second_position.id: self._expected_identity(second_position),
            },
        )

        self.assertEqual(summary["processed"], 2)
        self.assertEqual(summary["created_positions"], 2)
        self.assertEqual(summary["updated_positions"], 0)
        self.assertEqual(summary["errors"], 0)
        self.assertEqual(self.db.query(TradingPosition).count(), 2)
        self.assertEqual(self.db.query(PositionEvent).count(), 6)
        self.assertEqual(self.db.query(AccountLedgerEntry).count(), 2)

    def test_sync_all_legacy_positions_is_idempotent_across_reruns(self):
        position = self._seed_legacy_position(
            email="idempotent@example.com",
            user_public_id="user-idempotent",
            account_public_id="acct-idempotent",
            position_public_id="legacy-pos-idempotent",
            symbol="NVDA",
        )

        first = sync_all_legacy_positions_to_truth(
            self.db,
            expected_identities={
                position.id: self._expected_identity(position),
            },
        )
        second = sync_all_legacy_positions_to_truth(self.db)

        self.assertEqual(first["processed"], 1)
        self.assertEqual(first["created_positions"], 1)
        self.assertEqual(second["processed"], 1)
        self.assertEqual(second["created_positions"], 0)
        self.assertEqual(second["updated_positions"], 1)
        self.assertEqual(self.db.query(TradingPosition).count(), 1)
        self.assertEqual(self.db.query(PositionEvent).count(), 3)
        self.assertEqual(self.db.query(AccountLedgerEntry).count(), 1)


if __name__ == "__main__":
    unittest.main()
