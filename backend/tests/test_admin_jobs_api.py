import os
import tempfile
import unittest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import JobDefinition, JobRun, JobRunEvent, JobRunEventType, JobRunStatus, User
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


if __name__ == "__main__":
    unittest.main()
