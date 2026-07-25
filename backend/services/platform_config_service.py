"""
Trading Noobs Backend - Platform Config Resolution Helpers
"""
import hashlib
import os
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import get_ai_provider_settings, get_market_provider_settings
from models import FeatureFlag, IntegrationCredential, PlatformSetting, SystemSetting
from services.credential_service import decrypt_secret


_PLAINTEXT_SECRET_MARKERS = (
    "api_key",
    "apikey",
    "token",
    "secret",
    "password",
    "credential",
    "private_key",
    "access_key",
    "connection_string",
    "flex_query_id",
)


def _is_plaintext_secret_setting_key(key: str) -> bool:
    normalized = key.strip().lower().replace("-", "_")
    return any(marker in normalized for marker in _PLAINTEXT_SECRET_MARKERS)


def _stable_rollout_bucket(key: str, actor_key: str) -> int:
    digest = hashlib.sha256(f"{key}:{actor_key}".encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % 100


def get_platform_setting_value(db: Session, key: str) -> Optional[str]:
    if _is_plaintext_secret_setting_key(key):
        return None
    setting = db.query(PlatformSetting).filter(PlatformSetting.key == key).first()
    if setting and setting.value:
        return setting.value

    legacy = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    if legacy and legacy.value:
        return legacy.value
    return None


def get_integration_credential_secret(
    db: Session,
    provider_key: str,
    credential_key: str,
) -> Optional[str]:
    credential = db.query(IntegrationCredential).filter(
        IntegrationCredential.provider_key == provider_key,
        IntegrationCredential.credential_key == credential_key,
        IntegrationCredential.is_active == True,
    ).first()
    if credential:
        return decrypt_secret(credential.secret_ciphertext)
    return None


def get_feature_flag_enabled(db: Session, key: str, *, actor_key: str | None = None) -> bool:
    try:
        # Session.begin_nested() flushes all pending ORM state before opening its
        # SAVEPOINT. A capability read must neither flush nor poison a caller's
        # journal transaction, so query committed database state through the
        # enlisted connection and isolate only this statement in a SAVEPOINT.
        connection = db.connection()
        with connection.begin_nested():
            feature_flag = connection.execute(
                select(
                    FeatureFlag.enabled,
                    FeatureFlag.expires_at,
                    FeatureFlag.actor_targets,
                    FeatureFlag.rollout_percentage,
                ).where(FeatureFlag.key == key)
            ).mappings().first()
            if feature_flag is None or feature_flag["enabled"] is not True:
                return False

            expires_at = feature_flag["expires_at"]
            if expires_at is not None:
                if not isinstance(expires_at, datetime):
                    return False
                if expires_at.tzinfo is None:
                    expires_at = expires_at.replace(tzinfo=timezone.utc)
                if expires_at <= datetime.now(timezone.utc):
                    return False

            actor_targets = feature_flag["actor_targets"]
            if actor_targets is None:
                actor_targets = []
            if not isinstance(actor_targets, list) or any(
                not isinstance(target, str) or not target.strip()
                for target in actor_targets
            ):
                return False

            rollout_percentage = feature_flag["rollout_percentage"]
            if rollout_percentage is not None and (
                isinstance(rollout_percentage, bool)
                or not isinstance(rollout_percentage, int)
                or not 0 <= rollout_percentage <= 100
            ):
                return False

            if actor_key is not None and (
                not isinstance(actor_key, str) or not actor_key.strip()
            ):
                return False

            if actor_key is not None and actor_key in actor_targets:
                return True
            if rollout_percentage is not None:
                if actor_key is None:
                    return False
                return _stable_rollout_bucket(key, actor_key) < rollout_percentage
            if actor_targets:
                return False
            return True
    except Exception:
        return False


def get_llm_runtime_config(db: Session) -> dict[str, Optional[str]]:
    settings = get_ai_provider_settings()
    api_url = get_platform_setting_value(db, "llm_api_url") or os.getenv("LLM_API_URL") or settings.llm_api_url
    model = get_platform_setting_value(db, "llm_model") or os.getenv("LLM_MODEL") or settings.llm_model
    api_key = (
        get_integration_credential_secret(db, "openai", "api_key")
        or get_integration_credential_secret(db, "llm", "api_key")
        or os.getenv("LLM_API_KEY")
        or settings.llm_api_key
    )
    return {
        "api_url": api_url,
        "api_key": api_key,
        "model": model,
    }


def get_finnhub_api_key(db: Session) -> Optional[str]:
    settings = get_market_provider_settings()
    return (
        get_integration_credential_secret(db, "finnhub", "api_key")
        or os.getenv("FINNHUB_API_KEY")
        or settings.finnhub_api_key
    )
