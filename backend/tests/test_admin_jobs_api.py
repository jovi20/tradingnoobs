import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import BusinessLock, BusinessLockStatus, JobDefinition, JobRun, JobRunEvent, JobRunEventType, JobRunStatus, User
from routers.admin import get_current_admin


class AdminJobsApiTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.admin_user = User(
            email="admin-jobs@example.com",
            email_normalized="admin-jobs@example.com",
            hashed_password="hashed",
            public_id="admin-jobs-public-id",
            status="ACTIVE",
            is_active=True,
            role="admin",
        )

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        def override_get_current_admin():
            return self.admin_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_admin] = override_get_current_admin
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_admin_can_read_job_detail_with_events_and_result(self):
        db = self.SessionLocal()
        try:
            db.add(self.admin_user)
            db.flush()
            definition = JobDefinition(
                key="derived.timeline.refresh",
                display_name="Refresh Timeline Read Model",
                queue_name="derived",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            db.add(definition)
            db.flush()
            job_run = JobRun(
                user_id=self.admin_user.id,
                job_definition_id=definition.id,
                public_id="job-public-id",
                idempotency_key="truth.position_event.created:evt-1",
                status=JobRunStatus.SUCCEEDED,
                payload={"position_event_public_id": "evt-1"},
                result={"handler": "derived.timeline.refresh", "lifecycle_node_count": 1},
                max_attempts=3,
                attempt_count=1,
                queue_name="derived",
            )
            db.add(job_run)
            db.flush()
            db.add(
                BusinessLock(
                    scope="derived.timeline.refresh",
                    resource_key="tp-1",
                    owner_id=job_run.public_id,
                    owner_type="job_run",
                    status=BusinessLockStatus.RELEASED,
                    expires_at=datetime(2026, 5, 3, 10, 5, tzinfo=timezone.utc),
                )
            )
            db.add(
                JobRunEvent(
                    job_run_id=job_run.id,
                    event_type=JobRunEventType.STATUS_CHANGED,
                    from_status=JobRunStatus.RUNNING,
                    to_status=JobRunStatus.SUCCEEDED,
                    message="Job completed successfully.",
                    metadata_json={"result": job_run.result},
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/admin/jobs/job-public-id")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["public_id"], "job-public-id")
        self.assertEqual(payload["definition"]["key"], "derived.timeline.refresh")
        self.assertEqual(payload["status"], "SUCCEEDED")
        self.assertEqual(payload["queue_name"], "derived")
        self.assertEqual(payload["payload"], {"position_event_public_id": "evt-1"})
        self.assertEqual(payload["result"]["lifecycle_node_count"], 1)
        self.assertEqual(payload["business_locks"][0]["scope"], "derived.timeline.refresh")
        self.assertEqual(payload["business_locks"][0]["resource_key"], "tp-1")
        self.assertEqual(payload["business_locks"][0]["status"], "RELEASED")
        self.assertEqual(len(payload["events"]), 1)
        self.assertEqual(payload["events"][0]["event_type"], "STATUS_CHANGED")
        self.assertEqual(payload["events"][0]["to_status"], "SUCCEEDED")

    def test_admin_can_list_jobs_with_status_and_queue_filters(self):
        db = self.SessionLocal()
        try:
            db.add(self.admin_user)
            db.flush()
            definition = JobDefinition(
                key="derived.timeline.refresh",
                display_name="Refresh Timeline Read Model",
                queue_name="derived",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            db.add(definition)
            db.flush()
            db.add_all([
                JobRun(
                    user_id=self.admin_user.id,
                    job_definition_id=definition.id,
                    public_id="job-running",
                    status=JobRunStatus.RUNNING,
                    payload={"position_event_public_id": "evt-running"},
                    max_attempts=3,
                    attempt_count=1,
                    queue_name="derived",
                ),
                JobRun(
                    user_id=self.admin_user.id,
                    job_definition_id=definition.id,
                    public_id="job-queued",
                    status=JobRunStatus.QUEUED,
                    payload={"position_event_public_id": "evt-queued"},
                    max_attempts=3,
                    queue_name="derived",
                ),
                JobRun(
                    user_id=self.admin_user.id,
                    job_definition_id=definition.id,
                    public_id="job-other-queue",
                    status=JobRunStatus.RUNNING,
                    payload={"position_event_public_id": "evt-other"},
                    max_attempts=3,
                    queue_name="market",
                ),
            ])
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/admin/jobs?status=RUNNING&queue_name=derived&limit=10")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total"], 1)
        self.assertEqual(len(payload["items"]), 1)
        self.assertEqual(payload["items"][0]["public_id"], "job-running")
        self.assertEqual(payload["items"][0]["status"], "RUNNING")
        self.assertEqual(payload["items"][0]["definition"]["key"], "derived.timeline.refresh")

    def test_admin_job_detail_returns_404_for_unknown_public_id(self):
        response = self.client.get("/api/admin/jobs/missing-job")

        self.assertEqual(response.status_code, 404)

    def test_admin_can_requeue_failed_job(self):
        db = self.SessionLocal()
        try:
            db.add(self.admin_user)
            db.flush()
            definition = JobDefinition(
                key="derived.timeline.refresh",
                display_name="Refresh Timeline Read Model",
                queue_name="derived",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            db.add(definition)
            db.flush()
            job_run = JobRun(
                user_id=self.admin_user.id,
                job_definition_id=definition.id,
                public_id="job-failed",
                status=JobRunStatus.FAILED,
                payload={"position_event_public_id": "evt-failed"},
                result={"partial": True},
                error_message="handler exploded",
                max_attempts=3,
                attempt_count=3,
                queue_name="derived",
                locked_by="worker-a",
            )
            db.add(job_run)
            db.commit()
        finally:
            db.close()

        response = self.client.post("/api/admin/jobs/job-failed/requeue")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "QUEUED")
        self.assertEqual(payload["attempt_count"], 0)
        self.assertIsNone(payload["error_message"])
        self.assertEqual(payload["result"], {})
        self.assertIsNone(payload["locked_by"])
        self.assertEqual(payload["events"][-1]["from_status"], "FAILED")
        self.assertEqual(payload["events"][-1]["to_status"], "QUEUED")

    def test_admin_requeue_rejects_succeeded_job(self):
        db = self.SessionLocal()
        try:
            db.add(self.admin_user)
            db.flush()
            definition = JobDefinition(
                key="derived.timeline.refresh",
                display_name="Refresh Timeline Read Model",
                queue_name="derived",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            db.add(definition)
            db.flush()
            db.add(
                JobRun(
                    user_id=self.admin_user.id,
                    job_definition_id=definition.id,
                    public_id="job-succeeded",
                    status=JobRunStatus.SUCCEEDED,
                    payload={"position_event_public_id": "evt-done"},
                    result={"done": True},
                    max_attempts=3,
                    attempt_count=1,
                    queue_name="derived",
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.post("/api/admin/jobs/job-succeeded/requeue")

        self.assertEqual(response.status_code, 409)

    def test_admin_can_cancel_queued_job(self):
        db = self.SessionLocal()
        try:
            db.add(self.admin_user)
            db.flush()
            definition = JobDefinition(
                key="derived.timeline.refresh",
                display_name="Refresh Timeline Read Model",
                queue_name="derived",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            db.add(definition)
            db.flush()
            db.add(
                JobRun(
                    user_id=self.admin_user.id,
                    job_definition_id=definition.id,
                    public_id="job-queued-cancel",
                    status=JobRunStatus.QUEUED,
                    payload={"position_event_public_id": "evt-cancel"},
                    max_attempts=3,
                    queue_name="derived",
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.post("/api/admin/jobs/job-queued-cancel/cancel")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "CANCELLED")
        self.assertIsNotNone(payload["finished_at"])
        self.assertEqual(payload["events"][-1]["event_type"], "CANCELLED")
        self.assertEqual(payload["events"][-1]["from_status"], "QUEUED")
        self.assertEqual(payload["events"][-1]["to_status"], "CANCELLED")

    def test_admin_cancel_rejects_running_job(self):
        db = self.SessionLocal()
        try:
            db.add(self.admin_user)
            db.flush()
            definition = JobDefinition(
                key="derived.timeline.refresh",
                display_name="Refresh Timeline Read Model",
                queue_name="derived",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            db.add(definition)
            db.flush()
            db.add(
                JobRun(
                    user_id=self.admin_user.id,
                    job_definition_id=definition.id,
                    public_id="job-running-cancel",
                    status=JobRunStatus.RUNNING,
                    payload={"position_event_public_id": "evt-running"},
                    max_attempts=3,
                    attempt_count=1,
                    queue_name="derived",
                    locked_by="worker-a",
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.post("/api/admin/jobs/job-running-cancel/cancel")

        self.assertEqual(response.status_code, 409)

    def test_admin_can_force_cancel_running_job(self):
        db = self.SessionLocal()
        try:
            db.add(self.admin_user)
            db.flush()
            definition = JobDefinition(
                key="derived.timeline.refresh",
                display_name="Refresh Timeline Read Model",
                queue_name="derived",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            db.add(definition)
            db.flush()
            job_run = JobRun(
                user_id=self.admin_user.id,
                job_definition_id=definition.id,
                public_id="job-running-force-cancel",
                status=JobRunStatus.RUNNING,
                payload={"position_event_public_id": "evt-running"},
                max_attempts=3,
                attempt_count=1,
                queue_name="derived",
                locked_by="worker-a",
                locked_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            )
            db.add(job_run)
            db.flush()
            db.add(
                BusinessLock(
                    scope="derived.timeline.refresh",
                    resource_key="tp-force-cancel",
                    owner_id=job_run.public_id,
                    owner_type="job_run",
                    status=BusinessLockStatus.ACTIVE,
                    expires_at=datetime(2026, 5, 3, 10, 5, tzinfo=timezone.utc),
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.post("/api/admin/jobs/job-running-force-cancel/force-cancel")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "CANCELLED")
        self.assertIsNone(payload["locked_by"])
        self.assertIsNone(payload["locked_at"])
        self.assertEqual(payload["business_locks"][0]["status"], "RELEASED")
        self.assertEqual(payload["events"][-1]["event_type"], "CANCELLED")
        self.assertEqual(payload["events"][-1]["from_status"], "RUNNING")
        self.assertEqual(payload["events"][-1]["to_status"], "CANCELLED")
        self.assertEqual(payload["events"][-1]["metadata"]["force"], True)
        self.assertIn("warning", payload["events"][-1]["metadata"])
        self.assertIn("business locks", payload["events"][-1]["metadata"]["warning"].lower())

    def test_stale_running_job_returns_stale_reason_and_recommended_action(self):
        db = self.SessionLocal()
        try:
            db.add(self.admin_user)
            db.flush()
            definition = JobDefinition(
                key="derived.timeline.refresh",
                display_name="Refresh Timeline Read Model",
                queue_name="derived",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            db.add(definition)
            db.flush()
            db.add(
                JobRun(
                    user_id=self.admin_user.id,
                    job_definition_id=definition.id,
                    public_id="job-stale-running",
                    status=JobRunStatus.RUNNING,
                    payload={"position_event_public_id": "evt-stale"},
                    max_attempts=3,
                    attempt_count=1,
                    queue_name="derived",
                    locked_by="worker-a",
                    locked_at=datetime.now(timezone.utc) - timedelta(minutes=10),
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/admin/jobs?status=RUNNING&limit=10")

        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertEqual(item["public_id"], "job-stale-running")
        self.assertIn("exceeded", item["stale_reason"].lower())
        self.assertEqual(item["recommended_action"], "FORCE_CANCEL")
        self.assertIn("business locks", item["force_cancel_warning"].lower())

    def test_failed_job_returns_requeue_recommended_action(self):
        db = self.SessionLocal()
        try:
            db.add(self.admin_user)
            db.flush()
            definition = JobDefinition(
                key="derived.timeline.refresh",
                display_name="Refresh Timeline Read Model",
                queue_name="derived",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            db.add(definition)
            db.flush()
            db.add(
                JobRun(
                    user_id=self.admin_user.id,
                    job_definition_id=definition.id,
                    public_id="job-failed-recommended",
                    status=JobRunStatus.FAILED,
                    payload={"position_event_public_id": "evt-failed"},
                    error_message="handler exploded",
                    max_attempts=3,
                    attempt_count=3,
                    queue_name="derived",
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/admin/jobs/job-failed-recommended")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["recommended_action"], "REQUEUE")
        self.assertIsNone(payload["stale_reason"])


if __name__ == "__main__":
    unittest.main()
