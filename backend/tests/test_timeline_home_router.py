import os
import tempfile
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import (
    AIAnalysisResult,
    DerivedTimelineSnapshot,
    FeatureFlag,
    InsightArtifact,
    InsightRun,
    Position,
    PositionDirection,
    PositionStatus,
    TradingAccount,
    User,
)
from services.auth_service import get_current_user


class TimelineHomeRouterTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.database_url = f"sqlite:///{self.db_path}"
        self.engine = create_engine(
            self.database_url,
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        self.session = self.SessionLocal()
        self.user = User(
            email="timeline@example.com",
            email_normalized="timeline@example.com",
            hashed_password="hashed",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.session.add(self.user)
        self.session.commit()
        self.session.refresh(self.user)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.session.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def enable_legacy_mixed_feed(self):
        self.session.add(FeatureFlag(key="timeline_legacy_mixed_feed_enabled", enabled=True))
        self.session.commit()

    def test_timeline_home_returns_zero_state_when_user_has_no_accounts_or_positions(self):
        response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["page_state"], "ZERO")
        self.assertEqual(payload["data"]["review_inbox"]["counts"]["total"], 0)
        self.assertEqual(payload["data"]["timeline"]["active_view"], "ALL")
        self.assertEqual(payload["meta"]["freshness"], "FRESH")
        self.assertEqual(payload["meta"]["source"], "DERIVED")

    def test_timeline_home_returns_small_data_when_user_has_account_and_position(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-timeline",
            name="IBKR Main",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)

        position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="pos-open",
            symbol="NVDA",
            exchange="NASDAQ",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=1,
            opened_at=datetime.now(timezone.utc),
        )
        self.session.add(position)
        self.session.commit()

        response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["page_state"], "SMALL_DATA")
        self.assertEqual(payload["data"]["summary_bar"]["trade_count"], 1)
        self.assertEqual(payload["data"]["summary_bar"]["priority_alert_count"], 0)
        self.assertEqual(payload["meta"]["maturity"], "INSUFFICIENT_SAMPLE")

    def test_timeline_home_surfaces_materialized_timeline_snapshots(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-snapshot",
            name="Snapshot Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.flush()
        position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="pos-snapshot",
            symbol="AAPL",
            exchange="NASDAQ",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=1,
            opened_at=datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc),
        )
        self.session.add(position)
        self.session.flush()
        snapshot = DerivedTimelineSnapshot(
            user_id=self.user.id,
            trading_position_public_id="tp-snapshot",
            source="truth.lifecycle.bridge",
            snapshot_json={
                "position_title": "AAPL",
                "lifecycle_node_count": 2,
                "position_event_public_id": "evt-snapshot",
                "position_event_type": "REDUCE",
                "position_event_occurred_at": "2026-05-02T15:30:00Z",
            },
            refreshed_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        other_user = User(
            email="timeline-other@example.com",
            email_normalized="timeline-other@example.com",
            hashed_password="hashed",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.session.add(other_user)
        self.session.flush()
        other_snapshot = DerivedTimelineSnapshot(
            user_id=other_user.id,
            trading_position_public_id="tp-other-snapshot",
            source="truth.lifecycle.bridge",
            snapshot_json={
                "position_title": "SHOULD_NOT_LEAK",
                "lifecycle_node_count": 1,
                "position_event_type": "OPEN",
            },
            refreshed_at=datetime(2026, 5, 3, 11, 0, tzinfo=timezone.utc),
        )
        self.session.add_all([snapshot, other_snapshot])
        self.session.commit()

        response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        items = [
            item
            for group in payload["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        snapshot_items = [item for item in items if item["event_public_id"].startswith("derived-timeline:")]
        self.assertEqual(len(snapshot_items), 1)
        self.assertNotIn("SHOULD_NOT_LEAK", [item["headline"] for item in items])
        self.assertEqual(snapshot_items[0]["thread_public_id"], "tp-snapshot")
        self.assertEqual(snapshot_items[0]["event_type"], "REDUCE")
        self.assertEqual(snapshot_items[0]["occurred_at"], "2026-05-02T15:30:00Z")
        self.assertEqual(snapshot_items[0]["headline"], "AAPL 减仓")
        self.assertEqual(snapshot_items[0]["summary"], "Truth lifecycle snapshot refreshed with 2 nodes.")
        self.assertEqual(snapshot_items[0]["trust"]["source"], "DERIVED")

    def test_timeline_home_defaults_to_snapshot_only_without_feature_flag(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-default-snapshot",
            name="Default Snapshot Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.flush()
        self.session.add(
            Position(
                user_id=self.user.id,
                account_id=account.id,
                public_id="legacy-pos-default-hidden",
                symbol="MSFT",
                exchange="NASDAQ",
                direction=PositionDirection.LONG,
                status=PositionStatus.OPEN,
                total_quantity=1,
                opened_at=datetime(2026, 6, 5, 10, 0, tzinfo=timezone.utc),
            )
        )
        self.session.add(
            DerivedTimelineSnapshot(
                user_id=self.user.id,
                trading_position_public_id="tp-default-snapshot",
                source="truth.lifecycle.bridge",
                snapshot_json={
                    "position_title": "AAPL",
                    "lifecycle_node_count": 1,
                    "position_event_public_id": "truth-event-default",
                    "position_event_type": "OPEN",
                    "position_event_occurred_at": "2026-06-05T10:00:00Z",
                },
                refreshed_at=datetime(2026, 6, 5, 10, 1, tzinfo=timezone.utc),
            )
        )
        self.session.commit()

        response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        headlines = [
            item["headline"]
            for group in payload["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        joined_headlines = " ".join(headlines)
        self.assertIn("AAPL 开仓", headlines)
        self.assertNotIn("MSFT", joined_headlines)

    def test_timeline_home_snapshot_only_flag_hides_legacy_position_events(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-snapshot-only",
            name="Snapshot Only Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.flush()
        self.session.add(
            Position(
                user_id=self.user.id,
                account_id=account.id,
                public_id="pos-legacy-hidden",
                symbol="MSFT",
                exchange="NASDAQ",
                direction=PositionDirection.LONG,
                status=PositionStatus.OPEN,
                total_quantity=1,
                opened_at=datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc),
            )
        )
        self.session.add(
            DerivedTimelineSnapshot(
                user_id=self.user.id,
                trading_position_public_id="tp-snapshot-only",
                source="truth.lifecycle.bridge",
                snapshot_json={
                    "position_title": "MSFT",
                    "lifecycle_node_count": 1,
                    "position_event_type": "OPEN",
                    "position_event_occurred_at": "2026-05-03T09:30:00Z",
                },
                refreshed_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            )
        )
        self.session.add(FeatureFlag(key="timeline_snapshot_only_enabled", enabled=True))
        self.session.commit()

        response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        items = [
            item
            for group in response.json()["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        self.assertEqual(len(items), 1)
        self.assertTrue(items[0]["event_public_id"].startswith("derived-timeline:"))

    def test_timeline_home_snapshot_only_flag_includes_artifact_backed_ai_events(self):
        self.session.add(
            DerivedTimelineSnapshot(
                user_id=self.user.id,
                trading_position_public_id="tp-snapshot-ai",
                source="truth.lifecycle.bridge",
                snapshot_json={
                    "position_title": "NVDA",
                    "lifecycle_node_count": 2,
                    "position_event_type": "REDUCE",
                    "position_event_occurred_at": "2026-05-03T09:30:00Z",
                },
                refreshed_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            )
        )
        run = InsightRun(
            user_id=self.user.id,
            public_id="run-timeline-ai",
            run_type="position_review",
            status="COMPLETED",
            prompt_version="position-review.v1",
            input_refs=["tp-snapshot-ai"],
            started_at=datetime(2026, 5, 3, 11, 0, tzinfo=timezone.utc),
            completed_at=datetime(2026, 5, 3, 11, 1, tzinfo=timezone.utc),
        )
        self.session.add(run)
        self.session.flush()
        self.session.add(
            InsightArtifact(
                insight_run_id=run.id,
                public_id="artifact-timeline-ai",
                artifact_type="position_review",
                title="NVDA review artifact",
                summary="Exit discipline improved after reducing into strength.",
                content_markdown="## Review\nExit discipline improved.",
                payload={"linked_object_public_id": "tp-snapshot-ai"},
                evidence_refs=["tp-snapshot-ai", "evt-reduce"],
                chart_schema=None,
                trust_meta={
                    "freshness": "FRESH",
                    "source": "AI_GENERATED",
                    "value_status": "FINAL",
                    "source_refs": ["tp-snapshot-ai"],
                },
                created_at=datetime(2026, 5, 3, 11, 2, tzinfo=timezone.utc),
            )
        )
        self.session.add(FeatureFlag(key="timeline_snapshot_only_enabled", enabled=True))
        self.session.commit()

        response = self.client.get("/api/timeline/home?view=AI")

        self.assertEqual(response.status_code, 200)
        items = [
            item
            for group in response.json()["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["event_type"], "AI_INSIGHT")
        self.assertEqual(items[0]["event_public_id"], "insight-artifact:artifact-timeline-ai")
        self.assertEqual(items[0]["ai_annotation"]["artifact_public_id"], "artifact-timeline-ai")
        self.assertEqual(items[0]["ai_annotation"]["href"], "/insights/artifact-timeline-ai")
        self.assertEqual(items[0]["trust"]["source"], "AI_GENERATED")

    def test_timeline_home_snapshot_only_flag_skips_legacy_exception_builders(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-snapshot-only-side-effects",
            name="Snapshot Only Side Effects Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.flush()
        self.session.add(
            Position(
                user_id=self.user.id,
                account_id=account.id,
                public_id="pos-snapshot-only-side-effects",
                symbol="AAPL",
                exchange="NASDAQ",
                direction=PositionDirection.LONG,
                status=PositionStatus.OPEN,
                total_quantity=1,
                opened_at=datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc),
            )
        )
        self.session.add(
            AIAnalysisResult(
                user_id=self.user.id,
                analysis_type="strategy_health",
                ai_insights="Legacy AI signal should not be consulted for snapshot-only feed.",
                raw_data={"scope": "weekly"},
            )
        )
        self.session.add(
            DerivedTimelineSnapshot(
                user_id=self.user.id,
                trading_position_public_id="tp-snapshot-only-side-effects",
                source="truth.lifecycle.bridge",
                snapshot_json={
                    "position_title": "AAPL",
                    "lifecycle_node_count": 1,
                    "position_event_type": "OPEN",
                    "position_event_occurred_at": "2026-05-03T09:30:00Z",
                },
                refreshed_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            )
        )
        self.session.add(FeatureFlag(key="timeline_snapshot_only_enabled", enabled=True))
        self.session.commit()

        with (
            patch("routers.timeline.MarketDataService.get_quote", new_callable=AsyncMock) as get_quote,
            patch("routers.timeline.get_llm_runtime_config", return_value={"api_url": None, "api_key": None, "model": None}) as get_llm_config,
        ):
            response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(get_quote.await_count, 0)
        get_llm_config.assert_not_called()

    def test_timeline_home_defaults_to_snapshot_only_even_when_old_positive_flag_expires(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-snapshot-expired",
            name="Snapshot Expired Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.flush()
        self.session.add(
            Position(
                user_id=self.user.id,
                account_id=account.id,
                public_id="pos-legacy-visible",
                symbol="MSFT",
                exchange="NASDAQ",
                direction=PositionDirection.LONG,
                status=PositionStatus.OPEN,
                total_quantity=1,
                opened_at=datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc),
            )
        )
        self.session.add(
            DerivedTimelineSnapshot(
                user_id=self.user.id,
                trading_position_public_id="tp-snapshot-expired",
                source="truth.lifecycle.bridge",
                snapshot_json={
                    "position_title": "MSFT",
                    "lifecycle_node_count": 1,
                    "position_event_type": "OPEN",
                    "position_event_occurred_at": "2026-05-03T09:30:00Z",
                },
                refreshed_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            )
        )
        self.session.add(
            FeatureFlag(
                key="timeline_snapshot_only_enabled",
                enabled=True,
                expires_at=datetime(2000, 1, 1, tzinfo=timezone.utc),
            )
        )
        self.session.commit()

        response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        items = [
            item
            for group in response.json()["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        self.assertEqual(len(items), 1)
        self.assertTrue(any(item["event_public_id"].startswith("derived-timeline:") for item in items))
        self.assertFalse(any(item["event_public_id"].startswith("pos-legacy-visible:") for item in items))

    def test_timeline_home_legacy_mixed_feed_flag_restores_legacy_events(self):
        self.user.public_id = "timeline-target-user"
        self.session.commit()
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-snapshot-targeted",
            name="Snapshot Targeted Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.flush()
        self.session.add(
            Position(
                user_id=self.user.id,
                account_id=account.id,
                public_id="pos-targeted-visible",
                symbol="MSFT",
                exchange="NASDAQ",
                direction=PositionDirection.LONG,
                status=PositionStatus.OPEN,
                total_quantity=1,
                opened_at=datetime(2026, 5, 3, 9, 30, tzinfo=timezone.utc),
            )
        )
        self.session.add(
            DerivedTimelineSnapshot(
                user_id=self.user.id,
                trading_position_public_id="tp-snapshot-targeted",
                source="truth.lifecycle.bridge",
                snapshot_json={
                    "position_title": "MSFT",
                    "lifecycle_node_count": 1,
                    "position_event_type": "OPEN",
                    "position_event_occurred_at": "2026-05-03T09:30:00Z",
                },
                refreshed_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            )
        )
        self.session.add(
            FeatureFlag(
                key="timeline_legacy_mixed_feed_enabled",
                enabled=True,
                actor_targets=["timeline-target-user"],
            )
        )
        self.session.commit()

        response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        items = [
            item
            for group in response.json()["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        self.assertEqual(len(items), 2)
        self.assertTrue(any(item["event_public_id"].startswith("derived-timeline:") for item in items))
        self.assertTrue(any(item["event_public_id"].startswith("pos-targeted-visible:") for item in items))

    def test_timeline_home_builds_review_inbox_for_closed_position_without_review(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-review",
            name="Review Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)

        closed_position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="pos-missing-review",
            symbol="TSLA",
            exchange="NASDAQ",
            direction=PositionDirection.LONG,
            status=PositionStatus.CLOSED,
            total_quantity=0,
            realized_pnl=50,
            opened_at=datetime(2026, 4, 10, 9, 30, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 12, 20, 30, tzinfo=timezone.utc),
        )
        self.session.add(closed_position)
        self.session.commit()

        response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["review_inbox"]["counts"]["total"], 1)
        self.assertEqual(payload["data"]["review_inbox"]["counts"]["high_priority"], 1)
        item = payload["data"]["review_inbox"]["items"][0]
        self.assertEqual(item["kind"], "MISSING_REVIEW")
        self.assertEqual(item["linked_object"]["public_id"], "pos-missing-review")
        self.assertEqual(payload["data"]["summary_bar"]["priority_alert_count"], 1)

    def test_timeline_home_groups_open_close_and_review_events(self):
        self.enable_legacy_mixed_feed()

        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-events",
            name="Event Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)

        reviewed_position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="pos-reviewed",
            symbol="AAPL",
            exchange="NASDAQ",
            direction=PositionDirection.LONG,
            status=PositionStatus.CLOSED,
            total_quantity=0,
            realized_pnl=120,
            opened_at=datetime(2026, 4, 10, 9, 30, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 11, 20, 30, tzinfo=timezone.utc),
            trade_review="Followed the plan and exited into strength.",
            checklist_responses={"1": True, "2": False},
        )
        self.session.add(reviewed_position)
        self.session.commit()

        response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        event_types = [
            item["event_type"]
            for group in payload["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        self.assertIn("OPEN", event_types)
        self.assertIn("CLOSE", event_types)
        self.assertIn("REVIEW_COMPLETED", event_types)
        self.assertIn("CHECKLIST_MISS", event_types)

    def test_timeline_home_supports_selected_object_context(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-selected",
            name="Selected Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)

        position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="pos-selected",
            symbol="MSFT",
            exchange="NASDAQ",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=5,
            opened_at=datetime(2026, 4, 13, 9, 30, tzinfo=timezone.utc),
        )
        self.session.add(position)
        self.session.commit()

        response = self.client.get("/api/timeline/home?selected_object_public_id=pos-selected")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        selected = payload["data"]["context_rail"]["selected_object"]
        self.assertEqual(selected["public_id"], "pos-selected")
        self.assertEqual(selected["title"], "MSFT")

    def test_timeline_home_surfaces_ai_insight_events(self):
        self.enable_legacy_mixed_feed()

        ai_result = AIAnalysisResult(
            user_id=self.user.id,
            analysis_type="strategy_health",
            ai_insights="Your rule execution is improving, but exits remain delayed.",
            raw_data={"scope": "weekly"},
        )
        self.session.add(ai_result)
        self.session.commit()

        response = self.client.get("/api/timeline/home?view=AI")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        event_types = [
            item["event_type"]
            for group in payload["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        self.assertIn("AI_INSIGHT", event_types)
        ai_item = payload["data"]["timeline"]["groups"][0]["items"][0]
        self.assertIn("rule execution", ai_item["summary"])

    def test_timeline_home_surfaces_losing_streak_alerts_in_inbox_and_timeline(self):
        self.enable_legacy_mixed_feed()

        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-streak",
            name="Streak Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)

        positions = [
            Position(
                user_id=self.user.id,
                account_id=account.id,
                public_id=f"pos-loss-{idx}",
                symbol=symbol,
                exchange="NASDAQ",
                direction=PositionDirection.LONG,
                status=PositionStatus.CLOSED,
                total_quantity=0,
                realized_pnl=loss,
                opened_at=datetime(2026, 4, 10 + idx, 9, 30, tzinfo=timezone.utc),
                closed_at=datetime(2026, 4, 10 + idx, 20, 30, tzinfo=timezone.utc),
            )
            for idx, (symbol, loss) in enumerate([
                ("AMD", -80),
                ("TSLA", -60),
                ("NVDA", -40),
            ])
        ]
        self.session.add_all(positions)
        self.session.commit()

        response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        inbox_kinds = [item["kind"] for item in payload["data"]["review_inbox"]["items"]]
        self.assertIn("LOSING_STREAK", inbox_kinds)
        event_types = [
            item["event_type"]
            for group in payload["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        self.assertIn("LOSING_STREAK_ALERT", event_types)

    def test_timeline_home_paginates_timeline_events_with_limit_and_cursor(self):
        self.enable_legacy_mixed_feed()

        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-pagination",
            name="Pagination Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)

        positions = [
            Position(
                user_id=self.user.id,
                account_id=account.id,
                public_id=f"pos-page-{idx}",
                symbol=symbol,
                exchange="NASDAQ",
                direction=PositionDirection.LONG,
                status=PositionStatus.CLOSED,
                total_quantity=0,
                realized_pnl=100 + idx,
                opened_at=datetime(2026, 4, 10 + idx, 9, 30, tzinfo=timezone.utc),
                closed_at=datetime(2026, 4, 10 + idx, 16, 0, tzinfo=timezone.utc),
            )
            for idx, symbol in enumerate(["AAPL", "MSFT", "NVDA"])
        ]
        self.session.add_all(positions)
        self.session.commit()

        first_response = self.client.get("/api/timeline/home?limit=2")

        self.assertEqual(first_response.status_code, 200)
        first_payload = first_response.json()
        first_events = [
            item
            for group in first_payload["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        self.assertEqual(len(first_events), 2)
        self.assertIsNotNone(first_payload["data"]["timeline"]["next_cursor"])

        second_response = self.client.get(
            f"/api/timeline/home?limit=2&cursor={first_payload['data']['timeline']['next_cursor']}"
        )

        self.assertEqual(second_response.status_code, 200)
        second_payload = second_response.json()
        second_events = [
            item
            for group in second_payload["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        self.assertEqual(len(second_events), 2)
        self.assertTrue(
            {event["event_public_id"] for event in first_events}.isdisjoint(
                {event["event_public_id"] for event in second_events}
            )
        )

    def test_timeline_home_surfaces_data_stale_when_quote_fetch_fails_for_open_position(self):
        self.enable_legacy_mixed_feed()

        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-stale",
            name="Stale Account",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.session.add(account)
        self.session.commit()
        self.session.refresh(account)

        position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="pos-stale",
            symbol="AAPL",
            exchange="NASDAQ",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=5,
            opened_at=datetime(2026, 4, 13, 9, 30, tzinfo=timezone.utc),
        )
        self.session.add(position)
        self.session.commit()

        from unittest.mock import patch

        async def failing_quote(*args, **kwargs):
            raise Exception("Market data request timed out (5s)")

        with patch("routers.timeline.MarketDataService.get_quote", failing_quote):
            response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        event_types = [
            item["event_type"]
            for group in payload["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        self.assertIn("DATA_STALE", event_types)
        inbox_kinds = [item["kind"] for item in payload["data"]["review_inbox"]["items"]]
        self.assertIn("DATA_STALE", inbox_kinds)

    def test_timeline_home_surfaces_sync_exception_for_missing_llm_config_with_ai_signal(self):
        self.enable_legacy_mixed_feed()

        ai_result = AIAnalysisResult(
            user_id=self.user.id,
            analysis_type="emotion_pnl",
            ai_insights="Emotional trading is driving most recent losses.",
            raw_data={"scope": "weekly"},
        )
        self.session.add(ai_result)
        self.session.commit()

        from unittest.mock import patch

        with patch("routers.timeline.get_llm_runtime_config", return_value={"api_url": None, "api_key": None, "model": None}):
            response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        event_types = [
            item["event_type"]
            for group in payload["data"]["timeline"]["groups"]
            for item in group["items"]
        ]
        self.assertIn("SYNC_EXCEPTION", event_types)


if __name__ == "__main__":
    unittest.main()
