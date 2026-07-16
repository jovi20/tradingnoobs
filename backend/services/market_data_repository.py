"""Persistence helpers for the compact market-data store.

Repository methods flush changes but never commit. Callers retain ownership of the
surrounding transaction so quote writes, watermarks, and job state can be atomic.
"""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from sqlalchemy.orm import Session

from models import (
    AssetMaster,
    LatestMarketQuote,
    MarketDataWatermark,
    PriceBarDaily,
    ProviderSymbolMapping,
    TradeInstrument,
)


_UNSET = object()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _required_text(value: Any, field: str, *, uppercase: bool = False) -> str:
    normalized = str(value or "").strip()
    if not normalized:
        raise ValueError(f"{field} is required")
    return normalized.upper() if uppercase else normalized


def _provider_key(value: Any) -> str:
    return _required_text(value, "provider").lower()


def _json_capabilities(value: Any) -> Any:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return dict(value)
    if isinstance(value, str):
        return [value]
    if isinstance(value, (set, frozenset)):
        value = sorted(value, key=str)
    if isinstance(value, (tuple, list)):
        return [item.value if hasattr(item, "value") else item for item in value]
    return value


def _optional_decimal(value: Any, field: str) -> Decimal | None:
    if value is None or value == "":
        return None
    try:
        result = value if isinstance(value, Decimal) else Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} must be numeric") from exc
    if not result.is_finite():
        raise ValueError(f"{field} must be finite")
    return result


def _required_decimal(value: Any, field: str) -> Decimal:
    result = _optional_decimal(value, field)
    if result is None:
        raise ValueError(f"{field} is required")
    return result


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _coerce_datetime(value: Any, field: str) -> datetime:
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return _as_utc(value)
    if isinstance(value, (int, float, Decimal)):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    if isinstance(value, str):
        try:
            return _as_utc(datetime.fromisoformat(value.strip().replace("Z", "+00:00")))
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO datetime") from exc
    raise ValueError(f"{field} must be a datetime")


def _coerce_date(value: Any, field: str) -> date:
    if hasattr(value, "to_pydatetime"):
        value = value.to_pydatetime()
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value.strip()[:10])
        except ValueError as exc:
            raise ValueError(f"{field} must be an ISO date") from exc
    raise ValueError(f"{field} must be a date")


def _max_age_delta(
    *,
    max_age: timedelta | int | float | None,
    max_age_seconds: int | float | None,
) -> timedelta | None:
    if max_age is not None and max_age_seconds is not None:
        raise ValueError("provide max_age or max_age_seconds, not both")
    value = max_age_seconds if max_age_seconds is not None else max_age
    if value is None:
        return None
    delta = value if isinstance(value, timedelta) else timedelta(seconds=float(value))
    if delta.total_seconds() < 0:
        raise ValueError("max age cannot be negative")
    return delta


def _row_value(row: Mapping[str, Any] | Any, *keys: str, default: Any = _UNSET) -> Any:
    for key in keys:
        if isinstance(row, Mapping) and key in row:
            return row[key]
        if hasattr(row, key):
            return getattr(row, key)
    if default is not _UNSET:
        return default
    raise ValueError(f"daily bar is missing {keys[0]}")


