from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class MarketDataCapability(str, Enum):
    LATEST_QUOTE = "LATEST_QUOTE"
    DAILY_BAR = "DAILY_BAR"
    MARKET_CALENDAR = "MARKET_CALENDAR"


@dataclass(frozen=True)
class MarketProviderSpec:
    key: str
    priority: int
    markets: frozenset[str]
    capabilities: frozenset[MarketDataCapability]
    required_credentials: frozenset[str] = frozenset()
    enabled: bool = True

    def supports(self, *, market: str, capability: MarketDataCapability) -> bool:
        return self.enabled and market.upper() in self.markets and capability in self.capabilities

    def credentials_are_available(
        self,
        credential_availability: Mapping[str, bool] | None,
    ) -> bool:
        # None means the caller has no runtime credential context. This keeps
        # route inspection useful while execution paths provide an explicit map.
        if credential_availability is None:
            return True
        return all(credential_availability.get(key, False) for key in self.required_credentials)


class MarketProviderRegistry:
    def __init__(self, providers: tuple[MarketProviderSpec, ...]):
        keys = [provider.key for provider in providers]
        if len(keys) != len(set(keys)):
            raise ValueError("Market provider keys must be unique")
        self._providers = providers

    @property
    def providers(self) -> tuple[MarketProviderSpec, ...]:
        return self._providers

    def candidates(
        self,
        *,
        market: str,
        capability: MarketDataCapability,
        credential_availability: Mapping[str, bool] | None = None,
    ) -> tuple[MarketProviderSpec, ...]:
        eligible = (
            provider
            for provider in self._providers
            if provider.supports(market=market, capability=capability)
            and provider.credentials_are_available(credential_availability)
        )
        return tuple(sorted(eligible, key=lambda provider: (provider.priority, provider.key)))

    def provider_order(
        self,
        *,
        market: str,
        capability: MarketDataCapability,
        credential_availability: Mapping[str, bool] | None = None,
    ) -> tuple[str, ...]:
        return tuple(
            provider.key
            for provider in self.candidates(
                market=market,
                capability=capability,
                credential_availability=credential_availability,
            )
        )


DEFAULT_MARKET_PROVIDER_REGISTRY = MarketProviderRegistry(
    (
        MarketProviderSpec(
            key="finnhub",
            priority=10,
            markets=frozenset({"US"}),
            capabilities=frozenset(
                {
                    MarketDataCapability.LATEST_QUOTE,
                    MarketDataCapability.DAILY_BAR,
                    MarketDataCapability.MARKET_CALENDAR,
                }
            ),
            required_credentials=frozenset({"finnhub_api_key"}),
        ),
        MarketProviderSpec(
            key="yfinance",
            priority=20,
            markets=frozenset({"US"}),
            capabilities=frozenset(
                {
                    MarketDataCapability.LATEST_QUOTE,
                    MarketDataCapability.DAILY_BAR,
                }
            ),
        ),
        MarketProviderSpec(
            key="akshare",
            priority=10,
            markets=frozenset({"A_SHARE", "HK", "FOREX"}),
            capabilities=frozenset(
                {
                    MarketDataCapability.LATEST_QUOTE,
                    MarketDataCapability.DAILY_BAR,
                    MarketDataCapability.MARKET_CALENDAR,
                }
            ),
        ),
        MarketProviderSpec(
            key="binance",
            priority=10,
            markets=frozenset({"CRYPTO"}),
            capabilities=frozenset(
                {
                    MarketDataCapability.LATEST_QUOTE,
                    MarketDataCapability.DAILY_BAR,
                }
            ),
        ),
    )
)
