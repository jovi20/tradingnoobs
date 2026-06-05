import os
import tempfile
import unittest
from unittest.mock import AsyncMock, patch
import sys
import types

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
from models import AIAnalysisResult, AISummary, IdempotencyKey, InsightArtifact, InsightRun, User, WeeklyReport
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
        self.assertEqual(self.db.query(InsightRun).count(), 1)
        self.assertEqual(self.db.query(InsightArtifact).count(), 1)

        record = self.db.query(IdempotencyKey).one()
        self.assertEqual(record.scope, "insights.analysis.create")
        self.assertEqual(record.key, "user-insights-idempotency:analysis-retry-1")
        self.assertEqual(record.status, "COMPLETED")
        self.assertIsNotNone(record.response_json)

    def test_weekly_report_generate_replays_completed_idempotency_key_without_duplicate_report(self):
        payload = {
            "week_start": "2026-05-04",
            "week_end": "2026-05-10",
        }
        headers = {"Idempotency-Key": "weekly-report-retry-1"}

        async def fake_generate_weekly_report(db, user_id, week_start, week_end):
            report = WeeklyReport(
                user_id=user_id,
                week_start=week_start,
                week_end=week_end,
                trades_summary="Weekly trades summary.",
                munger_evaluation="Munger notes.",
                suggestions="Keep position sizing consistent.",
            )
            db.add(report)
            db.commit()
            db.refresh(report)
            return report

        with (
            patch(
                "routers.insights.get_llm_runtime_config",
                return_value={"api_url": "https://llm.example.test", "api_key": "key", "model": "model"},
            ),
            patch(
                "routers.insights.generate_weekly_report",
                new_callable=AsyncMock,
                side_effect=fake_generate_weekly_report,
            ) as generate_report,
        ):
            first = self.client.post("/api/insights/generate", json=payload, headers=headers)
            second = self.client.post("/api/insights/generate", json=payload, headers=headers)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(generate_report.await_count, 1)
        self.assertEqual(self.db.query(WeeklyReport).count(), 1)

        record = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.scope == "insights.weekly_report.generate",
            IdempotencyKey.key == "user-insights-idempotency:weekly-report-retry-1",
        ).one()
        self.assertEqual(record.status, "COMPLETED")
        self.assertIsNotNone(record.response_json)

    def test_summary_generate_replays_completed_idempotency_key_without_duplicate_ai_summary(self):
        headers = {"Idempotency-Key": "summary-retry-1"}

        with (
            patch(
                "routers.insights.get_llm_runtime_config",
                return_value={"api_url": "https://llm.example.test", "api_key": "key", "model": "model"},
            ),
            patch(
                "routers.insights.generate_journal_summary",
                new_callable=AsyncMock,
                return_value="Today summary.",
            ) as generate_summary,
        ):
            first = self.client.post("/api/insights/summary/generate", headers=headers)
            second = self.client.post("/api/insights/summary/generate", headers=headers)

        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertEqual(second.json(), first.json())
        self.assertEqual(generate_summary.await_count, 1)
        self.assertEqual(self.db.query(AISummary).count(), 1)
        self.assertEqual(self.db.query(InsightRun).count(), 1)
        self.assertEqual(self.db.query(InsightArtifact).count(), 1)

        record = self.db.query(IdempotencyKey).filter(
            IdempotencyKey.scope == "insights.summary.generate",
            IdempotencyKey.key == "user-insights-idempotency:summary-retry-1",
        ).one()
        self.assertEqual(record.status, "COMPLETED")
        self.assertIsNotNone(record.response_json)


if __name__ == "__main__":
    unittest.main()
