import unittest

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

    def test_forex_pair_routes_to_fx_provider(self):
        route = detect_asset_route("USDCNY")

        self.assertEqual(route.market, "FOREX")
        self.assertEqual(route.asset_type, "FX")
        self.assertEqual(route.provider_order, ("akshare",))


if __name__ == "__main__":
    unittest.main()
