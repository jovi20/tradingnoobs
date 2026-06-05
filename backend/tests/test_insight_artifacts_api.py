import os
import tempfile
import unittest
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from routers import insight_artifacts
from services.auth_service import create_user, get_current_user
from services.insight_artifact_service import InsightArtifactService


class InsightArtifactApiTests(unittest.TestCase):
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
        self.user = create_user(self.db, "artifact-api@example.com", "password123")

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.user

        app = FastAPI()
        app.include_router(insight_artifacts.router)
        app.include_router(insight_artifacts.artifact_router)
        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.app = app
        self.client = TestClient(app)

    def tearDown(self):
        self.app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_v1_insight_runs_expose_auditable_artifacts(self):
        service = InsightArtifactService(self.db)
        run = service.start_run(
            user_id=self.user.id,
            run_type="summary.daily",
            prompt_version="daily-v1",
            input_refs=["surface:timeline", "journal:today"],
            started_at=datetime(2026, 6, 5, 9, 0, tzinfo=timezone.utc),
        )
        service.add_artifact(
            run_public_id=run.public_id,
            artifact_type="summary_card",
            title="Daily summary artifact",
            summary="The strongest edge came from patient adds, not early exits.",
            content_markdown=None,
            payload={"linked_surface": "timeline"},
            evidence_refs=["journal:today", "dataset:positions"],
            chart_schema={"schema_version": "chart.v1", "chart_type": "bar", "series": [{"field": "discipline", "label": "Discipline"}]},
            trust_meta={"freshness": "FRESH", "source": "AI_GENERATED", "source_refs": ["journal:today"]},
        )
        service.complete_run(run_public_id=run.public_id, status="COMPLETED")
        self.db.commit()

        list_response = self.client.get("/api/v1/insights/runs")
        detail_response = self.client.get(f"/api/v1/insights/runs/{run.public_id}")

        self.assertEqual(list_response.status_code, 200)
        self.assertEqual(detail_response.status_code, 200)

        list_payload = list_response.json()
        detail_payload = detail_response.json()

        self.assertEqual(list_payload[0]["public_id"], run.public_id)
        self.assertNotIn("id", list_payload[0])
        self.assertEqual(detail_payload["public_id"], run.public_id)
        self.assertEqual(detail_payload["artifacts"][0]["artifact_type"], "summary_card")
        self.assertEqual(detail_payload["artifacts"][0]["chart_schema"]["schema_version"], "chart.v1")
        self.assertEqual(detail_payload["artifacts"][0]["evidence_refs"], ["journal:today", "dataset:positions"])
        self.assertNotIn("id", detail_payload["artifacts"][0])

    def test_get_insight_artifact_detail(self):
        service = InsightArtifactService(self.db)
        run = service.start_run(
            user_id=self.user.id,
            run_type="analysis.strategy_health",
            prompt_version="v1",
            input_refs=[],
            started_at=datetime(2026, 6, 5, 10, 0, tzinfo=timezone.utc),
        )
        artifact = service.add_artifact(
            run_public_id=run.public_id,
            artifact_type="analysis_card",
            title="Strategy health",
            summary="Average loss needs work.",
            content_markdown=None,
            payload={"linked_surface": "insights"},
            evidence_refs=["analysis:strategy_health"],
            chart_schema=None,
            trust_meta={"freshness": "FRESH", "source": "AI_GENERATED", "source_refs": ["dataset:positions"]},
        )
        service.complete_run(run_public_id=run.public_id, status="COMPLETED")
        self.db.commit()

        response = self.client.get(f"/api/v1/insights/artifacts/{artifact.public_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["public_id"], artifact.public_id)
        self.assertEqual(payload["run"]["public_id"], run.public_id)
        self.assertEqual(payload["summary"], "Average loss needs work.")
        self.assertNotIn("id", payload)


if __name__ == "__main__":
    unittest.main()
