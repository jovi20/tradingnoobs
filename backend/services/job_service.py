from models import IdempotencyKey, JobDefinition, JobRun, JobRunEvent
from services.identity_service import generate_public_id


class JobService:
    def __init__(self, db_session):
        self.db = db_session

    def enqueue_job(
        self,
        *,
        job_key: str,
        payload: dict,
        idempotency_scope: str,
        idempotency_key: str,
        locked_resource: str | None = None,
    ) -> JobRun:
        existing_key = self.db.query(IdempotencyKey).filter_by(
            scope=idempotency_scope,
            key=idempotency_key,
        ).one_or_none()
        if existing_key:
            existing_run = self.db.query(JobRun).filter_by(idempotency_key_id=existing_key.id).one()
            return existing_run

        definition = self._get_or_create_definition(job_key)
        key_record = IdempotencyKey(
            public_id=generate_public_id(),
            scope=idempotency_scope,
            key=idempotency_key,
            status="IN_PROGRESS",
            locked_resource=locked_resource,
        )
        self.db.add(key_record)
        self.db.flush()

        run = JobRun(
            public_id=generate_public_id(),
            job_definition_id=definition.id,
            idempotency_key_id=key_record.id,
            job_key=job_key,
            status="QUEUED",
            locked_resource=locked_resource,
            max_attempts=definition.max_attempts,
            payload=payload,
        )
        self.db.add(run)
        self.db.flush()

        key_record.response_payload = {"job_run_public_id": run.public_id}
        self.db.add(
            JobRunEvent(
                public_id=generate_public_id(),
                job_run_id=run.id,
                event_type="QUEUED",
                message="Job queued",
                payload={"job_key": job_key},
            )
        )
        self.db.flush()
        return run

    def _get_or_create_definition(self, job_key: str) -> JobDefinition:
        definition = self.db.query(JobDefinition).filter_by(job_key=job_key).one_or_none()
        if definition:
            return definition

        definition = JobDefinition(
            public_id=generate_public_id(),
            job_key=job_key,
            queue_name="default",
            max_attempts=3,
            timeout_seconds=300,
            is_active=True,
        )
        self.db.add(definition)
        self.db.flush()
        return definition

    def get_job_run_status(self, *, job_run_public_id: str) -> dict:
        run = self.db.query(JobRun).filter_by(public_id=job_run_public_id).one()
        events = (
            self.db.query(JobRunEvent)
            .filter_by(job_run_id=run.id)
            .order_by(JobRunEvent.created_at, JobRunEvent.id)
            .all()
        )
        return {
            "public_id": run.public_id,
            "job_key": run.job_key,
            "status": run.status,
            "locked_resource": run.locked_resource,
            "attempts": run.attempts,
            "max_attempts": run.max_attempts,
            "payload": run.payload,
            "result_payload": run.result_payload,
            "error_code": run.error_code,
            "error_message": run.error_message,
            "queued_at": run.queued_at.isoformat() if run.queued_at else None,
            "started_at": run.started_at.isoformat() if run.started_at else None,
            "finished_at": run.finished_at.isoformat() if run.finished_at else None,
            "events": [
                {
                    "public_id": event.public_id,
                    "event_type": event.event_type,
                    "message": event.message,
                    "payload": event.payload,
                    "created_at": event.created_at.isoformat() if event.created_at else None,
                }
                for event in events
            ],
        }
