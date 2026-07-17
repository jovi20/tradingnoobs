import asyncio
import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app_config.release_contract import ReleaseContractViolation
from database import Base
from models import FeatureFlag, LatestMarketQuote, MarketDataWatermark
from release_profile import (
    DeploymentCapabilityPolicy,
    RuntimeCapability,
    is_capability_enabled,
)
from services import exchange_rate_service
from services.capability_service import capability_rollout_flag_key
from services.market_data_access import MarketDataService


class OptionalServiceRuntimeGuardTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        exchange_rate_service._fx_cache.clear()
        self.ceiling_patch = patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            DeploymentCapabilityPolicy(frozenset({RuntimeCapability.MARKET})),
        )
        self.ceiling_patch.start()
        self.assertTrue(is_capability_enabled(RuntimeCapability.MARKET))

    def tearDown(self):
        self.ceiling_patch.stop()
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _set_market_flag(
        self,
        enabled: bool | None,
        *,
        actor_targets: list[str] | None = None,
        rollout_percentage: int | None = None,
    ) -> None:
        key = capability_rollout_flag_key(RuntimeCapability.MARKET)
        self.db.query(FeatureFlag).filter(FeatureFlag.key == key).delete()
        if enabled is not None:
            self.db.add(
                FeatureFlag(
                    key=key,
                    enabled=enabled,
                    actor_targets=actor_targets or [],
                    rollout_percentage=rollout_percentage,
                )
            )
        self.db.commit()

    def test_market_access_does_not_import_provider_when_runtime_flag_is_missing_or_disabled(self):
        original_import = __import__

        def guarded_import(name, *args, **kwargs):
            if name == "services.market_data_service":
                raise AssertionError("real Market service must not be imported")
            return original_import(name, *args, **kwargs)

        for enabled in (None, False):
            with self.subTest(enabled=enabled):
                self._set_market_flag(enabled)
                with patch("builtins.__import__", side_effect=guarded_import):
                    result = asyncio.run(MarketDataService(self.db).get_quote("AAPL"))
                self.assertEqual(result["error"], "FEATURE_DISABLED")
                self.assertEqual(result["freshness"], "UNAVAILABLE")

    def test_market_access_loads_provider_only_after_runtime_flag_is_enabled(self):
        self._set_market_flag(True)
        provider_result = {"symbol": "AAPL", "freshness": "FRESH"}

        with patch("services.market_data_service.MarketDataService") as real_service:
            real_service.return_value.get_quote = AsyncMock(return_value=provider_result)
            result = asyncio.run(MarketDataService(self.db).get_quote("AAPL"))

        self.assertEqual(result, provider_result)
        real_service.assert_called_once_with(self.db)
        real_service.return_value.get_quote.assert_awaited_once_with("AAPL")

    def test_actor_targeted_market_access_uses_the_same_actor_at_the_service_guard(self):
        self._set_market_flag(True, actor_targets=["selected-user"])
        provider_result = {"symbol": "AAPL", "freshness": "FRESH"}

        with patch("services.market_data_service.MarketDataService") as real_service:
            real_service.return_value.get_quote = AsyncMock(return_value=provider_result)
            selected = asyncio.run(
                MarketDataService(
                    self.db,
                    actor_key="selected-user",
                ).get_quote("AAPL")
            )
            rejected = asyncio.run(
                MarketDataService(
                    self.db,
                    actor_key="other-user",
                ).get_quote("AAPL")
            )

        self.assertEqual(selected, provider_result)
        self.assertEqual(rejected["error"], "FEATURE_DISABLED")
        real_service.assert_called_once_with(self.db)

    def test_actor_targeted_live_quote_persists_when_optional_warmup_is_not_globally_enabled(self):
        self._set_market_flag(True, actor_targets=["selected-user"])
        live_payload = {
            "symbol": "AAPL",
            "asset_type": "STOCK",
            "market": "US",
            "provider": "yfinance",
            "freshness": "FRESH",
            "degraded": False,
            "degraded_reason": None,
            "source_refs": ["provider:yfinance", "symbol:AAPL"],
            "quote": {
                "c": 210.0,
                "pc": 208.0,
                "name": "AAPL",
                "provider": "yfinance",
                "as_of": "2026-07-15T08:00:00+00:00",
                "freshness": "FRESH",
                "degraded": False,
                "source_refs": ["provider:yfinance", "symbol:AAPL"],
            },
            "error": None,
        }
        unavailable_payload = {
            **live_payload,
            "provider": None,
            "freshness": "UNAVAILABLE",
            "degraded": True,
            "degraded_reason": "provider offline",
            "quote": None,
            "error": "All market data providers failed",
        }

        service = MarketDataService(self.db, actor_key="selected-user")
        with patch(
            "services.market_data_service.get_quote_with_metadata",
            side_effect=(live_payload, unavailable_payload),
        ):
            live = asyncio.run(service.get_quote("AAPL", market="US"))
            fallback = asyncio.run(service.get_quote("AAPL", market="US"))

        self.assertEqual(live["c"], 210.0)
        self.assertEqual(fallback["c"], 210.0)
        self.assertEqual(fallback["freshness"], "STALE")
        self.assertTrue(fallback["degraded"])
        self.assertEqual(self.db.query(LatestMarketQuote).count(), 1)
        self.assertEqual(
            self.db.query(MarketDataWatermark)
            .filter(MarketDataWatermark.data_type == "LATEST_QUOTE")
            .count(),
            1,
        )

    def test_disabling_runtime_flag_blocks_an_already_loaded_market_delegate(self):
        self._set_market_flag(True)
        provider_result = {"symbol": "AAPL", "freshness": "FRESH"}

        with patch("services.market_data_service.MarketDataService") as real_service:
            real_service.return_value.get_quote = AsyncMock(return_value=provider_result)
            service = MarketDataService(self.db)
            self.assertEqual(asyncio.run(service.get_quote("AAPL")), provider_result)

            self._set_market_flag(False)
            disabled = asyncio.run(service.get_quote("AAPL"))

        self.assertEqual(disabled["error"], "FEATURE_DISABLED")
        real_service.return_value.get_quote.assert_awaited_once_with("AAPL")

    def test_exchange_rate_does_not_call_provider_without_effective_runtime_flag(self):
        for enabled in (None, False):
            with self.subTest(enabled=enabled):
                self._set_market_flag(enabled)
                with patch.object(
                    exchange_rate_service,
                    "_fetch_rate",
                    new=AsyncMock(side_effect=AssertionError("provider must not run")),
                ) as fetch_rate:
                    with self.assertRaises(exchange_rate_service.ExchangeRateUnavailableError):
                        asyncio.run(
                            exchange_rate_service.get_exchange_rate(
                                "USD",
                                "CNY",
                                db=self.db,
                            )
                        )
                fetch_rate.assert_not_awaited()

    def test_exchange_rate_rechecks_runtime_flag_before_using_a_warm_cache(self):
        exchange_rate_service._fx_cache["USD_CNY"] = {
            "rate": 7.25,
            "timestamp": exchange_rate_service.datetime.now(),
        }
        self._set_market_flag(False)

        with self.assertRaises(exchange_rate_service.ExchangeRateUnavailableError):
            asyncio.run(
                exchange_rate_service.get_exchange_rate(
                    "USD",
                    "CNY",
                    db=self.db,
                )
            )

    def test_actor_targeted_exchange_rate_uses_the_same_actor_at_the_cache_guard(self):
        exchange_rate_service._fx_cache["USD_CNY"] = {
            "rate": 7.25,
            "timestamp": exchange_rate_service.datetime.now(),
        }
        self._set_market_flag(True, actor_targets=["selected-user"])

        selected = asyncio.run(
            exchange_rate_service.get_exchange_rate(
                "USD",
                "CNY",
                db=self.db,
                actor_key="selected-user",
            )
        )
        self.assertEqual(selected, 7.25)
        with self.assertRaises(exchange_rate_service.ExchangeRateUnavailableError):
            asyncio.run(
                exchange_rate_service.get_exchange_rate(
                    "USD",
                    "CNY",
                    db=self.db,
                    actor_key="other-user",
                )
            )

    def test_exchange_rate_provider_failure_never_returns_or_caches_a_fabricated_rate(self):
        self._set_market_flag(True)

        with patch.object(
            exchange_rate_service,
            "run_in_threadpool",
            new=AsyncMock(
                side_effect=(
                    RuntimeError("provider one failed"),
                    RuntimeError("provider two failed"),
                )
            ),
        ):
            with self.assertRaises(exchange_rate_service.ExchangeRateUnavailableError):
                asyncio.run(
                    exchange_rate_service.get_exchange_rate(
                        "USDC",
                        "USD",
                        db=self.db,
                    )
                )

        self.assertNotIn("USDC_USD", exchange_rate_service._fx_cache)

    def test_usdt_is_never_aliased_to_usd_or_sent_to_provider(self):
        self._set_market_flag(True)
        with patch.object(
            exchange_rate_service,
            "_fetch_rate",
            new=AsyncMock(side_effect=AssertionError("provider must not run")),
        ) as fetch_rate:
            for pair in (("USDT", "USD"), ("USD", "USDT"), ("USDT", "USDT")):
                with self.subTest(pair=pair):
                    with self.assertRaises(ReleaseContractViolation) as raised:
                        asyncio.run(
                            exchange_rate_service.get_exchange_rate(
                                *pair,
                                db=self.db,
                            )
                        )
                    self.assertEqual(raised.exception.code, "UNSUPPORTED_RELEASE_CURRENCY")
        fetch_rate.assert_not_awaited()


if __name__ == "__main__":
    unittest.main()
