import unittest
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from job_worker_cli import run_worker_batch
from models import (
    AssetMaster,
    JobRun,
    JobRunStatus,
    OutboxEvent,
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
from services.outbox_service import relay_pending_outbox_events


class JobWorkerCliTests(unittest.TestCase):
    def test_run_worker_batch_processes_until_limit_or_empty_queue(self):
        db = Mock()
        session_factory = Mock(return_value=db)
        first_job = Mock(public_id="job-1")
        second_job = Mock(public_id="job-2")

        with patch(
            "job_worker_cli.run_next_due_job",
            side_effect=[first_job, second_job, None],
        ) as run_next:
            processed = run_worker_batch(
                session_factory=session_factory,
                queue_name="derived",
                worker_id="worker-a",
                handlers={"derived.timeline.refresh": lambda job_run: {}},
                limit=5,
            )

        self.assertEqual(processed, 2)
        self.assertEqual(run_next.call_count, 3)
        self.assertEqual(db.commit.call_count, 2)
        db.rollback.assert_not_called()
        db.close.assert_called_once()

    def test_run_worker_batch_rolls_back_and_closes_on_failure(self):
        db = Mock()
        session_factory = Mock(return_value=db)

        with patch("job_worker_cli.run_next_due_job", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                run_worker_batch(
                    session_factory=session_factory,
                    queue_name="derived",
                    worker_id="worker-a",
                    handlers={},
                    limit=1,
                )

        db.commit.assert_not_called()
        db.rollback.assert_called_once()
        db.close.assert_called_once()

    def test_run_worker_batch_consumes_job_created_from_outbox_relay(self):
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        try:
            user = User(
                email="job-worker@example.com",
                email_normalized="job-worker@example.com",
                hashed_password="hashed",
                public_id="user-job-worker-public-id",
                status="ACTIVE",
                is_active=True,
                role="user",
            )
            db.add(user)
            db.flush()
            account = TradingAccount(
                user_id=user.id,
                public_id="acct-worker-public-id",
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
            db.add_all([account, asset])
            db.flush()
            instrument = TradeInstrument(
                asset_id=asset.id,
                instrument_type=TradeInstrumentType.SPOT,
                display_name="Apple Spot",
                contract_symbol="AAPL",
                status="ACTIVE",
            )
            db.add(instrument)
            db.flush()
            position = TradingPosition(
                user_id=user.id,
                account_id=account.id,
                instrument_id=instrument.id,
                public_id="tp-worker-public-id",
                status=TradingPositionStatus.OPEN,
                side=TradingPositionSide.LONG,
                opened_at=datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc),
                base_currency="USD",
                quantity_opened=10,
                avg_open_price=180,
            )
            db.add(position)
            db.flush()
            event = PositionEvent(
                user_id=user.id,
                position_id=position.id,
                account_id=account.id,
                instrument_id=instrument.id,
                public_id="evt-worker",
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
            db.add(event)
            db.commit()
            db.add(
                OutboxEvent(
                    user_id=user.id,
                    aggregate_type="TradingPosition",
                    aggregate_public_id=position.public_id,
                    event_type="truth.position_event.created",
                    queue_name="derived",
                    dedupe_key="truth.position_event.created:evt-worker",
                    payload={
                        "trading_position_public_id": position.public_id,
                        "position_event_public_id": event.public_id,
                    },
                    available_at=datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc),
                )
            )
            db.commit()

            relayed = relay_pending_outbox_events(
                db,
                now=datetime(2026, 5, 3, 9, 1, tzinfo=timezone.utc),
            )
            db.commit()
            db.close()
            processed = run_worker_batch(
                session_factory=SessionLocal,
                queue_name="derived",
                worker_id="worker-a",
                limit=5,
                now=datetime(2026, 5, 3, 9, 2, tzinfo=timezone.utc),
            )

            db = SessionLocal()
            job_run = db.query(JobRun).one()
            self.assertEqual(relayed, 1)
            self.assertEqual(processed, 1)
            self.assertEqual(job_run.status, JobRunStatus.SUCCEEDED)
            self.assertEqual(job_run.result["handler"], "derived.timeline.refresh")
            self.assertEqual(job_run.result["position_event_public_id"], "evt-worker")
            self.assertEqual(job_run.result["lifecycle_node_count"], 1)
        finally:
            db.close()
            engine.dispose()
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
