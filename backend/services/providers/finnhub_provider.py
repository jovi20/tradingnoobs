from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _to_utc_timestamp(value: datetime) -> int:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return int(value.timestamp())


def get_quote(symbol: str, client: Any) -> dict[str, Any]:
    symbol_upper = symbol.upper()
    raw = client.quote(symbol_upper)
    if not raw or (raw.get("c") in (None, 0) and raw.get("pc") in (None, 0)):
        raise ValueError(f"Finnhub returned empty quote for {symbol_upper}")

    return {
        "symbol": symbol_upper,
        "provider": "finnhub",
        "price": raw.get("c"),
        "previous_close": raw.get("pc"),
        "high": raw.get("h"),
        "low": raw.get("l"),
        "open": raw.get("o"),
        "change_percent": raw.get("dp"),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "freshness": "FRESH",
        "degraded": False,
        "source_refs": ["provider:finnhub", f"symbol:{symbol_upper}"],
        "raw": raw,
    }


def get_history(symbol: str, start: datetime, end: datetime, client: Any) -> list[dict[str, Any]]:
    symbol_upper = symbol.upper()
    raw = client.stock_candles(
        symbol_upper,
        "D",
        _to_utc_timestamp(start),
        _to_utc_timestamp(end),
    )
    if not raw or raw.get("s") != "ok":
        return []

    timestamps = raw.get("t", [])
    rows: list[dict[str, Any]] = []
    for index, timestamp in enumerate(timestamps):
        rows.append(
            {
                "date": datetime.fromtimestamp(timestamp, tz=timezone.utc).strftime("%Y-%m-%d"),
                "open": raw.get("o", [])[index],
                "high": raw.get("h", [])[index],
                "low": raw.get("l", [])[index],
                "close": raw.get("c", [])[index],
                "volume": raw.get("v", [])[index],
            }
        )
    return rows
