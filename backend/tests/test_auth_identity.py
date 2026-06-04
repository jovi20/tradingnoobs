from datetime import timedelta

import pytest
from jose import jwt

from config import get_settings
from routers import auth
from schemas import UserResponse
from services.auth_service import create_access_token, create_user, get_current_user


def test_create_user_sets_public_identity_fields(db_session):
    user = create_user(db_session, " Trader@Example.COM ", "strong-password")

    assert len(user.public_id) == 26
    assert user.public_id == user.public_id.upper()
    assert user.email == "trader@example.com"
    assert user.email_normalized == "trader@example.com"
    assert user.status == "ACTIVE"
    assert user.locale == "en-US"
    assert user.timezone == "UTC"


def test_user_response_exposes_public_id(db_session):
    user = create_user(db_session, "public@example.com", "strong-password")

    response = UserResponse.model_validate(user)

    assert response.public_id == user.public_id
    assert response.email_normalized == "public@example.com"
    assert response.status == "ACTIVE"


@pytest.mark.asyncio
async def test_current_user_accepts_public_id_subject(db_session):
    user = create_user(db_session, "token@example.com", "strong-password")
    token = create_access_token({"sub": user.public_id}, expires_delta=timedelta(minutes=5))

    current_user = await get_current_user(token=token, db=db_session)

    assert current_user.public_id == user.public_id


@pytest.mark.asyncio
async def test_current_user_accepts_legacy_integer_subject(db_session):
    user = create_user(db_session, "legacy-token@example.com", "strong-password")
    settings = get_settings()
    token = jwt.encode({"sub": str(user.id)}, settings.secret_key, algorithm=settings.algorithm)

    current_user = await get_current_user(token=token, db=db_session)

    assert current_user.id == user.id


def test_auth_router_exposes_legacy_and_v1_prefixes():
    assert auth.router.prefix == "/api/auth"
    assert auth.v1_router.prefix == "/api/v1/auth"
