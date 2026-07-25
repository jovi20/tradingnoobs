from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from models import AuthRateLimitBucket


class RateLimitExceeded(Exception):
    def __init__(self, retry_after_seconds: int):
        super().__init__("Authentication rate limit exceeded")
        self.retry_after_seconds = max(1, retry_after_seconds)


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def _key_hash(value: str | None) -> str:
    normalized = (value or "<unknown>").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def consume_auth_attempt(
    db: Session,
    *,
    action: str,
    dimension: str,
    value: str | None,
    limit: int,
    window_seconds: int = 15 * 60,
    block_seconds: int = 15 * 60,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now(timezone.utc)
    bucket = (
        db.query(AuthRateLimitBucket)
        .filter(
            AuthRateLimitBucket.action == action,
            AuthRateLimitBucket.dimension == dimension,
            AuthRateLimitBucket.key_hash == _key_hash(value),
        )
        .with_for_update()
        .first()
    )
    if bucket is None:
        db.add(
            AuthRateLimitBucket(
                action=action,
                dimension=dimension,
                key_hash=_key_hash(value),
                window_started_at=current_time,
                attempt_count=1,
            )
        )
        db.flush()
        return

    if bucket.blocked_until is not None and _as_utc(bucket.blocked_until) > current_time:
        retry_after = int((_as_utc(bucket.blocked_until) - current_time).total_seconds())
        raise RateLimitExceeded(retry_after)

    window_started_at = _as_utc(bucket.window_started_at)
    if current_time - window_started_at >= timedelta(seconds=window_seconds):
        bucket.window_started_at = current_time
        bucket.attempt_count = 1
        bucket.blocked_until = None
    else:
        bucket.attempt_count += 1
        if bucket.attempt_count > limit:
            bucket.blocked_until = current_time + timedelta(seconds=block_seconds)
            db.add(bucket)
            db.commit()
            raise RateLimitExceeded(block_seconds)
    db.add(bucket)
    db.flush()


def check_auth_rate_limit(
    db: Session,
    *,
    action: str,
    dimension: str,
    value: str | None,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now(timezone.utc)
    bucket = db.query(AuthRateLimitBucket).filter(
        AuthRateLimitBucket.action == action,
        AuthRateLimitBucket.dimension == dimension,
        AuthRateLimitBucket.key_hash == _key_hash(value),
    ).first()
    if (
        bucket is not None
        and bucket.blocked_until is not None
        and _as_utc(bucket.blocked_until) > current_time
    ):
        retry_after = int(
            (_as_utc(bucket.blocked_until) - current_time).total_seconds()
        )
        raise RateLimitExceeded(retry_after)


def clear_auth_attempts(
    db: Session,
    *,
    action: str,
    dimension: str,
    value: str | None,
) -> None:
    db.query(AuthRateLimitBucket).filter(
        AuthRateLimitBucket.action == action,
        AuthRateLimitBucket.dimension == dimension,
        AuthRateLimitBucket.key_hash == _key_hash(value),
    ).delete(synchronize_session=False)
