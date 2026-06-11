from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import RiskSummaryResponse
from services.auth_service import get_current_user
from services.risk_alert_service import build_portfolio_risk_summary


router = APIRouter(prefix="/api/risk", tags=["Risk"])


@router.get("/summary", response_model=RiskSummaryResponse)
async def get_risk_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return build_portfolio_risk_summary(db, current_user.id)
