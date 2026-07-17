"""Effective-capability-aware Market access used by journal routes.

The real implementation is imported lazily only when the deployment ceiling
and database runtime rollout both enable Market.
"""
from __future__ import annotations

from typing import Any

from release_profile import RuntimeCapability
from services.capability_service import is_effective_capability_enabled


class MarketDataService:
    def __init__(self, db, *, actor_key: str | None = None, **kwargs):
        self.db = db
        self.actor_key = actor_key
        self.kwargs = kwargs
        self._delegate = None

    @property
    def is_available(self) -> bool:
        return is_effective_capability_enabled(
            self.db,
            RuntimeCapability.MARKET,
            actor_key=self.actor_key,
        )

    def _real_service(self):
        if not self.is_available:
            return None
        if self._delegate is None:
            from services.market_data_service import MarketDataService as RealMarketDataService

            self._delegate = RealMarketDataService(self.db, **self.kwargs)
        return self._delegate

    async def get_quote(self, symbol: str, *args, **kwargs) -> dict[str, Any]:
        service = self._real_service()
        if service is None:
            return {
                "symbol": symbol.upper(),
                "error": "FEATURE_DISABLED",
                "freshness": "UNAVAILABLE",
                "degraded": True,
                "degraded_reason": "MARKET capability is disabled",
                "source_refs": [],
            }
        return await service.get_quote(symbol, *args, **kwargs)

    async def get_or_create_asset_metadata(self, *args, **kwargs):
        service = self._real_service()
        if service is None:
            return None
        return await service.get_or_create_asset_metadata(*args, **kwargs)

    async def detect_asset_type_enhanced(self, *args, **kwargs):
        service = self._real_service()
        if service is None:
            return None
        return await service.detect_asset_type_enhanced(*args, **kwargs)

    async def get_price_history(self, *args, **kwargs) -> list[dict[str, Any]]:
        service = self._real_service()
        if service is None:
            return []
        return await service.get_price_history(*args, **kwargs)
