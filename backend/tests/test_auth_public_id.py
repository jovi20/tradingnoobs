import os
import tempfile
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from services.auth_service import authenticate_user, create_user, get_user_by_email


class AuthPublicIdTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_create_user_sets_public_identity_fields(self):
        user = create_user(self.session, "Trader@Example.com", "password123")

        self.assertIsNotNone(user.public_id)
        self.assertEqual(user.status, "ACTIVE")
        self.assertEqual(user.email_normalized, "trader@example.com")
        self.assertIsNone(user.last_login_at)

    def test_authenticate_user_uses_normalized_email_and_updates_last_login(self):
        created = create_user(self.session, "Trader@Example.com", "password123")
        self.assertIsNone(created.last_login_at)

        fetched = get_user_by_email(self.session, "TRADER@example.com")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.id, created.id)

        authed = authenticate_user(self.session, "TRADER@example.com", "password123")
        self.assertIsNotNone(authed)

        self.session.refresh(authed)
        self.assertIsNotNone(authed.last_login_at)


if __name__ == "__main__":
    unittest.main()
