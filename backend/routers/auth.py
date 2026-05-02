"""
Trading Noobs Backend - Authentication Router
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from jose import JWTError

from database import get_db
from schemas import UserCreate, UserResponse, Token
from services.auth_service import (
    authenticate_user,
    get_user_by_email,
    get_current_user,
    create_authenticated_session,
    create_user,
    oauth2_scheme,
    revoke_access_token,
)
from models import User, UserSettings, Strategy
from app_config.default_strategies import DEFAULT_STRATEGIES

router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user"""
    # Validate invitation code (case-insensitive)
    VALID_INVITE_CODE = "bigme"
    if user_data.invite_code.lower() != VALID_INVITE_CODE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid invitation code"
        )
    
    # Check if user exists
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = create_user(db, user_data.email, user_data.password)
    
    # Create default settings
    settings = UserSettings(user_id=user.id)
    db.add(settings)
    
    # Create default strategies
    for strategy_data in DEFAULT_STRATEGIES:
        strategy = Strategy(
            user_id=user.id,
            name=strategy_data["name"],
            description=strategy_data.get("description"),
            entry_rules=strategy_data.get("entry_rules"),
            exit_rules=strategy_data.get("exit_rules"),
            risk_rules=strategy_data.get("risk_rules"),
            symbols=[]
        )
        db.add(strategy)
    
    db.commit()
    
    return user


@router.post("/login", response_model=Token)
def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """Login and get access token"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = create_authenticated_session(
        db=db,
        user=user,
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info"""
    return current_user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    """Revoke the current access token and its session."""
    try:
        revoke_access_token(db, token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
