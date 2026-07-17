from datetime import datetime, timedelta, timezone
import re
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from models import (
    BusinessLock,
    BusinessLockStatus,
    FeatureFlag,
    IntegrationCredential,
    JobDefinition,
    JobRun,
    JobRunStatus,
    PlatformSetting,
    SystemSetting,
    User,
)
from schemas import (
    AdminBackupResponse,
    AdminBackupSummaryResponse,
    AdminOpsSummaryResponse,
    AdminPasswordResetResponse,
    AdminUserActiveUpdate,
    AdminUserOperationResponse,
    AdminUserRoleUpdate,
    AdminUserSummaryResponse,
    FeatureFlagResponse,
    FeatureFlagUpdate,
    IntegrationCredentialActiveUpdate,
    IntegrationCredentialResponse,
    IntegrationCredentialUpdate,
    PlatformSettingResponse,
    PlatformSettingUpdate,
    SystemSettingResponse,
    SystemSettingUpdate,
)
from routers.auth import get_current_user
from release_profile import RuntimeCapability, is_capability_enabled
from routers.disabled_capabilities import raise_feature_disabled
from observability import get_structured_logger, log_event
from services.admin_user_service import (
    AdminUserNotFound,
    AdminUserOperationBlocked,
    promote_user_to_admin,
    reset_user_password,
    set_user_active_state,
    update_user_role,
)
from services.backup_service import BackupProviderNotConfigured, detect_database_backend, list_database_backups, trigger_database_backup
from services.credential_service import decrypt_secret, encrypt_secret, mask_secret
from services.job_service import cancel_job_run, force_cancel_running_job_run, requeue_job_run
from services.capability_service import (
    CAPABILITY_ROLLOUT_FLAG_KEYS,
    is_effective_capability_enabled,
)

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)
logger = get_structured_logger("admin")
ADMIN_BACKUP_DIR = "backend/backups"
DEFAULT_JOB_STALE_TIMEOUT_SECONDS = 30 * 60
FORCE_CANCEL_WARNING = "Force-cancel releases active business locks owned by this job and may leave partial work behind."
_BROKER_IDENTIFIER_ALIASES = (
    "ibkr",
    "interactive_broker",
    "interactive_brokers",
    "interactivebroker",
    "interactivebrokers",
    "binance",
    "broker_sync",
    "brokersync",
)
_MARKET_IDENTIFIER_ALIASES = (
    "finnhub",
    "yfinance",
    "y_finance",
    "yahoo_finance",
    "yahoofinance",
    "akshare",
    "polygon",
    "alpha_vantage",
    "alphavantage",
    "market_data",
    "marketdata",
)
_BROKER_IDENTIFIER_TOKENS = {"broker", "brokers", "brokerage"}
_MARKET_IDENTIFIER_TOKENS = {"market", "markets"}
_AI_IDENTIFIER_ALIASES = (
    "openai",
    "azure_openai",
    "azureopenai",
    "anthropic",
    "claude",
    "deep_seek",
    "deepseek",
    "gemini",
    "google_gemini",
    "googlegemini",
    "groq",
    "mistral",
    "cohere",
    "ollama",
    "llm",
    "ai_insights",
    "aiinsights",
    "insights",
)
_AI_IDENTIFIER_TOKENS = {"ai", "llm", "insight", "insights"}
_SECRET_IDENTIFIER_ALIASES = (
    "api_key",
    "apikey",
    "api_token",
    "access_token",
    "refresh_token",
    "client_secret",
    "access_key",
    "access_key_id",
    "service_account_key",
    "service_account_json",
    "signing_key",
    "encryption_key",
    "connection_string",
    "database_url",
    "private_key",
    "token",
    "secret",
    "password",
    "credential",
    "credentials",
)
_SECRET_COMPACT_MARKERS = (
    "apikey",
    "token",
    "secret",
    "password",
    "credential",
    "privatekey",
    "accesskey",
    "serviceaccountkey",
    "serviceaccountjson",
    "signingkey",
    "encryptionkey",
    "connectionstring",
    "databaseurl",
)
_PROVIDER_KEY_QUALIFIER_TOKENS = {
    "api",
    "dev",
    "development",
    "flex",
    "prod",
    "production",
    "sandbox",
    "test",
}
_CAPABILITY_IDENTIFIER_ALIASES = (
    (RuntimeCapability.BROKER_SYNC, _BROKER_IDENTIFIER_ALIASES),
    (RuntimeCapability.MARKET, _MARKET_IDENTIFIER_ALIASES),
    (RuntimeCapability.AI_INSIGHTS, _AI_IDENTIFIER_ALIASES),
)
_REGISTERED_CREDENTIAL_KEYS = {
    RuntimeCapability.BROKER_SYNC: frozenset({"api_key", "api_secret", "flex_token"}),
    RuntimeCapability.MARKET: frozenset({"api_key", "api_token", "access_token"}),
    RuntimeCapability.AI_INSIGHTS: frozenset({"api_key", "access_token"}),
}
_CAPABILITY_BY_ROLLOUT_FLAG_KEY = {
    key: capability for capability, key in CAPABILITY_ROLLOUT_FLAG_KEYS.items()
}
_CAPABILITY_ROLLOUT_FLAG_PREFIX = "capability."
_DEPLOYMENT_OWNED_SETTING_KEYS = frozenset(
    {"deployment_capability_allowlist", "release_profile"}
)
_SECRET_CONFIGURATION_UNAVAILABLE_DETAIL = {
    "code": "SECRET_CONFIGURATION_UNAVAILABLE",
    "message": "Secret configuration is unavailable",
}
_CONFIGURATION_KEY_UNAVAILABLE_DETAIL = {
    "code": "CONFIGURATION_KEY_UNAVAILABLE",
    "message": "Configuration key is unavailable",
}
_PUBLIC_CAPABILITY_ROLLOUT_INVALID_DETAIL = {
    "code": "PUBLIC_CAPABILITY_ROLLOUT_INVALID",
    "message": "Public capabilities require a global runtime rollout",
}


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def _identifier_tokens(value: str) -> tuple[str, ...]:
    with_word_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value.strip())
    return tuple(
        token
        for token in re.sub(r"[^A-Za-z0-9]+", "_", with_word_boundaries)
        .lower()
        .strip("_")
        .split("_")
        if token
    )


