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
import httpx
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
from services.platform_config_service import get_llm_runtime_config

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
    "interactivebroker",
    "binance",
    "brokersync",
)
_MARKET_IDENTIFIER_ALIASES = (
    "finnhub",
    "yfinance",
    "yahoofinance",
    "akshare",
    "marketdata",
)
_BROKER_IDENTIFIER_TOKENS = {"broker", "brokers", "brokerage"}
_MARKET_IDENTIFIER_TOKENS = {"market", "markets"}
_AI_IDENTIFIER_ALIASES = (
    "openai",
    "llm",
    "aiinsights",
    "insights",
)
_AI_IDENTIFIER_TOKENS = {"ai", "llm", "insight", "insights"}
_CAPABILITY_BY_ROLLOUT_FLAG_KEY = {
    key: capability for capability, key in CAPABILITY_ROLLOUT_FLAG_KEYS.items()
}


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def _identifier_parts(value: str) -> tuple[set[str], str]:
    with_word_boundaries = re.sub(r"(?<=[a-z0-9])(?=[A-Z])", "_", value.strip())
    token_list = [
        token
        for token in re.sub(r"[^A-Za-z0-9]+", "_", with_word_boundaries)
        .lower()
        .strip("_")
        .split("_")
        if token
    ]
    return set(token_list), "".join(token_list)


def _optional_capability_for_identifiers(
    *identifiers: str,
) -> RuntimeCapability | None:
    parts = [_identifier_parts(identifier) for identifier in identifiers if identifier]

    for tokens, compact in parts:
        if _BROKER_IDENTIFIER_TOKENS.intersection(tokens) or any(
            alias in compact for alias in _BROKER_IDENTIFIER_ALIASES
        ):
            return RuntimeCapability.BROKER_SYNC

    for tokens, compact in parts:
        if _MARKET_IDENTIFIER_TOKENS.intersection(tokens) or any(
            alias in compact for alias in _MARKET_IDENTIFIER_ALIASES
        ):
            return RuntimeCapability.MARKET

    for tokens, compact in parts:
        if _AI_IDENTIFIER_TOKENS.intersection(tokens) or any(
            alias in compact for alias in _AI_IDENTIFIER_ALIASES
        ):
            return RuntimeCapability.AI_INSIGHTS

    return None


def _capability_is_visible(capability: RuntimeCapability | None) -> bool:
    return capability is None or is_capability_enabled(capability)


def _require_optional_capability(capability: RuntimeCapability | None) -> None:
    if capability is not None and not is_capability_enabled(capability):
        raise_feature_disabled(capability.value)


def _require_effective_optional_capability(
    db: Session,
    capability: RuntimeCapability,
    *,
    actor_key: str,
) -> None:
    _require_optional_capability(capability)
    if not is_effective_capability_enabled(
        db,
        capability,
        actor_key=actor_key,
    ):
        raise_feature_disabled(capability.value)


def _require_provider_capability(
    provider_key: str,
    credential_key: str | None = None,
) -> None:
    _require_optional_capability(
        _optional_capability_for_identifiers(provider_key, credential_key or "")
    )


def _require_setting_capability(key: str) -> None:
    _require_optional_capability(_optional_capability_for_identifiers(key))


def _require_job_capability(job_run: JobRun) -> None:
    job_key = (job_run.definition.key if job_run.definition else "").lower()
    if job_key.startswith("market.") and not is_capability_enabled(RuntimeCapability.MARKET):
        raise_feature_disabled(RuntimeCapability.MARKET.value)
    if job_key.startswith("broker.") and not is_capability_enabled(
        RuntimeCapability.BROKER_SYNC
    ):
        raise_feature_disabled(RuntimeCapability.BROKER_SYNC.value)
    if job_key.startswith(("ai.", "insight.")) and not is_capability_enabled(
        RuntimeCapability.AI_INSIGHTS
    ):
        raise_feature_disabled(RuntimeCapability.AI_INSIGHTS.value)


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


