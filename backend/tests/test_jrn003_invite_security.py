import hashlib
import logging
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from config import Settings, validate_release_settings
from database import Base, get_db
from main import create_app
from models import Invitation, SecurityAuditEvent, User
from release_profile import ReleaseProfile
from services.auth_service import create_authenticated_session, create_user
from services.redaction import REDACTED, sanitize_for_observability


class JRN003InviteSecurityTests(unittest.TestCase):
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
        )
        Base.metadata.create_all(bind=self.engine)

        db = self.SessionLocal()
        try:
            self.admin = create_user(
                db,
                "admin@example.com",
                "password123",
                timezone_name="Asia/Shanghai",
            )
            self.admin.role = "admin"
            db.add(self.admin)
            db.commit()
            self.admin_token = create_authenticated_session(db, self.admin)
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
        self.client = TestClient(self.app)

    def tearDown(self):
        self.client.close()
        self.app.dependency_overrides.clear()
        self.engine.dispose()
        os.remove(self.db_path)

    @property
    def admin_headers(self):
        return {"Authorization": f"Bearer {self.admin_token}"}

    def _create_invitation(self, expires_in_hours=24):
        response = self.client.post(
            "/api/admin/invitations",
            headers=self.admin_headers,
            json={"expires_in_hours": expires_in_hours},
        )
        self.assertEqual(response.status_code, 201, response.text)
        return response.json()

    def _register(self, code, *, email="trader@example.com", timezone_name="Asia/Tokyo"):
        return self.client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": "password123",
                "invite_code": code,
                "timezone": timezone_name,
            },
        )

    def test_invitation_is_random_hashed_one_time_and_audited(self):
        created = self._create_invitation()
        code = created["code"]
        self.assertGreaterEqual(len(code), 32)

        db = self.SessionLocal()
        try:
            invitation = db.query(Invitation).one()
            self.assertNotEqual(invitation.code_hash, code)
            self.assertEqual(
                invitation.code_hash,
                hashlib.sha256(code.encode("utf-8")).hexdigest(),
            )
        finally:
            db.close()

        response = self._register(code)
        self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(response.json()["timezone"], "Asia/Tokyo")

        replay = self._register(code, email="other@example.com")
        self.assertEqual(replay.status_code, 400)
        self.assertEqual(
            replay.json()["detail"]["code"],
            "INVITATION_ALREADY_REDEEMED",
        )

        db = self.SessionLocal()
        try:
            events = (
                db.query(SecurityAuditEvent)
                .order_by(SecurityAuditEvent.id)
                .all()
            )
        finally:
            db.close()
        event_types = [row.event_type for row in events]
        self.assertIn("INVITATION_CREATED", event_types)
        self.assertIn("INVITATION_REDEEMED", event_types)
        self.assertIn("INVITATION_REDEMPTION_REJECTED", event_types)
        replay_event = next(
            row
            for row in events
            if row.event_type == "INVITATION_REDEMPTION_REJECTED"
        )
        self.assertEqual(replay_event.subject_public_id, created["public_id"])

    def test_expired_revoked_and_invalid_timezone_are_rejected(self):
        invalid_timezone = self._create_invitation()
        response = self._register(
            invalid_timezone["code"],
            timezone_name="Not/A_Real_Zone",
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["code"], "TIMEZONE_INVALID")

        expired = self._create_invitation()
        db = self.SessionLocal()
        try:
            invitation = db.query(Invitation).filter(
                Invitation.public_id == expired["public_id"]
            ).one()
            invitation.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.commit()
        finally:
            db.close()
        response = self._register(expired["code"], email="expired@example.com")
        self.assertEqual(response.json()["detail"]["code"], "INVITATION_EXPIRED")

        revoked = self._create_invitation()
        revoke_response = self.client.post(
            f"/api/admin/invitations/{revoked['public_id']}/revoke",
            headers=self.admin_headers,
        )
        self.assertEqual(revoke_response.status_code, 200)
        response = self._register(revoked["code"], email="revoked@example.com")
        self.assertEqual(response.json()["detail"]["code"], "INVITATION_REVOKED")

    def test_legacy_user_must_set_timezone_before_journal_write(self):
        db = self.SessionLocal()
        try:
            user = create_user(db, "legacy@example.com", "password123")
            token = create_authenticated_session(db, user)
        finally:
            db.close()
        headers = {"Authorization": f"Bearer {token}"}

        blocked = self.client.post(
            "/api/strategies",
            headers=headers,
            json={"name": "Blocked until timezone"},
        )
        self.assertEqual(blocked.status_code, 428, blocked.text)
        self.assertEqual(blocked.json()["detail"]["code"], "TIMEZONE_REQUIRED")

        updated = self.client.patch(
            "/api/auth/me",
            headers=headers,
            json={"timezone": "America/New_York"},
        )
        self.assertEqual(updated.status_code, 200, updated.text)

        allowed = self.client.post(
            "/api/strategies",
            headers=headers,
            json={"name": "Allowed"},
        )
        self.assertEqual(allowed.status_code, 201, allowed.text)

    def test_login_and_invitation_redemption_are_rate_limited(self):
        db = self.SessionLocal()
        try:
            create_user(
                db,
                "limited@example.com",
                "password123",
                timezone_name="UTC",
            )
        finally:
            db.close()

        statuses = []
        for _ in range(6):
            response = self.client.post(
                "/api/auth/login",
                data={"username": "limited@example.com", "password": "wrong"},
            )
            statuses.append(response.status_code)
        self.assertEqual(statuses[:5], [401] * 5)
        self.assertEqual(statuses[5], 429)
        self.assertIn("Retry-After", response.headers)

        for index in range(6):
            response = self._register(
                "invalid-invitation",
                email="invite-limited@example.com",
            )
        self.assertEqual(response.status_code, 429)

    def test_user_and_plaintext_platform_secret_writes_are_rejected(self):
        secret_response = self.client.patch(
            "/api/settings",
            headers=self.admin_headers,
            json={"finnhub_api_key": "short-secret"},
        )
        self.assertEqual(secret_response.status_code, 422)

        platform_response = self.client.put(
            "/api/admin/platform/settings/finnhub_api_key",
            headers=self.admin_headers,
            json={"value": "short-secret"},
        )
        self.assertEqual(platform_response.status_code, 404)
        self.assertEqual(
            platform_response.json()["detail"]["code"],
            "SECRET_CONFIGURATION_UNAVAILABLE",
        )

    def test_password_recovery_log_never_contains_temporary_password(self):
        db = self.SessionLocal()
        try:
            target = create_user(
                db,
                "recovery@example.com",
                "password123",
                timezone_name="UTC",
            )
            target_public_id = target.public_id
        finally:
            db.close()

        with self.assertLogs("tradingnoobs.admin", level="INFO") as captured:
            response = self.client.post(
                f"/api/admin/users/{target_public_id}/reset-password",
                headers=self.admin_headers,
            )
        self.assertEqual(response.status_code, 200, response.text)
        temporary_password = response.json()["temporary_password"]
        self.assertTrue(temporary_password)
        self.assertNotIn(temporary_password, "\n".join(captured.output))


class JRN003ReleaseSecurityUnitTests(unittest.TestCase):
    def test_production_rejects_default_and_weak_secret_keys(self):
        for secret_key in ("", "short", "a" * 64, "your-super-secret-key-change-in-production"):
            with self.subTest(secret_key=secret_key):
                with self.assertRaises(RuntimeError):
                    validate_release_settings(
                        Settings(env_name="production", secret_key=secret_key)
                    )

        validate_release_settings(
            Settings(
                env_name="production",
                secret_key="D9!m2$Qa7@Lc4#Vx8%Nz1^Rt6&Yp3*Ks",
            )
        )

    def test_observability_redacts_short_secrets_queries_and_exceptions(self):
        sanitized = sanitize_for_observability(
            {
                "api_key": "tiny",
                "error": RuntimeError(
                    "GET https://provider.example/data?token=tiny&symbol=AAPL failed"
                ),
            }
        )
        self.assertEqual(sanitized["api_key"], REDACTED)
        self.assertNotIn("tiny", sanitized["error"])
        self.assertNotIn("symbol=AAPL", sanitized["error"])

        logger = logging.getLogger("jrn003-test")
        self.assertEqual(
            sanitize_for_observability("token=tiny", field_name="message"),
            f"token={REDACTED}",
        )
