import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import User
from services.auth_service import create_user
from services.insight_artifact_service import InsightArtifactService


class InsightArtifactServiceTests(unittest.TestCase):
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
        self.user = create_user(self.db, "artifacts@example.com", "password123")

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_insight_run_artifacts_are_auditable_and_evidence_linked(self):
        service = InsightArtifactService(self.db)

        run = service.start_run(
            user_id=self.user.id,
            run_type="analysis.strategy_health",
            prompt_version="v1",
            input_refs=["analysis:strategy_health", "surface:insights"],
            started_at=datetime(2026, 6, 5, 12, 0, tzinfo=timezone.utc),
        )

        artifact = service.add_artifact(
            run_public_id=run.public_id,
            artifact_type="analysis_card",
            title="Strategy health sidecar",
            summary="Win rate is stable but average loss still dominates expectancy.",
            content_markdown="## Legacy body",
            payload={"linked_surface": "insights"},
            evidence_refs=["analysis:strategy_health", "dataset:positions"],
            chart_schema={
                "schema_version": "chart.v1",
                "chart_type": "bar",
                "series": [{"field": "avg_pnl", "label": "Average PnL"}],
            },
            trust_meta={
                "freshness": "FRESH",
                "source": "AI_GENERATED",
                "source_refs": ["analysis:strategy_health", "dataset:positions"],
            },
        )
        service.complete_run(run_public_id=run.public_id, status="COMPLETED")
        self.db.commit()

        hydrated = service.get_run_with_artifacts(user_id=self.user.id, run_public_id=run.public_id)

        self.assertEqual(hydrated["public_id"], run.public_id)
        self.assertEqual(hydrated["artifacts"][0]["public_id"], artifact.public_id)
        self.assertEqual(hydrated["artifacts"][0]["evidence_refs"], ["analysis:strategy_health", "dataset:positions"])
        self.assertEqual(hydrated["artifacts"][0]["chart_schema"]["schema_version"], "chart.v1")
        self.assertEqual(hydrated["artifacts"][0]["trust_meta"]["source"], "AI_GENERATED")

    def test_get_artifact_by_public_id_is_user_scoped(self):
        service = InsightArtifactService(self.db)
        run = service.start_run(
            user_id=self.user.id,
            run_type="analysis.strategy_health",
            prompt_version="v1",
            input_refs=["analysis:strategy_health"],
        )
        artifact = service.add_artifact(
            run_public_id=run.public_id,
            artifact_type="analysis_card",
            title="Strategy health",
            summary="Average loss needs work.",
            content_markdown="# Legacy body",
            payload={"linked_surface": "insights"},
            evidence_refs=["analysis:strategy_health"],
            chart_schema={"schema_version": "chart.v1", "chart_type": "bar", "series": [{"field": "avg_pnl", "label": "Average PnL"}]},
            trust_meta={"freshness": "FRESH", "source": "AI_GENERATED", "source_refs": ["dataset:positions"]},
        )
        service.complete_run(run_public_id=run.public_id)
        other_user = create_user(self.db, "artifact-other@example.com", "password123")
        self.db.commit()

        payload = service.get_artifact(user_id=self.user.id, artifact_public_id=artifact.public_id)

        self.assertEqual(payload["public_id"], artifact.public_id)
        self.assertEqual(payload["run"]["public_id"], run.public_id)
        self.assertEqual(payload["summary"], "Average loss needs work.")
        with self.assertRaises(Exception):
            service.get_artifact(user_id=other_user.id, artifact_public_id=artifact.public_id)


if __name__ == "__main__":
    unittest.main()
