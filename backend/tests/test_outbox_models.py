import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import IdempotencyKey, JobRun, JobRunEvent, JobRunStatus, OutboxEvent, OutboxEventStatus, User
from services.outbox_service import relay_pending_outbox_events


class OutboxModelTests(unittest.TestCase):
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

    def test_outbox_event_persists_dispatch_metadata_and_payload(self):
        user = User(
            email="outbox@example.com",
            email_normalized="outbox@example.com",
            hashed_password="hashed",
            public_id="user-outbox-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        event = OutboxEvent(
            user_id=user.id,
            aggregate_type="TradingPosition",
            aggregate_public_id="tp-1",
            event_type="truth.position_event.created",
            queue_name="derived",
            dedupe_key="truth.position_event.created:evt-1",
            payload={"position_event_public_id": "evt-1"},
            available_at=datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        self.assertEqual(event.status, OutboxEventStatus.PENDING)
        self.assertEqual(event.attempt_count, 0)
        self.assertEqual(event.queue_name, "derived")
        self.assertEqual(event.payload["position_event_public_id"], "evt-1")
        self.assertEqual(event.user.email, "outbox@example.com")

    def test_relay_pending_outbox_events_creates_job_run_and_marks_published(self):
        user = User(
            email="relay@example.com",
            email_normalized="relay@example.com",
            hashed_password="hashed",
            public_id="user-relay-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        event = OutboxEvent(
            user_id=user.id,
            aggregate_type="TradingPosition",
            aggregate_public_id="tp-1",
            event_type="truth.position_event.created",
            queue_name="derived",
            dedupe_key="truth.position_event.created:evt-1",
            payload={
                "trading_position_public_id": "tp-1",
                "position_event_public_id": "evt-1",
                "position_event_type": "REDUCE",
            },
            available_at=datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc),
        )
        self.db.add(event)
        self.db.commit()

        relayed = relay_pending_outbox_events(
            self.db,
            now=datetime(2026, 5, 3, 9, 1, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(relayed, 1)
        self.db.refresh(event)
        self.assertEqual(event.status, OutboxEventStatus.PUBLISHED)
        self.assertIsNotNone(event.published_at)

        job_run = self.db.query(JobRun).one()
        self.assertEqual(job_run.status, JobRunStatus.QUEUED)
        self.assertEqual(job_run.queue_name, "derived")
        self.assertEqual(job_run.idempotency_key, event.dedupe_key)
        self.assertEqual(job_run.payload["outbox_event_public_id"], event.public_id)
        self.assertEqual(job_run.payload["position_event_public_id"], "evt-1")

        job_event = self.db.query(JobRunEvent).one()
        self.assertEqual(job_event.job_run_id, job_run.id)
        self.assertEqual(job_event.to_status, JobRunStatus.QUEUED)
        self.assertEqual(job_event.metadata_json["source"], "outbox")

        idempotency_key = self.db.query(IdempotencyKey).one()
        self.assertEqual(idempotency_key.scope, "outbox_event")
        self.assertEqual(idempotency_key.key, event.dedupe_key)
        self.assertEqual(idempotency_key.job_run_id, job_run.id)


if __name__ == "__main__":
    unittest.main()
