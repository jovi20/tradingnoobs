import os
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    AssetMaster,
    LatestMarketQuote,
    PriceBarDaily,
    ProviderSymbolMapping,
    TradeInstrument,
    TradeInstrumentType,
)
from services.market_data_repository import MarketDataRepository


class MarketDataRepositoryTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.db = self.SessionLocal()
        self.repository = MarketDataRepository(self.db)

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _asset(self, symbol: str = "AAPL") -> AssetMaster:
        asset = AssetMaster(
            canonical_code=symbol,
            display_symbol=symbol,
            name=symbol,
            asset_type="STOCK",
            status="ACTIVE",
            metadata_json={},
        )
        self.db.add(asset)
        self.db.commit()
        self.db.refresh(asset)
        return asset

    def test_resolve_asset_reuses_legacy_truth_record_before_market_code(self):
        legacy_asset = self._asset()

        resolved = self.repository.resolve_or_create_asset(
            symbol="aapl",
            market="us",
            asset_type="stock",
            quote_currency="usd",
        )
        self.db.commit()

        self.assertEqual(resolved.id, legacy_asset.id)
        self.assertEqual(resolved.canonical_code, "AAPL")
        self.assertEqual(resolved.quote_currency, "USD")
        self.assertEqual(resolved.metadata_json["market"], "US")
        self.assertEqual(self.db.query(AssetMaster).count(), 1)

    def test_resolve_asset_creates_market_qualified_code_for_new_symbol(self):
        asset = self.repository.resolve_or_create_asset(
            symbol="0700.hk",
            market="hk",
            asset_type="stock",
            quote_currency="hkd",
            name="Tencent",
        )
        self.db.commit()

        self.assertEqual(asset.canonical_code, "HK:0700.HK")
        self.assertEqual(asset.display_symbol, "0700.HK")
        self.assertEqual(asset.quote_currency, "HKD")
        self.assertEqual(asset.metadata_json, {"market": "HK"})

    def test_resolve_asset_does_not_reuse_explicit_other_market_listing(self):
        hk_asset = AssetMaster(
            canonical_code="HK:AAPL",
            display_symbol="AAPL",
            name="AAPL HK listing",
            asset_type="STOCK",
            status="ACTIVE",
            metadata_json={"market": "HK"},
        )
        self.db.add(hk_asset)
        self.db.commit()

        us_asset = self.repository.resolve_or_create_asset(
            symbol="AAPL",
            market="US",
            asset_type="STOCK",
            quote_currency="USD",
        )
        self.db.commit()

        self.assertNotEqual(us_asset.id, hk_asset.id)
        self.assertEqual(us_asset.canonical_code, "US:AAPL")

    def test_provider_symbol_mapping_upserts_asset_and_instrument_scopes(self):
        asset = self._asset()
        instrument = TradeInstrument(
            asset_id=asset.id,
            instrument_type=TradeInstrumentType.EQUITY_OPTION,
            display_name="AAPL 200C",
            contract_symbol="AAPL  260619C00200000",
            status="ACTIVE",
        )
        self.db.add(instrument)
        self.db.commit()

        asset_mapping = self.repository.upsert_provider_symbol_mapping(
            asset_id=asset.id,
            provider_key="Finnhub",
            provider_symbol="AAPL",
            provider_market="us",
            capabilities={"QUOTE", "DAILY_BAR"},
        )
        self.assertEqual(asset_mapping.capabilities_json, ["DAILY_BAR", "QUOTE"])
        updated_mapping = self.repository.upsert_provider_symbol_mapping(
            asset_id=asset.id,
            provider_key="finnhub",
            provider_symbol="AAPL.US",
            provider_market="US",
            capabilities=["QUOTE"],
        )
        option_mapping = self.repository.upsert_provider_symbol_mapping(
            asset_id=asset.id,
            instrument_id=instrument.id,
            provider_key="finnhub",
            provider_symbol="AAPL260619C200",
            provider_market="US",
            capabilities=["QUOTE"],
        )
        self.db.commit()

        self.assertEqual(updated_mapping.id, asset_mapping.id)
        self.assertEqual(updated_mapping.provider_symbol, "AAPL.US")
        self.assertEqual(updated_mapping.capabilities_json, ["DAILY_BAR", "QUOTE"])
        self.assertIsNone(updated_mapping.instrument_id)
        self.assertEqual(option_mapping.instrument_id, instrument.id)
        self.assertEqual(self.db.query(ProviderSymbolMapping).count(), 2)

        fetched = self.repository.get_provider_symbol_mapping(
            provider_key="FINNHUB",
            provider_symbol="AAPL.US",
            provider_market="us",
        )
        self.assertEqual(fetched.id, asset_mapping.id)

    def test_asset_level_mapping_partial_index_rejects_duplicates(self):
        asset = self._asset()
        self.db.add_all(
            [
                ProviderSymbolMapping(
                    asset_id=asset.id,
                    provider_key="finnhub",
                    provider_symbol="AAPL",
                    provider_market="US",
                    capabilities_json=[],
                    quality_status="ACTIVE",
                ),
                ProviderSymbolMapping(
                    asset_id=asset.id,
                    provider_key="finnhub",
                    provider_symbol="AAPL_ALT",
                    provider_market="US",
                    capabilities_json=[],
                    quality_status="ACTIVE",
                ),
            ]
        )

        with self.assertRaises(IntegrityError):
            self.db.commit()
        self.db.rollback()

    def test_latest_quote_upsert_keeps_newest_and_supports_fresh_reads(self):
        asset = self._asset()
        first_received = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
        first = self.repository.upsert_latest_quote(
            asset_id=asset.id,
            provider="Finnhub",
            price="210.25",
            previous_close="208.00",
            received_at=first_received,
            market_time=datetime(2026, 7, 15, 11, 59, tzinfo=timezone.utc),
            currency="usd",
            raw_payload={"c": 210.25},
        )
        stale = self.repository.upsert_latest_quote(
            asset_id=asset.id,
            provider="finnhub",
            price="1.00",
            received_at=first_received - timedelta(minutes=1),
        )
        latest = self.repository.upsert_latest_quote(
            asset_id=asset.id,
            provider="finnhub",
            price="211.50",
            received_at=first_received + timedelta(minutes=2),
            quality_status="good",
        )
        self.db.commit()

        self.assertEqual(stale.id, first.id)
        self.assertEqual(latest.id, first.id)
        self.assertEqual(latest.price, Decimal("211.50000000"))
        self.assertEqual(self.db.query(LatestMarketQuote).count(), 1)

        fresh = self.repository.get_latest_quote(
            asset_id=asset.id,
            provider="FINNHUB",
            max_age=timedelta(minutes=5),
            now=first_received + timedelta(minutes=6),
        )
        expired = self.repository.get_latest_quote(
            asset_id=asset.id,
            provider="finnhub",
            max_age_seconds=60,
            now=first_received + timedelta(minutes=6),
        )
        self.assertEqual(fresh.id, first.id)
        self.assertIsNone(expired)

    def test_daily_bar_batch_upsert_reads_range_and_ignores_older_payload(self):
        asset = self._asset()
        first_received = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
        stored = self.repository.upsert_daily_bars(
            asset_id=asset.id,
            provider="YFinance",
            currency="usd",
            received_at=first_received,
            bars=[
                {"date": "2026-07-13", "o": 100, "h": 105, "l": 99, "c": 103, "v": 1000},
                {
                    "trading_date": date(2026, 7, 14),
                    "open": 103,
                    "high": 107,
                    "low": 101,
                    "close": 106,
                    "adj_close": 105.5,
                    "volume": 1200,
                },
            ],
        )
        stale = self.repository.upsert_daily_bar(
            asset_id=asset.id,
            provider="yfinance",
            trading_date="2026-07-14",
            open_price=1,
            high_price=1,
            low_price=1,
            close_price=1,
            received_at=first_received - timedelta(hours=1),
        )
        updated = self.repository.upsert_daily_bar(
            asset_id=asset.id,
            provider="yfinance",
            trading_date="2026-07-14",
            open_price=103,
            high_price=108,
            low_price=101,
            close_price=107,
            received_at=first_received + timedelta(hours=1),
        )
        self.db.commit()

        self.assertEqual(len(stored), 2)
        self.assertEqual(stale.id, stored[1].id)
        self.assertEqual(updated.id, stored[1].id)
        self.assertEqual(updated.close_price, Decimal("107.00000000"))
        self.assertEqual(self.db.query(PriceBarDaily).count(), 2)

        ranged = self.repository.get_daily_bars(
            asset_id=asset.id,
            provider="YFINANCE",
            start_date="2026-07-14",
            end_date="2026-07-15",
        )
        fresh = self.repository.get_fresh_daily_bars(
            asset_id=asset.id,
            provider="yfinance",
            start_date="2026-07-13",
            end_date="2026-07-14",
            max_age=timedelta(minutes=90),
            now=first_received + timedelta(hours=2),
        )
        self.assertEqual([row.trading_date for row in ranged], [date(2026, 7, 14)])
        self.assertEqual([row.trading_date for row in fresh], [date(2026, 7, 14)])

    def test_watermark_expands_coverage_and_clears_prior_error(self):
        asset = self._asset()
        first_success = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc)
        watermark = self.repository.upsert_watermark(
            asset_id=asset.id,
            data_type="daily_bar",
            provider="YFinance",
            covered_from="2026-07-01",
            covered_to="2026-07-10",
            last_success_at=first_success,
        )
        failed = self.repository.upsert_watermark(
            asset_id=asset.id,
            data_type="DAILY_BAR",
            provider="yfinance",
            last_error="provider timeout",
        )
        next_success = first_success + timedelta(hours=1)
        extended = self.repository.upsert_watermark(
            asset_id=asset.id,
            data_type="daily_bar",
            provider="yfinance",
            covered_from="2026-06-25",
            covered_to="2026-07-14",
            last_success_at=next_success,
        )
        self.db.commit()

        self.assertEqual(failed.id, watermark.id)
        self.assertEqual(extended.id, watermark.id)
        self.assertEqual(extended.covered_from, date(2026, 6, 25))
        self.assertEqual(extended.covered_to, date(2026, 7, 14))
        self.assertIsNone(extended.last_error)
        self.assertEqual(
            extended.last_success_at.replace(tzinfo=timezone.utc),
            next_success,
        )

        fetched = self.repository.get_watermark(
            asset_id=asset.id,
            data_type="daily_bar",
            provider="YFINANCE",
        )
        self.assertEqual(fetched.id, watermark.id)


if __name__ == "__main__":
    unittest.main()
