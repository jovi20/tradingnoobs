from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from database import get_db
from models import User, SystemSetting
from schemas import SystemSettingResponse, SystemSettingUpdate
from routers.auth import get_current_user
import httpx

router = APIRouter(
    prefix="/api/admin",
    tags=["admin"],
    responses={404: {"description": "Not found"}},
)

def get_current_admin(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="The user doesn't have enough privileges"
        )
    return current_user

@router.get("/settings", response_model=List[SystemSettingResponse])
async def list_system_settings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin)
):
    """Get all system settings"""
    return db.query(SystemSetting).all()

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
    # Fetch Settings
    url_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_url').first()
    key_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_api_key').first()
    model_setting = db.query(SystemSetting).filter(SystemSetting.key == 'llm_model').first()
    
    if not url_setting or not url_setting.value:
        raise HTTPException(status_code=400, detail="LLM API URL not configured")
    if not key_setting or not key_setting.value:
        raise HTTPException(status_code=400, detail="LLM API Key not configured")
        
    llm_api_url = url_setting.value
    llm_api_key = key_setting.value
    llm_model = model_setting.value if model_setting and model_setting.value else "gpt-4"

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
