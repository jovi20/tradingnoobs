from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import NoResultFound

from database import get_db
from models import User
from routers.auth import get_current_user
from services.insight_artifact_service import InsightArtifactService


router = APIRouter(prefix="/api/v1/insights/runs", tags=["v1-insight-runs"])


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
    except NoResultFound:
        raise HTTPException(status_code=404, detail="Insight run not found")