@router.get("/ops/summary", response_model=AdminOpsSummaryResponse)
async def get_admin_ops_summary(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    database_backend = detect_database_backend(resolve_database_url_for_backup(db))
    backup_items = list_database_backups(backup_dir=ADMIN_BACKUP_DIR, limit=100)
    platform_settings = [
        setting
        for setting in db.query(PlatformSetting).all()
        if _capability_is_visible(_optional_capability_for_identifiers(setting.key))
    ]
    integration_credentials = [
        credential
        for credential in db.query(IntegrationCredential).all()
        if _capability_is_visible(
            _optional_capability_for_identifiers(
                credential.provider_key,
                credential.credential_key,
            )
        )
    ]
    now = datetime.now(timezone.utc)
    job_counts = {
        status_item.value: db.query(JobRun).filter(JobRun.status == status_item).count()
        for status_item in JobRunStatus
    }
    running_job_runs = (
        db.query(JobRun)
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
        enabled_feature_flag_count=db.query(FeatureFlag).filter(FeatureFlag.enabled == True).count(),
        expired_feature_flag_count=(
            db.query(FeatureFlag)
            .filter(FeatureFlag.expires_at.is_not(None), FeatureFlag.expires_at < now)
            .count()
        ),
        active_business_lock_count=db.query(BusinessLock).filter(BusinessLock.status == BusinessLockStatus.ACTIVE).count(),
        expired_business_lock_count=db.query(BusinessLock).filter(BusinessLock.status == BusinessLockStatus.EXPIRED).count(),
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
    job_run = db.query(JobRun).filter(JobRun.public_id == job_public_id).first()
    if not job_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job run not found")
    return _job_run_detail(job_run, business_locks=_business_locks_for_job_run(db, job_run))


@router.post("/jobs/{job_public_id}/requeue")
async def requeue_job_run_endpoint(
    job_public_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    job_run = db.query(JobRun).filter(JobRun.public_id == job_public_id).first()
    if not job_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job run not found")
    _require_job_capability(job_run)
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
    job_run = db.query(JobRun).filter(JobRun.public_id == job_public_id).first()
    if not job_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job run not found")
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
    job_run = db.query(JobRun).filter(JobRun.public_id == job_public_id).first()
    if not job_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job run not found")
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
    query = db.query(JobRun)
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
    settings = db.query(SystemSetting).order_by(SystemSetting.key.asc()).all()
    return [
        setting
        for setting in settings
        if _capability_is_visible(_optional_capability_for_identifiers(setting.key))
    ]


@router.get("/platform/settings", response_model=List[PlatformSettingResponse])
async def list_platform_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    settings = db.query(PlatformSetting).order_by(PlatformSetting.key.asc()).all()
    return [
        setting
        for setting in settings
        if _capability_is_visible(_optional_capability_for_identifiers(setting.key))
    ]


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
    credentials = db.query(IntegrationCredential).order_by(
        IntegrationCredential.provider_key.asc(),
        IntegrationCredential.credential_key.asc(),
    ).all()

    result = []
    for credential in credentials:
        capability = _optional_capability_for_identifiers(
            credential.provider_key,
            credential.credential_key,
        )
        if not _capability_is_visible(capability):
            continue
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
    return db.query(FeatureFlag).order_by(FeatureFlag.key.asc()).all()


@router.put("/platform/feature-flags/{key}", response_model=FeatureFlagResponse)
async def upsert_feature_flag(
    key: str,
    feature_flag_in: FeatureFlagUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    _require_optional_capability(_CAPABILITY_BY_ROLLOUT_FLAG_KEY.get(key))
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


@router.post("/test-llm", status_code=status.HTTP_200_OK)
async def test_llm_connection(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Test LLM API connection with current system settings"""
    _require_effective_optional_capability(
        db,
        RuntimeCapability.AI_INSIGHTS,
        actor_key=current_admin.public_id,
    )
    llm_config = get_llm_runtime_config(db)

    if not llm_config["api_url"]:
        raise HTTPException(status_code=400, detail="LLM API URL not configured")
    if not llm_config["api_key"]:
        raise HTTPException(status_code=400, detail="LLM API Key not configured")

    llm_api_url = llm_config["api_url"]
    llm_api_key = llm_config["api_key"]
    llm_model = llm_config["model"] or "gpt-4"

    # Construct URL
    api_endpoint = llm_api_url.strip().rstrip('/')
    if not api_endpoint.endswith('/chat/completions'):
        api_endpoint = f"{api_endpoint}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                api_endpoint,
                headers={
                    "Authorization": f"Bearer {llm_api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": llm_model,
                    "messages": [
                        {"role": "user", "content": "Hello"}
                    ],
                    "max_tokens": 5
                }
            )
            
            if response.status_code == 200:
                log_event(logger, "info", "llm_test_success", response_body=response.json())
                return {"status": "success", "message": "Connection successful"}
            else:
                error_msg = response.text
                try:
                    error_json = response.json()
                    if "error" in error_json:
                        msg = error_json["error"].get("message")
                        if msg:
                            error_msg = msg
                except:
                    pass
                raise HTTPException(status_code=400, detail=f"API Error ({response.status_code}): {error_msg}")
                
    except httpx.ConnectTimeout:
         raise HTTPException(status_code=504, detail="Connection Timed Out (30s). Check your network or API URL.")
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail=f"Network Error: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Test Failed: {str(e)}")