def _identifier_parts(value: str) -> tuple[set[str], str]:
    token_list = _identifier_tokens(value)
    return set(token_list), "".join(token_list)


def _identifier_contains_alias(value: str, aliases: tuple[str, ...]) -> bool:
    tokens = _identifier_tokens(value)
    if not tokens:
        return False

    for alias in aliases:
        alias_tokens = _identifier_tokens(alias)
        if not alias_tokens:
            continue
        width = len(alias_tokens)
        if any(
            tokens[index:index + width] == alias_tokens
            for index in range(len(tokens) - width + 1)
        ):
            return True
        if width > 1 and "".join(alias_tokens) in tokens:
            return True
    return False


def _identifier_starts_with_alias(value: str, aliases: tuple[str, ...]) -> bool:
    tokens = _identifier_tokens(value)
    if not tokens:
        return False

    for alias in aliases:
        alias_tokens = _identifier_tokens(alias)
        if not alias_tokens:
            continue
        if tokens[:len(alias_tokens)] == alias_tokens:
            remaining_tokens = tokens[len(alias_tokens):]
        elif len(alias_tokens) > 1 and tokens[0] == "".join(alias_tokens):
            remaining_tokens = tokens[1:]
        else:
            continue
        if all(
            token in _PROVIDER_KEY_QUALIFIER_TOKENS
            for token in remaining_tokens
        ):
            return True
    return False


def _registered_capability_for_identifier(
    identifier: str,
    *,
    provider_prefix_only: bool,
) -> RuntimeCapability | None:
    matcher = (
        _identifier_starts_with_alias
        if provider_prefix_only
        else _identifier_contains_alias
    )
    for capability, aliases in _CAPABILITY_IDENTIFIER_ALIASES:
        if matcher(identifier, aliases):
            return capability
    return None


def _is_secret_identifier(identifier: str) -> bool:
    _, compact = _identifier_parts(identifier)
    return _identifier_contains_alias(
        identifier,
        _SECRET_IDENTIFIER_ALIASES,
    ) or any(marker in compact for marker in _SECRET_COMPACT_MARKERS)


def _normalized_identifier_key(identifier: str) -> str:
    return "_".join(_identifier_tokens(identifier))


def _is_deployment_owned_setting_key(identifier: str) -> bool:
    return _normalized_identifier_key(identifier) in _DEPLOYMENT_OWNED_SETTING_KEYS


def _is_capability_namespace_key(identifier: str) -> bool:
    return identifier.strip().lower().startswith(_CAPABILITY_ROLLOUT_FLAG_PREFIX)


def _is_registered_credential_key(
    capability: RuntimeCapability,
    credential_key: str,
) -> bool:
    normalized_key = "_".join(_identifier_tokens(credential_key))
    return normalized_key in _REGISTERED_CREDENTIAL_KEYS.get(capability, frozenset())


def _optional_capability_for_identifiers(
    *identifiers: str,
) -> RuntimeCapability | None:
    identifiers_with_tokens = [
        (identifier, _identifier_parts(identifier)[0])
        for identifier in identifiers
        if identifier
    ]

    for identifier, tokens in identifiers_with_tokens:
        if _BROKER_IDENTIFIER_TOKENS.intersection(tokens) or (
            _registered_capability_for_identifier(
                identifier,
                provider_prefix_only=False,
            )
            == RuntimeCapability.BROKER_SYNC
        ):
            return RuntimeCapability.BROKER_SYNC

    for identifier, tokens in identifiers_with_tokens:
        if _MARKET_IDENTIFIER_TOKENS.intersection(tokens) or (
            _registered_capability_for_identifier(
                identifier,
                provider_prefix_only=False,
            )
            == RuntimeCapability.MARKET
        ):
            return RuntimeCapability.MARKET

    for identifier, tokens in identifiers_with_tokens:
        if _AI_IDENTIFIER_TOKENS.intersection(tokens) or (
            _registered_capability_for_identifier(
                identifier,
                provider_prefix_only=False,
            )
            == RuntimeCapability.AI_INSIGHTS
        ):
            return RuntimeCapability.AI_INSIGHTS

    return None


