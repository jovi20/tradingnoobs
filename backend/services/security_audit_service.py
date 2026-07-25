from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models import SecurityAuditEvent
from services.redaction import sanitize_for_observability


def add_security_audit_event(
    db: Session,
    *,
    event_type: str,
    outcome: str,
    actor_user_id: int | None = None,
    subject_type: str | None = None,
    subject_public_id: str | None = None,
    ip_address: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> SecurityAuditEvent:
    event = SecurityAuditEvent(
        event_type=event_type,
        outcome=outcome,
        actor_user_id=actor_user_id,
        subject_type=subject_type,
        subject_public_id=subject_public_id,
        ip_address=ip_address,
        metadata_json=sanitize_for_observability(metadata or {}),
    )
    db.add(event)
    return event
