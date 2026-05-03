"""
Trading Noobs Backend - Transactional Outbox Service
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import (
    IdempotencyKey,
    JobDefinition,
    JobRun,
    JobRunEvent,
    JobRunEventType,
    JobRunStatus,
    OutboxEvent,
    OutboxEventStatus,
    PositionEvent,
    TradingPosition,
)


OUTBOX_JOB_DEFINITIONS = {
    "truth.position_event.created": {
        "key": "derived.timeline.refresh",
        "display_name": "Refresh Timeline Read Model",
        "description": "Refresh derived timeline/lifecycle read models after truth position events change.",
    },
}


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def enqueue_position_event_created_outbox(
    db: Session,
    *,
    position: TradingPosition,
    event: PositionEvent,
) -> OutboxEvent:
    dedupe_key = f"truth.position_event.created:{event.public_id}"
    existing = db.query(OutboxEvent).filter(OutboxEvent.dedupe_key == dedupe_key).first()
    if existing:
        return existing

    outbox_event = OutboxEvent(
        user_id=event.user_id,
        aggregate_type="TradingPosition",
        aggregate_public_id=position.public_id,
        event_type="truth.position_event.created",
        queue_name="derived",
        dedupe_key=dedupe_key,
        payload={
            "trading_position_public_id": position.public_id,
            "position_event_public_id": event.public_id,
            "position_event_type": event.event_type.value,
        },
    )
    db.add(outbox_event)
    db.flush()
    return outbox_event


def _get_or_create_job_definition(db: Session, *, event_type: str, queue_name: str) -> JobDefinition:
    config = OUTBOX_JOB_DEFINITIONS.get(
        event_type,
        {
            "key": f"outbox.{event_type}",
            "display_name": event_type,
            "description": "Generic outbox-dispatched job.",
        },
    )
    definition = db.query(JobDefinition).filter(JobDefinition.key == config["key"]).first()
    if definition:
        return definition

    definition = JobDefinition(
        key=config["key"],
        display_name=config["display_name"],
        description=config["description"],
        queue_name=queue_name,
        retry_policy={"max_attempts": 3, "backoff": "exponential"},
        timeout_seconds=300,
        is_active=True,
    )
    db.add(definition)
    db.flush()
    return definition


def relay_pending_outbox_events(
    db: Session,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> int:
    now = _as_utc(now or datetime.now(timezone.utc))
    pending_events = (
        db.query(OutboxEvent)
        .filter(OutboxEvent.status == OutboxEventStatus.PENDING)
        .order_by(OutboxEvent.available_at.asc().nullsfirst(), OutboxEvent.id.asc())
        .limit(limit)
        .all()
    )

    relayed_count = 0
    for outbox_event in pending_events:
        if outbox_event.available_at and _as_utc(outbox_event.available_at) > now:
            continue

        idempotency_key = outbox_event.dedupe_key or outbox_event.public_id
        existing_idempotency = (
            db.query(IdempotencyKey)
            .filter(
                IdempotencyKey.scope == "outbox_event",
                IdempotencyKey.key == idempotency_key,
            )
            .first()
        )
        if existing_idempotency and existing_idempotency.job_run_id:
            outbox_event.status = OutboxEventStatus.PUBLISHED
            outbox_event.published_at = now
            db.flush()
            relayed_count += 1
            continue

        definition = _get_or_create_job_definition(
            db,
            event_type=outbox_event.event_type,
            queue_name=outbox_event.queue_name,
        )
        job_run = JobRun(
            user_id=outbox_event.user_id,
            job_definition_id=definition.id,
            idempotency_key=idempotency_key,
            status=JobRunStatus.QUEUED,
            priority=0,
            payload={
                **(outbox_event.payload or {}),
                "outbox_event_public_id": outbox_event.public_id,
                "outbox_event_type": outbox_event.event_type,
                "aggregate_type": outbox_event.aggregate_type,
                "aggregate_public_id": outbox_event.aggregate_public_id,
            },
            max_attempts=(definition.retry_policy or {}).get("max_attempts", 1),
            queue_name=outbox_event.queue_name,
            next_run_at=now,
        )
        db.add(job_run)
        db.flush()

        db.add(
            JobRunEvent(
                job_run_id=job_run.id,
                event_type=JobRunEventType.STATUS_CHANGED,
                from_status=None,
                to_status=JobRunStatus.QUEUED,
                message=f"Queued from outbox event {outbox_event.public_id}",
                metadata_json={"source": "outbox", "outbox_event_public_id": outbox_event.public_id},
            )
        )
        db.add(
            IdempotencyKey(
                user_id=outbox_event.user_id,
                scope="outbox_event",
                key=idempotency_key,
                request_hash=outbox_event.public_id,
                status="COMPLETED",
                job_run_id=job_run.id,
            )
        )
        outbox_event.status = OutboxEventStatus.PUBLISHED
        outbox_event.published_at = now
        outbox_event.attempt_count = (outbox_event.attempt_count or 0) + 1
        db.flush()
        relayed_count += 1

    return relayed_count
