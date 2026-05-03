import unittest
import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import Mock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from job_worker_cli import run_worker_batch
from models import JobRun, JobRunStatus, OutboxEvent, User
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
            db.commit()
            db.refresh(user)
            db.add(
                OutboxEvent(
                    user_id=user.id,
                    aggregate_type="TradingPosition",
                    aggregate_public_id="tp-1",
                    event_type="truth.position_event.created",
                    queue_name="derived",
                    dedupe_key="truth.position_event.created:evt-worker",
                    payload={"position_event_public_id": "evt-worker"},
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
            calls = []

            def refresh_timeline(job_run):
                calls.append(job_run.payload["position_event_public_id"])
                return {"refreshed": job_run.payload["position_event_public_id"]}

            processed = run_worker_batch(
                session_factory=SessionLocal,
                queue_name="derived",
                worker_id="worker-a",
                handlers={"derived.timeline.refresh": refresh_timeline},
                limit=5,
                now=datetime(2026, 5, 3, 9, 2, tzinfo=timezone.utc),
            )

            db = SessionLocal()
            job_run = db.query(JobRun).one()
            self.assertEqual(relayed, 1)
            self.assertEqual(processed, 1)
            self.assertEqual(calls, ["evt-worker"])
            self.assertEqual(job_run.status, JobRunStatus.SUCCEEDED)
            self.assertEqual(job_run.result, {"refreshed": "evt-worker"})
        finally:
            db.close()
            engine.dispose()
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
