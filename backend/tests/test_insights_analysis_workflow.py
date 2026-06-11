import os
import sys
import tempfile
import types
import unittest
from datetime import date
from unittest.mock import AsyncMock, patch

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
from models import User
from services.auth_service import get_current_user


class InsightsAnalysisWorkflowTests(unittest.TestCase):
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
            email="analysis-workflow@example.com",
            email_normalized="analysis-workflow@example.com",
            hashed_password="hashed",
            status="ACTIVE",
            is_active=True,
            role="user",
            public_id="user-analysis-workflow",
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

    def assert_invalid_range(self, payload: dict):
        with (
            patch("routers.insights.AnalyticsService.analyze", return_value={"stats": {}}) as analyze,
            patch("routers.insights.get_analysis_insight", new_callable=AsyncMock, return_value="AI notes") as insight,
        ):
            response = self.client.post(
                "/api/insights/analyze",
                json=payload,
                headers={"X-Request-ID": "req-analysis-range-invalid"},
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "VALIDATION_REQUEST_INVALID")
        self.assertEqual(response.json()["error"]["request_id"], "req-analysis-range-invalid")
        analyze.assert_not_called()
        insight.assert_not_called()

    def test_analysis_rejects_start_date_without_end_date(self):
        self.assert_invalid_range({
            "analysis_type": "strategy_health",
            "start_date": "2026-06-01",
        })

    def test_analysis_rejects_end_date_without_start_date(self):
        self.assert_invalid_range({
            "analysis_type": "strategy_health",
            "end_date": "2026-06-11",
        })

    def test_analysis_rejects_reversed_date_range(self):
        self.assert_invalid_range({
            "analysis_type": "strategy_health",
            "start_date": "2026-06-11",
            "end_date": "2026-06-01",
        })

    def test_analysis_rejects_range_longer_than_366_days(self):
        self.assert_invalid_range({
            "analysis_type": "strategy_health",
            "start_date": "2025-01-01",
            "end_date": "2026-01-02",
        })

    def test_analysis_accepts_valid_date_range(self):
        payload = {
            "analysis_type": "strategy_health",
            "start_date": "2026-06-01",
            "end_date": "2026-06-11",
        }

        with (
            patch("routers.insights.AnalyticsService.analyze", return_value={"stats": {}}) as analyze,
            patch("routers.insights.get_analysis_insight", new_callable=AsyncMock, return_value="AI notes") as insight,
        ):
            response = self.client.post("/api/insights/analyze", json=payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analysis_type"], "strategy_health")
        analyze.assert_called_once()
        _, kwargs = analyze.call_args
        self.assertEqual(kwargs["start_date"], date(2026, 6, 1))
        self.assertEqual(kwargs["end_date"], date(2026, 6, 11))
        self.assertEqual(insight.await_count, 1)


if __name__ == "__main__":
    unittest.main()
