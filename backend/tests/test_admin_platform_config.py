import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import FeatureFlag, IntegrationCredential, PlatformSetting, User
from release_profile import DeploymentCapabilityPolicy
from routers.admin import get_current_admin
from services.auth_service import get_current_user
from services.credential_service import decrypt_secret


class AdminPlatformConfigTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        self.admin_user = User(
            email="admin@example.com",
            email_normalized="admin@example.com",
            hashed_password="hashed",
            public_id="admin-public-id",
            status="ACTIVE",
            is_active=True,
            role="admin",
        )

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        def override_get_current_admin():
            return self.admin_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_admin
        app.dependency_overrides[get_current_admin] = override_get_current_admin
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_platform_setting_can_be_created_and_listed(self):
        update_response = self.client.put(
            "/api/admin/platform/settings/llm_api_url",
            json={
                "value": "https://api.openai.com/v1",
                "description": "Default LLM endpoint",
            },
        )
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["key"], "llm_api_url")

        list_response = self.client.get("/api/admin/platform/settings")
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["value"], "https://api.openai.com/v1")

        db = self.SessionLocal()
        try:
            setting = db.query(PlatformSetting).filter(PlatformSetting.key == "llm_api_url").one()
        finally:
            db.close()
        self.assertEqual(setting.value, "https://api.openai.com/v1")

    def test_integration_credential_is_encrypted_at_rest_and_masked_in_response(self):
        raw_secret = "sk-live-1234567890abcdef"
        response = self.client.put(
            "/api/admin/platform/integrations/openai/api_key",
            json={
                "secret_value": raw_secret,
                "description": "OpenAI production key",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["is_configured"])
        self.assertNotEqual(payload["masked_value"], raw_secret)
        self.assertTrue(payload["masked_value"].startswith("sk-l"))

        db = self.SessionLocal()
        try:
            credential = (
                db.query(IntegrationCredential)
                .filter(
                    IntegrationCredential.provider_key == "openai",
                    IntegrationCredential.credential_key == "api_key",
                )
                .one()
            )
        finally:
            db.close()

        self.assertNotEqual(credential.secret_ciphertext, raw_secret)
        self.assertEqual(decrypt_secret(credential.secret_ciphertext), raw_secret)

    def test_feature_flag_can_be_created_and_listed(self):
        response = self.client.put(
            "/api/admin/platform/feature-flags/timeline_home_enabled",
            json={
                "enabled": True,
                "actor_targets": ["beta-user-1"],
                "rollout_percentage": 25,
                "description": "Enable new timeline home",
            },
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["key"], "timeline_home_enabled")
        self.assertEqual(payload["rollout_percentage"], 25)

        list_response = self.client.get("/api/admin/platform/feature-flags")
        self.assertEqual(list_response.status_code, 200)
        flags = list_response.json()
        self.assertEqual(len(flags), 1)
        self.assertEqual(flags[0]["actor_targets"], ["beta-user-1"])

        db = self.SessionLocal()
        try:
            flag = db.query(FeatureFlag).filter(FeatureFlag.key == "timeline_home_enabled").one()
        finally:
            db.close()
        self.assertTrue(flag.enabled)

    def test_open_registration_rejects_non_global_rollout_without_side_effects(self):
        for payload in (
            {"enabled": True, "actor_targets": ["anonymous-user"]},
            {"enabled": True, "rollout_percentage": 100},
        ):
            with self.subTest(payload=payload):
                response = self.client.put(
                    "/api/admin/platform/feature-flags/capability.open_registration.v1",
                    json=payload,
                )
                self.assertEqual(response.status_code, 422, response.text)
                self.assertEqual(
                    response.json()["detail"]["code"],
                    "PUBLIC_CAPABILITY_ROLLOUT_INVALID",
                )

                db = self.SessionLocal()
                try:
                    count = db.query(FeatureFlag).filter(
                        FeatureFlag.key == "capability.open_registration.v1"
                    ).count()
                finally:
                    db.close()
                self.assertEqual(count, 0)

    def test_ceiling_excluded_ai_admin_writes_have_zero_side_effects(self):
        empty_policy = DeploymentCapabilityPolicy(frozenset())
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            empty_policy,
        ), patch("routers.admin_ai.httpx.AsyncClient") as http_client:
            flag_response = self.client.put(
                "/api/admin/platform/feature-flags/capability.ai_insights.v1",
                json={"enabled": True},
            )
            setting_response = self.client.put(
                "/api/admin/platform/settings/llm_model",
                json={"value": "gpt-5"},
            )
            credential_response = self.client.put(
                "/api/admin/platform/integrations/openai/api_key",
                json={"secret_value": "sk-must-not-persist"},
            )
            test_response = self.client.post("/api/admin/test-llm")

        for response in (
            flag_response,
            setting_response,
            credential_response,
            test_response,
        ):
            self.assertEqual(response.status_code, 404)
            self.assertEqual(response.json()["error"]["code"], "FEATURE_DISABLED")
            self.assertEqual(response.json()["detail"]["capability"], "AI_INSIGHTS")

        http_client.assert_not_called()
        db = self.SessionLocal()
        try:
            self.assertEqual(db.query(FeatureFlag).count(), 0)
            self.assertEqual(db.query(PlatformSetting).count(), 0)
            self.assertEqual(db.query(IntegrationCredential).count(), 0)
        finally:
            db.close()

    def test_test_llm_uses_new_platform_tables(self):
        flag_response = self.client.put(
            "/api/admin/platform/feature-flags/capability.ai_insights.v1",
            json={"enabled": True},
        )
        self.assertEqual(flag_response.status_code, 200)
        self.client.put(
            "/api/admin/platform/settings/llm_api_url",
            json={"value": "https://new.example/v1"},
        )
        self.client.put(
            "/api/admin/platform/settings/llm_model",
            json={"value": "gpt-5"},
        )
        self.client.put(
            "/api/admin/platform/integrations/openai/api_key",
            json={"secret_value": "sk-test-1234567890"},
        )

        class FakeResponse:
            status_code = 200

            def json(self):
                return {"ok": True}

        class FakeAsyncClient:
            def __init__(self, *args, **kwargs):
                pass

            async def __aenter__(self):
                return self

            async def __aexit__(self, exc_type, exc, tb):
                return False

            async def post(self, *args, **kwargs):
                return FakeResponse()

        with patch("routers.admin_ai.httpx.AsyncClient", FakeAsyncClient):
            response = self.client.post("/api/admin/test-llm")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "success")


if __name__ == "__main__":
    unittest.main()
