"""
Trading Noobs Backend - User Settings Router
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserSettings
from schemas import UserSettingsUpdate, UserSettingsResponse
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def mask_api_key(key: str | None) -> str | None:
    """Mask API key for security"""
    if not key or len(key) < 8:
        return key
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user settings"""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        # Create default settings
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
        db.commit()
        db.refresh(settings)
    
    # Mask sensitive keys in response
    response = UserSettingsResponse.model_validate(settings)
    response.binance_api_key = mask_api_key(settings.binance_api_key)
    response.finnhub_api_key = mask_api_key(settings.finnhub_api_key)
    
    return response


@router.patch("", response_model=UserSettingsResponse)
async def update_settings(
    settings_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user settings"""
    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
    
    update_data = settings_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    # Mask sensitive keys in response
    response = UserSettingsResponse.model_validate(settings)
    response.binance_api_key = mask_api_key(settings.binance_api_key)
    response.finnhub_api_key = mask_api_key(settings.finnhub_api_key)
    
    return response