def _capability_is_visible(capability: RuntimeCapability | None) -> bool:
    return capability is None or is_capability_enabled(capability)


def _require_optional_capability(capability: RuntimeCapability | None) -> None:
    if capability is not None and not is_capability_enabled(capability):
        raise_feature_disabled(capability.value)


def _require_provider_capability(
    provider_key: str,
    credential_key: str | None = None,
) -> None:
    capability = _registered_capability_for_identifier(
        provider_key,
        provider_prefix_only=True,
    )
    if capability is None or (
        credential_key is not None
        and not _is_registered_credential_key(capability, credential_key)
    ):
        _raise_secret_configuration_unavailable()
    _require_optional_capability(capability)


def _require_setting_capability(key: str) -> None:
    if _is_deployment_owned_setting_key(key) or _is_capability_namespace_key(key):
        _raise_configuration_key_unavailable()
    if _is_secret_identifier(key):
        capability = _registered_capability_for_identifier(
            key,
            provider_prefix_only=False,
        )
        if capability is None:
            _raise_secret_configuration_unavailable()
    else:
        capability = _optional_capability_for_identifiers(key)
    _require_optional_capability(capability)


def _raise_secret_configuration_unavailable() -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=_SECRET_CONFIGURATION_UNAVAILABLE_DETAIL,
    )


def _raise_configuration_key_unavailable() -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=_CONFIGURATION_KEY_UNAVAILABLE_DETAIL,
    )


def _setting_key_is_visible(key: str) -> bool:
    if _is_deployment_owned_setting_key(key) or _is_capability_namespace_key(key):
        return False
    if _is_secret_identifier(key):
        capability = _registered_capability_for_identifier(
            key,
            provider_prefix_only=False,
        )
        return capability is not None and is_capability_enabled(capability)
    return _capability_is_visible(_optional_capability_for_identifiers(key))


def _provider_credential_is_visible(
    provider_key: str,
    credential_key: str,
) -> bool:
    capability = _registered_capability_for_identifier(
        provider_key,
        provider_prefix_only=True,
    )
    return (
        capability is not None
        and _is_registered_credential_key(capability, credential_key)
        and is_capability_enabled(capability)
    )


def _job_runtime_capabilities(
    *,
    job_key: str,
    definition_queue_name: str,
    run_queue_name: str,
) -> frozenset[RuntimeCapability]:
    capabilities: set[RuntimeCapability] = set()
    for identifier in (job_key, definition_queue_name, run_queue_name):
        capability = _optional_capability_for_identifiers(identifier)
        if capability is not None:
            capabilities.add(capability)

        tokens, compact = _identifier_parts(identifier)
        if "pdf" in tokens or compact.startswith("pdf"):
            capabilities.add(RuntimeCapability.PDF_EXPORT)
        if "risk" in tokens or compact.startswith("risk"):
            capabilities.add(RuntimeCapability.RISK_CARDS)
    return frozenset(capabilities)


def _job_identity_query(db: Session):
    return db.query(
        JobRun.id.label("job_run_id"),
        JobRun.public_id.label("job_public_id"),
        JobRun.queue_name.label("run_queue_name"),
        JobDefinition.key.label("definition_key"),
        JobDefinition.queue_name.label("definition_queue_name"),
    ).join(JobDefinition, JobDefinition.id == JobRun.job_definition_id)


def _job_identity_or_404(db: Session, job_public_id: str):
    identity = _job_identity_query(db).filter(
        JobRun.public_id == job_public_id
    ).first()
    if identity is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job run not found",
        )
    return identity


def _job_run_for_identity(db: Session, identity) -> JobRun:
    job_run = db.query(JobRun).filter(JobRun.id == identity.job_run_id).first()
    if job_run is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job run not found",
        )
    return job_run


def _job_runtime_capabilities_for_identity(identity) -> frozenset[RuntimeCapability]:
    return _job_runtime_capabilities(
        job_key=identity.definition_key,
        definition_queue_name=identity.definition_queue_name,
        run_queue_name=identity.run_queue_name,
    )


def _require_job_deployment_capabilities(identity) -> None:
    for capability in sorted(
        _job_runtime_capabilities_for_identity(identity),
        key=lambda item: item.value,
    ):
        _require_optional_capability(capability)


def _require_job_capability(
    db: Session,
    identity,
    *,
    actor_key: str,
) -> None:
    for capability in sorted(
        _job_runtime_capabilities_for_identity(identity),
        key=lambda item: item.value,
    ):
        if not is_effective_capability_enabled(
            db,
            capability,
            actor_key=actor_key,
        ):
            raise_feature_disabled(capability.value)


