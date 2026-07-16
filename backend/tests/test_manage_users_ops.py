import os
import tempfile
import unittest
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import AuthToken, User, UserCredential, UserSession
from ops import manage_users
from services.auth_service import get_password_hash, utc_now, verify_password


class ManageUsersOpsTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.original_session_local = manage_users.SessionLocal
        manage_users.SessionLocal = self.SessionLocal

    def tearDown(self):
        manage_users.SessionLocal = self.original_session_local
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_reset_password_updates_credentials_and_revokes_active_session(self):
        old_hash = get_password_hash("old-password")
        db = self.SessionLocal()
        try:
            user = User(
                email="ops@example.com",
                email_normalized="ops@example.com",
                hashed_password=old_hash,
                status="ACTIVE",
                is_active=True,
            )
            db.add(user)
            db.flush()
            db.add(UserCredential(user_id=user.id, password_hash=old_hash))
            session = UserSession(
                user_id=user.id,
                status="ACTIVE",
                expires_at=utc_now() + timedelta(hours=1),
            )
            db.add(session)
            db.flush()
            db.add(
                AuthToken(
                    user_id=user.id,
                    session_id=session.id,
                    token_jti="ops-reset-token",
                    expires_at=utc_now() + timedelta(hours=1),
                )
            )
            db.commit()
        finally:
            db.close()

        manage_users.reset_password("OPS@example.com", "new-password")

        db = self.SessionLocal()
        try:
            user = db.query(User).filter(User.email_normalized == "ops@example.com").one()
            credential = db.query(UserCredential).filter(UserCredential.user_id == user.id).one()
            session = db.query(UserSession).filter(UserSession.user_id == user.id).one()
            token = db.query(AuthToken).filter(AuthToken.user_id == user.id).one()
            self.assertTrue(verify_password("new-password", user.hashed_password))
            self.assertTrue(verify_password("new-password", credential.password_hash))
            self.assertEqual(session.status, "REVOKED")
            self.assertIsNotNone(session.revoked_at)
            self.assertIsNotNone(token.revoked_at)
        finally:
            db.close()


if __name__ == "__main__":
    unittest.main()
