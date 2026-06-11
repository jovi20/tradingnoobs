from __future__ import annotations

import re
from typing import Any

from services.market_data_types import ProviderRoute


_CRYPTO_SUFFIXES = ("USDT", "BUSD", "USDC", "BTC", "ETH", "BNB")
_KNOWN_FX_CODES = {
    "AUD",
    "CAD",
    "CHF",
    "CNY",
    "EUR",
    "GBP",
    "HKD",
    "JPY",
    "NZD",
    "SGD",
    "USD",
}


def _value(value: Any) -> str | None:
    if value is None:
        return None
    enum_value = getattr(value, "value", value)
    return str(enum_value).upper()


def _build_route(
    *,
    symbol: str,
    market: str,
    asset_type: str,
    provider_order: tuple[str, ...],
    normalized_symbol: str | None = None,
    reason: str,
) -> ProviderRoute:
    refs = [f"symbol:{symbol}"]
    if market != "UNKNOWN":
        refs.append(f"market:{market}")
    refs.extend(f"provider:{provider}" for provider in provider_order)
    return ProviderRoute(
        symbol=symbol,
        normalized_symbol=normalized_symbol or symbol,
        asset_type=asset_type,
        market=market,
        provider_order=provider_order,
        source_refs=tuple(refs),
        reason=reason,
    )


def _is_a_share(symbol: str) -> bool:
    return any(
        re.match(pattern, symbol)
        for pattern in (
            r"^0[0-3]\d{4}$",
            r"^300\d{3}$",
            r"^6[0-9]\d{4}$",
            r"^[48][37]\d{4}$",
        )
    )


def _is_cn_fund(symbol: str) -> bool:
    return any(
        re.match(pattern, symbol)
        for pattern in (
            r"^5[016]\d{4}$",
            r"^1[568]\d{4}$",
        )
    )


def _is_forex_pair(symbol: str) -> bool:
    if not re.match(r"^[A-Z]{6}$", symbol):
        return False
    return symbol[:3] in _KNOWN_FX_CODES and symbol[3:] in _KNOWN_FX_CODES


def detect_asset_route(
    symbol: str,
    exchange: str | None = None,
    core_type: str | None = None,
    market: str | None = None,
    instrument: str | None = None,
) -> ProviderRoute:
    """Return deterministic provider routing for market data requests."""
    del instrument
    symbol_upper = symbol.upper().strip()
    exchange_upper = _value(exchange) or ""
    core_type_upper = _value(core_type) or ""
    market_upper = _value(market) or ""

    if core_type_upper == "CRYPTO" or market_upper == "CRYPTO" or "BINANCE" in exchange_upper:
        return _build_route(
            symbol=symbol_upper,
            market="CRYPTO",
            asset_type="CRYPTO",
            provider_order=("binance",),
            reason="crypto_hint",
        )

    if market_upper == "A_SHARE":
        return _build_route(
            symbol=symbol_upper,
            market="A_SHARE",
            asset_type="FUND" if core_type_upper == "FUND" else "STOCK",
            provider_order=("akshare",),
            reason="market_hint",
        )

    if market_upper == "HK" or exchange_upper in {"HK", "HKEX", "HONG KONG"}:
        return _build_route(
            symbol=symbol_upper,
            market="HK",
            asset_type="STOCK",
            provider_order=("akshare",),
            reason="hk_hint",
        )

    if core_type_upper == "FX" or market_upper == "FOREX":
        return _build_route(
            symbol=symbol_upper,
            market="FOREX",
            asset_type="FX",
            provider_order=("akshare",),
            reason="forex_hint",
        )

    if symbol_upper.endswith(_CRYPTO_SUFFIXES):
        return _build_route(
            symbol=symbol_upper,
            market="CRYPTO",
            asset_type="CRYPTO",
            provider_order=("binance",),
            reason="crypto_symbol_suffix",
        )

    if _is_a_share(symbol_upper):
        return _build_route(
            symbol=symbol_upper,
            market="A_SHARE",
            asset_type="STOCK",
            provider_order=("akshare",),
            reason="a_share_symbol_rule",
        )

    if _is_cn_fund(symbol_upper) or core_type_upper == "FUND":
        return _build_route(
            symbol=symbol_upper,
            market="A_SHARE",
            asset_type="FUND",
            provider_order=("akshare",),
            reason="fund_symbol_rule",
        )

    if symbol_upper.endswith(".HK") or re.match(r"^\d{5}$", symbol_upper):
        return _build_route(
            symbol=symbol_upper,
            market="HK",
            asset_type="STOCK",
            provider_order=("akshare",),
            reason="hk_symbol_rule",
        )

    if _is_forex_pair(symbol_upper):
        return _build_route(
            symbol=symbol_upper,
            market="FOREX",
            asset_type="FX",
            provider_order=("akshare",),
            reason="forex_pair_rule",
        )

    if re.match(r"^[A-Z][A-Z.\-]{0,7}$", symbol_upper):
        return _build_route(
            symbol=symbol_upper,
            market="US",
            asset_type="STOCK",
            provider_order=("finnhub", "yfinance"),
            reason="us_symbol_rule",
        )

    return _build_route(
        symbol=symbol_upper,
        market="UNKNOWN",
        asset_type=core_type_upper or "UNKNOWN",
        provider_order=(),
        reason="unknown",
    )
