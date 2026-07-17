"""Legacy registration handler isolated behind the OPEN_REGISTRATION capability."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app_config.default_strategies import DEFAULT_STRATEGIES
from database import get_db
from models import Strategy, UserSettings
from schemas import UserCreate, UserResponse
from services.auth_service import create_user, get_user_by_email


router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    if user_data.invite_code.lower() != "bigme":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation code",
        )

    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = create_user(db, user_data.email, user_data.password)
    db.add(UserSettings(user_id=user.id))
    for strategy_data in DEFAULT_STRATEGIES:
        db.add(
            Strategy(
                user_id=user.id,
                name=strategy_data["name"],
                description=strategy_data.get("description"),
                entry_rules=strategy_data.get("entry_rules"),
                exit_rules=strategy_data.get("exit_rules"),
                risk_rules=strategy_data.get("risk_rules"),
                symbols=[],
            )
        )
    db.commit()
    return user
