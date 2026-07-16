from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone
from typing import Any


def _number(value: Any) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def get_quote(symbol: str) -> dict[str, Any]:
    import yfinance as yf

    symbol_upper = symbol.upper()
    info = yf.Ticker(symbol_upper).fast_info
    current_price = _number(info.last_price)
    previous_close = _number(info.previous_close)
    if current_price is None:
        raise RuntimeError(f"YFinance returned empty quote for {symbol_upper}")

    change_percent = (
        ((current_price - previous_close) / previous_close) * 100
        if previous_close
        else 0.0
    )
    return {
        "symbol": symbol_upper,
        "provider": "yfinance",
        "price": current_price,
        "previous_close": previous_close,
        "high": _number(info.day_high),
        "low": _number(info.day_low),
        "open": _number(info.open),
        "change_percent": change_percent,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "freshness": "FRESH",
        "degraded": False,
        "source_refs": ["provider:yfinance", f"symbol:{symbol_upper}"],
        "raw": {},
    }


def get_history(symbol: str, start: datetime, end: datetime) -> list[dict[str, Any]]:
    import pandas as pd
    import yfinance as yf

    symbol_upper = symbol.upper()
    # yfinance treats end as exclusive. Include the requested final trading day.
    download_end = end + timedelta(days=1)
    history = yf.download(
        symbol_upper,
        start=start,
        end=download_end,
        progress=False,
        ignore_tz=True,
        auto_adjust=False,
        actions=False,
        threads=False,
    )
    if history.empty:
        return []

    if isinstance(history.columns, pd.MultiIndex):
        history.columns = history.columns.droplevel(1)

    rows: list[dict[str, Any]] = []
    for index, row in history.iterrows():
        rows.append(
            {
                "date": index.strftime("%Y-%m-%d"),
                "open": _number(row.get("Open")),
                "high": _number(row.get("High")),
                "low": _number(row.get("Low")),
                "close": _number(row.get("Close")),
                "volume": _number(row.get("Volume")),
            }
        )
    return rows
