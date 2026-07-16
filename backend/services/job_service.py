"""
Trading Noobs Backend - Job Execution Service
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Callable

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import BusinessLock, BusinessLockStatus, JobRun, JobRunEvent, JobRunEventType, JobRunStatus
from services.business_lock_service import acquire_business_lock, release_business_lock

JobHandler = Callable[[JobRun], dict | None]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _claim_candidate_cas(
    db: Session,
    *,
    candidate: JobRun,
    queue_name: str,
    worker_id: str,
    now: datetime,
) -> tuple[int, JobRunStatus, int] | None:
    job_run_id = candidate.id
    previous_status = candidate.status
    previous_attempt_count = candidate.attempt_count or 0
    updated = (
        db.query(JobRun)
        .filter(
            JobRun.id == job_run_id,
            JobRun.status == previous_status,
            JobRun.attempt_count == previous_attempt_count,
            JobRun.queue_name == queue_name,
            or_(JobRun.next_run_at.is_(None), JobRun.next_run_at <= now),
        )
        .update(
            {
                JobRun.status: JobRunStatus.RUNNING,
                JobRun.locked_by: worker_id,
                JobRun.locked_at: now,
                JobRun.started_at: now,
                JobRun.next_run_at: None,
                JobRun.attempt_count: previous_attempt_count + 1,
            },
            synchronize_session=False,
        )
    )
    if updated != 1:
        db.expire_all()
        return None
    db.expire_all()
    return job_run_id, previous_status, previous_attempt_count


def claim_next_due_job(
    db: Session,
    *,
    queue_name: str,
    worker_id: str,
    now: datetime | None = None,
) -> JobRun | None:
    now = _as_utc(now or datetime.now(timezone.utc))
    candidate_query = (
        db.query(JobRun)
        .filter(
            JobRun.status.in_([JobRunStatus.QUEUED, JobRunStatus.RETRYING]),
            JobRun.queue_name == queue_name,
            or_(JobRun.next_run_at.is_(None), JobRun.next_run_at <= now),
        )
        .order_by(JobRun.priority.desc(), JobRun.created_at.asc(), JobRun.id.asc())
    )
    if db.get_bind().dialect.name == "postgresql":
        candidate_query = candidate_query.with_for_update(skip_locked=True)

    while True:
        candidate = candidate_query.first()
        if candidate is None:
            return None

        claimed = _claim_candidate_cas(
            db,
            candidate=candidate,
            queue_name=queue_name,
            worker_id=worker_id,
            now=now,
        )
        if claimed is not None:
            job_run_id, previous_status, previous_attempt_count = claimed
            job_run = db.get(JobRun, job_run_id)
            break

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
            message=f"Attempt {previous_attempt_count + 1} started.",
            metadata_json={"worker_id": worker_id, "attempt": previous_attempt_count + 1},
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


def heartbeat_job_run(
    db: Session,
    *,
    job_run: JobRun,
    worker_id: str,
    now: datetime | None = None,
) -> JobRun:
    now = _as_utc(now or datetime.now(timezone.utc))
    if job_run.status != JobRunStatus.RUNNING:
        raise ValueError(f"Cannot heartbeat job in status {job_run.status.value}")
    if job_run.locked_by != worker_id:
        raise ValueError(f"Cannot heartbeat job locked by {job_run.locked_by}")

    job_run.locked_at = now
    db.add(
        JobRunEvent(
            job_run_id=job_run.id,
            event_type=JobRunEventType.LOG,
            from_status=JobRunStatus.RUNNING,
            to_status=JobRunStatus.RUNNING,
            message=f"Heartbeat from worker {worker_id}",
            metadata_json={"worker_id": worker_id, "heartbeat_at": now.isoformat()},
        )
    )
    db.flush()
    return job_run


def recover_stale_running_jobs(
    db: Session,
    *,
    queue_name: str,
    stale_after_seconds: int,
    retry_delay_seconds: int = 60,
    now: datetime | None = None,
) -> int:
    now = _as_utc(now or datetime.now(timezone.utc))
    stale_before = now - timedelta(seconds=stale_after_seconds)
    stale_runs = (
        db.query(JobRun)
        .filter(
            JobRun.status == JobRunStatus.RUNNING,
            JobRun.queue_name == queue_name,
            JobRun.locked_at.is_not(None),
            JobRun.locked_at <= stale_before,
        )
        .order_by(JobRun.locked_at.asc(), JobRun.id.asc())
        .all()
    )

    for job_run in stale_runs:
        fail_job_run(
            db,
            job_run=job_run,
            error_message=f"Job lock timed out after {stale_after_seconds} seconds.",
            retry_delay_seconds=retry_delay_seconds,
            now=now,
        )
    return len(stale_runs)


def _business_lock_specs(job_run: JobRun) -> list[dict]:
    payload = job_run.payload or {}
    specs = payload.get("business_locks") or []
    if not isinstance(specs, list):
        return []
    return [spec for spec in specs if isinstance(spec, dict)]


def _acquire_job_business_locks(
    db: Session,
    *,
    job_run: JobRun,
    now: datetime,
) -> list:
    acquired_locks = []
    for spec in _business_lock_specs(job_run):
        scope = spec.get("scope")
        resource_key = spec.get("resource_key")
        if not scope or not resource_key:
            continue
        lock = acquire_business_lock(
            db,
            scope=scope,
            resource_key=resource_key,
            owner_id=job_run.public_id,
            ttl_seconds=int(spec.get("ttl_seconds") or job_run.definition.timeout_seconds or 300),
            now=now,
            owner_type="job_run",
            metadata={"job_run_public_id": job_run.public_id, **(spec.get("metadata") or {})},
        )
        if lock is None:
            for acquired_lock in acquired_locks:
                release_business_lock(db, business_lock=acquired_lock, owner_id=job_run.public_id, now=now)
            raise RuntimeError(f"Business lock unavailable: {scope}:{resource_key}")
        acquired_locks.append(lock)
    return acquired_locks


def _release_job_business_locks(
    db: Session,
    *,
    job_run: JobRun,
    business_locks: list,
    now: datetime,
) -> None:
    for business_lock in business_locks:
        release_business_lock(db, business_lock=business_lock, owner_id=job_run.public_id, now=now)


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

    business_locks = []
    try:
        business_locks = _acquire_job_business_locks(db, job_run=job_run, now=now)
    except RuntimeError as exc:
        return fail_job_run(
            db,
            job_run=job_run,
            error_message=str(exc),
            retry_delay_seconds=retry_delay_seconds,
            now=now,
        )

    handler = handlers.get(job_run.definition.key)
    if handler is None:
        failed = fail_job_run(
            db,
            job_run=job_run,
            error_message=f"No handler registered for job definition {job_run.definition.key}",
            retry_delay_seconds=retry_delay_seconds,
            now=now,
        )
        _release_job_business_locks(db, job_run=job_run, business_locks=business_locks, now=now)
        return failed

    try:
        # A SAVEPOINT keeps a handler flush failure from poisoning the outer
        # transaction that owns claim state, attempt events, and business locks.
        with db.begin_nested():
            result = handler(job_run)
    except Exception as exc:
        failed = fail_job_run(
            db,
            job_run=job_run,
            error_message=str(exc),
            retry_delay_seconds=retry_delay_seconds,
            now=now,
        )
        _release_job_business_locks(db, job_run=job_run, business_locks=business_locks, now=now)
        return failed

    completed = complete_job_run(db, job_run=job_run, result=result or {}, now=now)
    _release_job_business_locks(db, job_run=job_run, business_locks=business_locks, now=now)
    return completed


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


def cancel_job_run(
    db: Session,
    *,
    job_run: JobRun,
    reason: str = "Cancelled by admin.",
    now: datetime | None = None,
) -> JobRun:
    now = _as_utc(now or datetime.now(timezone.utc))
    if job_run.status not in [JobRunStatus.QUEUED, JobRunStatus.RETRYING]:
        raise ValueError(f"Cannot cancel job in status {job_run.status.value}")

    previous_status = job_run.status
    job_run.status = JobRunStatus.CANCELLED
    job_run.error_message = reason
    job_run.locked_by = None
    job_run.locked_at = None
    job_run.next_run_at = None
    job_run.finished_at = now
    db.add(
        JobRunEvent(
            job_run_id=job_run.id,
            event_type=JobRunEventType.CANCELLED,
            from_status=previous_status,
            to_status=JobRunStatus.CANCELLED,
            message=reason,
            metadata_json={"source": "admin"},
        )
    )
    db.flush()
    return job_run


def force_cancel_running_job_run(
    db: Session,
    *,
    job_run: JobRun,
    reason: str = "Force-cancelled by admin.",
    now: datetime | None = None,
) -> JobRun:
    now = _as_utc(now or datetime.now(timezone.utc))
    if job_run.status != JobRunStatus.RUNNING:
        raise ValueError(f"Cannot force-cancel job in status {job_run.status.value}")

    previous_status = job_run.status
    active_locks = (
        db.query(BusinessLock)
        .filter(
            BusinessLock.owner_id == job_run.public_id,
            BusinessLock.owner_type == "job_run",
            BusinessLock.status == BusinessLockStatus.ACTIVE,
        )
        .all()
    )
    for business_lock in active_locks:
        release_business_lock(db, business_lock=business_lock, owner_id=job_run.public_id, now=now)

    job_run.status = JobRunStatus.CANCELLED
    job_run.error_message = reason
    job_run.locked_by = None
    job_run.locked_at = None
    job_run.next_run_at = None
    job_run.finished_at = now
    db.add(
        JobRunEvent(
            job_run_id=job_run.id,
            event_type=JobRunEventType.CANCELLED,
            from_status=previous_status,
            to_status=JobRunStatus.CANCELLED,
            message=reason,
            metadata_json={
                "source": "admin",
                "force": True,
                "warning": "Force-cancel releases active business locks owned by this job and may leave partial work behind.",
                "released_business_locks": [lock.public_id for lock in active_locks],
            },
        )
    )
    db.flush()
    return job_run
