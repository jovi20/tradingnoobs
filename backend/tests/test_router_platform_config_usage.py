import os
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import IntegrationCredential, PlatformSetting, User, WeeklyReport
from services.auth_service import get_current_user
from services.credential_service import encrypt_secret


class RouterPlatformConfigUsageTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        self.db = self.SessionLocal()
        self.user = User(
            email="router@example.com",
            email_normalized="router@example.com",
            hashed_password="hashed",
            public_id="router-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            db = self.SessionLocal()
            try:
                return db.query(User).filter(User.id == self.user.id).one()
            finally:
                db.close()

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.capability_patch = patch(
            "services.capability_service.get_feature_flag_enabled",
            return_value=True,
        )
        self.capability_patch.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.capability_patch.stop()
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_generate_current_week_report_uses_new_platform_tables(self):
        self.db.add(PlatformSetting(key="llm_api_url", value="https://new.example/v1"))
        self.db.add(PlatformSetting(key="llm_model", value="gpt-5"))
        self.db.add(
            IntegrationCredential(
                provider_key="openai",
                credential_key="api_key",
                secret_ciphertext=encrypt_secret("sk-test-1234567890"),
            )
        )
        self.db.commit()

        async def fake_generate_weekly_report(db, user_id, week_start, week_end):
            report = WeeklyReport(
                user_id=user_id,
                week_start=week_start,
                week_end=week_end,
                trades_summary="ok",
                munger_evaluation="ok",
                suggestions="ok",
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            return report

        with patch("routers.insights.generate_weekly_report", fake_generate_weekly_report):
            response = self.client.post("/api/insights/generate-current-week")

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["user_id"], self.user.id)
        self.assertEqual(payload["trades_summary"], "ok")

    def test_market_calendar_uses_new_finnhub_integration_credential(self):
        self.db.add(
            IntegrationCredential(
                provider_key="finnhub",
                credential_key="api_key",
                secret_ciphertext=encrypt_secret("new-finnhub-key"),
            )
        )
        self.db.commit()

        captured = {}

        class FakeMarketCalendarService:
            def __init__(self, finnhub_api_key=None):
                captured["finnhub_api_key"] = finnhub_api_key

            def get_calendar(self, market, year, month):
                return {"market": market, "year": year, "month": month}

        with patch("services.market_calendar.MarketCalendarService", FakeMarketCalendarService):
            response = self.client.get("/api/market/calendar?market=US&year=2026&month=4")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["market"], "US")
        self.assertEqual(captured["finnhub_api_key"], "new-finnhub-key")


if __name__ == "__main__":
    unittest.main()
