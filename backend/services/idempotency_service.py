"""
Trading Noobs Backend - Idempotency Service
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json

from sqlalchemy.orm import Session

from models import IdempotencyKey


@dataclass(frozen=True)
class IdempotencyBeginResult:
    record: IdempotencyKey
    created: bool


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def request_hash(request_payload: dict | list | str | int | float | bool | None) -> str:
    canonical = json.dumps(request_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def begin_idempotent_request(
    db: Session,
    *,
    scope: str,
    key: str,
    request_payload: dict | list | str | int | float | bool | None,
    now: datetime | None = None,
    ttl_seconds: int | None = None,
    user_id: int | None = None,
) -> IdempotencyBeginResult:
    now = _as_utc(now or datetime.now(timezone.utc))
    hashed_request = request_hash(request_payload)
    existing = (
        db.query(IdempotencyKey)
        .filter(IdempotencyKey.scope == scope, IdempotencyKey.key == key)
        .first()
    )
    if existing:
        if existing.expires_at and _as_utc(existing.expires_at) <= now:
            existing.request_hash = hashed_request
            existing.status = "IN_PROGRESS"
            existing.response_json = None
            existing.job_run_id = None
            existing.user_id = user_id
            existing.expires_at = now + timedelta(seconds=ttl_seconds) if ttl_seconds else None
            db.add(existing)
            db.flush()
            return IdempotencyBeginResult(record=existing, created=True)
        if existing.request_hash != hashed_request:
            raise ValueError("Idempotency key reuse with a different request payload.")
        return IdempotencyBeginResult(record=existing, created=False)

    record = IdempotencyKey(
        user_id=user_id,
        scope=scope,
        key=key,
        request_hash=hashed_request,
        status="IN_PROGRESS",
        expires_at=now + timedelta(seconds=ttl_seconds) if ttl_seconds else None,
    )
    db.add(record)
    db.flush()
    return IdempotencyBeginResult(record=record, created=True)


def complete_idempotent_request(
    db: Session,
    *,
    record: IdempotencyKey,
    response_json: dict | list | str | int | float | bool | None,
    now: datetime | None = None,
) -> IdempotencyKey:
    _as_utc(now or datetime.now(timezone.utc))
    record.status = "COMPLETED"
    record.response_json = response_json
    db.add(record)
    db.flush()
    return record
