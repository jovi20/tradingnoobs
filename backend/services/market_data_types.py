from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping


@dataclass(frozen=True)
class MarketDataRequest:
    symbol: str
    exchange: str | None = None
    core_type: str | None = None
    market: str | None = None
    instrument: str | None = None


@dataclass(frozen=True)
class ProviderRoute:
    symbol: str
    normalized_symbol: str
    asset_type: str
    market: str
    provider_order: tuple[str, ...]
    source_refs: tuple[str, ...] = field(default_factory=tuple)
    reason: str = "symbol_rule"

    @property
    def primary_provider(self) -> str | None:
        return self.provider_order[0] if self.provider_order else None


@dataclass(frozen=True)
class MarketDataProviderResult:
    symbol: str
    provider: str
    price: float | None = None
    previous_close: float | None = None
    high: float | None = None
    low: float | None = None
    open: float | None = None
    change_percent: float | None = None
    as_of: str | None = None
    freshness: str = "UNKNOWN"
    degraded: bool = False
    source_refs: tuple[str, ...] = field(default_factory=tuple)
    raw: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class MarketDataProviderError:
    symbol: str
    provider: str
    message: str
    retryable: bool = True
    source_refs: tuple[str, ...] = field(default_factory=tuple)