def _visible_job_run_query(db: Session):
    visible_definition_ids = [
        definition_id
        for definition_id, key, queue_name in db.query(
            JobDefinition.id,
            JobDefinition.key,
            JobDefinition.queue_name,
        ).all()
        if all(
            is_capability_enabled(capability)
            for capability in _job_runtime_capabilities(
                job_key=key,
                definition_queue_name=queue_name,
                run_queue_name="",
            )
        )
    ]
    visible_run_queue_names = [
        queue_name
        for (queue_name,) in db.query(JobRun.queue_name).distinct().all()
        if all(
            is_capability_enabled(capability)
            for capability in _job_runtime_capabilities(
                job_key="",
                definition_queue_name="",
                run_queue_name=queue_name,
            )
        )
    ]
    return db.query(JobRun).filter(
        JobRun.job_definition_id.in_(visible_definition_ids),
        JobRun.queue_name.in_(visible_run_queue_names),
    )


def _hidden_optional_job_public_ids(db: Session) -> list[str]:
    return [
        identity.job_public_id
        for identity in _job_identity_query(db).all()
        if any(
            not is_capability_enabled(capability)
            for capability in _job_runtime_capabilities_for_identity(identity)
        )
    ]


def _visible_business_lock_count(
    db: Session,
    *,
    lock_status: BusinessLockStatus,
    hidden_job_public_ids: list[str],
) -> int:
    total = (
        db.query(BusinessLock.id)
        .filter(BusinessLock.status == lock_status)
        .count()
    )
    if not hidden_job_public_ids:
        return total
    hidden_optional_job_locks = (
        db.query(BusinessLock.id)
        .filter(
            BusinessLock.status == lock_status,
            BusinessLock.owner_type == "job_run",
            BusinessLock.owner_id.in_(hidden_job_public_ids),
        )
        .count()
    )
    return total - hidden_optional_job_locks


def _business_lock_detail(business_lock: BusinessLock) -> dict:
    return {
        "public_id": business_lock.public_id,
        "scope": business_lock.scope,
        "resource_key": business_lock.resource_key,
        "owner_id": business_lock.owner_id,
        "owner_type": business_lock.owner_type,
        "status": _enum_value(business_lock.status),
        "metadata": business_lock.metadata_json or {},
        "acquired_at": business_lock.acquired_at,
        "expires_at": business_lock.expires_at,
        "released_at": business_lock.released_at,
    }


def _business_locks_for_job_run(db: Session, job_run: JobRun) -> list[BusinessLock]:
    return (
        db.query(BusinessLock)
        .filter(BusinessLock.owner_type == "job_run", BusinessLock.owner_id == job_run.public_id)
        .order_by(BusinessLock.created_at.asc(), BusinessLock.id.asc())
        .all()
    )


def _as_utc(value):
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _job_timeout_seconds(job_run: JobRun) -> int:
    timeout_seconds = getattr(job_run.definition, "timeout_seconds", None)
    return timeout_seconds or DEFAULT_JOB_STALE_TIMEOUT_SECONDS


def _job_stale_reason(job_run: JobRun) -> str | None:
    if job_run.status != JobRunStatus.RUNNING or not job_run.locked_at:
        return None
    locked_at = _as_utc(job_run.locked_at)
    timeout_seconds = _job_timeout_seconds(job_run)
    stale_after = locked_at + timedelta(seconds=timeout_seconds)
    if stale_after >= datetime.now(timezone.utc):
        return None
    return f"RUNNING job lock exceeded {timeout_seconds} seconds timeout."


def _job_recommended_action(job_run: JobRun, stale_reason: str | None) -> str | None:
    if job_run.status == JobRunStatus.FAILED:
        return "REQUEUE"
    if job_run.status == JobRunStatus.RETRYING:
        return "WAIT"
    if job_run.status == JobRunStatus.QUEUED:
        return "CANCEL"
    if stale_reason:
        return "FORCE_CANCEL"
    if job_run.status == JobRunStatus.RUNNING:
        return "WAIT"
    return None


def _job_force_cancel_warning(job_run: JobRun) -> str | None:
    if job_run.status == JobRunStatus.RUNNING:
        return FORCE_CANCEL_WARNING
    return None


def _job_recovery_metadata(job_run: JobRun) -> dict:
    stale_reason = _job_stale_reason(job_run)
    return {
        "stale_reason": stale_reason,
        "recommended_action": _job_recommended_action(job_run, stale_reason),
        "force_cancel_warning": _job_force_cancel_warning(job_run),
    }


