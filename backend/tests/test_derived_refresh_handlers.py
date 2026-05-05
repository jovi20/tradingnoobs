import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    AssetMaster,
    DerivedTimelineSnapshot,
    JobDefinition,
    JobRun,
    JobRunStatus,
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
from services.derived_refresh_handlers import refresh_timeline_read_model


class DerivedRefreshHandlerTests(unittest.TestCase):
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

    def test_refresh_timeline_read_model_returns_truth_lifecycle_summary(self):
        user = User(
            email="derived-handler@example.com",
            email_normalized="derived-handler@example.com",
            hashed_password="hashed",
            public_id="user-derived-handler-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        account = TradingAccount(
            user_id=1,
            public_id="acct-derived-handler-public-id",
            name="IBKR Main",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        asset = AssetMaster(
            canonical_code="AAPL",
            display_symbol="AAPL",
            name="Apple Inc.",
            asset_type="STOCK",
            quote_currency="USD",
            status="ACTIVE",
        )
        self.db.add_all([user, asset])
        self.db.flush()
        account.user_id = user.id
        self.db.add(account)
        self.db.flush()
        instrument = TradeInstrument(
            asset_id=asset.id,
            instrument_type=TradeInstrumentType.SPOT,
            display_name="Apple Spot",
            contract_symbol="AAPL",
            status="ACTIVE",
        )
        self.db.add(instrument)
        self.db.flush()
        position = TradingPosition(
            user_id=user.id,
            account_id=account.id,
            instrument_id=instrument.id,
            public_id="tp-derived-handler-public-id",
            status=TradingPositionStatus.OPEN,
            side=TradingPositionSide.LONG,
            opened_at=datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc),
            base_currency="USD",
            quantity_opened=10,
            avg_open_price=180,
        )
        self.db.add(position)
        self.db.flush()
        event = PositionEvent(
            user_id=user.id,
            position_id=position.id,
            account_id=account.id,
            instrument_id=instrument.id,
            public_id="evt-derived-handler-public-id",
            event_type=PositionEventType.OPEN,
            event_time=datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc),
            side_effect="LONG",
            quantity=10,
            price=180,
            currency="USD",
            gross_amount=1800,
            input_source="MANUAL",
            reason="Opening breakout position",
        )
        definition = JobDefinition(
            key="derived.timeline.refresh",
            display_name="Refresh Timeline Read Model",
            queue_name="derived",
            retry_policy={"max_attempts": 3},
            timeout_seconds=300,
            is_active=True,
        )
        self.db.add_all([event, definition])
        self.db.flush()
        job_run = JobRun(
            user_id=user.id,
            job_definition_id=definition.id,
            status=JobRunStatus.RUNNING,
            payload={
                "trading_position_public_id": position.public_id,
                "position_event_public_id": event.public_id,
            },
            max_attempts=3,
            queue_name="derived",
        )
        self.db.add(job_run)
        self.db.commit()

        result = refresh_timeline_read_model(self.db, job_run)

        self.assertEqual(result["handler"], "derived.timeline.refresh")
        self.assertEqual(result["trading_position_public_id"], position.public_id)
        self.assertEqual(result["position_event_public_id"], event.public_id)
        self.assertEqual(result["lifecycle_node_count"], 1)
        self.assertEqual(result["position_title"], "AAPL")
        self.assertEqual(result["source"], "truth.lifecycle.bridge")
        snapshot = self.db.query(DerivedTimelineSnapshot).one()
        self.assertEqual(snapshot.user_id, user.id)
        self.assertEqual(snapshot.trading_position_public_id, position.public_id)
        self.assertEqual(snapshot.source, "truth.lifecycle.bridge")
        self.assertEqual(snapshot.refreshed_by_job_run_public_id, job_run.public_id)
        self.assertEqual(snapshot.snapshot_json["position_title"], "AAPL")
        self.assertEqual(snapshot.snapshot_json["lifecycle_node_count"], 1)


if __name__ == "__main__":
    unittest.main()
