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
from models import InsightArtifact, InsightRun, User
from services.auth_service import get_current_user
from services.insight_artifact_service import InsightArtifactService


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
        self.other_user = User(
            email="analysis-workflow-other@example.com",
            email_normalized="analysis-workflow-other@example.com",
            hashed_password="hashed",
            status="ACTIVE",
            is_active=True,
            role="user",
            public_id="user-analysis-workflow-other",
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

    def create_ranged_analysis_artifact(self):
        payload = {
            "analysis_type": "strategy_health",
            "start_date": "2026-06-01",
            "end_date": "2026-06-11",
        }

        with (
            patch("routers.insights.AnalyticsService.analyze", return_value={"stats": {"A": {"count": 1}}}),
            patch("routers.insights.get_analysis_insight", new_callable=AsyncMock, return_value="AI notes"),
        ):
            response = self.client.post("/api/insights/analyze", json=payload)

        self.assertEqual(response.status_code, 200)
        self.db.expire_all()
        run = self.db.query(InsightRun).one()
        artifact = self.db.query(InsightArtifact).one()
        return run, artifact

    def test_generated_insight_run_input_refs_contain_date_range(self):
        run, _ = self.create_ranged_analysis_artifact()

        self.assertIn("analysis:strategy_health", run.input_refs)
        self.assertIn("date-range:2026-06-01:2026-06-11", run.input_refs)

    def test_generated_artifact_payload_contains_date_range(self):
        _, artifact = self.create_ranged_analysis_artifact()

        self.assertEqual(artifact.payload["analysis_type"], "strategy_health")
        self.assertEqual(artifact.payload["date_range"], {
            "start_date": "2026-06-01",
            "end_date": "2026-06-11",
            "label": "2026-06-01 to 2026-06-11",
        })

    def test_generated_artifact_trust_source_refs_contain_date_range(self):
        _, artifact = self.create_ranged_analysis_artifact()

        self.assertIn("date-range:2026-06-01:2026-06-11", artifact.evidence_refs)
        self.assertIn("date-range:2026-06-01:2026-06-11", artifact.trust_meta["source_refs"])

    def create_history_artifact(self, *, user_id: int, analysis_type: str, summary: str):
        service = InsightArtifactService(self.db)
        date_range = {
            "start_date": "2026-06-01",
            "end_date": "2026-06-11",
            "label": "2026-06-01 to 2026-06-11",
        }
        run = service.start_run(
            user_id=user_id,
            run_type=f"analysis.{analysis_type}",
            prompt_version="test-analysis-history",
            input_refs=[f"analysis:{analysis_type}", "date-range:2026-06-01:2026-06-11"],
        )
        artifact = service.add_artifact(
            run_public_id=run.public_id,
            artifact_type="analysis_card",
            title=f"Analysis · {analysis_type}",
            summary=summary,
            content_markdown="AI body",
            payload={
                "linked_surface": "insights",
                "analysis_type": analysis_type,
                "date_range": date_range,
                "raw_data": {"stats": {}},
            },
            evidence_refs=[f"analysis:{analysis_type}", "date-range:2026-06-01:2026-06-11"],
            chart_schema=None,
            trust_meta={
                "freshness": "FRESH",
                "source": "AI_GENERATED",
                "source_refs": [f"analysis:{analysis_type}", "date-range:2026-06-01:2026-06-11"],
            },
        )
        service.complete_run(run_public_id=run.public_id, status="COMPLETED")
        self.db.commit()
        self.db.refresh(run)
        self.db.refresh(artifact)
        return run, artifact

    def test_analysis_history_lists_only_current_user_artifacts(self):
        run, artifact = self.create_history_artifact(
            user_id=self.user.id,
            analysis_type="strategy_health",
            summary="Current user analysis.",
        )
        self.create_history_artifact(
            user_id=self.other_user.id,
            analysis_type="strategy_health",
            summary="Other user analysis.",
        )

        response = self.client.get("/api/insights/analyze/history")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["run_public_id"], run.public_id)
        self.assertEqual(payload[0]["artifact_public_id"], artifact.public_id)
        self.assertEqual(payload[0]["analysis_type"], "strategy_health")
        self.assertEqual(payload[0]["summary"], "Current user analysis.")
        self.assertEqual(payload[0]["date_range"]["label"], "2026-06-01 to 2026-06-11")
        self.assertEqual(payload[0]["href"], f"/insights/{artifact.public_id}")

    def test_analysis_history_filter_works(self):
        self.create_history_artifact(
            user_id=self.user.id,
            analysis_type="strategy_health",
            summary="Strategy analysis.",
        )
        _, artifact = self.create_history_artifact(
            user_id=self.user.id,
            analysis_type="emotion_pnl",
            summary="Emotion analysis.",
        )

        response = self.client.get("/api/insights/analyze/history?analysis_type=emotion_pnl")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(len(payload), 1)
        self.assertEqual(payload[0]["artifact_public_id"], artifact.public_id)
        self.assertEqual(payload[0]["analysis_type"], "emotion_pnl")

    def test_analysis_history_limit_is_enforced(self):
        for index in range(3):
            self.create_history_artifact(
                user_id=self.user.id,
                analysis_type="strategy_health",
                summary=f"Analysis {index}",
            )

        response = self.client.get("/api/insights/analyze/history?limit=2")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()), 2)


if __name__ == "__main__":
    unittest.main()
