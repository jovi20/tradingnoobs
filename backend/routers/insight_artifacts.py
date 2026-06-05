from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services.auth_service import get_current_user
from services.insight_artifact_service import InsightArtifactService

router = APIRouter(prefix="/api/v1/insights/runs", tags=["Insight Artifacts"])
artifact_router = APIRouter(prefix="/api/v1/insights/artifacts", tags=["Insight Artifacts"])


@router.get("")
def list_insight_runs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return InsightArtifactService(db).list_runs(user_id=current_user.id)


@router.get("/{run_public_id}")
def get_insight_run(
    run_public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return InsightArtifactService(db).get_run_with_artifacts(
            user_id=current_user.id,
            run_public_id=run_public_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Insight run not found") from exc


@artifact_router.get("/{artifact_public_id}")
def get_insight_artifact(
    artifact_public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return InsightArtifactService(db).get_artifact(
            user_id=current_user.id,
            artifact_public_id=artifact_public_id,
        )
    except Exception as exc:
        raise HTTPException(status_code=404, detail="Insight artifact not found") from exc
