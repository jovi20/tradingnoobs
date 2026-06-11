import os
import sys
import tempfile
import types
import unittest
from datetime import date, datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.modules.setdefault("finnhub", types.SimpleNamespace(Client=lambda *args, **kwargs: object()))
sys.modules.setdefault("pandas", types.SimpleNamespace(DataFrame=object))
sys.modules.setdefault("numpy", types.SimpleNamespace())
sys.modules.setdefault("binance", types.SimpleNamespace())
sys.modules.setdefault("binance.spot", types.SimpleNamespace(Spot=lambda *args, **kwargs: object()))

from database import Base, get_db
from main import app
from models import User, WeeklyReport
from services.auth_service import get_current_user


class InsightsReportExportTests(unittest.TestCase):
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
            email="insights-export@example.com",
            email_normalized="insights-export@example.com",
            hashed_password="hashed",
            status="ACTIVE",
            is_active=True,
            role="user",
            public_id="user-insights-export",
        )
        self.other_user = User(
            email="insights-export-other@example.com",
            email_normalized="insights-export-other@example.com",
            hashed_password="hashed",
            status="ACTIVE",
            is_active=True,
            role="user",
            public_id="user-insights-export-other",
        )
        self.db.add_all([self.user, self.other_user])
        self.db.commit()
        self.db.refresh(self.user)
        self.db.refresh(self.other_user)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def make_report(self, user_id: int):
        report = WeeklyReport(
            user_id=user_id,
            week_start=date(2026, 6, 1),
            week_end=date(2026, 6, 7),
            trades_summary="Weekly export route summary.",
            munger_evaluation="Stay rational.",
            suggestions="Keep risk small.",
            created_at=datetime(2026, 6, 8, 9, 30, tzinfo=timezone.utc),
        )
        self.db.add(report)
        self.db.commit()
        self.db.refresh(report)
        return report

    def test_owner_can_export_report_pdf(self):
        report = self.make_report(self.user.id)

        response = self.client.get(f"/api/insights/{report.id}/export/pdf")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["content-type"], "application/pdf")
        self.assertIn("attachment; filename=tradingnoobs-weekly-report-2026-06-01.pdf", response.headers["content-disposition"])
        self.assertEqual(response.headers["access-control-expose-headers"], "Content-Disposition")
        self.assertTrue(response.content.startswith(b"%PDF-"))
        self.assertIn(b"Weekly export route summary", response.content)

    def test_cross_user_export_is_rejected(self):
        report = self.make_report(self.other_user.id)

        response = self.client.get(f"/api/insights/{report.id}/export/pdf")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Report not found")

    def test_missing_report_returns_stable_error_envelope(self):
        response = self.client.get(
            "/api/insights/999999/export/pdf",
            headers={"X-Request-ID": "req-report-export-missing"},
        )

        self.assertEqual(response.status_code, 404)
        payload = response.json()
        self.assertEqual(payload["detail"], "Report not found")
        self.assertEqual(payload["error"]["code"], "INSIGHTS_NOT_FOUND")
        self.assertEqual(payload["error"]["request_id"], "req-report-export-missing")
        self.assertEqual(payload["error"]["status_code"], 404)


if __name__ == "__main__":
    unittest.main()
