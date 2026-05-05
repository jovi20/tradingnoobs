import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    BusinessLock,
    BusinessLockStatus,
    IdempotencyKey,
    JobDefinition,
    JobRun,
    JobRunEvent,
    JobRunEventType,
    JobRunStatus,
    User,
)


class JobModelTests(unittest.TestCase):
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

    def test_job_models_persist_definition_run_events_and_idempotency_key(self):
        user = User(
            email="jobs@example.com",
            email_normalized="jobs@example.com",
            hashed_password="hashed",
            public_id="user-jobs-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        definition = JobDefinition(
            key="derived.timeline.refresh",
            display_name="Refresh Timeline Read Model",
            description="Rebuild timeline cards after truth events change.",
            queue_name="derived",
            retry_policy={"max_attempts": 3, "backoff": "exponential"},
            timeout_seconds=300,
            is_active=True,
        )
        self.db.add(definition)
        self.db.commit()
        self.db.refresh(definition)

        run = JobRun(
            user_id=user.id,
            job_definition_id=definition.id,
            idempotency_key="timeline:tp-1:refresh",
            status=JobRunStatus.QUEUED,
            priority=10,
            payload={"trading_position_public_id": "tp-1"},
            max_attempts=3,
            next_run_at=datetime(2026, 5, 3, 8, 0, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)

        event = JobRunEvent(
            job_run_id=run.id,
            event_type=JobRunEventType.STATUS_CHANGED,
            from_status=None,
            to_status=JobRunStatus.QUEUED,
            message="Queued from truth event write.",
            metadata_json={"source": "position_event"},
        )
        idempotency_key = IdempotencyKey(
            user_id=user.id,
            scope="job_run",
            key="timeline:tp-1:refresh",
            request_hash="sha256:payload",
            status="IN_PROGRESS",
            job_run_id=run.id,
        )
        self.db.add_all([event, idempotency_key])
        self.db.commit()
        self.db.refresh(run)

        self.assertEqual(definition.runs[0].public_id, run.public_id)
        self.assertEqual(run.status, JobRunStatus.QUEUED)
        self.assertEqual(run.attempt_count, 0)
        self.assertEqual(run.max_attempts, 3)
        self.assertEqual(run.events[0].event_type, JobRunEventType.STATUS_CHANGED)
        self.assertEqual(run.idempotency_records[0].request_hash, "sha256:payload")

    def test_business_lock_persists_scope_resource_owner_and_expiry(self):
        lock = BusinessLock(
            scope="asset_timeframe",
            resource_key="AAPL:1d",
            owner_id="job-run-public-id",
            owner_type="job_run",
            status=BusinessLockStatus.ACTIVE,
            metadata_json={"asset": "AAPL", "timeframe": "1d"},
            acquired_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            expires_at=datetime(2026, 5, 3, 10, 5, tzinfo=timezone.utc),
        )
        self.db.add(lock)
        self.db.commit()
        self.db.refresh(lock)

        self.assertEqual(lock.status, BusinessLockStatus.ACTIVE)
        self.assertEqual(lock.scope, "asset_timeframe")
        self.assertEqual(lock.resource_key, "AAPL:1d")
        self.assertEqual(lock.owner_id, "job-run-public-id")
        self.assertEqual(lock.metadata_json["timeframe"], "1d")


if __name__ == "__main__":
    unittest.main()
