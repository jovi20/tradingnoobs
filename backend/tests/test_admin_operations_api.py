import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import User
from routers.admin import get_current_admin, get_current_user


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


if __name__ == "__main__":
    unittest.main()
