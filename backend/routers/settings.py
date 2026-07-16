"""
Trading Noobs Backend - User Settings Router
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserSettings
from schemas import UserSettingsUpdate, UserSettingsResponse
from release_profile import RuntimeCapability, is_capability_enabled
from routers.disabled_capabilities import raise_feature_disabled
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def mask_api_key(key: str | None) -> str | None:
    """Mask API key for security"""
    if not key:
        return None
    if len(key) <= 8:
        return "********"
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


_BROKER_SETTING_FIELDS = {
    "ibkr_flex_query_id",
    "ibkr_flex_token",
    "ibkr_flex_start_date",
    "binance_api_key",
    "binance_api_secret",
    "binance_market_type",
    "binance_symbols",
}
_MARKET_SETTING_FIELDS = {"finnhub_api_key"}


def _enforce_settings_capability_boundary(update_data: dict) -> None:
    if _BROKER_SETTING_FIELDS.intersection(update_data) and not is_capability_enabled(
        RuntimeCapability.BROKER_SYNC
    ):
        raise_feature_disabled(RuntimeCapability.BROKER_SYNC.value)
    if _MARKET_SETTING_FIELDS.intersection(update_data) and not is_capability_enabled(
        RuntimeCapability.MARKET
    ):
        raise_feature_disabled(RuntimeCapability.MARKET.value)


def _profile_safe_response(settings: UserSettings) -> UserSettingsResponse:
    response = UserSettingsResponse.model_validate(settings)
    if is_capability_enabled(RuntimeCapability.BROKER_SYNC):
        response.ibkr_flex_token = mask_api_key(settings.ibkr_flex_token)
        response.binance_api_key = mask_api_key(settings.binance_api_key)
        response.binance_api_secret_configured = bool(settings.binance_api_secret)
    else:
        response.ibkr_flex_query_id = None
        response.ibkr_flex_token = None
        response.ibkr_flex_start_date = None
        response.binance_api_key = None
        response.binance_api_secret_configured = False
        response.binance_market_type = None
        response.binance_symbols = None
    response.finnhub_api_key = (
        mask_api_key(settings.finnhub_api_key)
        if is_capability_enabled(RuntimeCapability.MARKET)
        else None
    )
    return response


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
    
    return _profile_safe_response(settings)


@router.patch("", response_model=UserSettingsResponse)
async def update_settings(
    settings_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user settings"""
    update_data = settings_data.model_dump(exclude_unset=True)
    _enforce_settings_capability_boundary(update_data)

    settings = db.query(UserSettings).filter(
        UserSettings.user_id == current_user.id
    ).first()
    
    if not settings:
        settings = UserSettings(user_id=current_user.id)
        db.add(settings)
    
    for field, value in update_data.items():
        setattr(settings, field, value)
    
    db.commit()
    db.refresh(settings)
    
    return _profile_safe_response(settings)
