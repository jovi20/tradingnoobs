import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    AccountLedgerEntry,
    AccountLedgerEntryType,
    AssetMaster,
    PositionEvent,
    PositionEventType,
    TradeInstrument,
    TradeInstrumentType,
    TradingAccount,
    TradingPosition,
    TradingPositionSide,
    TradingPositionStatus,
    User,
)


class TradingTruthModelTests(unittest.TestCase):
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

    def test_trading_truth_models_can_be_persisted_with_expected_defaults(self):
        user = User(
            email="truth@example.com",
            email_normalized="truth@example.com",
            hashed_password="hashed",
            public_id="user-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        account = TradingAccount(
            user_id=user.id,
            public_id="acct-public-id",
            name="IBKR Main",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

        asset = AssetMaster(
            canonical_code="AAPL",
            display_symbol="AAPL",
            name="Apple Inc.",
            asset_type="STOCK",
            quote_currency="USD",
            status="ACTIVE",
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)

        instrument = TradeInstrument(
            asset_id=asset.id,
            instrument_type=TradeInstrumentType.SPOT,
            display_name="Apple Spot",
            contract_symbol="AAPL",
            status="ACTIVE",
        )
        self.db.add(instrument)
        self.db.commit()
        self.db.refresh(instrument)

        position = TradingPosition(
            user_id=user.id,
            account_id=account.id,
            instrument_id=instrument.id,
            status=TradingPositionStatus.OPEN,
            side=TradingPositionSide.LONG,
            opened_at=datetime(2026, 4, 15, 9, 30, tzinfo=timezone.utc),
            base_currency="USD",
            quantity_opened=10,
            avg_open_price=180,
        )
        self.db.add(position)
        self.db.commit()
        self.db.refresh(position)

        event = PositionEvent(
            user_id=user.id,
            position_id=position.id,
            account_id=account.id,
            instrument_id=instrument.id,
            event_type=PositionEventType.OPEN,
            event_time=datetime(2026, 4, 15, 9, 30, tzinfo=timezone.utc),
            side_effect="LONG",
            quantity=10,
            price=180,
            currency="USD",
            gross_amount=1800,
            input_source="MANUAL",
            thesis="Opening breakout position",
            checklist_snapshot={"pre_market": True},
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        ledger_entry = AccountLedgerEntry(
            user_id=user.id,
            account_id=account.id,
            position_id=position.id,
            position_event_id=event.id,
            entry_type=AccountLedgerEntryType.REALIZED_PNL,
            occurred_at=datetime(2026, 4, 15, 9, 30, tzinfo=timezone.utc),
            currency="USD",
            amount=0,
            amount_account_ccy=0,
            fx_rate_to_account_ccy=1,
            source="MANUAL",
            description="Opening cash effect placeholder",
        )
        self.db.add(ledger_entry)
        self.db.commit()
        self.db.refresh(ledger_entry)
        self.db.refresh(position)

        self.assertIsNotNone(asset.public_id)
        self.assertIsNotNone(instrument.public_id)
        self.assertIsNotNone(position.public_id)
        self.assertIsNotNone(event.public_id)
        self.assertIsNotNone(ledger_entry.public_id)
        self.assertEqual(position.cost_basis_method, "FIFO")
        self.assertEqual(position.status, TradingPositionStatus.OPEN)
        self.assertEqual(position.instrument.contract_symbol, "AAPL")
        self.assertEqual(event.position.public_id, position.public_id)
        self.assertEqual(event.event_type, PositionEventType.OPEN)
        self.assertEqual(event.checklist_snapshot["pre_market"], True)
        self.assertEqual(ledger_entry.entry_type, AccountLedgerEntryType.REALIZED_PNL)
        self.assertEqual(ledger_entry.position_event.public_id, event.public_id)


if __name__ == "__main__":
    unittest.main()
