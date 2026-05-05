"""
Trading Noobs Backend - Derived Timeline Read Service
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from models import DerivedTimelineSnapshot


def list_recent_timeline_snapshots(
    db: Session,
    *,
    user_id: int,
    limit: int = 50,
) -> list[DerivedTimelineSnapshot]:
    return (
        db.query(DerivedTimelineSnapshot)
        .filter(DerivedTimelineSnapshot.user_id == user_id)
        .order_by(DerivedTimelineSnapshot.refreshed_at.desc(), DerivedTimelineSnapshot.id.desc())
        .limit(limit)
        .all()
    )
