import asyncio
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    AssetCoreType,
    AssetCurrency,
    AssetMarket,
    AssetMetadata,
    FeatureFlag,
    JobRun,
    JobRunStatus,
    LatestMarketQuote,
    MarketDataWatermark,
    PriceBarDaily,
    ProviderSymbolMapping,
)
from release_profile import RuntimeCapability
from services.capability_service import capability_rollout_flag_key
from services.derived_refresh_handlers import build_default_job_handlers
from services.job_service import run_next_due_job
from services.market_data_job_service import enqueue_quote_refresh
from services.market_data_repository import MarketDataRepository
from services.market_data_service import MarketDataService


class MarketDataPersistenceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = self.SessionLocal()
        self.db.add(
            FeatureFlag(
                key=capability_rollout_flag_key(RuntimeCapability.MARKET),
                enabled=True,
            )
        )
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def test_quote_is_persisted_and_stale_storage_fallback_is_returned(self):
        live_payload = {
            "symbol": "MSFT",
            "asset_type": "STOCK",
            "market": "US",
            "provider": "yfinance",
            "freshness": "FRESH",
            "degraded": False,
            "degraded_reason": None,
            "source_refs": ["provider:yfinance", "symbol:MSFT"],
            "quote": {
                "c": 421.13,
                "pc": 418.90,
                "h": 424.0,
                "l": 417.1,
                "o": 419.0,
                "dp": 0.53,
                "name": "MSFT",
                "provider": "yfinance",
                "as_of": "2026-07-15T08:00:00+00:00",
                "freshness": "FRESH",
                "degraded": False,
                "source_refs": ["provider:yfinance", "symbol:MSFT"],
            },
            "error": None,
        }
        service = MarketDataService(self.db, persistence_db=self.db)
        with patch(
            "services.market_data_service.get_quote_with_metadata",
            return_value=live_payload,
        ):
            quote = asyncio.run(service.get_quote("MSFT", market="US"))

        self.assertEqual(quote["c"], 421.13)
        self.assertEqual(self.db.query(LatestMarketQuote).count(), 1)
        self.assertEqual(self.db.query(ProviderSymbolMapping).count(), 1)
        self.assertEqual(
            self.db.query(MarketDataWatermark)
            .filter(MarketDataWatermark.data_type == "LATEST_QUOTE")
            .count(),
            1,
        )
        self.assertEqual(self.db.query(JobRun).count(), 1)

        with patch(
            "services.market_data_service.get_quote_with_metadata",
            return_value=live_payload,
        ):
            asyncio.run(service.get_quote("MSFT", market="US"))
        self.assertEqual(
            self.db.query(JobRun)
            .filter(JobRun.idempotency_key.like("market.daily_backfill:MSFT:%"))
            .count(),
            1,
        )

        unavailable_payload = {
            "symbol": "MSFT",
            "asset_type": "STOCK",
            "market": "US",
            "provider": None,
            "freshness": "UNAVAILABLE",
            "degraded": True,
            "degraded_reason": "yfinance failed: offline",
            "source_refs": ["provider:yfinance", "symbol:MSFT"],
            "quote": None,
            "error": "All market data providers failed",
        }
        with patch(
            "services.market_data_service.get_quote_with_metadata",
            return_value=unavailable_payload,
        ):
            fallback = asyncio.run(service.get_quote("MSFT", market="US"))

        self.assertEqual(fallback["c"], 421.13)
        self.assertEqual(fallback["provider"], "yfinance")
        self.assertEqual(fallback["freshness"], "STALE")
        self.assertTrue(fallback["degraded"])
        self.assertIn("storage:latest_market_quotes", fallback["source_refs"])

    def test_quote_warmup_reuses_sufficient_daily_coverage_from_another_provider(self):
        now = datetime.now(timezone.utc)
        repository = MarketDataRepository(self.db)
        asset = repository.resolve_or_create_asset(
            symbol="MSFT",
            market="US",
            asset_type="STOCK",
            quote_currency="USD",
            name="Microsoft",
        )
        repository.upsert_watermark(
            asset_id=asset.id,
            data_type="DAILY_BAR",
            provider="yfinance",
            covered_from=(now - timedelta(days=366)).date(),
            covered_to=now.date(),
            last_success_at=now,
        )

        finnhub_quote = {
            "symbol": "MSFT",
            "asset_type": "STOCK",
            "market": "US",
            "provider": "finnhub",
            "freshness": "FRESH",
            "degraded": False,
            "degraded_reason": None,
            "source_refs": ["provider:finnhub", "symbol:MSFT"],
            "quote": {
                "c": 421.13,
                "pc": 418.90,
                "name": "MSFT",
                "provider": "finnhub",
                "as_of": now.isoformat(),
                "freshness": "FRESH",
                "degraded": False,
                "source_refs": ["provider:finnhub", "symbol:MSFT"],
            },
            "error": None,
        }
        service = MarketDataService(self.db, persistence_db=self.db)
        with patch(
            "services.market_data_service.get_quote_with_metadata",
            return_value=finnhub_quote,
        ):
            quote = asyncio.run(service.get_quote("MSFT", market="US"))

        self.assertEqual(quote["provider"], "finnhub")
        self.assertEqual(self.db.query(LatestMarketQuote).count(), 1)
        self.assertEqual(
            self.db.query(MarketDataWatermark)
            .filter(MarketDataWatermark.data_type == "DAILY_BAR")
            .one()
            .provider,
            "yfinance",
        )
        self.assertEqual(
            self.db.query(JobRun)
            .filter(JobRun.idempotency_key.like("market.daily_backfill:MSFT:%"))
            .count(),
            0,
        )

    def test_daily_bars_are_persisted_and_reused_from_coverage(self):
        start = datetime(2026, 7, 13, tzinfo=timezone.utc)
        end = datetime(2026, 7, 15, tzinfo=timezone.utc)
        daily_payload = {
            "symbol": "MSFT",
            "asset_type": "STOCK",
            "market": "US",
            "provider": "yfinance",
            "adjustment_mode": "RAW",
            "degraded": False,
            "degraded_reason": None,
            "source_refs": ["provider:yfinance", "symbol:MSFT", "timeframe:1d"],
            "rows": [
                {
                    "date": "2026-07-13",
                    "open": 418.0,
                    "high": 422.0,
                    "low": 417.0,
                    "close": 421.0,
                    "volume": 1000,
                },
                {
                    "date": "2026-07-14",
                    "open": 420.0,
                    "high": 422.5,
                    "low": 419.0,
                    "close": 421.5,
                    "volume": 1100,
                },
                {
                    "date": "2026-07-15",
                    "open": 421.0,
                    "high": 423.0,
                    "low": 420.0,
                    "close": 422.0,
                    "volume": 1200,
                },
            ],
            "error": None,
        }
        service = MarketDataService(self.db, persistence_db=self.db)
        with patch(
            "services.market_data_service.get_daily_bars_with_metadata",
            return_value=daily_payload,
        ) as fetch_daily:
            first = asyncio.run(service.get_price_history("MSFT", start, end))

        self.assertEqual(len(first), 3)
        self.assertEqual(fetch_daily.call_count, 1)
        self.assertEqual(self.db.query(PriceBarDaily).count(), 3)
        watermark = (
            self.db.query(MarketDataWatermark)
            .filter(MarketDataWatermark.data_type == "DAILY_BAR")
            .one()
        )
        self.assertEqual(watermark.covered_from.isoformat(), "2026-07-13")
        self.assertEqual(watermark.covered_to.isoformat(), "2026-07-15")

        with patch(
            "services.market_data_service.get_daily_bars_with_metadata",
            side_effect=AssertionError("covered data should not be fetched again"),
        ):
            second = asyncio.run(service.get_price_history("MSFT", start, end))

        self.assertEqual(
            [row["date"] for row in second],
            ["2026-07-13", "2026-07-14", "2026-07-15"],
        )

    def test_daily_cache_gap_forces_provider_refetch(self):
        start = datetime(2026, 7, 13, tzinfo=timezone.utc)
        end = datetime(2026, 7, 15, tzinfo=timezone.utc)
        base_payload = {
            "symbol": "MSFT",
            "asset_type": "STOCK",
            "market": "US",
            "provider": "yfinance",
            "adjustment_mode": "RAW",
            "degraded": False,
            "degraded_reason": None,
            "source_refs": ["provider:yfinance", "symbol:MSFT", "timeframe:1d"],
            "error": None,
        }
        incomplete_payload = {
            **base_payload,
            "rows": [
                {"date": "2026-07-13", "open": 418, "high": 422, "low": 417, "close": 421},
                {"date": "2026-07-15", "open": 421, "high": 423, "low": 420, "close": 422},
            ],
        }
        complete_payload = {
            **base_payload,
            "rows": [
                *incomplete_payload["rows"][:1],
                {"date": "2026-07-14", "open": 420, "high": 422, "low": 419, "close": 421},
                *incomplete_payload["rows"][1:],
            ],
        }
        service = MarketDataService(self.db, persistence_db=self.db)
        with patch(
            "services.market_data_service.get_daily_bars_with_metadata",
            return_value=incomplete_payload,
        ):
            first = asyncio.run(service.get_price_history("MSFT", start, end))
        self.assertEqual([row["date"] for row in first], ["2026-07-13", "2026-07-15"])

        with patch(
            "services.market_data_service.get_daily_bars_with_metadata",
            return_value=complete_payload,
        ) as fetch_daily:
            second = asyncio.run(service.get_price_history("MSFT", start, end))

        self.assertEqual(fetch_daily.call_count, 1)
        self.assertEqual(
            [row["date"] for row in second],
            ["2026-07-13", "2026-07-14", "2026-07-15"],
        )
        self.assertEqual(self.db.query(PriceBarDaily).count(), 3)

    def test_market_worker_persists_quote_in_its_existing_transaction(self):
        payload = {
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
        quote_job = enqueue_quote_refresh(
            self.db,
            symbol="AAPL",
            market="US",
            now=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        )
        self.db.commit()

        with patch(
            "services.market_data_service.get_quote_with_metadata",
            return_value=payload,
        ):
            completed = run_next_due_job(
                self.db,
                queue_name="market",
                worker_id="test-market-worker",
                handlers=build_default_job_handlers(self.db),
                now=datetime(2026, 7, 15, 8, 1, tzinfo=timezone.utc),
            )
            self.db.commit()

        self.assertEqual(completed.id, quote_job.id)
        self.assertEqual(completed.status, JobRunStatus.SUCCEEDED)
        self.assertEqual(self.db.query(LatestMarketQuote).count(), 1)
        self.assertEqual(
            self.db.query(JobRun)
            .filter(JobRun.idempotency_key.like("market.daily_backfill:AAPL:%"))
            .count(),
            1,
        )

    def test_symbol_validation_exposes_actual_provider_and_trust_metadata(self):
        service = MarketDataService(self.db, persistence_db=self.db)
        metadata = AssetMetadata(
            symbol="MSFT",
            name="Microsoft",
            core_type=AssetCoreType.STOCK,
            market=AssetMarket.US,
            currency=AssetCurrency.USD,
        )
        quote = {
            "c": 421.13,
            "name": "MSFT",
            "provider": "yfinance",
            "as_of": "2026-07-15T08:00:00+00:00",
            "freshness": "FRESH",
            "degraded": False,
            "degraded_reason": None,
            "source_refs": ["provider:yfinance", "symbol:MSFT"],
        }
        with (
            patch.object(
                service,
                "get_or_create_asset_metadata",
                new=AsyncMock(return_value=metadata),
            ),
            patch.object(service, "get_quote", new=AsyncMock(return_value=quote)),
        ):
            result = asyncio.run(service.validate_symbol("MSFT", "NASDAQ"))

        self.assertTrue(result["valid"])
        self.assertEqual(result["provider"], "yfinance")
        self.assertEqual(result["as_of"], quote["as_of"])
        self.assertEqual(result["freshness"], "FRESH")
        self.assertFalse(result["degraded"])
        self.assertEqual(result["source_refs"], quote["source_refs"])


if __name__ == "__main__":
    unittest.main()
