from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from models import InsightArtifact, InsightRun


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class InsightArtifactService:
    def __init__(self, db: Session):
        self.db = db

    def start_run(
        self,
        *,
        user_id: int,
        run_type: str,
        prompt_version: str | None,
        input_refs: list[str],
        started_at: datetime | None = None,
        status: str = "RUNNING",
    ) -> InsightRun:
        run = InsightRun(
            user_id=user_id,
            run_type=run_type,
            status=status,
            prompt_version=prompt_version,
            input_refs=input_refs,
            started_at=started_at or _utc_now(),
            completed_at=(started_at or _utc_now()) if status == "COMPLETED" else None,
        )
        self.db.add(run)
        self.db.flush()
        return run

    def complete_run(
        self,
        *,
        run_public_id: str,
        status: str = "COMPLETED",
        error_code: str | None = None,
        error_message: str | None = None,
        completed_at: datetime | None = None,
    ) -> InsightRun:
        run = self.db.query(InsightRun).filter_by(public_id=run_public_id).one()
        run.status = status
        run.completed_at = completed_at or _utc_now()
        run.error_code = error_code
        run.error_message = error_message
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
        content_markdown: str | None,
        payload: dict,
        evidence_refs: list[str],
        chart_schema: dict | None,
        trust_meta: dict,
    ) -> InsightArtifact:
        run = self.db.query(InsightRun).filter_by(public_id=run_public_id).one()
        artifact = InsightArtifact(
            insight_run_id=run.id,
            artifact_type=artifact_type,
            title=title,
            summary=summary,
            content_markdown=content_markdown,
            payload=payload,
            evidence_refs=evidence_refs,
            chart_schema=chart_schema,
            trust_meta=trust_meta,
        )
        self.db.add(artifact)
        self.db.flush()
        return artifact

    def list_runs(self, *, user_id: int, limit: int = 20) -> list[dict]:
        runs = (
            self.db.query(InsightRun)
            .filter(InsightRun.user_id == user_id)
            .order_by(InsightRun.started_at.desc(), InsightRun.id.desc())
            .limit(limit)
            .all()
        )
        return [self.get_run_with_artifacts(user_id=user_id, run_public_id=run.public_id) for run in runs]

    def get_run_with_artifacts(self, *, user_id: int, run_public_id: str) -> dict:
        run = (
            self.db.query(InsightRun)
            .filter(InsightRun.user_id == user_id, InsightRun.public_id == run_public_id)
            .one()
        )
        artifacts = (
            self.db.query(InsightArtifact)
            .filter(InsightArtifact.insight_run_id == run.id)
            .order_by(InsightArtifact.created_at, InsightArtifact.id)
            .all()
        )
        return self._run_dict(run=run, artifacts=artifacts)

    def get_artifact(self, *, user_id: int, artifact_public_id: str) -> dict:
        artifact = (
            self.db.query(InsightArtifact)
            .join(InsightRun)
            .filter(InsightRun.user_id == user_id, InsightArtifact.public_id == artifact_public_id)
            .one()
        )
        payload = self._artifact_dict(artifact)
        payload["run"] = self._run_summary_dict(artifact.run)
        return payload

    def list_artifacts_for_object(
        self,
        *,
        user_id: int,
        linked_object_public_id: str,
        limit: int = 5,
    ) -> list[dict]:
        runs = (
            self.db.query(InsightRun)
            .filter(InsightRun.user_id == user_id)
            .order_by(InsightRun.started_at.desc(), InsightRun.id.desc())
            .all()
        )
        items: list[dict] = []
        for run in runs:
            for artifact in run.artifacts:
                payload_link = artifact.payload.get("linked_object_public_id") if isinstance(artifact.payload, dict) else None
                source_refs = artifact.trust_meta.get("source_refs", []) if isinstance(artifact.trust_meta, dict) else []
                if (
                    payload_link == linked_object_public_id
                    or linked_object_public_id in (run.input_refs or [])
                    or linked_object_public_id in (artifact.evidence_refs or [])
                    or linked_object_public_id in source_refs
                ):
                    items.append(self._artifact_dict(artifact))
        return items[:limit]

    @classmethod
    def _run_dict(cls, *, run: InsightRun, artifacts: list[InsightArtifact]) -> dict:
        return {
            "public_id": run.public_id,
            "run_type": run.run_type,
            "status": run.status,
            "prompt_version": run.prompt_version,
            "input_refs": run.input_refs or [],
            "started_at": run.started_at.isoformat().replace("+00:00", "Z"),
            "completed_at": run.completed_at.isoformat().replace("+00:00", "Z") if run.completed_at else None,
            "error_code": run.error_code,
            "error_message": run.error_message,
            "artifacts": [cls._artifact_dict(artifact) for artifact in artifacts],
        }

    @staticmethod
    def _run_summary_dict(run: InsightRun) -> dict:
        return {
            "public_id": run.public_id,
            "run_type": run.run_type,
            "status": run.status,
            "prompt_version": run.prompt_version,
            "input_refs": run.input_refs or [],
            "started_at": run.started_at.isoformat().replace("+00:00", "Z"),
            "completed_at": run.completed_at.isoformat().replace("+00:00", "Z") if run.completed_at else None,
            "error_code": run.error_code,
            "error_message": run.error_message,
        }

    @staticmethod
    def _artifact_dict(artifact: InsightArtifact) -> dict:
        return {
            "public_id": artifact.public_id,
            "artifact_type": artifact.artifact_type,
            "title": artifact.title,
            "summary": artifact.summary,
            "content_markdown": artifact.content_markdown,
            "payload": artifact.payload or {},
            "evidence_refs": artifact.evidence_refs or [],
            "chart_schema": artifact.chart_schema,
            "trust_meta": artifact.trust_meta or {},
            "created_at": artifact.created_at.isoformat().replace("+00:00", "Z") if artifact.created_at else None,
        }
