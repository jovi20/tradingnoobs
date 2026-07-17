import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import create_app
from models import AuthToken, FeatureFlag, User, UserCredential, UserSession
from release_profile import DeploymentCapabilityPolicy, ReleaseProfile, RuntimeCapability


class AuthSessionTrackingTests(unittest.TestCase):
    def setUp(self):
        self.ceiling_patch = patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            DeploymentCapabilityPolicy(frozenset({RuntimeCapability.OPEN_REGISTRATION})),
        )
        self.ceiling_patch.start()
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        db = self.SessionLocal()
        try:
            db.add(
                FeatureFlag(
                    key="capability.open_registration.v1",
                    enabled=True,
                    actor_targets=[],
                )
            )
            db.commit()
        finally:
            db.close()

        self.app = create_app(ReleaseProfile.DEVELOPMENT_FULL)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        self.app.dependency_overrides[get_db] = override_get_db
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.app.dependency_overrides.clear()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        self.ceiling_patch.stop()

    def test_login_creates_user_credential_session_and_token_records(self):
        register_response = self.client.post(
            "/api/auth/register",
            json={
                "email": "Trader@Example.com",
                "password": "password123",
                "invite_code": "bigme",
            },
        )
        self.assertEqual(register_response.status_code, 201)

        login_response = self.client.post(
            "/api/auth/login",
            data={
                "username": "TRADER@example.com",
                "password": "password123",
            },
        )
        self.assertEqual(login_response.status_code, 200)

        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.email_normalized == "trader@example.com").one()
            credential = db.query(UserCredential).filter(UserCredential.user_id == user.id).one()
            session = db.query(UserSession).filter(UserSession.user_id == user.id).one()
            token = db.query(AuthToken).filter(AuthToken.user_id == user.id).one()
        finally:
            db.close()

        self.assertEqual(credential.password_hash, user.hashed_password)
        self.assertIsNone(session.revoked_at)
        self.assertEqual(session.status, "ACTIVE")
        self.assertEqual(token.session_id, session.id)
        self.assertEqual(token.token_type, "bearer")
        self.assertIsNone(token.revoked_at)
        self.assertIsNotNone(user.last_login_at)

    def test_logout_revokes_token_and_session_and_blocks_me(self):
        self.client.post(
            "/api/auth/register",
            json={
                "email": "Trader@Example.com",
                "password": "password123",
                "invite_code": "bigme",
            },
        )

        login_response = self.client.post(
            "/api/auth/login",
            data={
                "username": "TRADER@example.com",
                "password": "password123",
            },
        )
        token = login_response.json()["access_token"]

        me_response = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_response.status_code, 200)

        logout_response = self.client.post(
            "/api/auth/logout",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(logout_response.status_code, 204)

        me_after_logout = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(me_after_logout.status_code, 401)

        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.email_normalized == "trader@example.com").one()
            session = db.query(UserSession).filter(UserSession.user_id == user.id).one()
            auth_token = db.query(AuthToken).filter(AuthToken.user_id == user.id).one()
        finally:
            db.close()

        self.assertEqual(session.status, "REVOKED")
        self.assertIsNotNone(session.revoked_at)
        self.assertIsNotNone(auth_token.revoked_at)

    def test_user_can_update_locale_and_timezone(self):
        self.client.post(
            "/api/auth/register",
            json={
                "email": "Trader@Example.com",
                "password": "password123",
                "invite_code": "bigme",
            },
        )
        login_response = self.client.post(
            "/api/auth/login",
            data={
                "username": "trader@example.com",
                "password": "password123",
            },
        )
        token = login_response.json()["access_token"]

        response = self.client.patch(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
            json={"locale": " zh-CN ", "timezone": " Asia/Shanghai "},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["locale"], "zh-CN")
        self.assertEqual(payload["timezone"], "Asia/Shanghai")

    def test_change_password_updates_credential_and_revokes_other_sessions(self):
        self.client.post(
            "/api/auth/register",
            json={
                "email": "Trader@Example.com",
                "password": "password123",
                "invite_code": "bigme",
            },
        )
        first_login = self.client.post(
            "/api/auth/login",
            data={
                "username": "trader@example.com",
                "password": "password123",
            },
        )
        second_login = self.client.post(
            "/api/auth/login",
            data={
                "username": "trader@example.com",
                "password": "password123",
            },
        )
        first_token = first_login.json()["access_token"]
        second_token = second_login.json()["access_token"]

        response = self.client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {first_token}"},
            json={
                "current_password": "password123",
                "new_password": "new-password-123",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["active_sessions_revoked"])

        revoked_me = self.client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {second_token}"},
        )
        self.assertEqual(revoked_me.status_code, 401)

        old_password_login = self.client.post(
            "/api/auth/login",
            data={
                "username": "trader@example.com",
                "password": "password123",
            },
        )
        self.assertEqual(old_password_login.status_code, 401)

        new_password_login = self.client.post(
            "/api/auth/login",
            data={
                "username": "trader@example.com",
                "password": "new-password-123",
            },
        )
        self.assertEqual(new_password_login.status_code, 200)

    def test_change_password_rejects_wrong_current_password(self):
        self.client.post(
            "/api/auth/register",
            json={
                "email": "Trader@Example.com",
                "password": "password123",
                "invite_code": "bigme",
            },
        )
        login_response = self.client.post(
            "/api/auth/login",
            data={
                "username": "trader@example.com",
                "password": "password123",
            },
        )
        token = login_response.json()["access_token"]

        response = self.client.post(
            "/api/auth/change-password",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "current_password": "wrong-password",
                "new_password": "new-password-123",
            },
        )

        self.assertEqual(response.status_code, 400)


if __name__ == "__main__":
    unittest.main()
