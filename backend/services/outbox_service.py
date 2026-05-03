"""
Trading Noobs Backend - Transactional Outbox Service
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from models import OutboxEvent, PositionEvent, TradingPosition


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
