import unittest
from datetime import datetime, timezone
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import FeatureFlag, JobDefinition, JobRun, JobRunStatus, OutboxEvent
from release_profile import RuntimeCapability
from services.capability_service import capability_rollout_flag_key
from services.market_data_job_service import (
    enqueue_daily_backfill,
    enqueue_quote_refresh,
    ensure_daily_backfill,
    ensure_quote_refresh,
)


class MarketDataJobServiceTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(bind=engine)
        self.addCleanup(engine.dispose)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.db = self.SessionLocal()
        self.addCleanup(self.db.close)
        self.db.add(
            FeatureFlag(
                key=capability_rollout_flag_key(RuntimeCapability.MARKET),
                enabled=True,
            )
        )
        self.db.flush()

    def _market_persistence_counts(self) -> tuple[int, int, int]:
        return (
            self.db.query(JobDefinition).filter(JobDefinition.key.like("market.%")).count(),
            self.db.query(JobRun).count(),
            self.db.query(OutboxEvent).count(),
        )

    def test_ensure_definitions_are_idempotent_and_use_market_queue(self):
        quote_first = ensure_quote_refresh(self.db)
        quote_second = ensure_quote_refresh(self.db)
        daily_first = ensure_daily_backfill(self.db)
        daily_second = ensure_daily_backfill(self.db)

        self.assertEqual(quote_first.id, quote_second.id)
        self.assertEqual(daily_first.id, daily_second.id)
        self.assertEqual(self.db.query(JobDefinition).count(), 2)
        self.assertEqual(quote_first.queue_name, "market")
        self.assertEqual(daily_first.queue_name, "market")
        self.assertEqual(quote_first.retry_policy["max_attempts"], 3)
        self.assertEqual(daily_first.retry_policy["max_attempts"], 3)

    def test_quote_enqueue_normalizes_payload_and_adds_lock(self):
        run = enqueue_quote_refresh(
            self.db,
            symbol=" msft ",
            exchange="NASDAQ",
            market="US",
            user_id=None,
            priority=5,
            now=datetime(2026, 7, 15, 8, 0, tzinfo=timezone.utc),
        )

        self.assertEqual(run.status, JobRunStatus.QUEUED)
        self.assertEqual(run.queue_name, "market")
        self.assertEqual(run.priority, 5)
        self.assertEqual(run.idempotency_key, "market.quote.refresh:MSFT")
        self.assertEqual(run.payload["symbol"], "MSFT")
        self.assertEqual(run.payload["exchange"], "NASDAQ")
        self.assertEqual(run.payload["market"], "US")
        self.assertEqual(
            run.payload["business_locks"],
            [
                {
                    "scope": "market.quote.refresh",
                    "resource_key": "MSFT",
                    "ttl_seconds": 60,
                }
            ],
        )

    def test_quote_enqueue_reuses_queued_running_or_retrying_job(self):
        for status in (
            JobRunStatus.QUEUED,
            JobRunStatus.RUNNING,
            JobRunStatus.RETRYING,
        ):
            with self.subTest(status=status):
                first = enqueue_quote_refresh(self.db, symbol="AAPL")
                first.status = status
                self.db.flush()

                second = enqueue_quote_refresh(self.db, symbol="aapl")

                self.assertEqual(second.id, first.id)
                self.assertEqual(
                    self.db.query(JobRun)
                    .filter(
                        JobRun.idempotency_key == "market.quote.refresh:AAPL",
                        JobRun.status.in_(
                            [
                                JobRunStatus.QUEUED,
                                JobRunStatus.RUNNING,
                                JobRunStatus.RETRYING,
                            ]
                        ),
                    )
                    .count(),
                    1,
                )
                first.status = JobRunStatus.SUCCEEDED
                self.db.flush()

    def test_quote_enqueue_creates_new_job_after_terminal_run(self):
        first = enqueue_quote_refresh(self.db, symbol="MSFT")
        first.status = JobRunStatus.SUCCEEDED
        self.db.flush()

        second = enqueue_quote_refresh(self.db, symbol="MSFT")

        self.assertNotEqual(second.id, first.id)
        self.assertEqual(second.idempotency_key, first.idempotency_key)

    def test_daily_backfill_deduplicates_canonical_symbol_and_range(self):
        first = enqueue_daily_backfill(
            self.db,
            symbol="msft",
            start="2026-01-01",
            end="2026-07-01T00:00:00Z",
            exchange="NASDAQ",
        )
        second = enqueue_daily_backfill(
            self.db,
            symbol="MSFT",
            start=datetime(2026, 1, 1, tzinfo=timezone.utc),
            end=datetime(2026, 7, 1, tzinfo=timezone.utc),
        )

        self.assertEqual(second.id, first.id)
        self.assertEqual(first.payload["start"], "2026-01-01T00:00:00+00:00")
        self.assertEqual(first.payload["end"], "2026-07-01T00:00:00+00:00")
        self.assertEqual(first.payload["business_locks"][0]["scope"], "market.daily_backfill")
        self.assertIn("MSFT:1d:", first.payload["business_locks"][0]["resource_key"])
        self.assertEqual(self.db.query(JobRun).count(), 1)

    def test_daily_backfill_allows_different_ranges(self):
        first = enqueue_daily_backfill(
            self.db,
            symbol="MSFT",
            start="2026-01-01",
            end="2026-02-01",
        )
        second = enqueue_daily_backfill(
            self.db,
            symbol="MSFT",
            start="2026-02-01",
            end="2026-03-01",
        )

        self.assertNotEqual(first.id, second.id)
        self.assertEqual(self.db.query(JobRun).count(), 2)

    def test_enqueue_validates_symbol_and_daily_range(self):
        with self.assertRaisesRegex(ValueError, "symbol must be a non-empty string"):
            enqueue_quote_refresh(self.db, symbol=" ")
        with self.assertRaisesRegex(ValueError, "start must be earlier than end"):
            enqueue_daily_backfill(
                self.db,
                symbol="MSFT",
                start="2026-07-01",
                end="2026-01-01",
            )

    def test_runtime_rollout_denials_do_not_persist_market_work(self):
        flag_key = capability_rollout_flag_key(RuntimeCapability.MARKET)
        cases = (
            ("missing", None),
            ("disabled", {"enabled": False}),
            (
                "expired",
                {
                    "enabled": True,
                    "expires_at": datetime(2000, 1, 1, tzinfo=timezone.utc),
                },
            ),
            ("malformed", {"enabled": True, "actor_targets": {}}),
        )

        for label, flag_values in cases:
            with self.subTest(label=label):
                self.db.query(FeatureFlag).delete()
                if flag_values is not None:
                    self.db.add(FeatureFlag(key=flag_key, **flag_values))
                self.db.flush()
                before = self._market_persistence_counts()

                with self.assertRaises(HTTPException) as raised:
                    enqueue_quote_refresh(self.db, symbol="AAPL")

                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail["code"], "FEATURE_DISABLED")
                self.assertEqual(self._market_persistence_counts(), before)

    def test_runtime_rollout_database_error_does_not_persist_market_work(self):
        before = self._market_persistence_counts()

        with patch(
            "services.capability_service.get_feature_flag_enabled",
            side_effect=RuntimeError("flag database unavailable"),
        ):
            with self.assertRaises(HTTPException) as raised:
                enqueue_daily_backfill(
                    self.db,
                    symbol="AAPL",
                    start="2026-01-01",
                    end="2026-02-01",
                )

        self.assertEqual(raised.exception.status_code, 404)
        self.assertEqual(raised.exception.detail["code"], "FEATURE_DISABLED")
        self.assertEqual(self._market_persistence_counts(), before)


if __name__ == "__main__":
    unittest.main()
