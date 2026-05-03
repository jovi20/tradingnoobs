from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from database import get_db
from models import FeatureFlag, IntegrationCredential, JobRun, JobRunStatus, PlatformSetting, SystemSetting, User
from schemas import (
    FeatureFlagResponse,
    FeatureFlagUpdate,
    IntegrationCredentialResponse,
    IntegrationCredentialUpdate,
    PlatformSettingResponse,
    PlatformSettingUpdate,
    SystemSettingResponse,
    SystemSettingUpdate,
)
from routers.auth import get_current_user
import httpx
from services.credential_service import decrypt_secret, encrypt_secret, mask_secret
from services.platform_config_service import get_llm_runtime_config

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)


def _enum_value(value):
    return value.value if hasattr(value, "value") else value


def _job_run_detail(job_run: JobRun) -> dict:
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
    }

def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user


@router.get("/jobs/{job_public_id}")
async def get_job_run_detail(
    job_public_id: str,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    job_run = db.query(JobRun).filter(JobRun.public_id == job_public_id).first()
    if not job_run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job run not found")
    return _job_run_detail(job_run)


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
    return db.query(SystemSetting).all()


@router.get("/platform/settings", response_model=List[PlatformSettingResponse])
async def list_platform_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    return db.query(PlatformSetting).order_by(PlatformSetting.key.asc()).all()


@router.put("/platform/settings/{key}", response_model=PlatformSettingResponse)
async def upsert_platform_setting(
    key: str,
    setting_in: PlatformSettingUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
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
                print(f"LLM Test Success: {response.json()}") # Debug log
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
