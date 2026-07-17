from __future__ import annotations

import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import create_app
from models import (
    BusinessLock,
    BusinessLockStatus,
    FeatureFlag,
    IntegrationCredential,
    JobDefinition,
    JobRun,
    JobRunEvent,
    JobRunStatus,
    PlatformSetting,
    SystemSetting,
    User,
)
from release_profile import (
    DeploymentCapabilityPolicy,
    OPTIONAL_RUNTIME_CAPABILITIES,
    ReleaseProfile,
)
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
        self._policy_patches = []

    def tearDown(self):
        for client in self._clients:
            client.close()
        for app in self._apps:
            app.dependency_overrides.clear()
        for policy_patch in reversed(self._policy_patches):
            policy_patch.stop()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _client(self, *, allow_optional: bool) -> TestClient:
        allowed = OPTIONAL_RUNTIME_CAPABILITIES if allow_optional else frozenset()
        policy_patch = patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            DeploymentCapabilityPolicy(frozenset(allowed)),
        )
        policy_patch.start()
        self._policy_patches.append(policy_patch)
        app = create_app(ReleaseProfile.JOURNAL_BASELINE)

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
        client = self._client(allow_optional=False)

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
                "/api/admin/platform/settings/llm_model",
                {"value": "gpt-5"},
                "AI_INSIGHTS",
            ),
            (
                "/api/admin/platform/integrations/openai/api_key",
                {"secret_value": "safe-llm-secret"},
                "AI_INSIGHTS",
            ),
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
        )

        for path, body, capability in blocked_requests:
            with self.subTest(path=path):
                response = client.put(path, json=body)
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
                self.assertEqual(response.json()["detail"]["capability"], capability)
                self.assertNotIn(body[next(iter(body))], response.text)
                self.assertEqual(self._row_counts(), baseline_counts)

    def test_empty_ceiling_hides_registered_and_unknown_secrets_before_decryption(self):
        registered_providers = (
            "anthropic",
            "deepseek",
            "gemini",
            "groq",
            "polygon",
            "yfinance",
            "alphavantage",
            "akshare",
        )
        db = self.SessionLocal()
        try:
            db.add_all(
                [
                    SystemSetting(key="site_name", value="Trading Noobs"),
                    SystemSetting(key="smtp_password", value="system-secret-sentinel"),
                    PlatformSetting(key="retention_days", value="30"),
                    PlatformSetting(key="custom_api_key", value="platform-secret-sentinel"),
                    *[
                        IntegrationCredential(
                            provider_key=provider_key,
                            credential_key="api_key",
                            secret_ciphertext="invalid-ciphertext-must-not-be-decrypted",
                            is_active=True,
                        )
                        for provider_key in registered_providers
                    ],
                    IntegrationCredential(
                        provider_key="custom-vendor",
                        credential_key="api_key",
                        secret_ciphertext="unknown-secret-must-not-be-decrypted",
                        is_active=True,
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        client = self._client(allow_optional=False)
        with patch(
            "routers.admin.decrypt_secret",
            side_effect=AssertionError("hidden credentials must not be decrypted"),
        ) as decrypt:
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
            ["retention_days"],
        )
        self.assertEqual(integration_response.status_code, 200)
        self.assertEqual(integration_response.json(), [])
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["platform_setting_count"], 1)
        self.assertEqual(summary_response.json()["configured_integration_count"], 0)
        self.assertEqual(summary_response.json()["active_integration_count"], 0)
        decrypt.assert_not_called()

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
            "smtp_password",
            "system-secret-sentinel",
            "custom_api_key",
            "platform-secret-sentinel",
            "custom-vendor",
            "unknown-secret-must-not-be-decrypted",
            *registered_providers,
        ):
            self.assertNotIn(forbidden, serialized)

    def test_expanded_registered_provider_writes_follow_capability_ceiling(self):
        client = self._client(allow_optional=False)
        baseline_counts = self._row_counts()
        provider_capabilities = {
            "anthropic": "AI_INSIGHTS",
            "deepseek": "AI_INSIGHTS",
            "gemini": "AI_INSIGHTS",
            "groq": "AI_INSIGHTS",
            "polygon": "MARKET",
            "yfinance": "MARKET",
            "alphavantage": "MARKET",
            "akshare": "MARKET",
        }

        for provider_key, capability in provider_capabilities.items():
            with self.subTest(provider_key=provider_key):
                response = client.put(
                    f"/api/admin/platform/integrations/{provider_key}/api_key",
                    json={"secret_value": f"{provider_key}-secret-sentinel"},
                )
                self.assertEqual(response.status_code, 404)
                self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
                self.assertEqual(response.json()["detail"]["capability"], capability)
                self.assertNotIn(f"{provider_key}-secret-sentinel", response.text)
                self.assertEqual(self._row_counts(), baseline_counts)

    def test_full_allowlist_preserves_registered_provider_compatibility(self):
        client = self._client(allow_optional=True)
        providers = (
            "anthropic",
            "deepseek",
            "gemini",
            "groq",
            "polygon",
            "yfinance",
            "alphavantage",
            "akshare",
        )

        for provider_key in providers:
            with self.subTest(provider_key=provider_key):
                response = client.put(
                    f"/api/admin/platform/integrations/{provider_key}/api_key",
                    json={"secret_value": f"{provider_key}-configured-secret"},
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.json()["is_configured"])
                self.assertNotIn(f"{provider_key}-configured-secret", response.text)

        for path in (
            "/api/admin/settings/anthropic_api_key",
            "/api/admin/platform/settings/polygon_access_token",
        ):
            with self.subTest(path=path):
                response = client.put(path, json={"value": "registered-secret-value"})
                self.assertEqual(response.status_code, 200)

        list_response = client.get("/api/admin/platform/integrations")
        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            {item["provider_key"] for item in list_response.json()},
            set(providers),
        )

    def test_unknown_secret_controls_fail_closed_with_stable_contract(self):
        db = self.SessionLocal()
        try:
            db.add_all(
                [
                    SystemSetting(key="smtp_password", value="original-system-secret"),
                    PlatformSetting(key="custom_api_key", value="original-platform-secret"),
                    PlatformSetting(key="aws_access_key_id", value="original-aws-credential"),
                    PlatformSetting(key="service_account_key", value="original-service-credential"),
                    PlatformSetting(key="signing_key", value="original-signing-credential"),
                    IntegrationCredential(
                        provider_key="custom-vendor",
                        credential_key="api_key",
                        secret_ciphertext="must-not-be-decrypted",
                        is_active=True,
                    ),
                    IntegrationCredential(
                        provider_key="openai-evil",
                        credential_key="api_key",
                        secret_ciphertext="prefix-spoof-must-not-be-decrypted",
                        is_active=True,
                    ),
                    IntegrationCredential(
                        provider_key="openai",
                        credential_key="client_secret",
                        secret_ciphertext="unknown-key-must-not-be-decrypted",
                        is_active=True,
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        for allow_optional in (False, True):
            client = self._client(allow_optional=allow_optional)
            requests = (
                (
                    "PUT",
                    "/api/admin/settings/smtp_password",
                    {"value": "new-system-secret-sentinel"},
                ),
                (
                    "PUT",
                    "/api/admin/settings/smtppassword",
                    {"value": "compact-secret-name-sentinel"},
                ),
                (
                    "PUT",
                    "/api/admin/platform/settings/custom_api_key",
                    {"value": "new-platform-secret-sentinel"},
                ),
                (
                    "PUT",
                    "/api/admin/platform/settings/notopenai_api_key",
                    {"value": "provider-name-spoof-secret-sentinel"},
                ),
                (
                    "PUT",
                    "/api/admin/platform/settings/aws_access_key_id",
                    {"value": "aws-credential-sentinel"},
                ),
                (
                    "PUT",
                    "/api/admin/platform/settings/service_account_key",
                    {"value": "service-account-credential-sentinel"},
                ),
                (
                    "PUT",
                    "/api/admin/platform/settings/signing_key",
                    {"value": "signing-credential-sentinel"},
                ),
                (
                    "PUT",
                    "/api/admin/platform/integrations/custom-vendor/api_key",
                    {"secret_value": "new-integration-secret-sentinel"},
                ),
                (
                    "PUT",
                    "/api/admin/platform/integrations/openai-evil/api_key",
                    {"secret_value": "provider-prefix-spoof-secret-sentinel"},
                ),
                (
                    "PUT",
                    "/api/admin/platform/integrations/openai/client_secret",
                    {"secret_value": "unknown-credential-key-secret-sentinel"},
                ),
                (
                    "PATCH",
                    "/api/admin/platform/integrations/custom-vendor/api_key/active",
                    {"is_active": False},
                ),
                (
                    "PUT",
                    "/api/admin/platform/integrations/custom/BINANCE_API_SECRET",
                    {"secret_value": "credential-key-spoof-secret-sentinel"},
                ),
            )

            with patch(
                "routers.admin.decrypt_secret",
                side_effect=AssertionError("unknown credentials must not be decrypted"),
            ) as decrypt:
                responses = [
                    client.request(method, path, json=body)
                    for method, path, body in requests
                ]
                list_response = client.get("/api/admin/platform/integrations")
                system_list_response = client.get("/api/admin/settings")
                platform_list_response = client.get("/api/admin/platform/settings")

            for response in responses:
                with self.subTest(
                    allow_optional=allow_optional,
                    response=response.request.url.path,
                ):
                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(
                        response.json()["error"]["code"],
                        "SECRET_CONFIGURATION_UNAVAILABLE",
                    )
                    self.assertEqual(
                        response.json()["detail"],
                        {
                            "code": "SECRET_CONFIGURATION_UNAVAILABLE",
                            "message": "Secret configuration is unavailable",
                        },
                    )
                    self.assertNotIn("sentinel", response.text)

            self.assertEqual(list_response.status_code, 200)
            self.assertNotIn("custom-vendor", list_response.text)
            self.assertNotIn("must-not-be-decrypted", list_response.text)
            self.assertNotIn("openai-evil", list_response.text)
            self.assertNotIn("prefix-spoof-must-not-be-decrypted", list_response.text)
            self.assertNotIn("client_secret", list_response.text)
            self.assertNotIn("unknown-key-must-not-be-decrypted", list_response.text)
            self.assertEqual(system_list_response.status_code, 200)
            self.assertNotIn("smtp_password", system_list_response.text)
            self.assertNotIn("original-system-secret", system_list_response.text)
            self.assertEqual(platform_list_response.status_code, 200)
            self.assertNotIn("custom_api_key", platform_list_response.text)
            self.assertNotIn("original-platform-secret", platform_list_response.text)
            self.assertNotIn("aws_access_key_id", platform_list_response.text)
            self.assertNotIn("original-aws-credential", platform_list_response.text)
            self.assertNotIn("service_account_key", platform_list_response.text)
            self.assertNotIn("original-service-credential", platform_list_response.text)
            self.assertNotIn("signing_key", platform_list_response.text)
            self.assertNotIn("original-signing-credential", platform_list_response.text)
            decrypt.assert_not_called()

        db = self.SessionLocal()
        try:
            self.assertEqual(
                db.query(SystemSetting).filter(SystemSetting.key == "smtp_password").one().value,
                "original-system-secret",
            )
            self.assertEqual(
                db.query(PlatformSetting).filter(PlatformSetting.key == "custom_api_key").one().value,
                "original-platform-secret",
            )
            credential = (
                db.query(IntegrationCredential)
                .filter(IntegrationCredential.provider_key == "custom-vendor")
                .one()
            )
            self.assertEqual(credential.secret_ciphertext, "must-not-be-decrypted")
            self.assertTrue(credential.is_active)
            self.assertEqual(db.query(IntegrationCredential).count(), 3)
        finally:
            db.close()

    def test_malformed_secret_json_uses_sanitized_validation_contract(self):
        client = self._client(allow_optional=False)
        baseline_counts = self._row_counts()
        secret_sentinel = "malformed-json-secret-sentinel"

        for path in (
            "/api/admin/platform/integrations/custom-vendor/api_key",
            "/api/admin/platform/settings/custom_api_key",
            "/api/admin/settings/smtp_password",
        ):
            with self.subTest(path=path):
                response = client.put(
                    path,
                    content=f'{{"secret_value":"{secret_sentinel}"',
                    headers={"content-type": "application/json"},
                )
                self.assertEqual(response.status_code, 422)
                self.assertEqual(
                    response.json()["error"]["code"],
                    "VALIDATION_REQUEST_INVALID",
                )
                self.assertNotIn(secret_sentinel, response.text)
                self.assertNotIn('"input"', response.text)
                self.assertNotIn('"ctx"', response.text)
                self.assertEqual(self._row_counts(), baseline_counts)

    def test_reserved_capability_and_deployment_keys_fail_closed(self):
        db = self.SessionLocal()
        try:
            db.add_all(
                [
                    SystemSetting(
                        key="DEPLOYMENT_CAPABILITY_ALLOWLIST",
                        value="MARKET",
                    ),
                    PlatformSetting(key="release_profile", value="DEVELOPMENT_FULL"),
                    FeatureFlag(
                        key="capability.unknown.v1",
                        enabled=True,
                    ),
                    FeatureFlag(
                        key="deployment_capability_allowlist",
                        enabled=True,
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        requests = (
            ("/api/admin/settings/DEPLOYMENT_CAPABILITY_ALLOWLIST", {"value": "MARKET"}),
            ("/api/admin/platform/settings/release_profile", {"value": "DEVELOPMENT_FULL"}),
            ("/api/admin/platform/settings/capability.market.v1", {"value": "true"}),
            ("/api/admin/platform/feature-flags/deployment_capability_allowlist", {"enabled": True}),
            ("/api/admin/platform/feature-flags/capability.market.v2", {"enabled": True}),
            ("/api/admin/platform/feature-flags/capability.unknown.v1", {"enabled": True}),
            ("/api/admin/platform/feature-flags/CAPABILITY.market.v1", {"enabled": True}),
        )

        for allow_optional in (False, True):
            client = self._client(allow_optional=allow_optional)
            baseline_counts = self._row_counts()
            for path, body in requests:
                with self.subTest(allow_optional=allow_optional, path=path):
                    response = client.put(path, json=body)
                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(
                        response.json()["error"]["code"],
                        "CONFIGURATION_KEY_UNAVAILABLE",
                    )
                    self.assertEqual(self._row_counts(), baseline_counts)

            serialized = "".join(
                (
                    client.get("/api/admin/settings").text,
                    client.get("/api/admin/platform/settings").text,
                    client.get("/api/admin/platform/feature-flags").text,
                )
            )
            for forbidden in (
                "DEPLOYMENT_CAPABILITY_ALLOWLIST",
                "DEVELOPMENT_FULL",
                "capability.unknown.v1",
                "deployment_capability_allowlist",
            ):
                self.assertNotIn(forbidden, serialized)

    def test_baseline_lists_filter_optional_rows_before_decryption(self):
        self._seed_settings_and_credentials(malformed_optional=True)
        client = self._client(allow_optional=False)

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
        self.assertEqual(platform_response.json(), [])
        self.assertEqual(integration_response.status_code, 200)
        self.assertEqual(integration_response.json(), [])
        self.assertEqual(summary_response.status_code, 200)
        summary = summary_response.json()
        self.assertEqual(summary["platform_setting_count"], 0)
        self.assertEqual(summary["configured_integration_count"], 0)
        self.assertEqual(summary["active_integration_count"], 0)
        self.assertEqual(decrypt.call_count, 0)

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
            "openai",
            "gpt-5",
        ):
            self.assertNotIn(forbidden, serialized)

    def test_baseline_job_reads_filter_optional_rows_before_json_deserialization(self):
        db = self.SessionLocal()
        try:
            ordinary_definition = JobDefinition(
                key="derived.timeline.refresh",
                display_name="Refresh Timeline",
                queue_name="derived",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            market_definition = JobDefinition(
                key="market.quote.refresh",
                display_name="Refresh Market Quote",
                queue_name="market",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            broker_definition = JobDefinition(
                key="broker.sync.pull",
                display_name="Pull Broker Executions",
                queue_name="broker",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            ai_definition = JobDefinition(
                key="ai.insight.generate",
                display_name="Generate AI Insight",
                queue_name="ai",
                retry_policy={"max_attempts": 3},
                timeout_seconds=300,
                is_active=True,
            )
            db.add_all(
                [
                    ordinary_definition,
                    market_definition,
                    broker_definition,
                    ai_definition,
                ]
            )
            db.flush()
            db.add_all(
                [
                    JobRun(
                        job_definition_id=ordinary_definition.id,
                        public_id="ordinary-job",
                        status=JobRunStatus.SUCCEEDED,
                        payload={"position_event_public_id": "event-1"},
                        result={"refreshed": True},
                        max_attempts=3,
                        attempt_count=1,
                        queue_name="derived",
                    ),
                    JobRun(
                        job_definition_id=market_definition.id,
                        public_id="optional-market-failed",
                        idempotency_key="optional-provider-secret-market-key",
                        status=JobRunStatus.FAILED,
                        payload={"secret": "optional-provider-secret-market-payload"},
                        result={"secret": "optional-provider-secret-market-result"},
                        error_message="optional-provider-secret-market-error",
                        max_attempts=3,
                        attempt_count=3,
                        queue_name="market",
                    ),
                    JobRun(
                        job_definition_id=market_definition.id,
                        public_id="optional-market-running",
                        status=JobRunStatus.RUNNING,
                        payload={"secret": "optional-provider-secret-running-payload"},
                        result={"secret": "optional-provider-secret-running-result"},
                        error_message="optional-provider-secret-running-error",
                        max_attempts=3,
                        attempt_count=1,
                        queue_name="market",
                        locked_by="legacy-market-worker",
                        locked_at=datetime.now(timezone.utc) - timedelta(hours=2),
                        started_at=datetime.now(timezone.utc) - timedelta(hours=2),
                    ),
                    JobRun(
                        job_definition_id=broker_definition.id,
                        public_id="optional-broker-failed",
                        status=JobRunStatus.FAILED,
                        payload={"secret": "optional-provider-secret-broker-payload"},
                        result={"secret": "optional-provider-secret-broker-result"},
                        error_message="optional-provider-secret-broker-error",
                        max_attempts=3,
                        attempt_count=2,
                        queue_name="broker",
                    ),
                    JobRun(
                        job_definition_id=ai_definition.id,
                        public_id="optional-ai-failed",
                        status=JobRunStatus.FAILED,
                        payload={"secret": "optional-provider-secret-ai-payload"},
                        result={"secret": "optional-provider-secret-ai-result"},
                        error_message="optional-provider-secret-ai-error",
                        max_attempts=3,
                        attempt_count=2,
                        queue_name="ai",
                    ),
                    BusinessLock(
                        scope="derived.timeline.refresh",
                        resource_key="ordinary-resource",
                        owner_id="ordinary-job",
                        owner_type="job_run",
                        status=BusinessLockStatus.ACTIVE,
                        metadata_json={"kind": "ordinary"},
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    ),
                    BusinessLock(
                        scope="market.quote.refresh",
                        resource_key="optional-market-resource",
                        owner_id="optional-market-running",
                        owner_type="job_run",
                        status=BusinessLockStatus.ACTIVE,
                        metadata_json={"secret": "optional-provider-secret-market-lock"},
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    ),
                    BusinessLock(
                        scope="broker.sync.pull",
                        resource_key="optional-broker-resource",
                        owner_id="optional-broker-failed",
                        owner_type="job_run",
                        status=BusinessLockStatus.EXPIRED,
                        metadata_json={"secret": "optional-provider-secret-broker-lock"},
                        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                    ),
                    BusinessLock(
                        scope="import.session.confirm",
                        resource_key="non-job-active-resource",
                        owner_id="import-session-1",
                        owner_type="import_session",
                        status=BusinessLockStatus.ACTIVE,
                        metadata_json={"kind": "non-job"},
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    ),
                    BusinessLock(
                        scope="import.session.expired",
                        resource_key="non-job-expired-resource",
                        owner_id="import-session-2",
                        owner_type="import_session",
                        status=BusinessLockStatus.EXPIRED,
                        metadata_json={"kind": "non-job"},
                        expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                    ),
                    BusinessLock(
                        scope="orphan.job.cleanup",
                        resource_key="orphan-job-resource",
                        owner_id="missing-job-public-id",
                        owner_type="job_run",
                        status=BusinessLockStatus.ACTIVE,
                        metadata_json={"kind": "orphan"},
                        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE job_runs "
                    "SET payload = :invalid_payload, result = :invalid_result "
                    "WHERE public_id LIKE 'optional-%'"
                ),
                {
                    "invalid_payload": "optional-provider-secret-invalid-payload{",
                    "invalid_result": "optional-provider-secret-invalid-result{",
                },
            )
            connection.execute(
                text(
                    "UPDATE business_locks "
                    "SET metadata = :invalid_metadata "
                    "WHERE owner_id LIKE 'optional-%'"
                ),
                {
                    "invalid_metadata": "optional-provider-secret-invalid-lock{",
                },
            )

        client = self._client(allow_optional=False)
        list_response = client.get("/api/admin/jobs")
        market_list_response = client.get("/api/admin/jobs?queue_name=market")
        summary_response = client.get("/api/admin/ops/summary")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(list_response.json()["total"], 1)
        self.assertEqual(
            [item["public_id"] for item in list_response.json()["items"]],
            ["ordinary-job"],
        )
        self.assertEqual(market_list_response.status_code, 200)
        self.assertEqual(market_list_response.json()["total"], 0)
        self.assertEqual(market_list_response.json()["items"], [])
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["job_counts"]["SUCCEEDED"], 1)
        self.assertEqual(summary_response.json()["job_counts"]["FAILED"], 0)
        self.assertEqual(summary_response.json()["job_counts"]["RUNNING"], 0)
        self.assertEqual(summary_response.json()["stale_running_job_count"], 0)
        self.assertEqual(summary_response.json()["active_business_lock_count"], 3)
        self.assertEqual(summary_response.json()["expired_business_lock_count"], 1)

        blocked_jobs = (
            ("optional-market-failed", "MARKET"),
            ("optional-broker-failed", "BROKER_SYNC"),
            ("optional-ai-failed", "AI_INSIGHTS"),
        )
        blocked_responses = [list_response, market_list_response, summary_response]
        for public_id, capability in blocked_jobs:
            with self.subTest(public_id=public_id):
                detail_response = client.get(f"/api/admin/jobs/{public_id}")
                requeue_response = client.post(
                    f"/api/admin/jobs/{public_id}/requeue"
                )
                cancel_response = client.post(
                    f"/api/admin/jobs/{public_id}/cancel"
                )
                for response in (
                    detail_response,
                    requeue_response,
                    cancel_response,
                ):
                    self.assertEqual(response.status_code, 404)
                    self.assertEqual(
                        response.json()["error"]["code"],
                        "FEATURE_DISABLED",
                    )
                    self.assertEqual(
                        response.json()["detail"]["capability"],
                        capability,
                    )
                    blocked_responses.append(response)

        force_cancel_response = client.post(
            "/api/admin/jobs/optional-market-running/force-cancel"
        )
        self.assertEqual(force_cancel_response.status_code, 404)
        self.assertEqual(
            force_cancel_response.json()["error"]["code"],
            "FEATURE_DISABLED",
        )
        blocked_responses.append(force_cancel_response)

        serialized = "".join(response.text for response in blocked_responses)
        self.assertNotIn("optional-provider-secret", serialized)

        db = self.SessionLocal()
        try:
            states = {
                public_id: (status_value, attempt_count, locked_by)
                for public_id, status_value, attempt_count, locked_by in db.query(
                    JobRun.public_id,
                    JobRun.status,
                    JobRun.attempt_count,
                    JobRun.locked_by,
                )
                .filter(JobRun.public_id.like("optional-%"))
                .all()
            }
            self.assertEqual(
                states["optional-market-failed"],
                (JobRunStatus.FAILED, 3, None),
            )
            self.assertEqual(
                states["optional-broker-failed"],
                (JobRunStatus.FAILED, 2, None),
            )
            self.assertEqual(
                states["optional-ai-failed"],
                (JobRunStatus.FAILED, 2, None),
            )
            self.assertEqual(
                states["optional-market-running"],
                (JobRunStatus.RUNNING, 1, "legacy-market-worker"),
            )
            self.assertEqual(db.query(JobRunEvent).count(), 0)
        finally:
            db.close()

    def test_baseline_feature_flags_filter_rollout_rows_before_json_deserialization(self):
        db = self.SessionLocal()
        try:
            db.add_all(
                [
                    FeatureFlag(
                        key="ordinary_timeline_experiment",
                        enabled=True,
                        actor_targets=["ordinary-user"],
                        description="Ordinary feature flag",
                    ),
                    FeatureFlag(
                        key="capability.market.v1",
                        enabled=True,
                        actor_targets=["optional-provider-secret-market-target"],
                        description="optional-provider-secret-market-description",
                    ),
                    FeatureFlag(
                        key="capability.broker_sync.v1",
                        enabled=True,
                        actor_targets=["optional-provider-secret-broker-target"],
                        description="optional-provider-secret-broker-description",
                    ),
                    FeatureFlag(
                        key="capability.ai_insights.v1",
                        enabled=False,
                        actor_targets=["optional-provider-secret-ai-target"],
                        expires_at=datetime.now(timezone.utc) - timedelta(days=1),
                        description="optional-provider-secret-ai-description",
                    ),
                    FeatureFlag(
                        key="capability.unknown.v9",
                        enabled=True,
                        actor_targets=["optional-provider-secret-unknown-target"],
                        description="optional-provider-secret-unknown-description",
                    ),
                ]
            )
            db.commit()
        finally:
            db.close()

        with self.engine.begin() as connection:
            connection.execute(
                text(
                    "UPDATE feature_flags "
                    "SET actor_targets = :invalid_targets "
                    "WHERE key LIKE 'capability.%'"
                ),
                {
                    "invalid_targets": "optional-provider-secret-invalid-targets{",
                },
            )

        client = self._client(allow_optional=False)
        list_response = client.get("/api/admin/platform/feature-flags")
        summary_response = client.get("/api/admin/ops/summary")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(
            [item["key"] for item in list_response.json()],
            ["ordinary_timeline_experiment"],
        )
        self.assertEqual(summary_response.status_code, 200)
        self.assertEqual(summary_response.json()["enabled_feature_flag_count"], 1)
        self.assertEqual(summary_response.json()["expired_feature_flag_count"], 0)
        serialized = list_response.text + summary_response.text
        self.assertNotIn("optional-provider-secret", serialized)
        self.assertNotIn("capability.market.v1", serialized)
        self.assertNotIn("capability.broker_sync.v1", serialized)
        self.assertNotIn("capability.ai_insights.v1", serialized)
        self.assertNotIn("capability.unknown.v9", serialized)

    def test_alias_active_update_is_blocked_without_mutation(self):
        self._seed_settings_and_credentials()
        client = self._client(allow_optional=False)

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

    def test_full_deployment_allowlist_preserves_optional_and_ordinary_admin_controls(self):
        self._seed_settings_and_credentials()
        client = self._client(allow_optional=True)

        system_response = client.get("/api/admin/settings")
        platform_response = client.get("/api/admin/platform/settings")
        integration_response = client.get("/api/admin/platform/integrations")
        self.assertEqual(system_response.status_code, 200)
        self.assertEqual(len(system_response.json()), 3)
        self.assertEqual(platform_response.status_code, 200)
        self.assertEqual(len(platform_response.json()), 3)
        self.assertEqual(integration_response.status_code, 200)
        self.assertEqual(len(integration_response.json()), 2)
        self.assertNotIn("custom", integration_response.text)

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
        client = self._client(allow_optional=False)
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