def _job_run_detail(job_run: JobRun, business_locks: list[BusinessLock] | None = None) -> dict:
    return {
        "public_id": job_run.public_id,
        "definition": {
            "public_id": job_run.definition.public_id,
            "key": job_run.definition.key,
            "display_name": job_run.definition.display_name,
            "queue_name": job_run.definition.queue_name,
        },
        "user_public_id": job_run.user.public_id if job_run.user else None,
        "idempotency_key": job_run.idempotency_key,
        "status": _enum_value(job_run.status),
        "priority": job_run.priority,
        "payload": job_run.payload or {},
        "result": job_run.result or {},
        "error_message": job_run.error_message,
        "attempt_count": job_run.attempt_count,
        "max_attempts": job_run.max_attempts,
        "queue_name": job_run.queue_name,
        "locked_by": job_run.locked_by,
        "locked_at": job_run.locked_at,
        "next_run_at": job_run.next_run_at,
        "started_at": job_run.started_at,
        "finished_at": job_run.finished_at,
        "created_at": job_run.created_at,
        "updated_at": job_run.updated_at,
        **_job_recovery_metadata(job_run),
        "business_locks": [_business_lock_detail(business_lock) for business_lock in (business_locks or [])],
        "events": [
            {
                "public_id": event.public_id,
                "event_type": _enum_value(event.event_type),
                "from_status": _enum_value(event.from_status),
                "to_status": _enum_value(event.to_status),
                "message": event.message,
                "metadata": event.metadata_json or {},
                "created_at": event.created_at,
            }
            for event in job_run.events
        ],
    }


def _job_run_summary(job_run: JobRun) -> dict:
    return {
        "public_id": job_run.public_id,
        "definition": {
            "public_id": job_run.definition.public_id,
            "key": job_run.definition.key,
            "display_name": job_run.definition.display_name,
        },
        "status": _enum_value(job_run.status),
        "queue_name": job_run.queue_name,
        "priority": job_run.priority,
        "attempt_count": job_run.attempt_count,
        "max_attempts": job_run.max_attempts,
        "next_run_at": job_run.next_run_at,
        "started_at": job_run.started_at,
        "finished_at": job_run.finished_at,
        "created_at": job_run.created_at,
        "error_message": job_run.error_message,
        **_job_recovery_metadata(job_run),
    }

def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


def resolve_database_url_for_backup(db: Session) -> str:
    return str(db.get_bind().url)


def _is_backup_provider_configured(database_backend: str) -> bool:
    return database_backend == "sqlite"


def _is_integration_configured(credential: IntegrationCredential) -> bool:
    try:
        return bool(decrypt_secret(credential.secret_ciphertext))
    except Exception:
        return False


def _visible_system_settings(db: Session) -> list[SystemSetting]:
    visible_keys = [
        key
        for (key,) in db.query(SystemSetting.key).all()
        if _setting_key_is_visible(key)
    ]
    if not visible_keys:
        return []
    return (
        db.query(SystemSetting)
        .filter(SystemSetting.key.in_(visible_keys))
        .order_by(SystemSetting.key.asc())
        .all()
    )


def _visible_platform_settings(db: Session) -> list[PlatformSetting]:
    visible_ids = [
        setting_id
        for setting_id, key in db.query(PlatformSetting.id, PlatformSetting.key).all()
        if _setting_key_is_visible(key)
    ]
    if not visible_ids:
        return []
    return (
        db.query(PlatformSetting)
        .filter(PlatformSetting.id.in_(visible_ids))
        .order_by(PlatformSetting.key.asc())
        .all()
    )


def _visible_integration_credentials(db: Session) -> list[IntegrationCredential]:
    visible_ids = [
        credential_id
        for credential_id, provider_key, credential_key in db.query(
            IntegrationCredential.id,
            IntegrationCredential.provider_key,
            IntegrationCredential.credential_key,
        ).all()
        if _provider_credential_is_visible(provider_key, credential_key)
    ]
    if not visible_ids:
        return []
    return (
        db.query(IntegrationCredential)
        .filter(IntegrationCredential.id.in_(visible_ids))
        .order_by(
            IntegrationCredential.provider_key.asc(),
            IntegrationCredential.credential_key.asc(),
        )
        .all()
    )


def _visible_feature_flag_ids(db: Session) -> list[int]:
    visible_ids = []
    for flag_id, key in db.query(FeatureFlag.id, FeatureFlag.key).all():
        if _is_deployment_owned_setting_key(key):
            continue
        capability = _CAPABILITY_BY_ROLLOUT_FLAG_KEY.get(key)
        if capability is not None:
            if is_capability_enabled(capability):
                visible_ids.append(flag_id)
            continue
        if not key.strip().lower().startswith(_CAPABILITY_ROLLOUT_FLAG_PREFIX):
            visible_ids.append(flag_id)
    return visible_ids


def _visible_feature_flags(db: Session) -> list[FeatureFlag]:
    visible_ids = _visible_feature_flag_ids(db)
    if not visible_ids:
        return []
    return (
        db.query(FeatureFlag)
        .filter(FeatureFlag.id.in_(visible_ids))
        .order_by(FeatureFlag.key.asc())
        .all()
    )


