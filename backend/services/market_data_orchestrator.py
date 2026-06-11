from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from sqlalchemy.orm import Session

from observability import get_structured_logger, log_event
from services.market_data_types import MarketDataRequest, ProviderRoute
from services.platform_config_service import get_finnhub_api_key
from services.provider_router import detect_asset_route
from services.providers import akshare_provider, binance_provider, finnhub_provider


CACHE_TTL_SECONDS = 60
logger = get_structured_logger("market_data.orchestrator")
ProviderFetcher = Callable[[MarketDataRequest, ProviderRoute, Session | None], dict[str, Any]]
_QUOTE_CACHE: dict[str, dict[str, Any]] = {}


def clear_quote_cache() -> None:
    _QUOTE_CACHE.clear()


def _cache_key(request: MarketDataRequest, route: ProviderRoute) -> str:
    return "|".join(
        [
            route.normalized_symbol,
            request.exchange or "",
            request.core_type or "",
            request.market or "",
            request.instrument or "",
        ]
    )


def _cached_payload(key: str) -> dict[str, Any] | None:
    cached = _QUOTE_CACHE.get(key)
    if not cached:
        return None
    age = datetime.now(timezone.utc) - cached["timestamp"]
    if age.total_seconds() > CACHE_TTL_SECONDS:
        return None
    payload = dict(cached["payload"])
    payload["freshness"] = "CACHED"
    quote = payload.get("quote")
    if isinstance(quote, dict):
        payload["quote"] = dict(quote)
        payload["quote"]["freshness"] = "CACHED"
    return payload


def _store_cache(key: str, payload: dict[str, Any]) -> None:
    if payload.get("quote") is None or payload.get("error"):
        return
    _QUOTE_CACHE[key] = {
        "timestamp": datetime.now(timezone.utc),
        "payload": payload,
    }


def _source_refs(route: ProviderRoute, provider_result: dict[str, Any] | None = None) -> list[str]:
    refs = list(route.source_refs)
    for ref in (provider_result or {}).get("source_refs", []):
        if ref not in refs:
            refs.append(ref)
    return refs


def _legacy_quote(provider_result: dict[str, Any], *, degraded: bool, degraded_reason: str | None, source_refs: list[str]) -> dict[str, Any]:
    raw = provider_result.get("raw") or {}
    quote = {
        "c": provider_result.get("price", raw.get("c")),
        "pc": provider_result.get("previous_close", raw.get("pc")),
        "h": provider_result.get("high", raw.get("h")),
        "l": provider_result.get("low", raw.get("l")),
        "o": provider_result.get("open", raw.get("o")),
        "dp": provider_result.get("change_percent", raw.get("dp", raw.get("change_percent"))),
        "name": raw.get("name", provider_result.get("symbol")),
        "provider": provider_result.get("provider"),
        "freshness": provider_result.get("freshness", "FRESH"),
        "degraded": degraded,
        "degraded_reason": degraded_reason,
        "source_refs": source_refs,
    }
    if "volume" in raw:
        quote["volume"] = raw["volume"]
    return quote


def _result_payload(
    *,
    route: ProviderRoute,
    provider_result: dict[str, Any],
    degraded: bool,
    degraded_reason: str | None,
) -> dict[str, Any]:
    refs = _source_refs(route, provider_result)
    provider = provider_result.get("provider")
    quote = _legacy_quote(
        provider_result,
        degraded=degraded,
        degraded_reason=degraded_reason,
        source_refs=refs,
    )
    return {
        "symbol": route.normalized_symbol,
        "asset_type": route.asset_type,
        "market": route.market,
        "provider": provider,
        "freshness": provider_result.get("freshness", "FRESH"),
        "degraded": degraded,
        "degraded_reason": degraded_reason,
        "source_refs": refs,
        "quote": quote,
        "error": None,
    }


