import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import BusinessLock, BusinessLockStatus, JobDefinition, JobRun, JobRunEvent, JobRunEventType, JobRunStatus
from services.job_service import (
    cancel_job_run,
    claim_next_due_job,
    complete_job_run,
    fail_job_run,
    heartbeat_job_run,
    recover_stale_running_jobs,
    requeue_job_run,
    run_next_due_job,
)


class JobServiceTests(unittest.TestCase):
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

    def _definition(self) -> JobDefinition:
        definition = JobDefinition(
            key="derived.timeline.refresh",
            display_name="Refresh Timeline Read Model",
            queue_name="derived",
            retry_policy={"max_attempts": 3},
            timeout_seconds=300,
            is_active=True,
        )
        self.db.add(definition)
        self.db.flush()
        return definition

    def test_claim_next_due_job_locks_highest_priority_queued_run(self):
        definition = self._definition()
        due_at = datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc)
        low_priority = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.QUEUED,
            priority=1,
            payload={"position_event_public_id": "evt-low"},
            max_attempts=3,
            queue_name="derived",
            next_run_at=due_at,
        )
        high_priority = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.QUEUED,
            priority=10,
            payload={"position_event_public_id": "evt-high"},
            max_attempts=3,
            queue_name="derived",
            next_run_at=due_at,
        )
        future = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.QUEUED,
            priority=100,
            payload={"position_event_public_id": "evt-future"},
            max_attempts=3,
            queue_name="derived",
            next_run_at=datetime(2026, 5, 3, 11, 0, tzinfo=timezone.utc),
        )
        self.db.add_all([low_priority, high_priority, future])
        self.db.commit()

        claimed = claim_next_due_job(
            self.db,
            queue_name="derived",
            worker_id="worker-a",
            now=datetime(2026, 5, 3, 10, 5, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(claimed.id, high_priority.id)
        self.assertEqual(claimed.status, JobRunStatus.RUNNING)
        self.assertEqual(claimed.locked_by, "worker-a")
        self.assertEqual(claimed.attempt_count, 1)
        self.assertIsNotNone(claimed.locked_at)
        self.assertIsNotNone(claimed.started_at)

        self.db.refresh(low_priority)
        self.db.refresh(future)
        self.assertEqual(low_priority.status, JobRunStatus.QUEUED)
        self.assertEqual(future.status, JobRunStatus.QUEUED)

        events = self.db.query(JobRunEvent).filter(JobRunEvent.job_run_id == claimed.id).all()
        self.assertEqual([event.event_type for event in events], [
            JobRunEventType.STATUS_CHANGED,
            JobRunEventType.ATTEMPT_STARTED,
        ])
        self.assertEqual(events[0].from_status, JobRunStatus.QUEUED)
        self.assertEqual(events[0].to_status, JobRunStatus.RUNNING)
        self.assertEqual(events[1].metadata_json["worker_id"], "worker-a")

    def test_complete_job_run_marks_running_job_succeeded_and_clears_lock(self):
        definition = self._definition()
        run = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.RUNNING,
            priority=1,
            payload={"position_event_public_id": "evt-done"},
            max_attempts=3,
            attempt_count=1,
            queue_name="derived",
            locked_by="worker-a",
            locked_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            started_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.commit()

        completed = complete_job_run(
            self.db,
            job_run=run,
            result={"refreshed": True},
            now=datetime(2026, 5, 3, 10, 2, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(completed.status, JobRunStatus.SUCCEEDED)
        self.assertEqual(completed.result, {"refreshed": True})
        self.assertIsNone(completed.locked_by)
        self.assertIsNone(completed.locked_at)
        self.assertIsNotNone(completed.finished_at)

        event = self.db.query(JobRunEvent).filter(JobRunEvent.job_run_id == run.id).one()
        self.assertEqual(event.event_type, JobRunEventType.STATUS_CHANGED)
        self.assertEqual(event.from_status, JobRunStatus.RUNNING)
        self.assertEqual(event.to_status, JobRunStatus.SUCCEEDED)

    def test_fail_job_run_schedules_retry_when_attempts_remain(self):
        definition = self._definition()
        run = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.RUNNING,
            priority=1,
            payload={"position_event_public_id": "evt-retry"},
            max_attempts=3,
            attempt_count=1,
            queue_name="derived",
            locked_by="worker-a",
            locked_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            started_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.commit()

        failed = fail_job_run(
            self.db,
            job_run=run,
            error_message="temporary timeout",
            retry_delay_seconds=120,
            now=datetime(2026, 5, 3, 10, 2, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(failed.status, JobRunStatus.RETRYING)
        self.assertEqual(failed.error_message, "temporary timeout")
        self.assertEqual(
            failed.next_run_at.replace(tzinfo=timezone.utc),
            datetime(2026, 5, 3, 10, 4, tzinfo=timezone.utc),
        )
        self.assertIsNone(failed.locked_by)
        self.assertIsNone(failed.locked_at)
        self.assertIsNone(failed.finished_at)

        events = self.db.query(JobRunEvent).filter(JobRunEvent.job_run_id == run.id).all()
        self.assertEqual([event.event_type for event in events], [
            JobRunEventType.ATTEMPT_FAILED,
            JobRunEventType.RETRY_SCHEDULED,
        ])
        self.assertEqual(events[0].from_status, JobRunStatus.RUNNING)
        self.assertEqual(events[0].to_status, JobRunStatus.RETRYING)
        self.assertEqual(events[1].metadata_json["retry_delay_seconds"], 120)

    def test_fail_job_run_marks_failed_when_attempts_are_exhausted(self):
        definition = self._definition()
        run = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.RUNNING,
            priority=1,
            payload={"position_event_public_id": "evt-failed"},
            max_attempts=2,
            attempt_count=2,
            queue_name="derived",
            locked_by="worker-a",
            locked_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            started_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.commit()

        failed = fail_job_run(
            self.db,
            job_run=run,
            error_message="permanent failure",
            retry_delay_seconds=120,
            now=datetime(2026, 5, 3, 10, 2, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(failed.status, JobRunStatus.FAILED)
        self.assertEqual(failed.error_message, "permanent failure")
        self.assertIsNone(failed.next_run_at)
        self.assertIsNone(failed.locked_by)
        self.assertIsNone(failed.locked_at)
        self.assertIsNotNone(failed.finished_at)

        event = self.db.query(JobRunEvent).filter(JobRunEvent.job_run_id == run.id).one()
        self.assertEqual(event.event_type, JobRunEventType.ATTEMPT_FAILED)
        self.assertEqual(event.from_status, JobRunStatus.RUNNING)
        self.assertEqual(event.to_status, JobRunStatus.FAILED)

    def test_run_next_due_job_dispatches_registered_handler_and_completes(self):
        definition = self._definition()
        run = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.QUEUED,
            priority=1,
            payload={"position_event_public_id": "evt-handler"},
            max_attempts=3,
            queue_name="derived",
            next_run_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.commit()
        calls = []

        def refresh_timeline(job_run):
            calls.append(job_run.payload)
            return {"timeline_refreshed": True}

        processed = run_next_due_job(
            self.db,
            queue_name="derived",
            worker_id="worker-a",
            handlers={"derived.timeline.refresh": refresh_timeline},
            now=datetime(2026, 5, 3, 10, 1, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(processed.id, run.id)
        self.assertEqual(calls, [{"position_event_public_id": "evt-handler"}])
        self.assertEqual(processed.status, JobRunStatus.SUCCEEDED)
        self.assertEqual(processed.result, {"timeline_refreshed": True})
        self.assertEqual(processed.attempt_count, 1)

    def test_run_next_due_job_fails_unknown_handler_without_retry_when_exhausted(self):
        definition = self._definition()
        run = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.QUEUED,
            priority=1,
            payload={"position_event_public_id": "evt-missing-handler"},
            max_attempts=1,
            queue_name="derived",
            next_run_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.commit()

        processed = run_next_due_job(
            self.db,
            queue_name="derived",
            worker_id="worker-a",
            handlers={},
            now=datetime(2026, 5, 3, 10, 1, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(processed.id, run.id)
        self.assertEqual(processed.status, JobRunStatus.FAILED)
        self.assertIn("No handler registered", processed.error_message)
        self.assertEqual(processed.attempt_count, 1)

    def test_run_next_due_job_retries_when_business_lock_is_held(self):
        definition = self._definition()
        held = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.RUNNING,
            priority=10,
            payload={"position_event_public_id": "evt-held"},
            max_attempts=3,
            attempt_count=1,
            queue_name="derived",
            locked_by="worker-a",
            locked_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        blocked = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.QUEUED,
            priority=1,
            payload={
                "position_event_public_id": "evt-blocked",
                "business_locks": [
                    {"scope": "asset_timeframe", "resource_key": "AAPL:1d", "ttl_seconds": 300}
                ],
            },
            max_attempts=3,
            queue_name="derived",
            next_run_at=datetime(2026, 5, 3, 10, 1, tzinfo=timezone.utc),
        )
        self.db.add_all([held, blocked])
        self.db.commit()
        from services.business_lock_service import acquire_business_lock

        acquire_business_lock(
            self.db,
            scope="asset_timeframe",
            resource_key="AAPL:1d",
            owner_id=held.public_id,
            ttl_seconds=300,
            now=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        self.db.commit()

        calls = []
        processed = run_next_due_job(
            self.db,
            queue_name="derived",
            worker_id="worker-b",
            handlers={"derived.timeline.refresh": lambda job_run: calls.append(job_run.public_id)},
            now=datetime(2026, 5, 3, 10, 1, tzinfo=timezone.utc),
            retry_delay_seconds=120,
        )
        self.db.commit()

        self.assertEqual(processed.id, blocked.id)
        self.assertEqual(processed.status, JobRunStatus.RETRYING)
        self.assertIn("Business lock unavailable", processed.error_message)
        self.assertEqual(calls, [])

    def test_run_next_due_job_releases_business_lock_after_success(self):
        definition = self._definition()
        run = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.QUEUED,
            priority=1,
            payload={
                "position_event_public_id": "evt-lock-success",
                "business_locks": [
                    {"scope": "asset_timeframe", "resource_key": "MSFT:1d", "ttl_seconds": 300}
                ],
            },
            max_attempts=3,
            queue_name="derived",
            next_run_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.commit()

        processed = run_next_due_job(
            self.db,
            queue_name="derived",
            worker_id="worker-a",
            handlers={"derived.timeline.refresh": lambda job_run: {"ok": True}},
            now=datetime(2026, 5, 3, 10, 1, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(processed.status, JobRunStatus.SUCCEEDED)
        lock = self.db.query(BusinessLock).one()
        self.assertEqual(lock.owner_id, run.public_id)
        self.assertEqual(lock.status, BusinessLockStatus.RELEASED)

    def test_requeue_job_run_resets_retrying_job_for_immediate_claim(self):
        definition = self._definition()
        run = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.RETRYING,
            priority=1,
            payload={"position_event_public_id": "evt-requeue"},
            max_attempts=3,
            attempt_count=2,
            queue_name="derived",
            error_message="temporary timeout",
            next_run_at=datetime(2026, 5, 3, 11, 0, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.commit()

        requeued = requeue_job_run(
            self.db,
            job_run=run,
            now=datetime(2026, 5, 3, 10, 2, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(requeued.status, JobRunStatus.QUEUED)
        self.assertEqual(requeued.attempt_count, 0)
        self.assertIsNone(requeued.error_message)
        self.assertEqual(requeued.result, {})
        self.assertEqual(
            requeued.next_run_at.replace(tzinfo=timezone.utc),
            datetime(2026, 5, 3, 10, 2, tzinfo=timezone.utc),
        )

        claimed = claim_next_due_job(
            self.db,
            queue_name="derived",
            worker_id="worker-a",
            now=datetime(2026, 5, 3, 10, 3, tzinfo=timezone.utc),
        )
        self.assertEqual(claimed.id, run.id)
        self.assertEqual(claimed.status, JobRunStatus.RUNNING)

    def test_cancel_job_run_removes_retrying_job_from_claimable_queue(self):
        definition = self._definition()
        run = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.RETRYING,
            priority=1,
            payload={"position_event_public_id": "evt-cancel"},
            max_attempts=3,
            attempt_count=1,
            queue_name="derived",
            error_message="temporary timeout",
            next_run_at=datetime(2026, 5, 3, 10, 2, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.commit()

        cancelled = cancel_job_run(
            self.db,
            job_run=run,
            now=datetime(2026, 5, 3, 10, 1, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(cancelled.status, JobRunStatus.CANCELLED)
        self.assertIsNone(cancelled.next_run_at)
        self.assertIsNotNone(cancelled.finished_at)

        claimed = claim_next_due_job(
            self.db,
            queue_name="derived",
            worker_id="worker-a",
            now=datetime(2026, 5, 3, 10, 3, tzinfo=timezone.utc),
        )
        self.assertIsNone(claimed)

    def test_heartbeat_job_run_refreshes_running_lock_for_same_worker(self):
        definition = self._definition()
        run = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.RUNNING,
            priority=1,
            payload={"position_event_public_id": "evt-heartbeat"},
            max_attempts=3,
            attempt_count=1,
            queue_name="derived",
            locked_by="worker-a",
            locked_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            started_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.commit()

        heartbeaten = heartbeat_job_run(
            self.db,
            job_run=run,
            worker_id="worker-a",
            now=datetime(2026, 5, 3, 10, 4, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(heartbeaten.status, JobRunStatus.RUNNING)
        self.assertEqual(heartbeaten.locked_by, "worker-a")
        self.assertEqual(
            heartbeaten.locked_at.replace(tzinfo=timezone.utc),
            datetime(2026, 5, 3, 10, 4, tzinfo=timezone.utc),
        )
        event = self.db.query(JobRunEvent).filter(JobRunEvent.job_run_id == run.id).one()
        self.assertEqual(event.event_type, JobRunEventType.LOG)
        self.assertEqual(event.metadata_json["worker_id"], "worker-a")

    def test_recover_stale_running_jobs_retries_only_timed_out_runs(self):
        definition = self._definition()
        stale = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.RUNNING,
            priority=1,
            payload={"position_event_public_id": "evt-stale"},
            max_attempts=3,
            attempt_count=1,
            queue_name="derived",
            locked_by="worker-a",
            locked_at=datetime(2026, 5, 3, 9, 50, tzinfo=timezone.utc),
            started_at=datetime(2026, 5, 3, 9, 49, tzinfo=timezone.utc),
        )
        fresh = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.RUNNING,
            priority=1,
            payload={"position_event_public_id": "evt-fresh"},
            max_attempts=3,
            attempt_count=1,
            queue_name="derived",
            locked_by="worker-b",
            locked_at=datetime(2026, 5, 3, 10, 4, tzinfo=timezone.utc),
            started_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        self.db.add_all([stale, fresh])
        self.db.commit()

        recovered_count = recover_stale_running_jobs(
            self.db,
            queue_name="derived",
            stale_after_seconds=300,
            retry_delay_seconds=120,
            now=datetime(2026, 5, 3, 10, 5, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(recovered_count, 1)
        self.db.refresh(stale)
        self.db.refresh(fresh)
        self.assertEqual(stale.status, JobRunStatus.RETRYING)
        self.assertEqual(stale.error_message, "Job lock timed out after 300 seconds.")
        self.assertIsNone(stale.locked_by)
        self.assertIsNone(stale.locked_at)
        self.assertEqual(
            stale.next_run_at.replace(tzinfo=timezone.utc),
            datetime(2026, 5, 3, 10, 7, tzinfo=timezone.utc),
        )
        self.assertEqual(fresh.status, JobRunStatus.RUNNING)
        self.assertEqual(fresh.locked_by, "worker-b")

    def test_recover_stale_running_jobs_fails_exhausted_runs(self):
        definition = self._definition()
        run = JobRun(
            job_definition_id=definition.id,
            status=JobRunStatus.RUNNING,
            priority=1,
            payload={"position_event_public_id": "evt-stale-exhausted"},
            max_attempts=1,
            attempt_count=1,
            queue_name="derived",
            locked_by="worker-a",
            locked_at=datetime(2026, 5, 3, 9, 50, tzinfo=timezone.utc),
            started_at=datetime(2026, 5, 3, 9, 49, tzinfo=timezone.utc),
        )
        self.db.add(run)
        self.db.commit()

        recovered_count = recover_stale_running_jobs(
            self.db,
            queue_name="derived",
            stale_after_seconds=300,
            now=datetime(2026, 5, 3, 10, 5, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(recovered_count, 1)
        self.assertEqual(run.status, JobRunStatus.FAILED)
        self.assertEqual(run.error_message, "Job lock timed out after 300 seconds.")
        self.assertIsNone(run.next_run_at)
        self.assertIsNotNone(run.finished_at)


if __name__ == "__main__":
    unittest.main()