@router.get("/ops/summary", response_model=AdminOpsSummaryResponse)
async def get_admin_ops_summary(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    database_backend = detect_database_backend(resolve_database_url_for_backup(db))
    backup_items = list_database_backups(backup_dir=ADMIN_BACKUP_DIR, limit=100)
    platform_settings = _visible_platform_settings(db)
    integration_credentials = _visible_integration_credentials(db)
    now = datetime.now(timezone.utc)
    visible_job_runs = _visible_job_run_query(db)
    hidden_optional_job_public_ids = _hidden_optional_job_public_ids(db)
    visible_feature_flag_ids = _visible_feature_flag_ids(db)
    job_counts = {
        status_item.value: visible_job_runs.filter(JobRun.status == status_item).count()
        for status_item in JobRunStatus
    }
    running_job_runs = (
        visible_job_runs
        .filter(JobRun.status == JobRunStatus.RUNNING, JobRun.locked_at.is_not(None))
        .all()
    )
    return AdminOpsSummaryResponse(
        database_backend=database_backend,
        backup_provider_configured=_is_backup_provider_configured(database_backend),
        backup_count=len(backup_items),
        latest_backup_at=backup_items[0]["created_at"] if backup_items else None,
        user_count=db.query(User).count(),
        active_user_count=db.query(User).filter(User.is_active == True).count(),
        admin_count=db.query(User).filter(User.role == "admin").count(),
        job_counts=job_counts,
        stale_running_job_count=sum(1 for job_run in running_job_runs if _job_stale_reason(job_run)),
        platform_setting_count=len(platform_settings),
        configured_integration_count=sum(1 for credential in integration_credentials if _is_integration_configured(credential)),
        active_integration_count=sum(1 for credential in integration_credentials if credential.is_active),
        enabled_feature_flag_count=(
            db.query(FeatureFlag.id)
            .filter(
                FeatureFlag.id.in_(visible_feature_flag_ids),
                FeatureFlag.enabled == True,
            )
            .count()
        ),
        expired_feature_flag_count=(
            db.query(FeatureFlag.id)
            .filter(
                FeatureFlag.id.in_(visible_feature_flag_ids),
                FeatureFlag.expires_at.is_not(None),
                FeatureFlag.expires_at < now,
            )
            .count()
        ),
        active_business_lock_count=_visible_business_lock_count(
            db,
            lock_status=BusinessLockStatus.ACTIVE,
            hidden_job_public_ids=hidden_optional_job_public_ids,
        ),
        expired_business_lock_count=_visible_business_lock_count(
            db,
            lock_status=BusinessLockStatus.EXPIRED,
            hidden_job_public_ids=hidden_optional_job_public_ids,
        ),
    )


@router.get("/ops/backups", response_model=List[AdminBackupSummaryResponse])
async def list_database_backups_endpoint(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return list_database_backups(backup_dir=ADMIN_BACKUP_DIR, limit=limit)


@router.post("/ops/backups", response_model=AdminBackupResponse)
async def trigger_database_backup_endpoint(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    database_url = resolve_database_url_for_backup(db)
    try:
        backup_result = trigger_database_backup(database_url, backup_dir=ADMIN_BACKUP_DIR)
    except BackupProviderNotConfigured as exc:
        log_event(
            logger,
            "warning",
            "database_backup_provider_not_configured",
            actor_user_public_id=current_admin.public_id,
            error=str(exc),
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="BACKUP_PROVIDER_NOT_CONFIGURED",
        ) from exc

    log_event(
        logger,
        "info",
        "database_backup_triggered",
        actor_user_public_id=current_admin.public_id,
        backup_id=backup_result["backup_id"],
        database_backend=backup_result["database_backend"],
    )
    return AdminBackupResponse(**backup_result)


@router.get("/users", response_model=List[AdminUserSummaryResponse])
async def list_admin_users(
    limit: int = Query(default=100, ge=1, le=200),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return (
        db.query(User)
        .order_by(User.created_at.desc(), User.id.desc())
        .limit(limit)
        .all()
    )


@router.post("/users/{user_public_id}/promote", response_model=AdminUserOperationResponse)
async def promote_admin_user_endpoint(
    user_public_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    try:
        result = promote_user_to_admin(db, user_public_id=user_public_id, actor_user=current_admin)
    except AdminUserNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND") from exc

    db.commit()
    log_event(
        logger,
        "info",
        "admin_user_promoted",
        actor_user_public_id=current_admin.public_id,
        target_user_public_id=user_public_id,
    )
    return AdminUserOperationResponse(**result)


@router.patch("/users/{user_public_id}/role", response_model=AdminUserOperationResponse)
async def update_admin_user_role_endpoint(
    user_public_id: str,
    role_in: AdminUserRoleUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    try:
        result = update_user_role(db, user_public_id=user_public_id, role=role_in.role, actor_user=current_admin)
    except AdminUserNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND") from exc
    except AdminUserOperationBlocked as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    db.commit()
    log_event(
        logger,
        "info",
        "admin_user_role_updated",
        actor_user_public_id=current_admin.public_id,
        target_user_public_id=user_public_id,
        role=result["role"],
    )
    return AdminUserOperationResponse(**result)


@router.patch("/users/{user_public_id}/active", response_model=AdminUserOperationResponse)
async def update_admin_user_active_state_endpoint(
    user_public_id: str,
    active_in: AdminUserActiveUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    try:
        result = set_user_active_state(
            db,
            user_public_id=user_public_id,
            is_active=active_in.is_active,
            actor_user=current_admin,
        )
    except AdminUserNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND") from exc
    except AdminUserOperationBlocked as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc

    db.commit()
    log_event(
        logger,
        "info",
        "admin_user_active_state_updated",
        actor_user_public_id=current_admin.public_id,
        target_user_public_id=user_public_id,
        is_active=active_in.is_active,
    )
    return AdminUserOperationResponse(**result)


@router.post("/users/{user_public_id}/reset-password", response_model=AdminPasswordResetResponse)
async def reset_admin_user_password_endpoint(
    user_public_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    try:
        result = reset_user_password(db, user_public_id=user_public_id, actor_user=current_admin)
    except AdminUserNotFound as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="USER_NOT_FOUND") from exc

    db.commit()
    log_event(
        logger,
        "info",
        "admin_user_password_reset",
        actor_user_public_id=current_admin.public_id,
        target_user_public_id=user_public_id,
        revoked_session_count=result["revoked_session_count"],
        revoked_token_count=result["revoked_token_count"],
    )
    return AdminPasswordResetResponse(**result)


@router.get("/jobs/{job_public_id}")
async def get_job_run_detail(
    job_public_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    identity = _job_identity_or_404(db, job_public_id)
    _require_job_deployment_capabilities(identity)
    job_run = _job_run_for_identity(db, identity)
    return _job_run_detail(job_run, business_locks=_business_locks_for_job_run(db, job_run))


@router.post("/jobs/{job_public_id}/requeue")
async def requeue_job_run_endpoint(
    job_public_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    identity = _job_identity_or_404(db, job_public_id)
    _require_job_capability(
        db,
        identity,
        actor_key=current_admin.public_id,
    )
    job_run = _job_run_for_identity(db, identity)
    try:
        requeued = requeue_job_run(db, job_run=job_run)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(requeued)
    return _job_run_detail(requeued, business_locks=_business_locks_for_job_run(db, requeued))


@router.post("/jobs/{job_public_id}/cancel")
async def cancel_job_run_endpoint(
    job_public_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    identity = _job_identity_or_404(db, job_public_id)
    _require_job_deployment_capabilities(identity)
    job_run = _job_run_for_identity(db, identity)
    try:
        cancelled = cancel_job_run(db, job_run=job_run)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(cancelled)
    return _job_run_detail(cancelled, business_locks=_business_locks_for_job_run(db, cancelled))


@router.post("/jobs/{job_public_id}/force-cancel")
async def force_cancel_job_run_endpoint(
    job_public_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    identity = _job_identity_or_404(db, job_public_id)
    _require_job_deployment_capabilities(identity)
    job_run = _job_run_for_identity(db, identity)
    try:
        cancelled = force_cancel_running_job_run(db, job_run=job_run)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    db.commit()
    db.refresh(cancelled)
    return _job_run_detail(cancelled, business_locks=_business_locks_for_job_run(db, cancelled))


@router.get("/jobs")
async def list_job_runs(
    status_filter: JobRunStatus | None = Query(default=None, alias="status"),
    queue_name: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    query = _visible_job_run_query(db)
    if status_filter is not None:
        query = query.filter(JobRun.status == status_filter)
    if queue_name:
        query = query.filter(JobRun.queue_name == queue_name)

    total = query.count()
    jobs = (
        query
        .order_by(JobRun.created_at.desc(), JobRun.id.desc())
        .limit(limit)
        .all()
    )
    return {
        "items": [_job_run_summary(job_run) for job_run in jobs],
        "total": total,
        "limit": limit,
    }

@router.get("/settings", response_model=List[SystemSettingResponse])
async def list_system_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all system settings"""
    return _visible_system_settings(db)


@router.get("/platform/settings", response_model=List[PlatformSettingResponse])
async def list_platform_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return _visible_platform_settings(db)


@router.put("/platform/settings/{key}", response_model=PlatformSettingResponse)
async def upsert_platform_setting(
    key: str,
    setting_in: PlatformSettingUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    _require_setting_capability(key)
    setting = db.query(PlatformSetting).filter(PlatformSetting.key == key).first()
    if not setting:
        setting = PlatformSetting(key=key)
        db.add(setting)

    if setting_in.value is not None:
        setting.value = setting_in.value
    if setting_in.description is not None:
        setting.description = setting_in.description

    db.commit()
    db.refresh(setting)
    return setting


@router.get("/platform/integrations", response_model=List[IntegrationCredentialResponse])
async def list_integration_credentials(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    credentials = _visible_integration_credentials(db)

    result = []
    for credential in credentials:
        secret_value = decrypt_secret(credential.secret_ciphertext)
        result.append(
            IntegrationCredentialResponse(
                id=credential.id,
                provider_key=credential.provider_key,
                credential_key=credential.credential_key,
                masked_value=mask_secret(secret_value),
                description=credential.description,
                is_active=credential.is_active,
                is_configured=bool(secret_value),
                created_at=credential.created_at,
                updated_at=credential.updated_at,
            )
        )
    return result


@router.put("/platform/integrations/{provider_key}/{credential_key}", response_model=IntegrationCredentialResponse)
async def upsert_integration_credential(
    provider_key: str,
    credential_key: str,
    credential_in: IntegrationCredentialUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    _require_provider_capability(provider_key, credential_key)
    credential = db.query(IntegrationCredential).filter(
        IntegrationCredential.provider_key == provider_key,
        IntegrationCredential.credential_key == credential_key,
    ).first()

    if not credential:
        credential = IntegrationCredential(
            provider_key=provider_key,
            credential_key=credential_key,
            secret_ciphertext=encrypt_secret(credential_in.secret_value),
        )
        db.add(credential)
    else:
        credential.secret_ciphertext = encrypt_secret(credential_in.secret_value)

    if credential_in.description is not None:
        credential.description = credential_in.description
    if credential_in.is_active is not None:
        credential.is_active = credential_in.is_active

    db.commit()
    db.refresh(credential)
    secret_value = decrypt_secret(credential.secret_ciphertext)
    return IntegrationCredentialResponse(
        id=credential.id,
        provider_key=credential.provider_key,
        credential_key=credential.credential_key,
        masked_value=mask_secret(secret_value),
        description=credential.description,
        is_active=credential.is_active,
        is_configured=bool(secret_value),
        created_at=credential.created_at,
        updated_at=credential.updated_at,
    )


@router.patch("/platform/integrations/{provider_key}/{credential_key}/active", response_model=IntegrationCredentialResponse)
async def update_integration_credential_active_state(
    provider_key: str,
    credential_key: str,
    credential_in: IntegrationCredentialActiveUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    _require_provider_capability(provider_key, credential_key)
    credential = db.query(IntegrationCredential).filter(
        IntegrationCredential.provider_key == provider_key,
        IntegrationCredential.credential_key == credential_key,
    ).first()
    if not credential:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="INTEGRATION_CREDENTIAL_NOT_FOUND")

    credential.is_active = credential_in.is_active
    db.commit()
    db.refresh(credential)
    secret_value = decrypt_secret(credential.secret_ciphertext)
    return IntegrationCredentialResponse(
        id=credential.id,
        provider_key=credential.provider_key,
        credential_key=credential.credential_key,
        masked_value=mask_secret(secret_value),
        description=credential.description,
        is_active=credential.is_active,
        is_configured=bool(secret_value),
        created_at=credential.created_at,
        updated_at=credential.updated_at,
    )


@router.get("/platform/feature-flags", response_model=List[FeatureFlagResponse])
async def list_feature_flags(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return _visible_feature_flags(db)


@router.put("/platform/feature-flags/{key}", response_model=FeatureFlagResponse)
async def upsert_feature_flag(
    key: str,
    feature_flag_in: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    if _is_deployment_owned_setting_key(key):
        _raise_configuration_key_unavailable()
    capability = _CAPABILITY_BY_ROLLOUT_FLAG_KEY.get(key)
    if _is_capability_namespace_key(key) and capability is None:
        _raise_configuration_key_unavailable()
    _require_optional_capability(capability)
    if capability == RuntimeCapability.OPEN_REGISTRATION and (
        feature_flag_in.actor_targets
        or feature_flag_in.rollout_percentage is not None
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=_PUBLIC_CAPABILITY_ROLLOUT_INVALID_DETAIL,
        )
    feature_flag = db.query(FeatureFlag).filter(FeatureFlag.key == key).first()
    if not feature_flag:
        feature_flag = FeatureFlag(key=key)
        db.add(feature_flag)

    feature_flag.enabled = feature_flag_in.enabled
    feature_flag.actor_targets = feature_flag_in.actor_targets
    feature_flag.rollout_percentage = feature_flag_in.rollout_percentage
    feature_flag.expires_at = feature_flag_in.expires_at
    feature_flag.description = feature_flag_in.description

    db.commit()
    db.refresh(feature_flag)
    return feature_flag

@router.put("/settings/{key}", response_model=SystemSettingResponse)
async def update_system_setting(
    key: str,
    setting_in: SystemSettingUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Update or create a system setting"""
    _require_setting_capability(key)
    setting = db.query(SystemSetting).filter(SystemSetting.key == key).first()
    
    if not setting:
        setting = SystemSetting(key=key, value=setting_in.value, description=setting_in.description)
        db.add(setting)
    else:
        if setting_in.value is not None:
            setting.value = setting_in.value
        if setting_in.description is not None:
            setting.description = setting_in.description
            
    db.commit()
    db.refresh(setting)
    return setting
