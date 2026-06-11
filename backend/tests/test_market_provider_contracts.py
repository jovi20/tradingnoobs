import inspect
import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from services.providers import akshare_provider, binance_provider, finnhub_provider


class FakeFinnhubClient:
    def quote(self, symbol):
        self.quoted_symbol = symbol
        return {
            "c": 421.13,
            "pc": 418.90,
            "h": 424.00,
            "l": 417.10,
            "o": 419.00,
            "dp": 0.53,
        }

    def stock_candles(self, symbol, resolution, start, end):
        self.history_args = (symbol, resolution, start, end)
        return {
            "s": "ok",
            "t": [int(datetime(2026, 6, 10, tzinfo=timezone.utc).timestamp())],
            "o": [419.0],
            "h": [424.0],
            "l": [417.1],
            "c": [421.13],
            "v": [123456],
        }


class MarketProviderContractTests(unittest.TestCase):
    def test_finnhub_quote_returns_normalized_contract(self):
        client = FakeFinnhubClient()

        quote = finnhub_provider.get_quote("msft", client)

        self.assertEqual(quote["symbol"], "MSFT")
        self.assertEqual(quote["provider"], "finnhub")
        self.assertEqual(quote["price"], 421.13)
        self.assertEqual(quote["previous_close"], 418.90)
        self.assertEqual(quote["high"], 424.00)
        self.assertEqual(quote["low"], 417.10)
        self.assertEqual(quote["open"], 419.00)
        self.assertEqual(quote["change_percent"], 0.53)
        self.assertEqual(quote["freshness"], "FRESH")
        self.assertFalse(quote["degraded"])
        self.assertEqual(quote["source_refs"], ["provider:finnhub", "symbol:MSFT"])

    def test_finnhub_history_returns_normalized_rows(self):
        client = FakeFinnhubClient()

        rows = finnhub_provider.get_history("MSFT", datetime(2026, 6, 1), datetime(2026, 6, 11), client)

        self.assertEqual(
            rows,
            [
                {
                    "date": "2026-06-10",
                    "open": 419.0,
                    "high": 424.0,
                    "low": 417.1,
                    "close": 421.13,
                    "volume": 123456,
                }
            ],
        )

    def test_akshare_normalized_quote_wraps_a_share_provider(self):
        with patch(
            "services.providers.akshare_provider.get_a_stock_quote",
            return_value={"c": 100, "pc": 95, "h": 102, "l": 94, "o": 96, "change_percent": 5.26},
        ):
            quote = akshare_provider.get_normalized_quote("600519", market="A_SHARE")

        self.assertEqual(quote["symbol"], "600519")
        self.assertEqual(quote["provider"], "akshare")
        self.assertEqual(quote["price"], 100)
        self.assertEqual(quote["previous_close"], 95)
        self.assertEqual(quote["source_refs"], ["provider:akshare", "symbol:600519", "market:A_SHARE"])

    def test_binance_normalized_quote_wraps_crypto_provider(self):
        with patch(
            "services.providers.binance_provider.get_crypto_quote",
            return_value={"c": 68000, "pc": 67000, "h": 69000, "l": 66000, "o": 67100, "change_percent": 1.49},
        ):
            quote = binance_provider.get_normalized_quote("btcusdt")

        self.assertEqual(quote["symbol"], "BTCUSDT")
        self.assertEqual(quote["provider"], "binance")
        self.assertEqual(quote["price"], 68000)
        self.assertEqual(quote["previous_close"], 67000)
        self.assertEqual(quote["source_refs"], ["provider:binance", "symbol:BTCUSDT"])

    def test_binance_klines_uses_logger_instead_of_print(self):
        source = inspect.getsource(binance_provider.get_klines)

        self.assertNotIn("print(", source)


if __name__ == "__main__":
    unittest.main()
