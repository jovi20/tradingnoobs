import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import AIAnalysisResult, IdempotencyKey, User
from services.auth_service import get_current_user


class InsightsIdempotencyTests(unittest.TestCase):
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
            email="insights-idempotency@example.com",
            email_normalized="insights-idempotency@example.com",
            hashed_password="hashed",
            status="ACTIVE",
            is_active=True,
            role="user",
            public_id="user-insights-idempotency",
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

    def test_analyze_replays_completed_idempotency_key_without_duplicate_ai_result(self):
        payload = {
            "analysis_type": "strategy_health",
            "start_date": "2026-05-01",
            "end_date": "2026-05-10",
        }
        headers = {"Idempotency-Key": "analysis-retry-1"}

        with (
            patch("routers.insights.AnalyticsService.analyze", return_value={"score": 82}) as analyze,
            patch("routers.insights.get_analysis_insight", new_callable=AsyncMock, return_value="Discipline is improving.") as insight,
        ):
            first = self.client.post("/api/insights/analyze", json=payload, headers=headers)
            second = self.client.post("/api/insights/analyze", json=payload, headers=headers)

        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(analyze.call_count, 1)
        self.assertEqual(insight.await_count, 1)
        self.assertEqual(self.db.query(AIAnalysisResult).count(), 1)

        record = self.db.query(IdempotencyKey).one()
        self.assertEqual(record.scope, "insights.analysis.create")
        self.assertEqual(record.key, "user-insights-idempotency:analysis-retry-1")
        self.assertEqual(record.status, "COMPLETED")
        self.assertIsNotNone(record.response_json)


if __name__ == "__main__":
    unittest.main()
