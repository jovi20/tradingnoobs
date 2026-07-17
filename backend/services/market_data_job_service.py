"""Create and deduplicate market-data jobs for the database-backed worker."""
from __future__ import annotations

from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy.orm import Session

from models import JobDefinition, JobRun, JobRunStatus
from release_profile import RuntimeCapability
from routers.disabled_capabilities import raise_feature_disabled
from services.capability_service import is_effective_capability_enabled


MARKET_QUEUE = "market"
ACTIVE_JOB_STATUSES = (
    JobRunStatus.QUEUED,
    JobRunStatus.RUNNING,
    JobRunStatus.RETRYING,
)


def _require_market_capability(db: Session) -> None:
    if not is_effective_capability_enabled(db, RuntimeCapability.MARKET):
        raise_feature_disabled(RuntimeCapability.MARKET.value)


def _ensure_definition(
    db: Session,
    *,
    key: str,
    display_name: str,
    description: str,
    timeout_seconds: int,
) -> JobDefinition:
    _require_market_capability(db)
    definition = db.query(JobDefinition).filter(JobDefinition.key == key).first()
    if definition is not None:
        return definition

    definition = JobDefinition(
        key=key,
        display_name=display_name,
        description=description,
        queue_name=MARKET_QUEUE,
        retry_policy={"max_attempts": 3, "backoff": "exponential"},
        timeout_seconds=timeout_seconds,
        is_active=True,
    )
    db.add(definition)
    db.flush()
    return definition


def ensure_quote_refresh(db: Session) -> JobDefinition:
    return _ensure_definition(
        db,
        key="market.quote.refresh",
        display_name="Refresh Market Quote",
        description="Fetch the latest normalized quote and trust metadata for a symbol.",
        timeout_seconds=60,
    )


def ensure_daily_backfill(db: Session) -> JobDefinition:
    return _ensure_definition(
        db,
        key="market.daily_backfill",
        display_name="Backfill Daily Market Data",
        description="Fetch daily market bars for a symbol and requested time range.",
        timeout_seconds=600,
    )


ensure_quote_refresh_job_definition = ensure_quote_refresh
ensure_daily_backfill_job_definition = ensure_daily_backfill


def _symbol(value: Any) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("symbol must be a non-empty string")
    return value.strip().upper()


def _optional_string(value: Any, *, field: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string when provided")
    return value.strip()


def _utc_datetime(value: Any, *, field: str) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, date):
        parsed = datetime.combine(value, time.min)
    elif isinstance(value, str) and value.strip():
        normalized = value.strip()
        if normalized.endswith("Z"):
            normalized = f"{normalized[:-1]}+00:00"
        try:
            parsed = datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO-8601 date or datetime") from exc
    else:
        raise ValueError(f"{field} must be an ISO-8601 date or datetime")

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _as_utc(value: datetime | None) -> datetime:
    value = value or datetime.now(timezone.utc)
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _active_job(db: Session, *, definition: JobDefinition, idempotency_key: str) -> JobRun | None:
    return (
        db.query(JobRun)
        .filter(
            JobRun.job_definition_id == definition.id,
            JobRun.idempotency_key == idempotency_key,
            JobRun.status.in_(ACTIVE_JOB_STATUSES),
        )
        .order_by(JobRun.created_at.desc(), JobRun.id.desc())
        .first()
    )


def _enqueue(
    db: Session,
    *,
    definition: JobDefinition,
    idempotency_key: str,
    payload: dict[str, Any],
    user_id: int | None,
    priority: int,
    now: datetime | None,
) -> JobRun:
    definition = (
        db.query(JobDefinition)
        .filter(JobDefinition.id == definition.id)
        .with_for_update()
        .one()
    )
    existing = _active_job(db, definition=definition, idempotency_key=idempotency_key)
    if existing is not None:
        return existing

    run = JobRun(
        user_id=user_id,
        job_definition_id=definition.id,
        idempotency_key=idempotency_key,
        status=JobRunStatus.QUEUED,
        priority=priority,
        payload=payload,
        max_attempts=int((definition.retry_policy or {}).get("max_attempts", 1)),
        queue_name=MARKET_QUEUE,
        next_run_at=_as_utc(now),
    )
    db.add(run)
    db.flush()
    return run


def enqueue_quote_refresh(
    db: Session,
    *,
    symbol: str,
    exchange: str | None = None,
    core_type: str | None = None,
    market: str | None = None,
    instrument: str | None = None,
    user_id: int | None = None,
    priority: int = 0,
    now: datetime | None = None,
) -> JobRun:
    _require_market_capability(db)
    normalized_symbol = _symbol(symbol)
    payload = {
        "symbol": normalized_symbol,
        "business_locks": [
            {
                "scope": "market.quote.refresh",
                "resource_key": normalized_symbol,
                "ttl_seconds": 60,
            }
        ],
    }
    for key, value in (
        ("exchange", _optional_string(exchange, field="exchange")),
        ("core_type", _optional_string(core_type, field="core_type")),
        ("market", _optional_string(market, field="market")),
        ("instrument", _optional_string(instrument, field="instrument")),
    ):
        if value is not None:
            payload[key] = value

    return _enqueue(
        db,
        definition=ensure_quote_refresh(db),
        idempotency_key=f"market.quote.refresh:{normalized_symbol}",
        payload=payload,
        user_id=user_id,
        priority=priority,
        now=now,
    )


def enqueue_daily_backfill(
    db: Session,
    *,
    symbol: str,
    start: date | datetime | str,
    end: date | datetime | str,
    exchange: str | None = None,
    user_id: int | None = None,
    priority: int = 0,
    now: datetime | None = None,
) -> JobRun:
    _require_market_capability(db)
    normalized_symbol = _symbol(symbol)
    normalized_start = _utc_datetime(start, field="start")
    normalized_end = _utc_datetime(end, field="end")
    if normalized_start >= normalized_end:
        raise ValueError("start must be earlier than end")

    start_value = normalized_start.isoformat()
    end_value = normalized_end.isoformat()
    range_key = f"{normalized_symbol}:1d:{start_value}:{end_value}"
    payload = {
        "symbol": normalized_symbol,
        "start": start_value,
        "end": end_value,
        "business_locks": [
            {
                "scope": "market.daily_backfill",
                "resource_key": range_key,
                "ttl_seconds": 600,
            }
        ],
    }
    normalized_exchange = _optional_string(exchange, field="exchange")
    if normalized_exchange is not None:
        payload["exchange"] = normalized_exchange

    return _enqueue(
        db,
        definition=ensure_daily_backfill(db),
        idempotency_key=f"market.daily_backfill:{range_key}",
        payload=payload,
        user_id=user_id,
        priority=priority,
        now=now,
    )
