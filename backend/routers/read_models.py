from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from routers.auth import get_current_user
from services.read_model_service import ReadModelService


router = APIRouter(prefix="/api/v1/read-models", tags=["v1-read-models"])


@router.get("/home")
def get_home_read_model(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ReadModelService(db).build_home_read_model(user_id=current_user.id)


@router.get("/trading-positions/{position_public_id}/lifecycle")
def get_lifecycle_read_model(
    position_public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return ReadModelService(db).build_lifecycle_detail(
        user_id=current_user.id,
        position_public_id=position_public_id,
    )
