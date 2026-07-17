"""
Trading Noobs Backend - User Settings Router
"""
from collections.abc import Mapping
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from database import get_db
from models import User, UserSettings
from schemas import UserSettingsUpdate, UserSettingsResponse
from release_profile import RuntimeCapability
from routers.disabled_capabilities import raise_feature_disabled
from services.auth_service import get_current_user
from services.capability_service import is_effective_capability_enabled

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
_AI_SETTING_FIELDS = {"llm_api_url", "llm_api_key", "llm_model"}

_CORE_RESPONSE_COLUMNS = (
    UserSettings.id,
    UserSettings.user_id,
    UserSettings.theme,
    UserSettings.up_color,
    UserSettings.display_currency,
)
_BROKER_RESPONSE_COLUMNS = (
    UserSettings.ibkr_flex_query_id,
    UserSettings.ibkr_flex_token,
    UserSettings.ibkr_flex_start_date,
    UserSettings.binance_api_key,
    UserSettings.binance_api_secret,
    UserSettings.binance_market_type,
    UserSettings.binance_symbols,
)
_MARKET_RESPONSE_COLUMNS = (UserSettings.finnhub_api_key,)
_AI_RESPONSE_COLUMNS = (UserSettings.llm_api_url, UserSettings.llm_model)


_SETTING_FIELDS_BY_CAPABILITY = {
    RuntimeCapability.BROKER_SYNC: _BROKER_SETTING_FIELDS,
    RuntimeCapability.MARKET: _MARKET_SETTING_FIELDS,
    RuntimeCapability.AI_INSIGHTS: _AI_SETTING_FIELDS,
}


def _effective_settings_capabilities(
    db: Session,
    *,
    actor_key: str,
) -> frozenset[RuntimeCapability]:
    return frozenset(
        capability
        for capability in _SETTING_FIELDS_BY_CAPABILITY
        if is_effective_capability_enabled(
            db,
            capability,
            actor_key=actor_key,
        )
    )


def _enforce_settings_capability_boundary(
    update_data: dict,
    *,
    effective_capabilities: frozenset[RuntimeCapability],
) -> None:
    for capability, fields in _SETTING_FIELDS_BY_CAPABILITY.items():
        if not fields.intersection(update_data):
            continue
        if capability not in effective_capabilities:
            raise_feature_disabled(capability.value)


def _response_columns(
    effective_capabilities: frozenset[RuntimeCapability],
) -> tuple[Any, ...]:
    columns = list(_CORE_RESPONSE_COLUMNS)
    if RuntimeCapability.BROKER_SYNC in effective_capabilities:
        columns.extend(_BROKER_RESPONSE_COLUMNS)
    if RuntimeCapability.MARKET in effective_capabilities:
        columns.extend(_MARKET_RESPONSE_COLUMNS)
    if RuntimeCapability.AI_INSIGHTS in effective_capabilities:
        columns.extend(_AI_RESPONSE_COLUMNS)
    return tuple(columns)


def _load_settings_projection(
    db: Session,
    user_id: int,
    *,
    effective_capabilities: frozenset[RuntimeCapability],
) -> Mapping[str, Any] | None:
    return db.execute(
        select(*_response_columns(effective_capabilities)).where(
            UserSettings.user_id == user_id
        )
    ).mappings().first()


def _setting_value(
    settings: Mapping[str, Any] | UserSettings,
    field: str,
    default: Any = None,
) -> Any:
    if isinstance(settings, Mapping):
        return settings.get(field, default)
    return getattr(settings, field, default)


def _profile_safe_response(
    settings: Mapping[str, Any] | UserSettings,
    *,
    effective_capabilities: frozenset[RuntimeCapability],
) -> UserSettingsResponse:
    response_data: dict[str, Any] = {
        "id": _setting_value(settings, "id"),
        "user_id": _setting_value(settings, "user_id"),
        "theme": _setting_value(settings, "theme", "system") or "system",
        "up_color": _setting_value(settings, "up_color", "GREEN") or "GREEN",
        "display_currency": "USD",
    }
    if RuntimeCapability.BROKER_SYNC in effective_capabilities:
        response_data.update(
            ibkr_flex_query_id=_setting_value(settings, "ibkr_flex_query_id"),
            ibkr_flex_token=mask_api_key(_setting_value(settings, "ibkr_flex_token")),
            ibkr_flex_start_date=_setting_value(settings, "ibkr_flex_start_date"),
            binance_api_key=mask_api_key(_setting_value(settings, "binance_api_key")),
            binance_api_secret_configured=bool(
                _setting_value(settings, "binance_api_secret")
            ),
            binance_market_type=_setting_value(settings, "binance_market_type"),
            binance_symbols=_setting_value(settings, "binance_symbols"),
        )
    if RuntimeCapability.MARKET in effective_capabilities:
        response_data["finnhub_api_key"] = mask_api_key(
            _setting_value(settings, "finnhub_api_key")
        )
    if RuntimeCapability.AI_INSIGHTS in effective_capabilities:
        response_data.update(
            llm_api_url=_setting_value(settings, "llm_api_url"),
            llm_model=_setting_value(settings, "llm_model"),
        )

    return UserSettingsResponse(**response_data)


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
    effective_capabilities = _effective_settings_capabilities(
        db,
        actor_key=current_user.public_id,
    )
    settings = _load_settings_projection(
        db,
        current_user.id,
        effective_capabilities=effective_capabilities,
    )
    
    if not settings:
        # Create default settings
        db.add(UserSettings(user_id=current_user.id))
        db.commit()
        settings = _load_settings_projection(
            db,
            current_user.id,
            effective_capabilities=effective_capabilities,
        )
    
    return _profile_safe_response(
        settings,
        effective_capabilities=effective_capabilities,
    )


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
    effective_capabilities = _effective_settings_capabilities(
        db,
        actor_key=current_user.public_id,
    )
    _enforce_settings_capability_boundary(
        update_data,
        effective_capabilities=effective_capabilities,
    )

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
    settings = _load_settings_projection(
        db,
        current_user.id,
        effective_capabilities=effective_capabilities,
    )
    return _profile_safe_response(
        settings,
        effective_capabilities=effective_capabilities,
    )
