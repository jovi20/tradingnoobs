from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi import Depends, Request
from fastapi.testclient import TestClient
from fastapi.routing import APIRoute
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import create_app
from models import FeatureFlag, User, WeeklyReport
from release_profile import (
    DeploymentCapabilityPolicy,
    ReleaseProfile,
    RuntimeCapability,
)
from services.auth_service import get_current_user
from services.capability_service import capability_rollout_flag_key


ROUTE_CAPABILITIES = (
    ("POST", "/api/admin/test-llm", RuntimeCapability.AI_INSIGHTS),
    ("GET", "/api/market/quote/AAPL", RuntimeCapability.MARKET),
    ("POST", "/api/positions/not-found/analyze", RuntimeCapability.MARKET),
    ("GET", "/api/broker-sync/runs", RuntimeCapability.BROKER_SYNC),
    ("GET", "/api/insights", RuntimeCapability.AI_INSIGHTS),
    ("GET", "/api/v1/insights/runs", RuntimeCapability.AI_INSIGHTS),
    ("GET", "/api/insights/999/export/pdf", RuntimeCapability.PDF_EXPORT),
    ("GET", "/api/risk/summary", RuntimeCapability.RISK_CARDS),
)


class OptionalRouteRuntimeGuardTests(unittest.TestCase):
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
        self.user = User(
            email="runtime-guard@example.com",
            email_normalized="runtime-guard@example.com",
            hashed_password="hashed",
            public_id="runtime-guard-user",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        self.ceiling_patch = patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            DeploymentCapabilityPolicy(
                frozenset(
                    {
                        *(capability for _, _, capability in ROUTE_CAPABILITIES),
                        RuntimeCapability.OPEN_REGISTRATION,
                    }
                )
            ),
        )
        self.ceiling_patch.start()
        self.app = create_app(ReleaseProfile.DEVELOPMENT_FULL)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.user

        self.app.dependency_overrides[get_db] = override_get_db
        self.app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.app.dependency_overrides.clear()
        self.ceiling_patch.stop()
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _enable(self, *capabilities: RuntimeCapability) -> None:
        self.db.add_all(
            FeatureFlag(
                key=capability_rollout_flag_key(capability),
                enabled=True,
                actor_targets=[],
            )
            for capability in capabilities
        )
        self.db.commit()

    def test_missing_runtime_flags_block_every_real_router(self):
        for method, path, capability in ROUTE_CAPABILITIES:
            with self.subTest(path=path):
                response = self.client.request(method, path)
                self.assertEqual(response.status_code, 404, (path, response.text))
                self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
                self.assertEqual(response.json()["detail"]["capability"], capability.value)

    def test_app_factory_does_not_mutate_shared_optional_routes(self):
        from routers import (
            admin_ai,
            broker_sync,
            insight_artifacts,
            insights,
            market,
            pdf_export,
            position_market_analysis,
            risk,
        )

        optional_routers = (
            admin_ai.router,
            broker_sync.router,
            insight_artifacts.router,
            insight_artifacts.artifact_router,
            insights.router,
            market.router,
            pdf_export.router,
            position_market_analysis.router,
            risk.router,
        )
        create_app(ReleaseProfile.DEVELOPMENT_FULL)

        for router in optional_routers:
            for route in router.routes:
                if isinstance(route, APIRoute):
                    self.assertNotIn("_runtime_preflight_capability", route.__dict__)
                    self.assertNotIn("get_route_handler", route.__dict__)

    def test_lazy_handlers_and_overrides_remain_application_local(self):
        resources = []

        def build_isolated_app(*, enabled: bool, suffix: str):
            database_path = Path(self.db_path).with_name(f"isolated-{suffix}.db")
            engine = create_engine(
                f"sqlite:///{database_path}",
                connect_args={"check_same_thread": False},
            )
            session_factory = sessionmaker(bind=engine)
            Base.metadata.create_all(bind=engine)
            with session_factory() as db:
                user = User(
                    email=f"isolated-{suffix}@example.com",
                    email_normalized=f"isolated-{suffix}@example.com",
                    hashed_password="hashed",
                    public_id=f"isolated-{suffix}",
                    status="ACTIVE",
                    is_active=True,
                    role="user",
                )
                db.add(user)
                if enabled:
                    db.add(
                        FeatureFlag(
                            key=capability_rollout_flag_key(
                                RuntimeCapability.AI_INSIGHTS
                            ),
                            enabled=True,
                            actor_targets=[],
                        )
                    )
                db.commit()
                db.refresh(user)
                user_public_id = user.public_id

            application = create_app(ReleaseProfile.DEVELOPMENT_FULL)

            def override_get_db():
                with session_factory() as db:
                    yield db

            async def override_get_current_user():
                with session_factory() as db:
                    return db.query(User).filter(
                        User.public_id == user_public_id
                    ).one()

            application.dependency_overrides[get_db] = override_get_db
            application.dependency_overrides[
                get_current_user
            ] = override_get_current_user
            client = TestClient(application, raise_server_exceptions=False)
            resources.append((client, application, engine, database_path))
            return client

        disabled_client = build_isolated_app(enabled=False, suffix="disabled")
        enabled_client = build_isolated_app(enabled=True, suffix="enabled")
        try:
            statuses = [
                disabled_client.get("/api/v1/insights/runs").status_code,
                enabled_client.get("/api/v1/insights/runs").status_code,
                disabled_client.get("/api/v1/insights/runs").status_code,
                enabled_client.get("/api/v1/insights/runs").status_code,
            ]
            self.assertEqual(statuses, [404, 200, 404, 200])
            self.assertFalse(
                hasattr(resources[0][1].state, "lazy_capability_route_handlers")
            )
            self.assertTrue(
                hasattr(resources[1][1].state, "lazy_capability_route_handlers")
            )
        finally:
            for client, application, engine, database_path in resources:
                client.close()
                application.dependency_overrides.clear()
                engine.dispose()
                database_path.unlink(missing_ok=True)

    def test_missing_runtime_flags_block_before_json_body_parsing(self):
        requests = (
            ("/api/admin/test-llm", RuntimeCapability.AI_INSIGHTS),
            ("/api/insights/analyze", RuntimeCapability.AI_INSIGHTS),
            ("/api/broker-sync/ibkr/sync", RuntimeCapability.BROKER_SYNC),
        )

        for path, capability in requests:
            with self.subTest(path=path):
                response = self.client.post(
                    path,
                    content='{"secret":"must-not-be-parsed"',
                    headers={"content-type": "application/json"},
                )
                self.assertEqual(response.status_code, 404, (path, response.text))
                self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
                self.assertEqual(response.json()["detail"]["capability"], capability.value)
                self.assertNotIn("must-not-be-parsed", response.text)

    def test_missing_runtime_flag_stops_mutating_handler_before_side_effects(self):
        before_count = self.db.query(WeeklyReport).count()

        with patch("routers.insights.generate_weekly_report") as generate_report:
            response = self.client.post("/api/insights/generate-current-week")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
        generate_report.assert_not_called()
        self.db.expire_all()
        self.assertEqual(self.db.query(WeeklyReport).count(), before_count)

    def test_actor_targeted_rollout_reaches_only_the_selected_user(self):
        other_user = User(
            email="runtime-guard-other@example.com",
            email_normalized="runtime-guard-other@example.com",
            hashed_password="hashed",
            public_id="runtime-guard-other-user",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add_all(
            [
                other_user,
                FeatureFlag(
                    key=capability_rollout_flag_key(RuntimeCapability.AI_INSIGHTS),
                    enabled=True,
                    actor_targets=[self.user.public_id],
                    rollout_percentage=0,
                ),
            ]
        )
        self.db.commit()

        self.app.dependency_overrides[get_current_user] = lambda: other_user
        denied = self.client.get("/api/v1/insights/runs")
        self.assertEqual(denied.status_code, 404, denied.text)
        self.assertEqual(denied.json()["error"]["code"], "FEATURE_DISABLED")

        self.app.dependency_overrides[get_current_user] = lambda: self.user
        allowed = self.client.get("/api/v1/insights/runs")
        self.assertEqual(allowed.status_code, 200, allowed.text)
        self.assertEqual(allowed.json(), [])

    def test_request_aware_nested_overrides_reach_actor_targeted_rollout(self):
        self.db.add(
            FeatureFlag(
                key=capability_rollout_flag_key(RuntimeCapability.AI_INSIGHTS),
                enabled=True,
                actor_targets=[self.user.public_id],
                rollout_percentage=0,
            )
        )
        self.db.commit()

        async def override_user(
            request: Request,
            db=Depends(get_db),
        ):
            self.assertEqual(request.url.path, "/api/v1/insights/runs")
            return db.query(User).filter(
                User.public_id == self.user.public_id
            ).one()

        self.app.dependency_overrides[get_current_user] = override_user

        response = self.client.get("/api/v1/insights/runs")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json(), [])

    def test_request_aware_database_override_is_closed_after_dispatch(self):
        self._enable(RuntimeCapability.AI_INSIGHTS)
        opened_paths = []
        closed_paths = []

        def override_db(request: Request):
            opened_paths.append(request.url.path)
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()
                closed_paths.append(request.url.path)

        async def override_user(request: Request):
            self.assertEqual(request.url.path, "/api/v1/insights/runs")
            return self.user

        self.app.dependency_overrides[get_db] = override_db
        self.app.dependency_overrides[get_current_user] = override_user

        response = self.client.get("/api/v1/insights/runs")

        self.assertEqual(response.status_code, 200, response.text)
        self.assertGreaterEqual(len(opened_paths), 2)
        self.assertEqual(closed_paths, opened_paths)

    def test_market_capability_cannot_call_ai_classification(self):
        self._enable(RuntimeCapability.MARKET)

        with patch(
            "services.llm_service.classify_asset_rich",
            side_effect=AssertionError("MARKET must not cross the AI capability ceiling"),
        ) as classify_asset_rich:
            response = self.client.get("/api/market/detect/AAPL")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["symbol"], "AAPL")
        classify_asset_rich.assert_not_called()

    def test_enabled_runtime_flags_reach_each_real_router(self):
        self._enable(
            RuntimeCapability.MARKET,
            RuntimeCapability.BROKER_SYNC,
            RuntimeCapability.AI_INSIGHTS,
            RuntimeCapability.PDF_EXPORT,
            RuntimeCapability.RISK_CARDS,
        )
        report = WeeklyReport(
            user_id=self.user.id,
            week_start=date(2026, 7, 6),
            week_end=date(2026, 7, 12),
            trades_summary="Runtime-gated export.",
            created_at=datetime(2026, 7, 13, tzinfo=timezone.utc),
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)

        async def fake_get_quote(_service, symbol, _exchange):
            return {
                "c": 100,
                "provider": "test",
                "freshness": "FRESH",
                "source_refs": [f"symbol:{symbol}"],
            }

        with (
            patch("routers.market.MarketDataService.get_quote", new=fake_get_quote),
            patch("routers.market.MarketDataService.detect_asset_type", return_value="STOCK"),
        ):
            market_response = self.client.get("/api/market/quote/AAPL")

        self.assertEqual(market_response.status_code, 200)
        position_analysis_response = self.client.post(
            "/api/positions/not-found/analyze"
        )
        self.assertEqual(position_analysis_response.status_code, 404)
        self.assertEqual(
            position_analysis_response.json()["detail"],
            "Position not found",
        )
        self.assertEqual(self.client.post("/api/admin/test-llm").status_code, 403)
        self.assertEqual(self.client.get("/api/broker-sync/runs").status_code, 200)
        self.assertEqual(self.client.get("/api/insights").status_code, 200)
        self.assertEqual(self.client.get("/api/v1/insights/runs").status_code, 200)
        self.assertEqual(
            self.client.get(f"/api/insights/{report.id}/export/pdf").status_code,
            200,
        )
        self.assertEqual(self.client.get("/api/risk/summary").status_code, 200)


if __name__ == "__main__":
    unittest.main()