class MarketDataRepository:
    def __init__(self, db: Session):
        self.db = db

    def _require_asset(self, asset_id: int) -> AssetMaster:
        asset = self.db.get(AssetMaster, asset_id)
        if asset is None:
            raise ValueError(f"asset {asset_id} does not exist")
        return asset

    def resolve_or_create_asset(
        self,
        *,
        symbol: str,
        market: str,
        asset_type: str,
        quote_currency: str | None = None,
        name: str | None = None,
    ) -> AssetMaster:
        normalized_symbol = _required_text(symbol, "symbol", uppercase=True)
        normalized_market = _required_text(market, "market", uppercase=True)
        normalized_type = _required_text(asset_type, "asset_type", uppercase=True)
        market_code = f"{normalized_market}:{normalized_symbol}"

        # Legacy truth records use the bare symbol. Reuse those before considering
        # the market-qualified code so persistence does not split one holding.
        asset = (
            self.db.query(AssetMaster)
            .filter(AssetMaster.canonical_code == normalized_symbol)
            .first()
        )
        if asset is None:
            asset = (
                self.db.query(AssetMaster)
                .filter(AssetMaster.canonical_code == market_code)
                .first()
            )
        if asset is None:
            display_candidates = (
                self.db.query(AssetMaster)
                .filter(AssetMaster.display_symbol == normalized_symbol)
                .order_by(AssetMaster.id)
                .all()
            )
            market_candidates = [
                candidate
                for candidate in display_candidates
                if (candidate.metadata_json or {}).get("market") == normalized_market
            ]
            if len(market_candidates) == 1:
                asset = market_candidates[0]
            elif (
                len(display_candidates) == 1
                and not (display_candidates[0].metadata_json or {}).get("market")
            ):
                asset = display_candidates[0]

        normalized_currency = (
            _required_text(quote_currency, "quote_currency", uppercase=True)
            if quote_currency is not None
            else None
        )
        if asset is not None:
            metadata = dict(asset.metadata_json or {})
            if not metadata.get("market"):
                metadata["market"] = normalized_market
                asset.metadata_json = metadata
            if not asset.quote_currency and normalized_currency:
                asset.quote_currency = normalized_currency
            self.db.flush()
            return asset

        asset = AssetMaster(
            canonical_code=market_code,
            display_symbol=normalized_symbol,
            name=(name or normalized_symbol).strip() or normalized_symbol,
            asset_type=normalized_type,
            quote_currency=normalized_currency,
            status="ACTIVE",
            metadata_json={"market": normalized_market},
        )
        self.db.add(asset)
        self.db.flush()
        return asset

    def get_provider_symbol_mapping(
        self,
        *,
        provider_key: str,
        asset_id: int | None = None,
        instrument_id: int | None = None,
        provider_market: str | None = None,
        provider_symbol: str | None = None,
    ) -> ProviderSymbolMapping | None:
        if asset_id is None and instrument_id is None and provider_symbol is None:
            raise ValueError("asset_id, instrument_id, or provider_symbol is required")

        query = self.db.query(ProviderSymbolMapping).filter(
            ProviderSymbolMapping.provider_key == _provider_key(provider_key)
        )
        if asset_id is not None:
            query = query.filter(ProviderSymbolMapping.asset_id == asset_id)
        if instrument_id is None and asset_id is not None:
            query = query.filter(ProviderSymbolMapping.instrument_id.is_(None))
        elif instrument_id is not None:
            query = query.filter(ProviderSymbolMapping.instrument_id == instrument_id)
        if provider_market is not None:
            query = query.filter(
                ProviderSymbolMapping.provider_market
                == _required_text(provider_market, "provider_market", uppercase=True)
            )
        if provider_symbol is not None:
            query = query.filter(
                ProviderSymbolMapping.provider_symbol
                == _required_text(provider_symbol, "provider_symbol")
            )
        return query.order_by(ProviderSymbolMapping.id).first()

    def upsert_provider_symbol_mapping(
        self,
        *,
        asset_id: int,
        provider_key: str,
        provider_symbol: str,
        provider_market: str,
        instrument_id: int | None = None,
        capabilities: Any = None,
        quality_status: str = "ACTIVE",
        verified_at: datetime | None = None,
    ) -> ProviderSymbolMapping:
        self._require_asset(asset_id)
        if instrument_id is not None:
            instrument = self.db.get(TradeInstrument, instrument_id)
            if instrument is None or instrument.asset_id != asset_id:
                raise ValueError("instrument_id must belong to asset_id")

        normalized_provider = _provider_key(provider_key)
        normalized_market = _required_text(provider_market, "provider_market", uppercase=True)
        normalized_symbol = _required_text(provider_symbol, "provider_symbol")
        mapping = self.get_provider_symbol_mapping(
            provider_key=normalized_provider,
            asset_id=asset_id,
            instrument_id=instrument_id,
            provider_market=normalized_market,
        )
        if mapping is None:
            mapping = ProviderSymbolMapping(
                asset_id=asset_id,
                instrument_id=instrument_id,
                provider_key=normalized_provider,
                provider_market=normalized_market,
                provider_symbol=normalized_symbol,
                capabilities_json=_json_capabilities(capabilities),
                quality_status=_required_text(quality_status, "quality_status", uppercase=True),
                last_verified_at=(
                    _coerce_datetime(verified_at, "verified_at")
                    if verified_at is not None
                    else _utc_now()
                ),
            )
            self.db.add(mapping)
        else:
            mapping.provider_symbol = normalized_symbol
            if capabilities is not None:
                normalized_capabilities = _json_capabilities(capabilities)
                if isinstance(mapping.capabilities_json, list) and isinstance(normalized_capabilities, list):
                    mapping.capabilities_json = sorted(
                        {str(item) for item in [*mapping.capabilities_json, *normalized_capabilities]}
                    )
                else:
                    mapping.capabilities_json = normalized_capabilities
            mapping.quality_status = _required_text(quality_status, "quality_status", uppercase=True)
            mapping.last_verified_at = (
                _coerce_datetime(verified_at, "verified_at")
                if verified_at is not None
                else _utc_now()
            )
        self.db.flush()
        return mapping

    def upsert_latest_quote(
        self,
        *,
        asset_id: int,
        provider: str,
        price: Any,
        previous_close: Any = None,
        open_price: Any = None,
        high_price: Any = None,
        low_price: Any = None,
        volume: Any = None,
        change_amount: Any = None,
        change_percent: Any = None,
        currency: str | None = None,
        market_time: datetime | int | float | str | None = None,
        received_at: datetime | int | float | str | None = None,
        quality_status: str = "GOOD",
        raw_payload: Any = None,
    ) -> LatestMarketQuote:
        self._require_asset(asset_id)
        normalized_provider = _provider_key(provider)
        normalized_received_at = (
            _coerce_datetime(received_at, "received_at")
            if received_at is not None
            else _utc_now()
        )
        quote = (
            self.db.query(LatestMarketQuote)
            .filter(
                LatestMarketQuote.asset_id == asset_id,
                LatestMarketQuote.provider == normalized_provider,
            )
            .first()
        )
        if quote is not None and _as_utc(quote.received_at) > normalized_received_at:
            return quote
        if quote is None:
            quote = LatestMarketQuote(asset_id=asset_id, provider=normalized_provider)
            self.db.add(quote)

        quote.price = _required_decimal(price, "price")
        quote.previous_close = _optional_decimal(previous_close, "previous_close")
        quote.open_price = _optional_decimal(open_price, "open_price")
        quote.high_price = _optional_decimal(high_price, "high_price")
        quote.low_price = _optional_decimal(low_price, "low_price")
        quote.volume = _optional_decimal(volume, "volume")
        quote.change_amount = _optional_decimal(change_amount, "change_amount")
        quote.change_percent = _optional_decimal(change_percent, "change_percent")
        quote.currency = (
            _required_text(currency, "currency", uppercase=True) if currency is not None else None
        )
        quote.market_time = (
            _coerce_datetime(market_time, "market_time") if market_time is not None else None
        )
        quote.received_at = normalized_received_at
        quote.quality_status = _required_text(quality_status, "quality_status", uppercase=True)
        quote.raw_payload = raw_payload
        self.db.flush()
        return quote

    def get_latest_quote(
        self,
        *,
        asset_id: int,
        provider: str | None = None,
        max_age: timedelta | int | float | None = None,
        max_age_seconds: int | float | None = None,
        now: datetime | None = None,
        quality_statuses: Sequence[str] | None = None,
    ) -> LatestMarketQuote | None:
        query = self.db.query(LatestMarketQuote).filter(LatestMarketQuote.asset_id == asset_id)
        if provider is not None:
            query = query.filter(LatestMarketQuote.provider == _provider_key(provider))
        age = _max_age_delta(max_age=max_age, max_age_seconds=max_age_seconds)
        if age is not None:
            current_time = _coerce_datetime(now, "now") if now is not None else _utc_now()
            query = query.filter(LatestMarketQuote.received_at >= current_time - age)
        if quality_statuses is not None:
            normalized_statuses = [
                _required_text(status, "quality_status", uppercase=True)
                for status in quality_statuses
            ]
            if not normalized_statuses:
                return None
            query = query.filter(LatestMarketQuote.quality_status.in_(normalized_statuses))
        return query.order_by(LatestMarketQuote.received_at.desc(), LatestMarketQuote.id.desc()).first()

    def get_fresh_latest_quote(
        self,
        *,
        asset_id: int,
        max_age: timedelta | int | float,
        provider: str | None = None,
        now: datetime | None = None,
        quality_statuses: Sequence[str] | None = None,
    ) -> LatestMarketQuote | None:
        return self.get_latest_quote(
            asset_id=asset_id,
            provider=provider,
            max_age=max_age,
            now=now,
            quality_statuses=quality_statuses,
        )

    def upsert_daily_bar(
        self,
        *,
        asset_id: int,
        provider: str,
        trading_date: date | datetime | str,
        open_price: Any,
        high_price: Any,
        low_price: Any,
        close_price: Any,
        adjusted_close: Any = None,
        volume: Any = None,
        adjustment_mode: str = "RAW",
        currency: str | None = None,
        received_at: datetime | int | float | str | None = None,
        quality_status: str = "GOOD",
        raw_payload: Any = None,
    ) -> PriceBarDaily:
        return self.upsert_daily_bars(
            asset_id=asset_id,
            provider=provider,
            adjustment_mode=adjustment_mode,
            currency=currency,
            received_at=received_at,
            quality_status=quality_status,
            bars=[
                {
                    "trading_date": trading_date,
                    "open_price": open_price,
                    "high_price": high_price,
                    "low_price": low_price,
                    "close_price": close_price,
                    "adjusted_close": adjusted_close,
                    "volume": volume,
                    "raw_payload": raw_payload,
                }
            ],
        )[0]

    def upsert_daily_bars(
        self,
        *,
        asset_id: int,
        provider: str,
        bars: Iterable[Mapping[str, Any] | Any],
        adjustment_mode: str = "RAW",
        currency: str | None = None,
        received_at: datetime | int | float | str | None = None,
        quality_status: str = "GOOD",
    ) -> list[PriceBarDaily]:
        self._require_asset(asset_id)
        normalized_provider = _provider_key(provider)
        default_adjustment = _required_text(
            adjustment_mode,
            "adjustment_mode",
            uppercase=True,
        )
        default_currency = (
            _required_text(currency, "currency", uppercase=True) if currency is not None else None
        )
        default_received = (
            _coerce_datetime(received_at, "received_at")
            if received_at is not None
            else _utc_now()
        )
        default_quality = _required_text(quality_status, "quality_status", uppercase=True)

        normalized_rows: list[dict[str, Any]] = []
        for row in bars:
            row_received = _row_value(row, "received_at", default=default_received)
            row_adjustment = _row_value(row, "adjustment_mode", default=default_adjustment)
            row_currency = _row_value(row, "currency", default=default_currency)
            row_quality = _row_value(row, "quality_status", default=default_quality)
            normalized_rows.append(
                {
                    "trading_date": _coerce_date(
                        _row_value(row, "trading_date", "date"),
                        "trading_date",
                    ),
                    "adjustment_mode": _required_text(
                        row_adjustment,
                        "adjustment_mode",
                        uppercase=True,
                    ),
                    "open_price": _required_decimal(
                        _row_value(row, "open_price", "open", "o"),
                        "open_price",
                    ),
                    "high_price": _required_decimal(
                        _row_value(row, "high_price", "high", "h"),
                        "high_price",
                    ),
                    "low_price": _required_decimal(
                        _row_value(row, "low_price", "low", "l"),
                        "low_price",
                    ),
                    "close_price": _required_decimal(
                        _row_value(row, "close_price", "close", "c"),
                        "close_price",
                    ),
                    "adjusted_close": _optional_decimal(
                        _row_value(row, "adjusted_close", "adj_close", default=None),
                        "adjusted_close",
                    ),
                    "volume": _optional_decimal(
                        _row_value(row, "volume", "v", default=None),
                        "volume",
                    ),
                    "currency": (
                        _required_text(row_currency, "currency", uppercase=True)
                        if row_currency is not None
                        else None
                    ),
                    "received_at": _coerce_datetime(row_received, "received_at"),
                    "quality_status": _required_text(
                        row_quality,
                        "quality_status",
                        uppercase=True,
                    ),
                    "raw_payload": _row_value(row, "raw_payload", default=None),
                }
            )
        if not normalized_rows:
            return []

        dates = {row["trading_date"] for row in normalized_rows}
        modes = {row["adjustment_mode"] for row in normalized_rows}
        existing_rows = (
            self.db.query(PriceBarDaily)
            .filter(
                PriceBarDaily.asset_id == asset_id,
                PriceBarDaily.provider == normalized_provider,
                PriceBarDaily.trading_date.in_(dates),
                PriceBarDaily.adjustment_mode.in_(modes),
            )
            .all()
        )
        by_key = {
            (row.trading_date, row.adjustment_mode): row
            for row in existing_rows
        }
        results: list[PriceBarDaily] = []
        for values in normalized_rows:
            key = (values["trading_date"], values["adjustment_mode"])
            stored = by_key.get(key)
            if stored is not None and _as_utc(stored.received_at) > values["received_at"]:
                results.append(stored)
                continue
            if stored is None:
                stored = PriceBarDaily(
                    asset_id=asset_id,
                    provider=normalized_provider,
                    trading_date=values["trading_date"],
                    adjustment_mode=values["adjustment_mode"],
                )
                self.db.add(stored)
                by_key[key] = stored
            for field, value in values.items():
                setattr(stored, field, value)
            results.append(stored)
        self.db.flush()
        return results

    def get_daily_bars(
        self,
        *,
        asset_id: int,
        start_date: date | datetime | str,
        end_date: date | datetime | str,
        provider: str | None = None,
        adjustment_mode: str | None = "RAW",
        max_age: timedelta | int | float | None = None,
        max_age_seconds: int | float | None = None,
        now: datetime | None = None,
        quality_statuses: Sequence[str] | None = None,
    ) -> list[PriceBarDaily]:
        normalized_start = _coerce_date(start_date, "start_date")
        normalized_end = _coerce_date(end_date, "end_date")
        if normalized_start > normalized_end:
            raise ValueError("start_date cannot be after end_date")
        query = self.db.query(PriceBarDaily).filter(
            PriceBarDaily.asset_id == asset_id,
            PriceBarDaily.trading_date >= normalized_start,
            PriceBarDaily.trading_date <= normalized_end,
        )
        if provider is not None:
            query = query.filter(PriceBarDaily.provider == _provider_key(provider))
        if adjustment_mode is not None:
            query = query.filter(
                PriceBarDaily.adjustment_mode
                == _required_text(adjustment_mode, "adjustment_mode", uppercase=True)
            )
        age = _max_age_delta(max_age=max_age, max_age_seconds=max_age_seconds)
        if age is not None:
            current_time = _coerce_datetime(now, "now") if now is not None else _utc_now()
            query = query.filter(PriceBarDaily.received_at >= current_time - age)
        if quality_statuses is not None:
            normalized_statuses = [
                _required_text(status, "quality_status", uppercase=True)
                for status in quality_statuses
            ]
            if not normalized_statuses:
                return []
            query = query.filter(PriceBarDaily.quality_status.in_(normalized_statuses))
        return query.order_by(
            PriceBarDaily.trading_date,
            PriceBarDaily.provider,
            PriceBarDaily.id,
        ).all()

    def get_daily_range(self, **kwargs: Any) -> list[PriceBarDaily]:
        return self.get_daily_bars(**kwargs)

    def get_fresh_daily_bars(
        self,
        *,
        asset_id: int,
        start_date: date | datetime | str,
        end_date: date | datetime | str,
        max_age: timedelta | int | float,
        provider: str | None = None,
        adjustment_mode: str | None = "RAW",
        now: datetime | None = None,
        quality_statuses: Sequence[str] | None = None,
    ) -> list[PriceBarDaily]:
        return self.get_daily_bars(
            asset_id=asset_id,
            start_date=start_date,
            end_date=end_date,
            provider=provider,
            adjustment_mode=adjustment_mode,
            max_age=max_age,
            now=now,
            quality_statuses=quality_statuses,
        )

    def upsert_watermark(
        self,
        *,
        asset_id: int,
        data_type: str,
        provider: str,
        covered_from: date | datetime | str | None = None,
        covered_to: date | datetime | str | None = None,
        last_success_at: datetime | int | float | str | None | object = _UNSET,
        last_error: str | None | object = _UNSET,
        merge_coverage: bool = True,
    ) -> MarketDataWatermark:
        self._require_asset(asset_id)
        normalized_type = _required_text(data_type, "data_type", uppercase=True)
        normalized_provider = _provider_key(provider)
        normalized_from = (
            _coerce_date(covered_from, "covered_from") if covered_from is not None else None
        )
        normalized_to = _coerce_date(covered_to, "covered_to") if covered_to is not None else None
        if normalized_from and normalized_to and normalized_from > normalized_to:
            raise ValueError("covered_from cannot be after covered_to")

        watermark = self.get_watermark(
            asset_id=asset_id,
            data_type=normalized_type,
            provider=normalized_provider,
        )
        if watermark is None:
            watermark = MarketDataWatermark(
                asset_id=asset_id,
                data_type=normalized_type,
                provider=normalized_provider,
            )
            self.db.add(watermark)

        if merge_coverage:
            if normalized_from is not None:
                watermark.covered_from = min(
                    value for value in (watermark.covered_from, normalized_from) if value is not None
                )
            if normalized_to is not None:
                watermark.covered_to = max(
                    value for value in (watermark.covered_to, normalized_to) if value is not None
                )
        else:
            watermark.covered_from = normalized_from
            watermark.covered_to = normalized_to

        has_successful_coverage = normalized_from is not None or normalized_to is not None
        if last_success_at is not _UNSET:
            watermark.last_success_at = (
                _coerce_datetime(last_success_at, "last_success_at")
                if last_success_at is not None
                else None
            )
        elif has_successful_coverage:
            watermark.last_success_at = _utc_now()

        if last_error is not _UNSET:
            watermark.last_error = str(last_error) if last_error is not None else None
        elif has_successful_coverage:
            watermark.last_error = None
        self.db.flush()
        return watermark

    def get_watermark(
        self,
        *,
        asset_id: int,
        data_type: str,
        provider: str,
    ) -> MarketDataWatermark | None:
        return (
            self.db.query(MarketDataWatermark)
            .filter(
                MarketDataWatermark.asset_id == asset_id,
                MarketDataWatermark.data_type
                == _required_text(data_type, "data_type", uppercase=True),
                MarketDataWatermark.provider == _provider_key(provider),
            )
            .first()
        )


