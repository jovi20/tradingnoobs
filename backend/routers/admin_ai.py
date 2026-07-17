"""AI administration routes loaded only inside the deployment capability ceiling."""
from __future__ import annotations

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from models import User
from observability import get_structured_logger, log_event
from routers.admin import get_current_admin
from routers.disabled_capabilities import raise_feature_disabled
from release_profile import RuntimeCapability
from services.capability_service import is_effective_capability_enabled
from services.platform_config_service import get_llm_runtime_config


router = APIRouter(prefix="/api/admin", tags=["admin-ai"])
logger = get_structured_logger("admin.ai")


@router.post("/test-llm", status_code=status.HTTP_200_OK)
async def test_llm_connection(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    """Test the configured LLM without exposing provider payloads or secrets."""
    if not is_effective_capability_enabled(
        db,
        RuntimeCapability.AI_INSIGHTS,
        actor_key=current_admin.public_id,
    ):
        raise_feature_disabled(RuntimeCapability.AI_INSIGHTS.value)
    llm_config = get_llm_runtime_config(db)
    llm_api_url = llm_config["api_url"]
    llm_api_key = llm_config["api_key"]
    llm_model = llm_config["model"] or "gpt-4"
    if not llm_api_url:
        raise HTTPException(status_code=400, detail="LLM_API_URL_NOT_CONFIGURED")
    if not llm_api_key:
        raise HTTPException(status_code=400, detail="LLM_API_KEY_NOT_CONFIGURED")

    api_endpoint = llm_api_url.strip().rstrip("/")
    if not api_endpoint.endswith("/chat/completions"):
        api_endpoint = f"{api_endpoint}/chat/completions"

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                api_endpoint,
                headers={
                    "Authorization": f"Bearer {llm_api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": llm_model,
                    "messages": [{"role": "user", "content": "Hello"}],
                    "max_tokens": 5,
                },
            )
    except httpx.ConnectTimeout as exc:
        raise HTTPException(status_code=504, detail="LLM_PROVIDER_TIMEOUT") from exc
    except httpx.RequestError as exc:
        raise HTTPException(status_code=502, detail="LLM_PROVIDER_UNAVAILABLE") from exc

    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="LLM_PROVIDER_REJECTED")

    log_event(logger, "info", "llm_test_success")
    return {"status": "success", "message": "Connection successful"}
