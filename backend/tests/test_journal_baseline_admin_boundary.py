from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import create_app
from models import IntegrationCredential, PlatformSetting, SystemSetting, User
from release_profile import ReleaseProfile
from routers.admin import get_current_admin
from services.credential_service import decrypt_secret, encrypt_secret


class JournalBaselineAdminBoundaryTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
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
            self.admin = User(
                email="admin-boundary@example.com",
                email_normalized="admin-boundary@example.com",
                hashed_password="hashed",
                public_id="admin-boundary-public-id",
                status="ACTIVE",
                is_active=True,
                role="admin",
            )
            db.add(self.admin)
            db.commit()
        finally:
            db.close()

        self._clients: list[TestClient] = []
        self._apps = []

    def tearDown(self):
        for client in self._clients:
            client.close()
        for app in self._apps:
            app.dependency_overrides.clear()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _client(self, profile: ReleaseProfile) -> TestClient:
        app = create_app(profile)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_admin] = lambda: self.admin
        client = TestClient(app, raise_server_exceptions=False)
        self._apps.append(app)
        self._clients.append(client)
        return client

    def _row_counts(self) -> tuple[int, int, int]:
        db = self.SessionLocal()
        try:
            return (
                db.query(SystemSetting).count(),
                db.query(PlatformSetting).count(),
                db.query(IntegrationCredential).count(),
            )
        finally:
            db.close()

    def _seed_settings_and_credentials(self, *, malformed_optional: bool = False) -> None:
        db = self.SessionLocal()
        try:
            optional_ciphertext = (
                "must-not-be-decrypted"
                if malformed_optional
                else encrypt_secret("optional-provider-secret")
            )
            db.add_all(
                [
                    SystemSetting(key="site_name", value="Trading Noobs"),
                    SystemSetting(key="ibkr_flex_query_id", value="query-legacy"),
                    SystemSetting(key="FINNHUB-API-TOKEN", value="short-market-secret"),
                    PlatformSetting(key="llm_model", value="gpt-5"),
                    PlatformSetting(key="prod_ibkr_flex_password", value="broker-secret"),
                    PlatformSetting(key="finnhub_api_key", value="market-secret"),
                    IntegrationCredential(
                        provider_key="openai",
                        credential_key="api_key",
                        secret_ciphertext=encrypt_secret("safe-llm-secret"),
                        is_active=True,
                    ),
                    IntegrationCredential(
                        provider_key="IBKR-Flex",
                        credential_key="api_key",
                        secret_ciphertext=optional_ciphertext,
                        is_active=True,
                    ),
                    IntegrationCredential(
                        provider_key="custom",
                        credential_key="finnhub_api_token",
                        secret_ciphertext=optional_ciphertext,
                        is_active=True,
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

    def test_alias_writes_fail_closed_without_persistence(self):
        client = self._client(ReleaseProfile.JOURNAL_BASELINE)

        self.assertEqual(
            client.put(
                "/api/admin/platform/settings/llm_model",
                json={"value": "gpt-5"},
            ).status_code,
            200,
        )
        self.assertEqual(
            client.put(
                "/api/admin/platform/integrations/openai/api_key",
                json={"secret_value": "safe-llm-secret"},
            ).status_code,
            200,
        )
        self.assertEqual(
            client.put(
                "/api/admin/settings/ordinary_retention_days",
                json={"value": "30"},
            ).status_code,
            200,
        )
        baseline_counts = self._row_counts()
        blocked_requests = (
            (
                "/api/admin/settings/prefix-IBKR-flex-password-suffix",
                {"value": "broker-secret"},
                "BROKER_SYNC",
            ),
            (
                "/api/admin/platform/settings/FINNHUB-API-TOKEN",
                {"value": "market-secret"},
                "MARKET",
            ),
            (
                "/api/admin/platform/settings/prod_y-finance_api_key",
                {"value": "market-secret"},
                "MARKET",
            ),
            (
                "/api/admin/platform/integrations/ibkr-flex/api_key",
                {"secret_value": "broker-secret"},
                "BROKER_SYNC",
            ),
            (
                "/api/admin/platform/integrations/finnhub-prod/api_key",
                {"secret_value": "market-secret"},
                "MARKET",
            ),
            (
                "/api/admin/platform/integrations/custom/BINANCE_API_SECRET",
                {"secret_value": "broker-secret"},
                "BROKER_SYNC",
            ),
        )

        for path, body, capability in blocked_requests:
            with self.subTest(path=path):
                response = client.put(path, json=body)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
                self.assertEqual(response.json()["detail"]["capability"], capability)
                self.assertNotIn(body[next(iter(body))], response.text)
                self.assertEqual(self._row_counts(), baseline_counts)

    def test_baseline_lists_filter_optional_rows_before_decryption(self):
        self._seed_settings_and_credentials(malformed_optional=True)
        client = self._client(ReleaseProfile.JOURNAL_BASELINE)

        with patch("routers.admin.decrypt_secret", wraps=decrypt_secret) as decrypt:
            system_response = client.get("/api/admin/settings")
            platform_response = client.get("/api/admin/platform/settings")
            integration_response = client.get("/api/admin/platform/integrations")
            summary_response = client.get("/api/admin/ops/summary")

        self.assertEqual(system_response.status_code, 200)
        self.assertEqual(
            [item["key"] for item in system_response.json()],
            ["site_name"],
        )
        self.assertEqual(platform_response.status_code, 200)
        self.assertEqual(
            [item["key"] for item in platform_response.json()],
            ["llm_model"],
        )
        self.assertEqual(integration_response.status_code, 200)
        self.assertEqual(
            [item["provider_key"] for item in integration_response.json()],
            ["openai"],
        )
        self.assertEqual(summary_response.status_code, 200)
        summary = summary_response.json()
        self.assertEqual(summary["platform_setting_count"], 1)
        self.assertEqual(summary["configured_integration_count"], 1)
        self.assertEqual(summary["active_integration_count"], 1)
        self.assertEqual(decrypt.call_count, 2)

        serialized = "".join(
            response.text
            for response in (
                system_response,
                platform_response,
                integration_response,
                summary_response,
            )
        )
        for forbidden in (
            "query-legacy",
            "short-market-secret",
            "broker-secret",
            "market-secret",
            "IBKR-Flex",
            "finnhub_api_token",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_alias_active_update_is_blocked_without_mutation(self):
        self._seed_settings_and_credentials()
        client = self._client(ReleaseProfile.JOURNAL_BASELINE)

        response = client.patch(
            "/api/admin/platform/integrations/IBKR-Flex/api_key/active",
            json={"is_active": False},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
        db = self.SessionLocal()
        try:
            credential = (
                db.query(IntegrationCredential)
                .filter(
                    IntegrationCredential.provider_key == "IBKR-Flex",
                    IntegrationCredential.credential_key == "api_key",
                )
                .one()
            )
            self.assertTrue(credential.is_active)
        finally:
            db.close()

    def test_development_full_preserves_optional_and_ordinary_admin_controls(self):
        self._seed_settings_and_credentials()
        client = self._client(ReleaseProfile.DEVELOPMENT_FULL)

        system_response = client.get("/api/admin/settings")
        platform_response = client.get("/api/admin/platform/settings")
        integration_response = client.get("/api/admin/platform/integrations")
        self.assertEqual(system_response.status_code, 200)
        self.assertEqual(len(system_response.json()), 3)
        self.assertEqual(platform_response.status_code, 200)
        self.assertEqual(len(platform_response.json()), 3)
        self.assertEqual(integration_response.status_code, 200)
        self.assertEqual(len(integration_response.json()), 3)

        setting_response = client.put(
            "/api/admin/platform/settings/finnhub-prod-api-token",
            json={"value": "replacement-market-secret"},
        )
        credential_response = client.put(
            "/api/admin/platform/integrations/ibkr-flex/flex_token",
            json={"secret_value": "replacement-broker-secret"},
        )
        active_response = client.patch(
            "/api/admin/platform/integrations/IBKR-Flex/api_key/active",
            json={"is_active": False},
        )
        ordinary_response = client.put(
            "/api/admin/settings/ordinary_retention_days",
            json={"value": "30"},
        )
        system_optional_response = client.put(
            "/api/admin/settings/ibkr_flex_password",
            json={"value": "replacement-broker-secret"},
        )

        self.assertEqual(setting_response.status_code, 200)
        self.assertEqual(credential_response.status_code, 200)
        self.assertEqual(active_response.status_code, 200)
        self.assertFalse(active_response.json()["is_active"])
        self.assertEqual(ordinary_response.status_code, 200)
        self.assertEqual(system_optional_response.status_code, 200)

    def test_invalid_optional_secret_payload_is_sanitized_before_response(self):
        client = self._client(ReleaseProfile.JOURNAL_BASELINE)
        baseline_counts = self._row_counts()
        requests = (
            (
                "/api/admin/platform/integrations/ibkr/flex_token",
                {"secret_value": {"secret": "shrt"}},
            ),
            (
                "/api/admin/platform/settings/finnhub_api_key",
                {"value": {"secret": "shrt"}},
            ),
            (
                "/api/admin/settings/binance_api_secret",
                {"value": {"secret": "shrt"}},
            ),
        )

        for path, body in requests:
            with self.subTest(path=path):
                response = client.put(path, json=body)
                self.assertEqual(response.status_code, 422)
                self.assertNotIn("shrt", response.text)
                self.assertNotIn('"input"', response.text)
                self.assertNotIn('"ctx"', response.text)
                self.assertEqual(self._row_counts(), baseline_counts)


if __name__ == "__main__":
    unittest.main()
