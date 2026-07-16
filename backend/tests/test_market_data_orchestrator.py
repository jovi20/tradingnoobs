import unittest
from datetime import datetime
from unittest.mock import patch

from services.market_data_types import MarketDataRequest
from services.market_data_orchestrator import (
    clear_quote_cache,
    get_daily_bars_with_metadata,
    get_quote_with_metadata,
)
from services.market_provider_registry import (
    DEFAULT_MARKET_PROVIDER_REGISTRY,
    MarketDataCapability,
)
from services.provider_router import detect_asset_route


class MarketProviderRouterTests(unittest.TestCase):
    def test_crypto_symbol_routes_to_binance(self):
        route = detect_asset_route("BTCUSDT")

        self.assertEqual(route.market, "CRYPTO")
        self.assertEqual(route.asset_type, "CRYPTO")
        self.assertEqual(route.provider_order, ("binance",))
        self.assertEqual(route.normalized_symbol, "BTCUSDT")
        self.assertIn("market:CRYPTO", route.source_refs)

    def test_a_share_symbol_routes_to_akshare(self):
        route = detect_asset_route("600519")

        self.assertEqual(route.market, "A_SHARE")
        self.assertEqual(route.asset_type, "STOCK")
        self.assertEqual(route.provider_order, ("akshare",))
        self.assertIn("symbol:600519", route.source_refs)

    def test_hk_symbol_routes_to_akshare(self):
        route = detect_asset_route("0700.HK")

        self.assertEqual(route.market, "HK")
        self.assertEqual(route.asset_type, "STOCK")
        self.assertEqual(route.provider_order, ("akshare",))
        self.assertEqual(route.normalized_symbol, "0700.HK")

    def test_us_symbol_routes_to_finnhub_then_yfinance(self):
        route = detect_asset_route("MSFT")

        self.assertEqual(route.market, "US")
        self.assertEqual(route.asset_type, "STOCK")
        self.assertEqual(route.provider_order, ("finnhub", "yfinance"))
        self.assertIn("provider:finnhub", route.source_refs)
        self.assertIn("provider:yfinance", route.source_refs)

    def test_us_route_excludes_finnhub_when_credential_is_unavailable(self):
        route = detect_asset_route(
            "MSFT",
            credential_availability={"finnhub_api_key": False},
        )

        self.assertEqual(route.provider_order, ("yfinance",))
        self.assertNotIn("provider:finnhub", route.source_refs)
        self.assertIn("provider:yfinance", route.source_refs)

    def test_forex_pair_routes_to_fx_provider(self):
        route = detect_asset_route("USDCNY")

        self.assertEqual(route.market, "FOREX")
        self.assertEqual(route.asset_type, "FX")
        self.assertEqual(route.provider_order, ("akshare",))

    def test_registry_filters_by_capability_market_and_credentials(self):
        no_finnhub_key = {"finnhub_api_key": False}

        self.assertEqual(
            DEFAULT_MARKET_PROVIDER_REGISTRY.provider_order(
                market="US",
                capability=MarketDataCapability.LATEST_QUOTE,
                credential_availability=no_finnhub_key,
            ),
            ("yfinance",),
        )
        self.assertEqual(
            DEFAULT_MARKET_PROVIDER_REGISTRY.provider_order(
                market="US",
                capability=MarketDataCapability.MARKET_CALENDAR,
                credential_availability=no_finnhub_key,
            ),
            (),
        )
        self.assertEqual(
            DEFAULT_MARKET_PROVIDER_REGISTRY.provider_order(
                market="CRYPTO",
                capability=MarketDataCapability.LATEST_QUOTE,
                credential_availability=no_finnhub_key,
            ),
            ("binance",),
        )