def _error_payload(route: ProviderRoute, failures: list[tuple[str, Exception]]) -> dict[str, Any]:
    refs = list(route.source_refs)
    for provider, _error in failures:
        provider_ref = f"provider:{provider}"
        if provider_ref not in refs:
            refs.append(provider_ref)
    failure_summary = "; ".join(f"{provider} failed: {error}" for provider, error in failures)
    return {
        "symbol": route.normalized_symbol,
        "asset_type": route.asset_type,
        "market": route.market,
        "provider": None,
        "freshness": "UNAVAILABLE",
        "degraded": True,
        "degraded_reason": failure_summary,
        "source_refs": refs,
        "quote": None,
        "error": "All market data providers failed",
    }


def _fetch_binance_quote(request: MarketDataRequest, route: ProviderRoute, db: Session | None) -> dict[str, Any]:
    del request, db
    return binance_provider.get_normalized_quote(route.normalized_symbol)


def _fetch_akshare_quote(request: MarketDataRequest, route: ProviderRoute, db: Session | None) -> dict[str, Any]:
    del request, db
    return akshare_provider.get_normalized_quote(route.normalized_symbol, route.market)


def _fetch_finnhub_quote(request: MarketDataRequest, route: ProviderRoute, db: Session | None) -> dict[str, Any]:
    del request
    api_key = get_finnhub_api_key(db) if db else None
    if not api_key:
        raise RuntimeError("Finnhub API key is not configured")
    import finnhub

    client = finnhub.Client(api_key=api_key)
    return finnhub_provider.get_quote(route.normalized_symbol, client)


def _fetch_yfinance_quote(request: MarketDataRequest, route: ProviderRoute, db: Session | None) -> dict[str, Any]:
    del request, db
    import yfinance as yf

    ticker = yf.Ticker(route.normalized_symbol)
    info = ticker.fast_info
    current_price = info.last_price
    previous_close = info.previous_close
    if not current_price:
        raise RuntimeError("YFinance returned empty quote")
    change_percent = ((current_price - previous_close) / previous_close) * 100 if previous_close else 0
    return {
        "symbol": route.normalized_symbol,
        "provider": "yfinance",
        "price": current_price,
        "previous_close": previous_close,
        "high": info.day_high,
        "low": info.day_low,
        "open": info.open,
        "change_percent": change_percent,
        "as_of": datetime.now(timezone.utc).isoformat(),
        "freshness": "FRESH",
        "degraded": False,
        "source_refs": ["provider:yfinance", f"symbol:{route.normalized_symbol}"],
        "raw": {},
    }


PROVIDER_FETCHERS: dict[str, ProviderFetcher] = {
    "akshare": _fetch_akshare_quote,
    "binance": _fetch_binance_quote,
    "finnhub": _fetch_finnhub_quote,
    "yfinance": _fetch_yfinance_quote,
}


def get_quote_with_metadata(request: MarketDataRequest, db: Session | None = None) -> dict[str, Any]:
    route = detect_asset_route(
        request.symbol,
        exchange=request.exchange,
        core_type=request.core_type,
        market=request.market,
        instrument=request.instrument,
    )
    key = _cache_key(request, route)
    cached = _cached_payload(key)
    if cached:
        return cached

    failures: list[tuple[str, Exception]] = []
    for provider in route.provider_order:
        fetcher = PROVIDER_FETCHERS.get(provider)
        if not fetcher:
            failures.append((provider, RuntimeError("provider fetcher not registered")))
            continue
        try:
            provider_result = fetcher(request, route, db)
            degraded = bool(failures) or bool(provider_result.get("degraded", False))
            degraded_reason = "; ".join(f"{name} failed: {error}" for name, error in failures) or provider_result.get("degraded_reason")
            payload = _result_payload(
                route=route,
                provider_result=provider_result,
                degraded=degraded,
                degraded_reason=degraded_reason,
            )
            if failures:
                log_event(
                    logger,
                    "warning",
                    "market_provider_fallback_succeeded",
                    symbol=route.normalized_symbol,
                    provider=provider,
                    failures=degraded_reason,
                )
            _store_cache(key, payload)
            return payload
        except Exception as error:
            failures.append((provider, error))
            log_event(
                logger,
                "warning",
                "market_provider_failed",
                symbol=route.normalized_symbol,
                provider=provider,
                error=str(error),
            )

    return _error_payload(route, failures)
