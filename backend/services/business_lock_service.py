"""
Trading Noobs Backend - Business Lock Service
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import BusinessLock, BusinessLockStatus


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _is_active(lock: BusinessLock, now: datetime) -> bool:
    expires_at = _as_utc(lock.expires_at)
    return lock.status == BusinessLockStatus.ACTIVE and expires_at > now


def acquire_business_lock(
    db: Session,
    *,
    scope: str,
    resource_key: str,
    owner_id: str,
    ttl_seconds: int,
    now: datetime | None = None,
    owner_type: str = "job_run",
    metadata: dict | None = None,
) -> BusinessLock | None:
    now = _as_utc(now or datetime.now(timezone.utc))
    expires_at = now + timedelta(seconds=ttl_seconds)
    existing = (
        db.query(BusinessLock)
        .filter(BusinessLock.scope == scope, BusinessLock.resource_key == resource_key)
        .first()
    )

    if existing and _is_active(existing, now) and existing.owner_id != owner_id:
        return None

    lock = existing or BusinessLock(scope=scope, resource_key=resource_key, owner_id=owner_id)
    lock.owner_id = owner_id
    lock.owner_type = owner_type
    lock.status = BusinessLockStatus.ACTIVE
    lock.metadata_json = metadata or {}
    lock.acquired_at = now
    lock.expires_at = expires_at
    lock.released_at = None
    db.add(lock)
    db.flush()
    return lock


def release_business_lock(
    db: Session,
    *,
    business_lock: BusinessLock,
    owner_id: str,
    now: datetime | None = None,
) -> BusinessLock:
    now = _as_utc(now or datetime.now(timezone.utc))
    if business_lock.owner_id != owner_id:
        raise ValueError(f"Cannot release business lock owned by {business_lock.owner_id}")

    business_lock.status = BusinessLockStatus.RELEASED
    business_lock.released_at = now
    db.add(business_lock)
    db.flush()
    return business_lock
