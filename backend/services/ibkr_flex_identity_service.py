"""Shared IBKR Flex instrument identity normalization."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Iterable

from app_config.release_contract import (
    ReleaseContractViolation,
    require_allowed_asset_type,
    require_allowed_instrument_type,
    require_allowed_market,
    require_exchange_code,
    require_normalized_symbol,
)
from services.ibkr_flex_parser import NormalizedIbkrFlexEvent


ASSET_CATEGORY_IDENTITY = {
    "STK": ("STOCK", "US", "SPOT"),
    "ETF": ("FUND", "US", "SPOT"),
    "CRYPTO": ("CRYPTO", "CRYPTO", "SPOT"),
}


class IbkrFlexIdentityError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def derive_ibkr_instrument_identity(
    event: NormalizedIbkrFlexEvent,
) -> dict[str, str]:
    mapped = ASSET_CATEGORY_IDENTITY.get(event.asset_category)
    if mapped is None:
        raise IbkrFlexIdentityError(
            "UNSUPPORTED_ASSET_TYPE",
            f"Unsupported IBKR asset category: {event.asset_category}",
        )
    asset_type, market, instrument_type = mapped
    try:
        return {
            "asset_type": require_allowed_asset_type(asset_type),
            "market": require_allowed_market(market),
            "exchange_code": require_exchange_code(event.exchange),
            "normalized_symbol": require_normalized_symbol(event.symbol),
            "instrument_type": require_allowed_instrument_type(
                instrument_type
            ),
            "quote_currency": event.currency,
            "provider_conid": event.conid,
        }
    except ReleaseContractViolation as exc:
        raise IbkrFlexIdentityError(exc.code, str(exc)) from exc


def ibkr_group_key(
    identity: dict[str, str],
    direction: str,
) -> tuple[str, ...]:
    return (
        identity["asset_type"],
        identity["market"],
        identity["exchange_code"],
        identity["normalized_symbol"],
        identity["instrument_type"],
        identity["quote_currency"],
        direction,
    )


def ibkr_direction_from_source_fields(
    raw_side: str,
    raw_open_close: str,
) -> str:
    return (
        "LONG"
        if (raw_side, raw_open_close)
        in {("BUY", "OPEN"), ("SELL", "CLOSE")}
        else "SHORT"
    )


def ibkr_provisional_direction(event: NormalizedIbkrFlexEvent) -> str:
    return ibkr_direction_from_source_fields(
        event.raw_side,
        event.raw_open_close,
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def ibkr_ambiguous_order_keys(
    events: Iterable[NormalizedIbkrFlexEvent],
) -> frozenset[tuple[str, str]]:
    buckets: dict[
        tuple[tuple[str, ...], datetime, int],
        set[tuple[str, str]],
    ] = {}
    for event in events:
        identity = derive_ibkr_instrument_identity(event)
        group = ibkr_group_key(
            identity,
            ibkr_provisional_direction(event),
        )
        bucket = (
            group,
            _as_utc(event.occurred_at_utc),
            int(event.transaction_id),
        )
        buckets.setdefault(bucket, set()).add(
            (
                event.external_source_event_id,
                event.source_payload_fingerprint,
            )
        )

    # Distinct positive-quantity facts in one lifecycle cannot commute:
    # swapping them changes at least each fact's event-level pre/post quantity.
    return frozenset(
        economic_key
        for economic_keys in buckets.values()
        if len(economic_keys) > 1
        for economic_key in economic_keys
    )
