"""Market data handlers for the synchronous database-backed job worker."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, time, timezone
from typing import Any

from sqlalchemy.orm import Session

from models import JobRun
from services.market_data_service import MarketDataService


def _payload(job_run: JobRun) -> dict[str, Any]:
    payload = job_run.payload
    if payload is None:
        return {}
    if not isinstance(payload, dict):
        raise ValueError(f"{job_run.definition.key} requires an object payload")
    return payload


def _required_string(payload: dict[str, Any], key: str, *, job_key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{job_key} requires a non-empty {key}")
    return value.strip()


def _optional_string(payload: dict[str, Any], key: str, *, job_key: str) -> str | None:
    value = payload.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{job_key} requires {key} to be a non-empty string when provided")
    return value.strip()


def _parse_datetime(value: Any, *, field: str, job_key: str) -> datetime:
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
            raise ValueError(f"{job_key} requires {field} to be an ISO-8601 date or datetime") from exc
    else:
        raise ValueError(f"{job_key} requires {field} to be an ISO-8601 date or datetime")

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _run(coroutine):
    return asyncio.run(coroutine)


def refresh_market_quote(db: Session, job_run: JobRun) -> dict[str, Any]:
    job_key = "market.quote.refresh"
    payload = _payload(job_run)
    symbol = _required_string(payload, "symbol", job_key=job_key).upper()
    exchange = _optional_string(payload, "exchange", job_key=job_key)
    core_type = _optional_string(payload, "core_type", job_key=job_key)
    market = _optional_string(payload, "market", job_key=job_key)
    instrument = _optional_string(payload, "instrument", job_key=job_key)

    quote = _run(
        MarketDataService(db, persistence_db=db).get_quote(
            symbol,
            exchange=exchange,
            core_type=core_type,
            market=market,
            instrument=instrument,
        )
    )
    if not isinstance(quote, dict):
        raise RuntimeError(f"{job_key} returned an invalid quote for {symbol}")
    if quote.get("error"):
        raise RuntimeError(f"{job_key} failed for {symbol}: {quote['error']}")
    if quote.get("c") is None:
        raise RuntimeError(f"{job_key} returned no price for {symbol}")

    return {
        "handler": job_key,
        "symbol": symbol,
        "price": quote.get("c"),
        "previous_close": quote.get("pc"),
        "provider": quote.get("provider"),
        "freshness": quote.get("freshness", "UNKNOWN"),
        "degraded": bool(quote.get("degraded", False)),
        "source_refs": list(quote.get("source_refs") or []),
    }


def backfill_market_daily(db: Session, job_run: JobRun) -> dict[str, Any]:
    job_key = "market.daily_backfill"
    payload = _payload(job_run)
    symbol = _required_string(payload, "symbol", job_key=job_key).upper()
    exchange = _optional_string(payload, "exchange", job_key=job_key)
    start = _parse_datetime(payload.get("start"), field="start", job_key=job_key)
    end = _parse_datetime(payload.get("end"), field="end", job_key=job_key)
    if start >= end:
        raise ValueError(f"{job_key} requires start to be earlier than end")

    rows = _run(
        MarketDataService(db, persistence_db=db).get_price_history(
            symbol,
            start,
            end,
            exchange=exchange,
        )
    )
    if not isinstance(rows, list):
        raise RuntimeError(f"{job_key} returned an invalid history result for {symbol}")
    if not rows:
        raise RuntimeError(f"{job_key} returned no daily bars for {symbol}")

    first_bar = rows[0].get("date") if rows and isinstance(rows[0], dict) else None
    last_bar = rows[-1].get("date") if rows and isinstance(rows[-1], dict) else None
    return {
        "handler": job_key,
        "symbol": symbol,
        "timeframe": "1d",
        "start": start.isoformat(),
        "end": end.isoformat(),
        "rows_fetched": len(rows),
        "first_bar": first_bar,
        "last_bar": last_bar,
    }


def build_market_data_job_handlers(db: Session):
    return {
        "market.quote.refresh": lambda job_run: refresh_market_quote(db, job_run),
        "market.daily_backfill": lambda job_run: backfill_market_daily(db, job_run),
    }
