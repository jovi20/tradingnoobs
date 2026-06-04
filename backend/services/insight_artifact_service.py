from datetime import datetime, timezone

from models import InsightArtifact, InsightRun
from services.identity_service import generate_public_id


class InsightArtifactService:
    def __init__(self, db_session):
        self.db = db_session

    def start_run(
        self,
        *,
        user_id: int,
        run_type: str,
        input_refs: list[str],
        prompt_version: str | None,
        started_at: datetime | None = None,
    ) -> InsightRun:
        run = InsightRun(
            public_id=generate_public_id(),
            user_id=user_id,
            run_type=run_type,
            status="RUNNING",
            prompt_version=prompt_version,
            input_refs=input_refs,
            started_at=started_at or datetime.now(timezone.utc),
        )
        self.db.add(run)
        self.db.flush()
        return run

    def add_artifact(
        self,
        *,
        run_public_id: str,
        artifact_type: str,
        title: str,
        summary: str,
        evidence_refs: list[str],
        payload: dict,
        chart_schema: dict | None = None,
        trust_meta: dict | None = None,
        content_markdown: str | None = None,
    ) -> InsightArtifact:
        run = self.db.query(InsightRun).filter_by(public_id=run_public_id).one()
        artifact = InsightArtifact(
            public_id=generate_public_id(),
            insight_run_id=run.id,
            artifact_type=artifact_type,
            title=title,
            summary=summary,
            content_markdown=content_markdown,
            payload=payload,
            evidence_refs=evidence_refs,
            chart_schema=chart_schema,
            trust_meta=trust_meta or {},
        )
        self.db.add(artifact)
        run.status = "COMPLETED"
        run.completed_at = datetime.now(timezone.utc)
        self.db.flush()
        return artifact

    def get_run_with_artifacts(self, *, user_id: int, run_public_id: str) -> dict:
        run = self.db.query(InsightRun).filter_by(user_id=user_id, public_id=run_public_id).one()
        artifacts = (
            self.db.query(InsightArtifact)
            .filter_by(insight_run_id=run.id)
            .order_by(InsightArtifact.created_at, InsightArtifact.id)
            .all()
        )
        return self._run_dict(run=run, artifacts=artifacts)

    def list_runs(self, *, user_id: int) -> list[dict]:
        runs = (
            self.db.query(InsightRun)
            .filter_by(user_id=user_id)
            .order_by(InsightRun.started_at.desc(), InsightRun.id.desc())
            .all()
        )
        return [self._run_dict(run=run, artifacts=[]) for run in runs]

    @classmethod
    def _run_dict(cls, *, run: InsightRun, artifacts: list[InsightArtifact]) -> dict:
        return {
            "public_id": run.public_id,
            "run_type": run.run_type,
            "status": run.status,
            "prompt_version": run.prompt_version,
            "input_refs": run.input_refs,
            "started_at": cls._isoformat(run.started_at),
            "completed_at": cls._isoformat(run.completed_at) if run.completed_at else None,
            "error_code": run.error_code,
            "error_message": run.error_message,
            "artifacts": [cls._artifact_dict(artifact) for artifact in artifacts],
        }

    @staticmethod
    def _artifact_dict(artifact: InsightArtifact) -> dict:
        return {
            "public_id": artifact.public_id,
            "artifact_type": artifact.artifact_type,
            "title": artifact.title,
            "summary": artifact.summary,
            "content_markdown": artifact.content_markdown,
            "payload": artifact.payload,
            "evidence_refs": artifact.evidence_refs,
            "chart_schema": artifact.chart_schema,
            "trust_meta": artifact.trust_meta,
        }

    @staticmethod
    def _isoformat(value: datetime) -> str:
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.isoformat()
