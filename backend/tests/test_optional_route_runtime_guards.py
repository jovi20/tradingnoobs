from __future__ import annotations

import os
import tempfile
import unittest
from datetime import date, datetime, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
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
    ("GET", "/api/market/quote/AAPL", RuntimeCapability.MARKET),
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
                frozenset(capability for _, _, capability in ROUTE_CAPABILITIES)
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
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
                self.assertEqual(response.json()["detail"]["capability"], capability.value)

    def test_missing_runtime_flag_stops_mutating_handler_before_side_effects(self):
        before_count = self.db.query(WeeklyReport).count()

        with patch("routers.insights.generate_weekly_report") as generate_report:
            response = self.client.post("/api/insights/generate-current-week")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
        generate_report.assert_not_called()
        self.db.expire_all()
        self.assertEqual(self.db.query(WeeklyReport).count(), before_count)

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
