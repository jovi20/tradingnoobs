"""
Trading Noobs Backend - User Settings Router
"""
from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserSettings
from schemas import UserSettingsUpdate, UserSettingsResponse
from release_profile import RuntimeCapability
from routers.disabled_capabilities import raise_feature_disabled
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/settings", tags=["Settings"])


def mask_api_key(key: str | None) -> str | None:
    if not key:
        return None
    if len(key) <= 8:
        return "********"
    return key[:4] + "*" * (len(key) - 8) + key[-4:]


_RETIRED_SETTING_FIELDS = {
    RuntimeCapability.BROKER_SYNC: {
        "ibkr_flex_query_id",
        "ibkr_flex_token",
        "ibkr_flex_start_date",
        "binance_api_key",
        "binance_api_secret",
        "binance_market_type",
        "binance_symbols",
    },
    RuntimeCapability.MARKET: {"finnhub_api_key"},
    RuntimeCapability.AI_INSIGHTS: {"llm_api_url", "llm_api_key", "llm_model"},
}


def _enforce_settings_capability_boundary(
    update_data: dict,
    *,
    effective_capabilities: frozenset[RuntimeCapability],
) -> None:
    """Compatibility guard for retired callers; the request schema rejects these fields."""
    for capability, fields in _RETIRED_SETTING_FIELDS.items():
        if fields.intersection(update_data):
            raise_feature_disabled(capability.value)


_CORE_RESPONSE_COLUMNS = (
    UserSettings.id,
    UserSettings.user_id,
    UserSettings.theme,
    UserSettings.up_color,
    UserSettings.display_currency,
)


def _load_settings_projection(
    db: Session,
    user_id: int,
) -> dict | None:
    return db.execute(
        select(*_CORE_RESPONSE_COLUMNS).where(
            UserSettings.user_id == user_id
        )
    ).mappings().first()


def _profile_safe_response(settings: dict) -> UserSettingsResponse:
    return UserSettingsResponse(
        id=settings["id"],
        user_id=settings["user_id"],
        theme=settings["theme"] or "system",
        up_color=settings["up_color"] or "GREEN",
        display_currency="USD",
    )


@router.get(
    "",
    response_model=UserSettingsResponse,
    response_model_exclude_unset=True,
)
async def get_settings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user settings"""
    settings = _load_settings_projection(db, current_user.id)
    
    if not settings:
        # Create default settings
        db.add(UserSettings(user_id=current_user.id))
        db.commit()
        settings = _load_settings_projection(db, current_user.id)
    
    return _profile_safe_response(settings)


@router.patch(
    "",
    response_model=UserSettingsResponse,
    response_model_exclude_unset=True,
)
async def update_settings(
    settings_data: UserSettingsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update user settings"""
    update_data = settings_data.model_dump(exclude_unset=True)
    settings_id = db.execute(
        select(UserSettings.id).where(UserSettings.user_id == current_user.id)
    ).scalar_one_or_none()
    if settings_id is None:
        db.add(UserSettings(user_id=current_user.id, **update_data))
    elif update_data:
        db.execute(
            update(UserSettings)
            .where(UserSettings.id == settings_id)
            .values(**update_data)
        )
    
    db.commit()
    settings = _load_settings_projection(db, current_user.id)
    return _profile_safe_response(settings)
