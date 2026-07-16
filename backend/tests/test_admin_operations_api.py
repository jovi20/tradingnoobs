import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import (
    AuthToken,
    BusinessLock,
    BusinessLockStatus,
    FeatureFlag,
    IntegrationCredential,
    PlatformSetting,
    User,
    UserCredential,
    UserSession,
)
from routers.admin import get_current_admin, get_current_user
from services.auth_service import get_password_hash, verify_password
from services.credential_service import encrypt_secret


class AdminOperationsApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "admin-ops.db")
        self.backup_dir = os.path.join(self.temp_dir.name, "backups")
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

        self.admin_user = User(
            email="admin-ops@example.com",
            email_normalized="admin-ops@example.com",
            hashed_password="hashed",
            public_id="admin-ops-public-id",
            status="ACTIVE",
            is_active=True,
            role="admin",
        )
        self.non_admin_user = User(
            email="operator@example.com",
            email_normalized="operator@example.com",
            hashed_password="hashed",
            public_id="operator-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )

        db = self.SessionLocal()
        try:
            db.add_all([self.admin_user, self.non_admin_user])
            db.commit()
        finally:
            db.close()

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        def override_get_current_admin():
            return self.admin_user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_admin] = override_get_current_admin
        self.backup_dir_patch = patch("routers.admin.ADMIN_BACKUP_DIR", self.backup_dir, create=True)
        self.backup_dir_patch.start()
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.backup_dir_patch.stop()
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_admin_can_trigger_sqlite_backup(self):
        response = self.client.post("/api/admin/ops/backups")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["database_backend"], "sqlite")
        self.assertTrue(payload["backup_id"].startswith("sqlite-"))
        self.assertTrue(payload["path"].endswith(".db"))
        self.assertTrue(Path(payload["path"]).exists())
        self.assertEqual(Path(payload["path"]).parent, Path(self.backup_dir))
        self.assertIsNotNone(payload["created_at"])
        self.assertIn("completed", payload["message"].lower())

    def test_admin_can_list_backup_history(self):
        self.client.post("/api/admin/ops/backups")

        response = self.client.get("/api/admin/ops/backups")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertTrue(payload[0]["backup_id"].startswith("sqlite-"))
        self.assertGreater(payload[0]["size_bytes"], 0)

    def test_admin_can_get_ops_summary(self):
        self.client.post("/api/admin/ops/backups")
        db = self.SessionLocal()
        try:
            db.add(PlatformSetting(key="llm_model", value="gpt-4.1"))
            db.add(
                IntegrationCredential(
                    provider_key="openai",
                    credential_key="api_key",
                    secret_ciphertext=encrypt_secret("sk-test-secret"),
                    is_active=True,
                )
            )
            db.add(FeatureFlag(key="ops_console", enabled=True))
            db.add(
                FeatureFlag(
                    key="expired_flag",
                    enabled=False,
                    expires_at=datetime.now(timezone.utc) - timedelta(days=1),
                )
            )
            db.add(
                BusinessLock(
                    scope="test",
                    resource_key="portfolio:user",
                    owner_id="job-public-id",
                    owner_type="job_run",
                    status=BusinessLockStatus.ACTIVE,
                    acquired_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(minutes=10),
                )
            )
            db.add(
                BusinessLock(
                    scope="test",
                    resource_key="portfolio:expired",
                    owner_id="job-public-id",
                    owner_type="job_run",
                    status=BusinessLockStatus.EXPIRED,
                    acquired_at=datetime.now(timezone.utc) - timedelta(hours=2),
                    expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.get("/api/admin/ops/summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["database_backend"], "sqlite")
        self.assertTrue(payload["backup_provider_configured"])
        self.assertEqual(payload["backup_count"], 1)
        self.assertEqual(payload["user_count"], 2)
        self.assertEqual(payload["active_user_count"], 2)
        self.assertEqual(payload["admin_count"], 1)
        self.assertIn("QUEUED", payload["job_counts"])
        self.assertEqual(payload["platform_setting_count"], 1)
        self.assertEqual(payload["configured_integration_count"], 1)
        self.assertEqual(payload["active_integration_count"], 1)
        self.assertEqual(payload["enabled_feature_flag_count"], 1)
        self.assertEqual(payload["expired_feature_flag_count"], 1)
        self.assertEqual(payload["active_business_lock_count"], 1)
        self.assertEqual(payload["expired_business_lock_count"], 1)

    def test_non_admin_cannot_trigger_backup(self):
        app.dependency_overrides.pop(get_current_admin, None)

        async def override_get_current_user():
            return self.non_admin_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        response = self.client.post("/api/admin/ops/backups")

        self.assertEqual(response.status_code, 403)

    def test_postgres_backup_returns_provider_not_configured(self):
        with patch(
            "routers.admin.resolve_database_url_for_backup",
            return_value="postgresql://trader:secret@localhost/tradingnoobs",
            create=True,
        ):
            response = self.client.post("/api/admin/ops/backups")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "BACKUP_PROVIDER_NOT_CONFIGURED")

    def test_admin_can_list_users_for_ops_console(self):
        response = self.client.get("/api/admin/users")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 2)
        operator = next(item for item in payload if item["public_id"] == "operator-public-id")
        self.assertEqual(operator["email"], "operator@example.com")
        self.assertEqual(operator["role"], "user")
        self.assertTrue(operator["is_active"])

    def test_non_admin_cannot_list_users_for_ops_console(self):
        app.dependency_overrides.pop(get_current_admin, None)

        async def override_get_current_user():
            return self.non_admin_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        response = self.client.get("/api/admin/users")

        self.assertEqual(response.status_code, 403)

    def test_admin_can_promote_user_by_public_id(self):
        response = self.client.post("/api/admin/users/operator-public-id/promote")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["user_public_id"], "operator-public-id")
        self.assertEqual(payload["role"], "admin")
        self.assertIn("promoted", payload["message"].lower())

        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.public_id == "operator-public-id").one()
            self.assertEqual(user.role, "admin")
        finally:
            db.close()

    def test_promote_missing_user_returns_404(self):
        response = self.client.post("/api/admin/users/missing-user/promote")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "USER_NOT_FOUND")

    def test_admin_can_update_user_role(self):
        response = self.client.patch("/api/admin/users/operator-public-id/role", json={"role": "admin"})

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["role"], "admin")

    def test_cannot_demote_last_active_admin(self):
        response = self.client.patch("/api/admin/users/admin-ops-public-id/role", json={"role": "user"})

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "LAST_ACTIVE_ADMIN")

    def test_can_demote_inactive_admin_when_active_admin_remains(self):
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.public_id == "operator-public-id").one()
            user.role = "admin"
            user.is_active = False
            user.status = "DISABLED"
            db.commit()
        finally:
            db.close()

        response = self.client.patch("/api/admin/users/operator-public-id/role", json={"role": "user"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["role"], "user")

    def test_admin_can_disable_and_enable_user(self):
        disable_response = self.client.patch(
            "/api/admin/users/operator-public-id/active",
            json={"is_active": False},
        )

        self.assertEqual(disable_response.status_code, 200)
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.public_id == "operator-public-id").one()
            self.assertFalse(user.is_active)
            self.assertEqual(user.status, "DISABLED")
        finally:
            db.close()

        enable_response = self.client.patch(
            "/api/admin/users/operator-public-id/active",
            json={"is_active": True},
        )

        self.assertEqual(enable_response.status_code, 200)
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.public_id == "operator-public-id").one()
            self.assertTrue(user.is_active)
            self.assertEqual(user.status, "ACTIVE")
        finally:
            db.close()

    def test_admin_cannot_disable_self(self):
        response = self.client.patch(
            "/api/admin/users/admin-ops-public-id/active",
            json={"is_active": False},
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "CANNOT_DISABLE_SELF")

    def test_admin_can_reset_user_password(self):
        response = self.client.post("/api/admin/users/operator-public-id/reset-password")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["status"], "SUCCESS")
        self.assertEqual(payload["user_public_id"], "operator-public-id")
        self.assertGreaterEqual(len(payload["temporary_password"]), 18)
        self.assertTrue(payload["active_sessions_revoked"])
        self.assertIn("only shown once", payload["message"].lower())

    def test_password_reset_updates_user_credential_hash(self):
        old_hash = get_password_hash("old-password")
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.public_id == "operator-public-id").one()
            user.hashed_password = old_hash
            db.add(
                UserCredential(
                    user_id=user.id,
                    password_hash=old_hash,
                    password_updated_at=datetime.now(timezone.utc) - timedelta(days=5),
                )
            )
            db.flush()
            session = UserSession(
                user_id=user.id,
                status="ACTIVE",
                last_seen_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(days=30),
            )
            db.add(session)
            db.flush()
            db.add(
                AuthToken(
                    user_id=user.id,
                    session_id=session.id,
                    token_jti="token-to-revoke",
                    token_type="bearer",
                    expires_at=datetime.now(timezone.utc) + timedelta(days=30),
                )
            )
            db.commit()
        finally:
            db.close()

        response = self.client.post("/api/admin/users/operator-public-id/reset-password")

        self.assertEqual(response.status_code, 200)
        temporary_password = response.json()["temporary_password"]
        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.public_id == "operator-public-id").one()
            credential = db.query(UserCredential).filter(UserCredential.user_id == user.id).one()
            auth_token = db.query(AuthToken).filter(AuthToken.token_jti == "token-to-revoke").one()
            session = db.query(UserSession).filter(UserSession.id == auth_token.session_id).one()
            self.assertNotEqual(credential.password_hash, old_hash)
            self.assertNotEqual(user.hashed_password, old_hash)
            self.assertTrue(verify_password(temporary_password, credential.password_hash))
            self.assertTrue(verify_password(temporary_password, user.hashed_password))
            self.assertEqual(session.status, "REVOKED")
            self.assertIsNotNone(session.revoked_at)
            self.assertIsNotNone(auth_token.revoked_at)
        finally:
            db.close()

    def test_non_admin_cannot_reset_password(self):
        app.dependency_overrides.pop(get_current_admin, None)

        async def override_get_current_user():
            return self.non_admin_user

        app.dependency_overrides[get_current_user] = override_get_current_user

        response = self.client.post("/api/admin/users/admin-ops-public-id/reset-password")

        self.assertEqual(response.status_code, 403)

    def test_admin_can_toggle_integration_active_state_without_rotating_secret(self):
        db = self.SessionLocal()
        try:
            db.add(
                IntegrationCredential(
                    provider_key="openai",
                    credential_key="api_key",
                    secret_ciphertext=encrypt_secret("sk-test-secret"),
                    description="OpenAI API Key",
                    is_active=True,
                )
            )
            db.commit()
        finally:
            db.close()

        disable_response = self.client.patch(
            "/api/admin/platform/integrations/openai/api_key/active",
            json={"is_active": False},
        )

        self.assertEqual(disable_response.status_code, 200)
        self.assertFalse(disable_response.json()["is_active"])
        self.assertTrue(disable_response.json()["is_configured"])

        enable_response = self.client.patch(
            "/api/admin/platform/integrations/openai/api_key/active",
            json={"is_active": True},
        )

        self.assertEqual(enable_response.status_code, 200)
        self.assertTrue(enable_response.json()["is_active"])

    def test_toggle_missing_integration_returns_404(self):
        response = self.client.patch(
            "/api/admin/platform/integrations/openai/api_key/active",
            json={"is_active": False},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "INTEGRATION_CREDENTIAL_NOT_FOUND")


if __name__ == "__main__":
    unittest.main()
