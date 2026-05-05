"""
Trading Noobs Backend - Job Execution Service
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import JobRun, JobRunEvent, JobRunEventType, JobRunStatus

JobHandler = Callable[[JobRun], dict | None]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def claim_next_due_job(
    db: Session,
    *,
    queue_name: str,
    worker_id: str,
    now: datetime | None = None,
) -> JobRun | None:
    now = _as_utc(now or datetime.now(timezone.utc))
    job_run = (
        db.query(JobRun)
        .filter(
            JobRun.status.in_([JobRunStatus.QUEUED, JobRunStatus.RETRYING]),
            JobRun.queue_name == queue_name,
            or_(JobRun.next_run_at.is_(None), JobRun.next_run_at <= now),
        )
        .order_by(JobRun.priority.desc(), JobRun.created_at.asc(), JobRun.id.asc())
        .first()
    )
    if not job_run:
        return None

    previous_status = job_run.status
    job_run.status = JobRunStatus.RUNNING
    job_run.locked_by = worker_id
    job_run.locked_at = now
    job_run.started_at = now
    job_run.attempt_count = (job_run.attempt_count or 0) + 1
    db.add(
        JobRunEvent(
            job_run_id=job_run.id,
            event_type=JobRunEventType.STATUS_CHANGED,
            from_status=previous_status,
            to_status=JobRunStatus.RUNNING,
            message=f"Claimed by worker {worker_id}",
            metadata_json={"worker_id": worker_id, "queue_name": queue_name},
        )
    )
    db.add(
        JobRunEvent(
            job_run_id=job_run.id,
            event_type=JobRunEventType.ATTEMPT_STARTED,
            from_status=None,
            to_status=JobRunStatus.RUNNING,
            message=f"Attempt {job_run.attempt_count} started.",
            metadata_json={"worker_id": worker_id, "attempt": job_run.attempt_count},
        )
    )
    db.flush()
    return job_run


def complete_job_run(
    db: Session,
    *,
    job_run: JobRun,
    result: dict | None = None,
    now: datetime | None = None,
) -> JobRun:
    now = _as_utc(now or datetime.now(timezone.utc))
    previous_status = job_run.status
    job_run.status = JobRunStatus.SUCCEEDED
    job_run.result = result or {}
    job_run.error_message = None
    job_run.locked_by = None
    job_run.locked_at = None
    job_run.finished_at = now
    db.add(
        JobRunEvent(
            job_run_id=job_run.id,
            event_type=JobRunEventType.STATUS_CHANGED,
            from_status=previous_status,
            to_status=JobRunStatus.SUCCEEDED,
            message="Job completed successfully.",
            metadata_json={"result": job_run.result},
        )
    )
    db.flush()
    return job_run


def fail_job_run(
    db: Session,
    *,
    job_run: JobRun,
    error_message: str,
    retry_delay_seconds: int = 60,
    now: datetime | None = None,
) -> JobRun:
    now = _as_utc(now or datetime.now(timezone.utc))
    previous_status = job_run.status
    attempts_remain = (job_run.attempt_count or 0) < (job_run.max_attempts or 1)
    next_status = JobRunStatus.RETRYING if attempts_remain else JobRunStatus.FAILED

    job_run.status = next_status
    job_run.error_message = error_message
    job_run.locked_by = None
    job_run.locked_at = None
    job_run.next_run_at = now + timedelta(seconds=retry_delay_seconds) if attempts_remain else None
    job_run.finished_at = None if attempts_remain else now
    db.add(
        JobRunEvent(
            job_run_id=job_run.id,
            event_type=JobRunEventType.ATTEMPT_FAILED,
            from_status=previous_status,
            to_status=next_status,
            message=error_message,
            metadata_json={"attempt": job_run.attempt_count, "max_attempts": job_run.max_attempts},
        )
    )
    if attempts_remain:
        db.add(
            JobRunEvent(
                job_run_id=job_run.id,
                event_type=JobRunEventType.RETRY_SCHEDULED,
                from_status=previous_status,
                to_status=JobRunStatus.RETRYING,
                message="Retry scheduled.",
                metadata_json={
                    "retry_delay_seconds": retry_delay_seconds,
                    "next_run_at": job_run.next_run_at.isoformat(),
                },
            )
        )
    db.flush()
    return job_run


def run_next_due_job(
    db: Session,
    *,
    queue_name: str,
    worker_id: str,
    handlers: dict[str, JobHandler],
    now: datetime | None = None,
    retry_delay_seconds: int = 60,
) -> JobRun | None:
    now = _as_utc(now or datetime.now(timezone.utc))
    job_run = claim_next_due_job(db, queue_name=queue_name, worker_id=worker_id, now=now)
    if not job_run:
        return None

    handler = handlers.get(job_run.definition.key)
    if handler is None:
        return fail_job_run(
            db,
            job_run=job_run,
            error_message=f"No handler registered for job definition {job_run.definition.key}",
            retry_delay_seconds=retry_delay_seconds,
            now=now,
        )

    try:
        result = handler(job_run)
    except Exception as exc:
        return fail_job_run(
            db,
            job_run=job_run,
            error_message=str(exc),
            retry_delay_seconds=retry_delay_seconds,
            now=now,
        )

    return complete_job_run(db, job_run=job_run, result=result or {}, now=now)


def requeue_job_run(
    db: Session,
    *,
    job_run: JobRun,
    reason: str = "Requeued by admin.",
    now: datetime | None = None,
) -> JobRun:
    now = _as_utc(now or datetime.now(timezone.utc))
    if job_run.status not in [JobRunStatus.FAILED, JobRunStatus.RETRYING]:
        raise ValueError(f"Cannot requeue job in status {job_run.status.value}")

    previous_status = job_run.status
    job_run.status = JobRunStatus.QUEUED
    job_run.result = {}
    job_run.error_message = None
    job_run.attempt_count = 0
    job_run.locked_by = None
    job_run.locked_at = None
    job_run.next_run_at = now
    job_run.started_at = None
    job_run.finished_at = None
    db.add(
        JobRunEvent(
            job_run_id=job_run.id,
            event_type=JobRunEventType.STATUS_CHANGED,
            from_status=previous_status,
            to_status=JobRunStatus.QUEUED,
            message=reason,
            metadata_json={"source": "admin", "reset_attempts": True},
        )
    )
    db.flush()
    return job_run
