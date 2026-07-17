import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app, create_app
from models import (
    AIAnalysisResult,
    DailySnapshot,
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
from release_profile import DeploymentCapabilityPolicy
from routers.timeline import build_router as build_timeline_router
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
        self.extra_clients = []

    def tearDown(self):
        for client in self.extra_clients:
            client.close()
        app.dependency_overrides.clear()
        self.session.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def enable_legacy_mixed_feed(self):
        self.session.add(FeatureFlag(key="timeline_legacy_mixed_feed_enabled", enabled=True))
        self.session.commit()

    def allow_capabilities(self, *capabilities: str):
        allowed = set(capabilities)
        return patch(
            "routers.timeline.is_effective_capability_enabled",
            side_effect=lambda _db, capability, **_kwargs: capability.value in allowed,
        )

    def build_optional_timeline_client(self):
        optional_app = FastAPI()
        optional_app.include_router(
            build_timeline_router(include_ai_contract=True)
        )

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.user

        optional_app.dependency_overrides[get_db] = override_get_db
        optional_app.dependency_overrides[
            get_current_user
        ] = override_get_current_user
        client = TestClient(optional_app)
        self.extra_clients.append(client)
        return client

    def add_daily_snapshot(self, snapshot_date: date, total_equity: str) -> None:
        self.session.add(
            DailySnapshot(
                user_id=self.user.id,
                date=snapshot_date,
                total_assets=Decimal(total_equity),
                total_liabilities=Decimal("0"),
                total_equity=Decimal(total_equity),
                net_transfers=Decimal("0"),
            )
        )
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
        self.assertEqual(payload["meta"]["note"], "审计快照视图")
        self.assertEqual(
            [item["key"] for item in payload["data"]["context_rail"]["quick_filters"]],
            ["ALL", "TRADING", "REVIEW", "EXCEPTION"],
        )

    def test_timeline_ai_view_is_disabled_without_effective_capability(self):
        response = self.client.get("/api/timeline/home?view=AI")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
        self.assertEqual(response.json()["detail"]["capability"], "AI_INSIGHTS")

    def test_empty_deployment_ceiling_uses_journal_timeline_response_contract(self):
        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.user

        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            DeploymentCapabilityPolicy(frozenset()),
        ):
            baseline_app = create_app()
            baseline_app.dependency_overrides[get_db] = override_get_db
            baseline_app.dependency_overrides[get_current_user] = override_get_current_user
            baseline_client = TestClient(baseline_app)

            response = baseline_client.get("/api/timeline/home")
            ai_response = baseline_client.get("/api/timeline/home?view=AI")

        self.assertEqual(response.status_code, 200)
        payload = response.json()["data"]
        self.assertEqual(
            [item["key"] for item in payload["context_rail"]["quick_filters"]],
            ["ALL", "TRADING", "REVIEW", "EXCEPTION"],
        )
        self.assertNotIn("net_equity_change", payload["summary_bar"])
        self.assertNotIn("ai_annotation", str(payload))
        self.assertEqual(ai_response.status_code, 404)
        self.assertEqual(ai_response.json()["error"]["code"], "FEATURE_DISABLED")

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
        self.assertEqual(snapshot_items[0]["summary"], "生命周期快照已更新，共 2 个事件节点。")
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
        optional_client = self.build_optional_timeline_client()
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

        with self.allow_capabilities("AI_INSIGHTS"):
            response = optional_client.get("/api/timeline/home?view=AI")

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

    def test_journal_timeline_skips_optional_reads_and_dtos_in_legacy_feed(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-empty-ceiling",
            name="Empty Ceiling Account",
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
                public_id="pos-empty-ceiling",
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
                ai_insights="Legacy AI signal must not bypass the capability ceiling.",
                raw_data={"scope": "weekly"},
            )
        )
        self.session.add(
            DerivedTimelineSnapshot(
                user_id=self.user.id,
                trading_position_public_id="tp-empty-ceiling",
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
        self.session.add(FeatureFlag(key="timeline_legacy_mixed_feed_enabled", enabled=True))
        self.session.commit()
        self.add_daily_snapshot(date(2026, 6, 10), "100000")
        self.add_daily_snapshot(date(2026, 6, 11), "94000")

        with (
            patch(
                "routers.timeline.is_effective_capability_enabled",
                return_value=False,
            ) as capability_enabled,
            patch("routers.timeline._list_ai_summaries") as list_ai_summaries,
            patch("routers.timeline._list_ai_analysis_results") as list_ai_results,
            patch("routers.timeline._list_insight_runs") as list_insight_runs,
            patch("routers.timeline._load_llm_runtime_config") as load_llm_config,
            patch("routers.timeline._load_portfolio_risk_summary") as load_risk_summary,
            patch("routers.timeline._build_data_stale_items") as build_data_stale_items,
            patch("routers.timeline._build_ai_insight_events") as build_ai_events,
            patch("routers.timeline._build_ai_insight_events_from_runs") as build_artifact_events,
            patch("routers.timeline._build_sync_exception_events") as build_sync_events,
            patch("routers.timeline._build_risk_review_inbox_items") as build_risk_items,
            patch("routers.timeline._build_data_stale_events") as build_data_stale_events,
            patch("services.platform_config_service.get_llm_runtime_config") as read_llm_secret,
            patch(
                "services.market_data_access.MarketDataService.get_quote",
                new_callable=AsyncMock,
            ) as market_quote,
            patch("services.risk_alert_service.build_portfolio_risk_summary") as build_risk_summary,
        ):
            response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        capability_enabled.assert_not_called()
        for optional_access in (
            list_ai_summaries,
            list_ai_results,
            list_insight_runs,
            load_llm_config,
            load_risk_summary,
            build_data_stale_items,
            build_ai_events,
            build_artifact_events,
            build_sync_events,
            build_risk_items,
            build_data_stale_events,
        ):
            optional_access.assert_not_called()
        read_llm_secret.assert_not_called()
        market_quote.assert_not_awaited()
        build_risk_summary.assert_not_called()

        payload = response.json()["data"]
        event_types = {
            item["event_type"]
            for group in payload["timeline"]["groups"]
            for item in group["items"]
        }
        self.assertTrue({"AI_INSIGHT", "DATA_STALE", "SYNC_EXCEPTION"}.isdisjoint(event_types))
        inbox_kinds = {item["kind"] for item in payload["review_inbox"]["items"]}
        self.assertTrue(
            {
                "DATA_STALE",
                "DAILY_LOSS_LIMIT",
                "PORTFOLIO_CONCENTRATION",
                "DRAWDOWN_ALERT",
            }.isdisjoint(inbox_kinds)
        )

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
        self.assertEqual(response.json()["meta"]["note"], "已启用旧版混合回退")

    def test_timeline_home_defaults_review_inbox_to_truth_snapshots_not_legacy_positions(self):
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
        self.assertEqual(payload["data"]["review_inbox"]["counts"]["total"], 0)
        self.assertEqual(payload["data"]["review_inbox"]["counts"]["high_priority"], 0)

    def test_timeline_home_builds_review_inbox_from_pending_review_snapshot(self):
        self.session.add(
            DerivedTimelineSnapshot(
                user_id=self.user.id,
                trading_position_public_id="tp-missing-review",
                source="truth.lifecycle.bridge",
                snapshot_json={
                    "position_title": "TSLA",
                    "review_status": "CLOSED_PENDING_REVIEW",
                    "position_event_type": "CLOSE",
                    "position_event_occurred_at": "2026-04-12T20:30:00Z",
                },
                refreshed_at=datetime(2026, 4, 12, 20, 31, tzinfo=timezone.utc),
            )
        )
        self.session.commit()

        response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["review_inbox"]["counts"]["total"], 1)
        self.assertEqual(payload["data"]["review_inbox"]["counts"]["high_priority"], 1)
        item = payload["data"]["review_inbox"]["items"][0]
        self.assertEqual(item["kind"], "MISSING_REVIEW")
        self.assertEqual(item["linked_object"]["public_id"], "tp-missing-review")
        self.assertEqual(item["linked_object"]["href"], "/positions/tp-missing-review")
        self.assertEqual(item["trust"]["source"], "DERIVED")
        self.assertEqual(payload["data"]["summary_bar"]["priority_alert_count"], 1)

    def test_timeline_home_adds_daily_loss_risk_alert_to_review_inbox(self):
        optional_client = self.build_optional_timeline_client()
        self.add_daily_snapshot(date(2026, 6, 10), "100000")
        self.add_daily_snapshot(date(2026, 6, 11), "94000")

        with self.allow_capabilities("RISK_CARDS"):
            response = optional_client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        risk_items = [
            item
            for item in payload["data"]["review_inbox"]["items"]
            if item["kind"] == "DAILY_LOSS_LIMIT"
        ]
        self.assertEqual(len(risk_items), 1)
        self.assertEqual(risk_items[0]["severity"], "CRITICAL")
        self.assertEqual(risk_items[0]["recommended_action"]["kind"], "OPEN_DASHBOARD")
        self.assertEqual(risk_items[0]["recommended_action"]["href"], "/dashboard")
        self.assertEqual(risk_items[0]["linked_object"]["object_type"], "PORTFOLIO")
        self.assertEqual(payload["data"]["summary_bar"]["priority_alert_count"], 1)

    def test_timeline_home_exception_view_counts_risk_review_inbox_alert(self):
        optional_client = self.build_optional_timeline_client()
        self.add_daily_snapshot(date(2026, 6, 10), "100000")
        self.add_daily_snapshot(date(2026, 6, 11), "96500")

        with self.allow_capabilities("RISK_CARDS"):
            response = optional_client.get("/api/timeline/home?view=EXCEPTION")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["timeline"]["active_view"], "EXCEPTION")
        self.assertEqual(payload["data"]["review_inbox"]["counts"]["total"], 1)
        self.assertEqual(payload["data"]["review_inbox"]["counts"]["high_priority"], 1)
        self.assertEqual(payload["data"]["summary_bar"]["priority_alert_count"], 1)

    def test_timeline_home_does_not_add_risk_alert_for_empty_portfolio(self):
        with self.allow_capabilities("RISK_CARDS"):
            response = self.client.get("/api/timeline/home")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        risk_kinds = {
            "DAILY_LOSS_LIMIT",
            "PORTFOLIO_CONCENTRATION",
            "DRAWDOWN_ALERT",
        }
        self.assertTrue(
            risk_kinds.isdisjoint(
                {item["kind"] for item in payload["data"]["review_inbox"]["items"]}
            )
        )

    def test_timeline_home_legacy_mixed_feed_restores_legacy_review_inbox_items(self):
        self.enable_legacy_mixed_feed()
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-review-legacy",
            name="Review Account Legacy",
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
            public_id="pos-missing-review-legacy",
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
        item = payload["data"]["review_inbox"]["items"][0]
        self.assertEqual(item["kind"], "MISSING_REVIEW")
        self.assertEqual(item["linked_object"]["public_id"], "pos-missing-review-legacy")

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
        optional_client = self.build_optional_timeline_client()
        self.enable_legacy_mixed_feed()

        ai_result = AIAnalysisResult(
            user_id=self.user.id,
            analysis_type="strategy_health",
            ai_insights="Your rule execution is improving, but exits remain delayed.",
            raw_data={"scope": "weekly"},
        )
        self.session.add(ai_result)
        self.session.commit()

        with self.allow_capabilities("AI_INSIGHTS"):
            response = optional_client.get("/api/timeline/home?view=AI")

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
        optional_client = self.build_optional_timeline_client()
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

        async def failing_quote(*args, **kwargs):
            raise Exception("Market data request timed out (5s)")

        with (
            self.allow_capabilities("MARKET"),
            patch("services.market_data_access.MarketDataService.get_quote", failing_quote),
        ):
            response = optional_client.get("/api/timeline/home")

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
        optional_client = self.build_optional_timeline_client()
        self.enable_legacy_mixed_feed()

        ai_result = AIAnalysisResult(
            user_id=self.user.id,
            analysis_type="emotion_pnl",
            ai_insights="Emotional trading is driving most recent losses.",
            raw_data={"scope": "weekly"},
        )
        self.session.add(ai_result)
        self.session.commit()

        with (
            self.allow_capabilities("AI_INSIGHTS"),
            patch(
                "routers.timeline._load_llm_runtime_config",
                return_value={"api_url": None, "api_key": None, "model": None},
            ),
        ):
            response = optional_client.get("/api/timeline/home")

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