def resolve_or_create_asset(db: Session, **kwargs: Any) -> AssetMaster:
    return MarketDataRepository(db).resolve_or_create_asset(**kwargs)


def get_provider_symbol_mapping(db: Session, **kwargs: Any) -> ProviderSymbolMapping | None:
    return MarketDataRepository(db).get_provider_symbol_mapping(**kwargs)


def upsert_provider_symbol_mapping(db: Session, **kwargs: Any) -> ProviderSymbolMapping:
    return MarketDataRepository(db).upsert_provider_symbol_mapping(**kwargs)


def upsert_latest_quote(db: Session, **kwargs: Any) -> LatestMarketQuote:
    return MarketDataRepository(db).upsert_latest_quote(**kwargs)


def get_latest_quote(db: Session, **kwargs: Any) -> LatestMarketQuote | None:
    return MarketDataRepository(db).get_latest_quote(**kwargs)


def get_fresh_latest_quote(db: Session, **kwargs: Any) -> LatestMarketQuote | None:
    return MarketDataRepository(db).get_fresh_latest_quote(**kwargs)


def upsert_daily_bar(db: Session, **kwargs: Any) -> PriceBarDaily:
    return MarketDataRepository(db).upsert_daily_bar(**kwargs)


def upsert_daily_bars(db: Session, **kwargs: Any) -> list[PriceBarDaily]:
    return MarketDataRepository(db).upsert_daily_bars(**kwargs)


def get_daily_bars(db: Session, **kwargs: Any) -> list[PriceBarDaily]:
    return MarketDataRepository(db).get_daily_bars(**kwargs)


def get_daily_range(db: Session, **kwargs: Any) -> list[PriceBarDaily]:
    return MarketDataRepository(db).get_daily_range(**kwargs)


def get_fresh_daily_bars(db: Session, **kwargs: Any) -> list[PriceBarDaily]:
    return MarketDataRepository(db).get_fresh_daily_bars(**kwargs)


def upsert_watermark(db: Session, **kwargs: Any) -> MarketDataWatermark:
    return MarketDataRepository(db).upsert_watermark(**kwargs)


def get_watermark(db: Session, **kwargs: Any) -> MarketDataWatermark | None:
    return MarketDataRepository(db).get_watermark(**kwargs)
