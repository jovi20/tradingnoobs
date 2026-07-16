import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

from services.derived_refresh_handlers import build_default_job_handlers
from services.market_data_job_handlers import backfill_market_daily, refresh_market_quote


def _job_run(key: str, payload):
    return Mock(payload=payload, definition=Mock(key=key))


class MarketDataJobHandlerTests(unittest.TestCase):
    def setUp(self):
        self.db = Mock()

    def test_default_registry_includes_market_handlers(self):
        handlers = build_default_job_handlers(self.db)

        self.assertIn("derived.timeline.refresh", handlers)
        self.assertIn("market.quote.refresh", handlers)
        self.assertIn("market.daily_backfill", handlers)

    def test_quote_refresh_validates_payload_and_returns_summary(self):
        quote = {
            "c": 421.13,
            "pc": 418.90,
            "provider": "finnhub",
            "freshness": "FRESH",
            "degraded": False,
            "source_refs": ["provider:finnhub", "symbol:MSFT"],
        }
        with patch(
            "services.market_data_job_handlers.MarketDataService.get_quote",
            new=AsyncMock(return_value=quote),
        ) as get_quote:
            result = refresh_market_quote(
                self.db,
                _job_run(
                    "market.quote.refresh",
                    {"symbol": " msft ", "exchange": "NASDAQ", "market": "US"},
                ),
            )

        get_quote.assert_awaited_once_with(
            "MSFT",
            exchange="NASDAQ",
            core_type=None,
            market="US",
            instrument=None,
        )
        self.assertEqual(
            result,
            {
                "handler": "market.quote.refresh",
                "symbol": "MSFT",
                "price": 421.13,
                "previous_close": 418.90,
                "provider": "finnhub",
                "freshness": "FRESH",
                "degraded": False,
                "source_refs": ["provider:finnhub", "symbol:MSFT"],
            },
        )

    def test_quote_refresh_rejects_missing_symbol(self):
        with self.assertRaisesRegex(ValueError, "requires a non-empty symbol"):
            refresh_market_quote(self.db, _job_run("market.quote.refresh", {}))

    def test_quote_refresh_rejects_non_object_payload(self):
        with self.assertRaisesRegex(ValueError, "requires an object payload"):
            refresh_market_quote(self.db, _job_run("market.quote.refresh", []))

    def test_quote_refresh_turns_provider_error_into_job_failure(self):
        with patch(
            "services.market_data_job_handlers.MarketDataService.get_quote",
            new=AsyncMock(return_value={"error": "providers unavailable"}),
        ):
            with self.assertRaisesRegex(RuntimeError, "providers unavailable"):
                refresh_market_quote(
                    self.db,
                    _job_run("market.quote.refresh", {"symbol": "MSFT"}),
                )

    def test_daily_backfill_parses_range_and_returns_compact_summary(self):
        rows = [
            {"date": "2026-06-10", "close": 420.0},
            {"date": "2026-06-11", "close": 421.13},
        ]
        with patch(
            "services.market_data_job_handlers.MarketDataService.get_price_history",
            new=AsyncMock(return_value=rows),
        ) as get_history:
            result = backfill_market_daily(
                self.db,
                _job_run(
                    "market.daily_backfill",
                    {
                        "symbol": "msft",
                        "exchange": "NASDAQ",
                        "start": "2026-06-01",
                        "end": "2026-06-12T00:00:00Z",
                    },
                ),
            )

        get_history.assert_awaited_once_with(
            "MSFT",
            datetime(2026, 6, 1, tzinfo=timezone.utc),
            datetime(2026, 6, 12, tzinfo=timezone.utc),
            exchange="NASDAQ",
        )
        self.assertEqual(result["handler"], "market.daily_backfill")
        self.assertEqual(result["timeframe"], "1d")
        self.assertEqual(result["rows_fetched"], 2)
        self.assertEqual(result["first_bar"], "2026-06-10")
        self.assertEqual(result["last_bar"], "2026-06-11")
        self.assertNotIn("rows", result)

    def test_daily_backfill_rejects_invalid_range(self):
        with self.assertRaisesRegex(ValueError, "start to be earlier than end"):
            backfill_market_daily(
                self.db,
                _job_run(
                    "market.daily_backfill",
                    {"symbol": "MSFT", "start": "2026-06-12", "end": "2026-06-01"},
                ),
            )

    def test_daily_backfill_treats_empty_provider_result_as_retryable_failure(self):
        with patch(
            "services.market_data_job_handlers.MarketDataService.get_price_history",
            new=AsyncMock(return_value=[]),
        ):
            with self.assertRaisesRegex(RuntimeError, "returned no daily bars"):
                backfill_market_daily(
                    self.db,
                    _job_run(
                        "market.daily_backfill",
                        {
                            "symbol": "MSFT",
                            "start": "2026-06-01",
                            "end": "2026-06-12",
                        },
                    ),
                )


if __name__ == "__main__":
    unittest.main()
