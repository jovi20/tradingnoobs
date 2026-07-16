from __future__ import annotations

import asyncio
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import create_app
from models import (
    IntegrationCredential,
    JobDefinition,
    JobRun,
    OutboxEvent,
    PlatformSetting,
    SystemSetting,
    User,
    UserSettings,
)
from release_profile import (
    ReleaseProfile,
    RuntimeCapability,
    bind_release_profile,
    is_capability_enabled,
    parse_release_profile,
)
from routers.admin import (
    _require_provider_capability,
    _require_setting_capability,
    get_current_admin,
)
from routers.settings import _enforce_settings_capability_boundary, mask_api_key
from services.auth_service import get_current_user as get_settings_current_user
from services.market_data_job_service import (
    enqueue_daily_backfill,
    enqueue_quote_refresh,
    ensure_daily_backfill,
    ensure_quote_refresh,
)


class JournalBaselineProfileTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(ReleaseProfile.JOURNAL_BASELINE)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def test_unknown_profile_fails_closed(self):
        self.assertEqual(
            parse_release_profile("unknown-profile"),
            ReleaseProfile.JOURNAL_BASELINE,
        )
        self.assertFalse(
            is_capability_enabled(
                RuntimeCapability.MARKET,
                profile="unknown-profile",
            )
        )

    def test_known_optional_paths_return_stable_feature_disabled_without_echo(self):
        secret_values = ("shrt", "query-123", "reference-456")
        requests = (
            (
                "post",
                "/api/broker-sync/ibkr/sync?token=shrt&query_id=query-123",
                {"token": "shrt", "reference_code": "reference-456"},
                "BROKER_SYNC",
            ),
            (
                "get",
                "/api/market/quote/AAPL?api_key=shrt&reference_code=reference-456",
                None,
                "MARKET",
            ),
        )
        for method, path, body, capability in requests:
            response = self.client.request(method, path, json=body)
            self.assertEqual(response.status_code, 404)
            payload = response.json()
            self.assertEqual(payload["error"]["code"], "FEATURE_DISABLED")
            self.assertEqual(payload["detail"]["capability"], capability)
            serialized = response.text
            for secret in secret_values:
                self.assertNotIn(secret, serialized)

    def test_unknown_path_remains_normal_not_found(self):
        response = self.client.get("/api/not-a-real-capability")
        self.assertEqual(response.status_code, 404)
        self.assertNotEqual(response.json()["error"]["code"], "FEATURE_DISABLED")

    def test_disabled_routes_are_absent_from_openapi(self):
        paths = self.app.openapi()["paths"]
        self.assertFalse(any(path.startswith("/api/market") for path in paths))
        self.assertFalse(any(path.startswith("/api/broker-sync") for path in paths))

    def test_short_user_secret_is_never_returned_verbatim(self):
        self.assertEqual(mask_api_key("shrt"), "********")
        self.assertNotIn("shrt", mask_api_key("shrt"))

    def test_user_and_admin_optional_secret_writes_fail_closed(self):
        with bind_release_profile(ReleaseProfile.JOURNAL_BASELINE):
            guarded_calls = (
                lambda: _enforce_settings_capability_boundary({"ibkr_flex_token": "shrt"}),
                lambda: _enforce_settings_capability_boundary({"finnhub_api_key": "shrt"}),
                lambda: _require_provider_capability("finnhub"),
                lambda: _require_provider_capability("ibkr"),
                lambda: _require_setting_capability("binance_api_secret"),
            )
            for guarded_call in guarded_calls:
                with self.assertRaises(HTTPException) as raised:
                    guarded_call()
                self.assertEqual(raised.exception.status_code, 404)
                self.assertEqual(raised.exception.detail["code"], "FEATURE_DISABLED")

    def test_fx_fallback_does_not_call_market_provider(self):
        from services import exchange_rate_service

        with bind_release_profile(ReleaseProfile.JOURNAL_BASELINE):
            with patch.object(
                exchange_rate_service,
                "_fetch_rate",
                new=AsyncMock(side_effect=AssertionError("provider must not run")),
            ) as fetch_rate:
                rate = asyncio.run(exchange_rate_service.get_exchange_rate("USD", "CNY"))
        self.assertGreater(rate, 0)
        fetch_rate.assert_not_awaited()

    def test_clean_process_imports_no_real_optional_handlers(self):
        backend_dir = Path(__file__).resolve().parents[1]
        script = "\n".join(
            (
                "import sys",
                "import main",
                "from services.derived_refresh_handlers import build_default_job_handlers",
                "forbidden = [",
                "    'routers.market',",
                "    'routers.broker_sync',",
                "    'services.market_data_service',",
                "    'services.market_data_job_handlers',",
                "    'services.broker_sync.service',",
                "]",
                "loaded = [name for name in forbidden if name in sys.modules]",
                "assert main.app.state.release_profile == 'JOURNAL_BASELINE'",
                "assert loaded == [], loaded",
                "assert sorted(build_default_job_handlers(None)) == ['derived.timeline.refresh']",
            )
        )
        env = os.environ.copy()
        env["RELEASE_PROFILE"] = "JOURNAL_BASELINE"
        env["PYTHONPATH"] = str(backend_dir)
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)


class JournalBaselineDatabaseBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        db_path = os.path.join(self.temp_dir.name, "journal-baseline.db")
        self.engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False,
        )
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()
        try:
            self.user = User(
                email="baseline-user@example.com",
                email_normalized="baseline-user@example.com",
                hashed_password="hashed",
                public_id="baseline-user-public-id",
                status="ACTIVE",
                is_active=True,
                role="user",
            )
            self.admin = User(
                email="baseline-admin@example.com",
                email_normalized="baseline-admin@example.com",
                hashed_password="hashed",
                public_id="baseline-admin-public-id",
                status="ACTIVE",
                is_active=True,
                role="admin",
            )
            db.add_all([self.user, self.admin])
            db.commit()
        finally:
            db.close()

        self.app = create_app(ReleaseProfile.JOURNAL_BASELINE)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[get_db] = override_get_db
        self.app.dependency_overrides[get_settings_current_user] = lambda: self.user
        self.app.dependency_overrides[get_current_admin] = lambda: self.admin
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.app.dependency_overrides.clear()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def _optional_persistence_counts(self) -> tuple[int, int, int, int]:
        db = self.SessionLocal()
        try:
            return (
                db.query(UserSettings).count(),
                db.query(SystemSetting).count(),
                db.query(PlatformSetting).count(),
                db.query(IntegrationCredential).count(),
            )
        finally:
            db.close()

    def test_authenticated_optional_secret_writes_return_404_without_db_side_effects(self):
        secret = "must-not-be-persisted"
        requests = (
            ("patch", "/api/settings", {"ibkr_flex_token": secret}, "BROKER_SYNC"),
            ("patch", "/api/settings", {"finnhub_api_key": secret}, "MARKET"),
            (
                "put",
                "/api/admin/settings/binance_api_secret",
                {"value": secret},
                "BROKER_SYNC",
            ),
            (
                "put",
                "/api/admin/platform/settings/finnhub_api_key",
                {"value": secret},
                "MARKET",
            ),
            (
                "put",
                "/api/admin/platform/integrations/ibkr/flex_token",
                {"secret_value": secret},
                "BROKER_SYNC",
            ),
            (
                "put",
                "/api/admin/platform/integrations/finnhub/api_key",
                {"secret_value": secret},
                "MARKET",
            ),
        )
        baseline_counts = self._optional_persistence_counts()

        for method, path, body, capability in requests:
            with self.subTest(path=path):
                response = self.client.request(method, path, json=body)
                self.assertEqual(response.status_code, 404)
                payload = response.json()
                self.assertEqual(payload["error"]["code"], "FEATURE_DISABLED")
                self.assertEqual(payload["detail"]["capability"], capability)
                self.assertNotIn(secret, response.text)
                self.assertEqual(self._optional_persistence_counts(), baseline_counts)

    def test_market_job_entrypoints_fail_closed_without_persisting_job_state(self):
        db = self.SessionLocal()
        try:
            with bind_release_profile(ReleaseProfile.JOURNAL_BASELINE):
                guarded_calls = (
                    lambda: ensure_quote_refresh(db),
                    lambda: ensure_daily_backfill(db),
                    lambda: enqueue_quote_refresh(db, symbol="AAPL"),
                    lambda: enqueue_daily_backfill(
                        db,
                        symbol="AAPL",
                        start="2026-01-01",
                        end="2026-02-01",
                    ),
                )
                for guarded_call in guarded_calls:
                    with self.assertRaises(HTTPException) as raised:
                        guarded_call()
                    self.assertEqual(raised.exception.status_code, 404)
                    self.assertEqual(raised.exception.detail["code"], "FEATURE_DISABLED")

            self.assertEqual(
                db.query(JobDefinition).filter(JobDefinition.key.like("market.%")).count(),
                0,
            )
            self.assertEqual(db.query(JobRun).count(), 0)
            self.assertEqual(db.query(OutboxEvent).count(), 0)
        finally:
            db.rollback()
            db.close()


if __name__ == "__main__":
    unittest.main()
