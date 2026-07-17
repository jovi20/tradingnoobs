from __future__ import annotations

import asyncio
from datetime import date
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import create_app
from models import (
    FeatureFlag,
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
    DeploymentCapabilityPolicy,
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
from services.capability_service import capability_rollout_flag_key
from services.market_data_job_service import (
    enqueue_daily_backfill,
    enqueue_quote_refresh,
    ensure_daily_backfill,
    ensure_quote_refresh,
)


class JournalBaselineProfileTests(unittest.TestCase):
    def setUp(self):
        self.ceiling_patch = patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            DeploymentCapabilityPolicy(frozenset()),
        )
        self.ceiling_patch.start()
        self.app = create_app(ReleaseProfile.JOURNAL_BASELINE)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.ceiling_patch.stop()

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
        self.assertNotIn("/api/auth/register", paths)
        self.assertNotIn("/api/positions/import/upload", paths)
        self.assertNotIn("/api/positions/import/confirm", paths)
        self.assertNotIn("/api/positions/import/template", paths)

    def test_legacy_import_paths_are_side_effect_free_until_persistent_import_exists(self):
        requests = (
            ("post", "/api/positions/import/upload", {"files": {"file": ("trades.csv", b"symbol,date")}}),
            ("post", "/api/positions/import/confirm", {"json": {"file_token": "untrusted", "account_id": 999}}),
            ("get", "/api/positions/import/template", {}),
        )

        for method, path, kwargs in requests:
            response = self.client.request(method, path, **kwargs)
            self.assertEqual(response.status_code, 404, response.text)
            self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
            self.assertEqual(response.json()["detail"]["capability"], "GENERIC_BOOTSTRAP")

    def test_open_registration_is_a_side_effect_free_disabled_route(self):
        with patch(
            "routers.open_registration.create_user",
            side_effect=AssertionError("registration handler must not run"),
        ) as create_user:
            response = self.client.post(
                "/api/auth/register",
                json={
                    "email": "should-not-exist@example.com",
                    "password": "password123",
                    "invite_code": "bigme",
                },
            )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
        self.assertEqual(response.json()["detail"]["capability"], "OPEN_REGISTRATION")
        create_user.assert_not_called()

    def test_short_user_secret_is_never_returned_verbatim(self):
        self.assertEqual(mask_api_key("shrt"), "********")
        self.assertNotIn("shrt", mask_api_key("shrt"))

    def test_user_and_admin_optional_secret_writes_fail_closed(self):
        with bind_release_profile(ReleaseProfile.JOURNAL_BASELINE):
            guarded_calls = (
                lambda: _enforce_settings_capability_boundary(
                    {"ibkr_flex_token": "shrt"},
                    effective_capabilities=frozenset(),
                ),
                lambda: _enforce_settings_capability_boundary(
                    {"finnhub_api_key": "shrt"},
                    effective_capabilities=frozenset(),
                ),
                lambda: _enforce_settings_capability_boundary(
                    {"llm_api_url": "https://llm.invalid"},
                    effective_capabilities=frozenset(),
                ),
                lambda: _enforce_settings_capability_boundary(
                    {"llm_api_key": "shrt"},
                    effective_capabilities=frozenset(),
                ),
                lambda: _enforce_settings_capability_boundary(
                    {"llm_model": "test-model"},
                    effective_capabilities=frozenset(),
                ),
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
                with self.assertRaises(exchange_rate_service.ExchangeRateUnavailableError):
                    asyncio.run(exchange_rate_service.get_exchange_rate("USD", "CNY"))
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
                "    'routers.insights',",
                "    'routers.insight_artifacts',",
                "    'routers.pdf_export',",
                "    'routers.risk',",
                "    'services.market_data_service',",
                "    'services.market_data_job_handlers',",
                "    'services.broker_sync.service',",
                "    'services.import_service',",
                "    'services.insight_artifact_service',",
                "    'services.llm_service',",
                "    'services.report_export_service',",
                "]",
                "loaded = [name for name in forbidden if name in sys.modules]",
                "assert main.app.state.release_profile == 'JOURNAL_BASELINE'",
                "assert loaded == [], loaded",
                "assert sorted(build_default_job_handlers(None)) == ['derived.timeline.refresh']",
            )
        )
        env = os.environ.copy()
        env["RELEASE_PROFILE"] = "JOURNAL_BASELINE"
        env["DEPLOYMENT_CAPABILITY_ALLOWLIST"] = ""
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

    def test_market_allowlist_alone_does_not_import_optional_handlers(self):
        backend_dir = Path(__file__).resolve().parents[1]
        script = "\n".join(
            (
                "import sys",
                "from database import Base, engine",
                "import models",
                "Base.metadata.create_all(bind=engine)",
                "import main",
                "forbidden = [",
                "    'routers.market',",
                "    'routers.position_market_analysis',",
                "    'services.market_data_service',",
                "    'services.providers.akshare_provider',",
                "    'services.providers.binance_provider',",
                "]",
                "loaded = [name for name in forbidden if name in sys.modules]",
                "assert loaded == [], loaded",
                "from fastapi.testclient import TestClient",
                "with TestClient(main.app) as client:",
                "    response = client.get('/api/market/quote/AAPL')",
                "assert response.status_code == 404, response.text",
                "assert response.json()['error']['code'] == 'FEATURE_DISABLED'",
                "loaded = [name for name in forbidden if name in sys.modules]",
                "assert loaded == [], loaded",
                "paths = main.app.openapi()['paths']",
                "assert not any(path.startswith('/api/market') for path in paths)",
                "assert '/api/positions/{position_id}/analyze' not in paths",
            )
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            database_path = Path(temp_dir) / "market-allowlist.db"
            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{database_path}"
            env["RELEASE_PROFILE"] = "JOURNAL_BASELINE"
            env["DEPLOYMENT_CAPABILITY_ALLOWLIST"] = "MARKET"
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
        self.ceiling_patch = patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            DeploymentCapabilityPolicy(frozenset()),
        )
        self.ceiling_patch.start()
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
        self.ceiling_patch.stop()
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
            ("patch", "/api/settings", {"ibkr_flex_query_id": secret}, "BROKER_SYNC"),
            ("patch", "/api/settings", {"ibkr_flex_token": secret}, "BROKER_SYNC"),
            (
                "patch",
                "/api/settings",
                {"ibkr_flex_start_date": "2026-07-17"},
                "BROKER_SYNC",
            ),
            ("patch", "/api/settings", {"binance_api_key": secret}, "BROKER_SYNC"),
            ("patch", "/api/settings", {"binance_api_secret": secret}, "BROKER_SYNC"),
            (
                "patch",
                "/api/settings",
                {"binance_market_type": "SPOT"},
                "BROKER_SYNC",
            ),
            (
                "patch",
                "/api/settings",
                {"binance_symbols": ["BTCUSDT"]},
                "BROKER_SYNC",
            ),
            ("patch", "/api/settings", {"finnhub_api_key": secret}, "MARKET"),
            (
                "patch",
                "/api/settings",
                {"llm_api_url": "https://llm.invalid/v1"},
                "AI_INSIGHTS",
            ),
            ("patch", "/api/settings", {"llm_api_key": secret}, "AI_INSIGHTS"),
            ("patch", "/api/settings", {"llm_model": "test-model"}, "AI_INSIGHTS"),
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

    def test_get_settings_projects_only_core_columns_when_optional_capabilities_are_disabled(self):
        secret = "must-not-be-loaded"
        db = self.SessionLocal()
        try:
            db.add(
                UserSettings(
                    user_id=self.user.id,
                    theme="dark",
                    up_color="RED",
                    display_currency="HKD",
                    ibkr_flex_query_id=secret,
                    ibkr_flex_token=secret,
                    ibkr_flex_start_date=date(2026, 7, 17),
                    binance_api_key=secret,
                    binance_api_secret=secret,
                    binance_market_type="SPOT",
                    binance_symbols=["BTCUSDT"],
                    finnhub_api_key=secret,
                    llm_api_url="https://llm.invalid/v1",
                    llm_api_key=secret,
                    llm_model="test-model",
                )
            )
            db.commit()
        finally:
            db.close()

        user_settings_selects: list[str] = []

        def capture_select(
            _conn,
            _cursor,
            statement,
            _parameters,
            _context,
            _executemany,
        ):
            normalized = statement.lower()
            if normalized.lstrip().startswith("select") and "user_settings" in normalized:
                user_settings_selects.append(normalized)

        event.listen(self.engine, "before_cursor_execute", capture_select)
        try:
            response = self.client.get("/api/settings")
        finally:
            event.remove(self.engine, "before_cursor_execute", capture_select)

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["theme"], "dark")
        self.assertEqual(payload["up_color"], "RED")
        self.assertEqual(payload["display_currency"], "USD")
        for field in (
            "ibkr_flex_query_id",
            "ibkr_flex_token",
            "ibkr_flex_start_date",
            "binance_api_key",
            "binance_market_type",
            "binance_symbols",
            "finnhub_api_key",
            "llm_api_url",
            "llm_model",
        ):
            self.assertNotIn(field, payload)
        self.assertNotIn("binance_api_secret_configured", payload)
        self.assertNotIn(secret, response.text)

        self.assertTrue(user_settings_selects)
        selected_sql = "\n".join(user_settings_selects)
        for column_name in (
            "ibkr_flex_query_id",
            "ibkr_flex_token",
            "ibkr_flex_start_date",
            "binance_api_key",
            "binance_api_secret",
            "binance_market_type",
            "binance_symbols",
            "finnhub_api_key",
            "llm_api_url",
            "llm_api_key",
            "llm_model",
        ):
            self.assertNotIn(column_name, selected_sql)

    def test_display_currency_is_usd_only_and_invalid_values_have_no_side_effects(self):
        for value in ("HKD", "CNY", "EUR", "GBP", None):
            with self.subTest(value=value):
                response = self.client.patch(
                    "/api/settings",
                    json={"display_currency": value, "theme": "dark"},
                )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(
                    response.json()["error"]["code"],
                    "VALIDATION_REQUEST_INVALID",
                )
                db = self.SessionLocal()
                try:
                    self.assertEqual(db.query(UserSettings).count(), 0)
                finally:
                    db.close()

        response = self.client.patch(
            "/api/settings",
            json={"display_currency": "USD", "theme": "dark"},
        )
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["display_currency"], "USD")
        db = self.SessionLocal()
        try:
            settings = db.query(UserSettings).one()
            self.assertEqual(settings.display_currency, "USD")
            self.assertEqual(settings.theme, "dark")
        finally:
            db.close()

    def test_allowlisted_settings_stay_core_only_without_runtime_rollout(self):
        secret = "runtime-disabled-secret"
        db = self.SessionLocal()
        try:
            db.add(
                UserSettings(
                    user_id=self.user.id,
                    theme="dark",
                    up_color="RED",
                    display_currency="USD",
                    ibkr_flex_token=secret,
                    finnhub_api_key=secret,
                    llm_api_url="https://runtime-disabled.invalid/v1",
                    llm_api_key=secret,
                    llm_model="runtime-disabled-model",
                )
            )
            db.commit()
        finally:
            db.close()

        enabled_policy = DeploymentCapabilityPolicy(
            frozenset(
                {
                    RuntimeCapability.BROKER_SYNC,
                    RuntimeCapability.MARKET,
                    RuntimeCapability.AI_INSIGHTS,
                }
            )
        )
        user_settings_selects: list[str] = []

        def capture_select(
            _conn,
            _cursor,
            statement,
            _parameters,
            _context,
            _executemany,
        ):
            normalized = statement.lower()
            if normalized.lstrip().startswith("select") and "user_settings" in normalized:
                user_settings_selects.append(normalized)

        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            enabled_policy,
        ):
            event.listen(self.engine, "before_cursor_execute", capture_select)
            try:
                response = self.client.get("/api/settings")
            finally:
                event.remove(self.engine, "before_cursor_execute", capture_select)

            rejected = self.client.patch(
                "/api/settings",
                json={"llm_model": "must-not-be-written"},
            )

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(
            set(response.json()),
            {"id", "user_id", "theme", "up_color", "display_currency"},
        )
        self.assertNotIn(secret, response.text)
        self.assertEqual(rejected.status_code, 404, rejected.text)
        self.assertEqual(rejected.json()["error"]["code"], "FEATURE_DISABLED")
        self.assertEqual(rejected.json()["detail"]["capability"], "AI_INSIGHTS")

        selected_sql = "\n".join(user_settings_selects)
        for column_name in (
            "ibkr_flex_token",
            "finnhub_api_key",
            "llm_api_url",
            "llm_api_key",
            "llm_model",
        ):
            self.assertNotIn(column_name, selected_sql)

        db = self.SessionLocal()
        try:
            settings = db.query(UserSettings).one()
            self.assertEqual(settings.llm_model, "runtime-disabled-model")
        finally:
            db.close()

    def test_enabled_optional_settings_keep_compatible_persistence_and_masking(self):
        enabled_policy = DeploymentCapabilityPolicy(
            frozenset(
                {
                    RuntimeCapability.BROKER_SYNC,
                    RuntimeCapability.MARKET,
                    RuntimeCapability.AI_INSIGHTS,
                }
            )
        )
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            enabled_policy,
        ):
            db = self.SessionLocal()
            try:
                db.add_all(
                    [
                        FeatureFlag(
                            key=capability_rollout_flag_key(capability),
                            enabled=True,
                            actor_targets=[],
                        )
                        for capability in (
                            RuntimeCapability.BROKER_SYNC,
                            RuntimeCapability.MARKET,
                            RuntimeCapability.AI_INSIGHTS,
                        )
                    ]
                )
                db.commit()
            finally:
                db.close()

            response = self.client.patch(
                "/api/settings",
                json={
                    "ibkr_flex_query_id": "query-123",
                    "ibkr_flex_token": "ibkr-secret-token",
                    "binance_api_key": "binance-api-key",
                    "binance_api_secret": "binance-api-secret",
                    "finnhub_api_key": "finnhub-api-key",
                    "llm_api_url": "https://llm.invalid/v1",
                    "llm_api_key": "llm-api-secret",
                    "llm_model": "test-model",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        payload = response.json()
        self.assertEqual(payload["ibkr_flex_query_id"], "query-123")
        self.assertEqual(payload["ibkr_flex_token"], "ibkr*********oken")
        self.assertEqual(payload["binance_api_key"], "bina*******-key")
        self.assertTrue(payload["binance_api_secret_configured"])
        self.assertEqual(payload["finnhub_api_key"], "finn*******-key")
        self.assertEqual(payload["llm_api_url"], "https://llm.invalid/v1")
        self.assertEqual(payload["llm_model"], "test-model")
        self.assertNotIn("llm-api-secret", response.text)

        db = self.SessionLocal()
        try:
            settings = db.query(UserSettings).one()
            self.assertEqual(settings.ibkr_flex_token, "ibkr-secret-token")
            self.assertEqual(settings.binance_api_secret, "binance-api-secret")
            self.assertEqual(settings.finnhub_api_key, "finnhub-api-key")
            self.assertEqual(settings.llm_api_key, "llm-api-secret")
        finally:
            db.close()

    def test_invalid_optional_secret_payload_does_not_echo_validation_input(self):
        secret = "nested-short-secret"

        response = self.client.patch(
            "/api/settings",
            json={"ibkr_flex_token": {"secret": secret}},
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_REQUEST_INVALID")
        self.assertNotIn(secret, response.text)
        self.assertNotIn('"input"', response.text)

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