class MarketDataOrchestratorTests(unittest.TestCase):
    def setUp(self):
        clear_quote_cache()

    def tearDown(self):
        clear_quote_cache()

    def test_primary_provider_success_returns_fresh_metadata(self):
        def fake_finnhub(request, route, db):
            return {
                "symbol": route.normalized_symbol,
                "provider": "finnhub",
                "price": 421.13,
                "previous_close": 418.90,
                "high": 424.00,
                "low": 417.10,
                "open": 419.00,
                "change_percent": 0.53,
                "freshness": "FRESH",
                "degraded": False,
                "source_refs": ["provider:finnhub", "symbol:MSFT"],
            }

        with (
            patch("services.market_data_orchestrator._resolve_finnhub_api_key", return_value="test-key"),
            patch.dict("services.market_data_orchestrator.PROVIDER_FETCHERS", {"finnhub": fake_finnhub}),
        ):
            result = get_quote_with_metadata(MarketDataRequest(symbol="MSFT"))

        self.assertEqual(result["provider"], "finnhub")
        self.assertEqual(result["freshness"], "FRESH")
        self.assertFalse(result["degraded"])
        self.assertEqual(result["quote"]["c"], 421.13)
        self.assertEqual(result["quote"]["pc"], 418.90)
        self.assertIn("provider:finnhub", result["source_refs"])

    def test_fallback_success_returns_degraded_metadata(self):
        def failing_finnhub(request, route, db):
            raise RuntimeError("finnhub down")

        def fake_yfinance(request, route, db):
            return {
                "symbol": route.normalized_symbol,
                "provider": "yfinance",
                "price": 420.00,
                "previous_close": 418.00,
                "freshness": "FRESH",
                "degraded": False,
                "source_refs": ["provider:yfinance", "symbol:MSFT"],
            }

        with (
            patch("services.market_data_orchestrator._resolve_finnhub_api_key", return_value="test-key"),
            patch.dict(
                "services.market_data_orchestrator.PROVIDER_FETCHERS",
                {"finnhub": failing_finnhub, "yfinance": fake_yfinance},
            ),
        ):
            result = get_quote_with_metadata(MarketDataRequest(symbol="MSFT"))

        self.assertEqual(result["provider"], "yfinance")
        self.assertEqual(result["freshness"], "FRESH")
        self.assertTrue(result["degraded"])
        self.assertIn("finnhub failed", result["degraded_reason"])
        self.assertEqual(result["quote"]["c"], 420.00)
        self.assertIn("provider:finnhub", result["source_refs"])
        self.assertIn("provider:yfinance", result["source_refs"])

    def test_unconfigured_finnhub_is_skipped_without_degradation(self):
        def unexpected_finnhub(request, route, db):
            raise AssertionError("ineligible provider should not be called")

        def fake_yfinance(request, route, db):
            return {
                "symbol": route.normalized_symbol,
                "provider": "yfinance",
                "price": 420.00,
                "previous_close": 418.00,
                "freshness": "FRESH",
                "degraded": False,
                "source_refs": ["provider:yfinance", "symbol:MSFT"],
            }

        with (
            patch("services.market_data_orchestrator._resolve_finnhub_api_key", return_value=None),
            patch.dict(
                "services.market_data_orchestrator.PROVIDER_FETCHERS",
                {"finnhub": unexpected_finnhub, "yfinance": fake_yfinance},
            ),
        ):
            result = get_quote_with_metadata(MarketDataRequest(symbol="MSFT"))

        self.assertEqual(result["provider"], "yfinance")
        self.assertFalse(result["degraded"])
        self.assertIsNone(result["degraded_reason"])
        self.assertNotIn("provider:finnhub", result["source_refs"])
        self.assertIn("provider:yfinance", result["source_refs"])

    def test_all_providers_fail_returns_stable_error_payload(self):
        def failing_provider(request, route, db):
            raise RuntimeError("offline")

        with (
            patch("services.market_data_orchestrator._resolve_finnhub_api_key", return_value="test-key"),
            patch.dict(
                "services.market_data_orchestrator.PROVIDER_FETCHERS",
                {"finnhub": failing_provider, "yfinance": failing_provider},
            ),
        ):
            result = get_quote_with_metadata(MarketDataRequest(symbol="MSFT"))

        self.assertIsNone(result["provider"])
        self.assertEqual(result["freshness"], "UNAVAILABLE")
        self.assertTrue(result["degraded"])
        self.assertIsNone(result["quote"])
        self.assertEqual(result["error"], "All market data providers failed")
        self.assertIn("provider:finnhub", result["source_refs"])
        self.assertIn("provider:yfinance", result["source_refs"])

    def test_daily_bars_skip_unconfigured_finnhub_without_degradation(self):
        def fake_yfinance(request, route, start, end, db):
            return {
                "provider": "yfinance",
                "adjustment_mode": "RAW",
                "rows": [
                    {
                        "date": "2026-07-15",
                        "open": 419.0,
                        "high": 424.0,
                        "low": 417.1,
                        "close": 421.13,
                        "volume": 123456,
                    }
                ],
            }

        with (
            patch("services.market_data_orchestrator._resolve_finnhub_api_key", return_value=None),
            patch.dict(
                "services.market_data_orchestrator.DAILY_BAR_FETCHERS",
                {"yfinance": fake_yfinance},
            ),
        ):
            result = get_daily_bars_with_metadata(
                MarketDataRequest(symbol="MSFT"),
                datetime(2026, 7, 1),
                datetime(2026, 7, 15),
            )

        self.assertEqual(result["provider"], "yfinance")
        self.assertFalse(result["degraded"])
        self.assertEqual(len(result["rows"]), 1)
        self.assertNotIn("provider:finnhub", result["source_refs"])

    def test_daily_bars_mark_real_provider_fallback_as_degraded(self):
        def failing_finnhub(request, route, start, end, db):
            raise RuntimeError("finnhub offline")

        def fake_yfinance(request, route, start, end, db):
            return {
                "provider": "yfinance",
                "adjustment_mode": "RAW",
                "rows": [{"date": "2026-07-15", "open": 1, "high": 2, "low": 1, "close": 2}],
            }

        with (
            patch("services.market_data_orchestrator._resolve_finnhub_api_key", return_value="key"),
            patch.dict(
                "services.market_data_orchestrator.DAILY_BAR_FETCHERS",
                {"finnhub": failing_finnhub, "yfinance": fake_yfinance},
            ),
        ):
            result = get_daily_bars_with_metadata(
                MarketDataRequest(symbol="MSFT"),
                datetime(2026, 7, 1),
                datetime(2026, 7, 15),
            )

        self.assertEqual(result["provider"], "yfinance")
        self.assertTrue(result["degraded"])
        self.assertIn("finnhub offline", result["degraded_reason"])


if __name__ == "__main__":
    unittest.main()
