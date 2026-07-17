"""Pre-body runtime capability guards for deployment-allowlisted routes."""
from __future__ import annotations

from copy import copy
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from fastapi.dependencies.utils import get_dependant, solve_dependencies
from fastapi.responses import JSONResponse
from fastapi.routing import APIRoute
from jose import JWTError, jwt
from starlette.routing import request_response

from config import get_settings
from database import SessionLocal, get_db
from models import AuthToken, User
from observability import (
    REQUEST_ID_HEADER,
    build_error_response_payload,
    get_or_create_request_id,
)
from release_profile import RuntimeCapability
from routers.disabled_capabilities import feature_disabled_detail
from services.auth_service import get_current_user
from services.capability_service import is_effective_capability_enabled


async def _resolve_dependency_override(request: Request, dependency):
    override = request.app.dependency_overrides.get(dependency)
    if override is None:
        raise LookupError("Dependency override is not configured")

    async def holder(value=Depends(override)):
        return value

    dependant = get_dependant(path=request.url.path, call=holder)
    solved = await solve_dependencies(
        request=request,
        dependant=dependant,
        body=None,
        background_tasks=None,
        response=None,
        dependency_overrides_provider=request.app,
        dependency_cache={},
        async_exit_stack=request.scope["fastapi_inner_astack"],
        embed_body_fields=False,
    )
    if solved.errors or "value" not in solved.values:
        raise RuntimeError("Dependency override could not be resolved before body parsing")
    return solved.values["value"]


@asynccontextmanager
async def _database_session(request: Request):
    override = request.app.dependency_overrides.get(get_db)
    if override is None:
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()
        return

    yield await _resolve_dependency_override(request, get_db)


async def _overridden_actor_key(request: Request) -> str | None:
    override = request.app.dependency_overrides.get(get_current_user)
    if override is None:
        return None
    try:
        user = await _resolve_dependency_override(request, get_current_user)
    except Exception:
        return None
    public_id = getattr(user, "public_id", None)
    return public_id if isinstance(public_id, str) and public_id else None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _bearer_actor_key(request: Request, db) -> str | None:
    authorization = request.headers.get("authorization", "")
    scheme, separator, token = authorization.partition(" ")
    if not separator or scheme.lower() != "bearer" or not token.strip():
        return None

    settings = get_settings()
    try:
        payload = jwt.decode(
            token.strip(),
            settings.secret_key,
            algorithms=[settings.algorithm],
        )
        user_id = int(payload["sub"])
        token_jti = str(payload["jti"])
    except (JWTError, KeyError, TypeError, ValueError):
        return None

    auth_token = db.query(AuthToken).filter(AuthToken.token_jti == token_jti).first()
    if auth_token is None or auth_token.revoked_at is not None:
        return None
    if auth_token.expires_at is not None and _as_utc(auth_token.expires_at) <= datetime.now(timezone.utc):
        return None
    if (
        auth_token.session is None
        or auth_token.session.revoked_at is not None
        or auth_token.session.status != "ACTIVE"
    ):
        return None

    user = db.query(User).filter(User.id == user_id).first()
    if user is None or not user.is_active:
        return None
    return user.public_id


async def _actor_key(request: Request, db, *, public_route: bool) -> str | None:
    if public_route:
        return None
    overridden = await _overridden_actor_key(request)
    if overridden is not None:
        return overridden
    return _bearer_actor_key(request, db)


def _feature_disabled_response(request: Request, capability: RuntimeCapability) -> JSONResponse:
    detail = feature_disabled_detail(capability.value)
    request_id = get_or_create_request_id(
        getattr(request.state, "request_id", None)
        or request.headers.get(REQUEST_ID_HEADER)
    )
    return JSONResponse(
        status_code=404,
        content=build_error_response_payload(
            code="FEATURE_DISABLED",
            detail=detail,
            message=detail["message"],
            request_id=request_id,
            status_code=404,
        ),
        headers={REQUEST_ID_HEADER: request_id},
    )


def install_runtime_capability_preflight(
    route: APIRoute,
    capability: RuntimeCapability,
    *,
    public_route: bool = False,
) -> None:
    """Guard a real optional route before FastAPI reads or validates its body."""

    installed_capability = getattr(route, "_runtime_preflight_capability", None)
    if installed_capability == (capability, public_route):
        return
    if installed_capability is not None:
        raise RuntimeError("An optional route cannot be assigned to multiple capabilities")

    original_get_route_handler = route.get_route_handler

    def get_guarded_route_handler():
        original_handler = original_get_route_handler()

        async def guarded_handler(request: Request):
            try:
                async with _database_session(request) as db:
                    actor_key = await _actor_key(request, db, public_route=public_route)
                    enabled = is_effective_capability_enabled(
                        db,
                        capability,
                        actor_key=actor_key,
                    )
            except Exception:
                enabled = False

            if not enabled:
                return _feature_disabled_response(request, capability)
            return await original_handler(request)

        return guarded_handler

    route.get_route_handler = get_guarded_route_handler
    route.app = request_response(route.get_route_handler())
    route._runtime_preflight_capability = (capability, public_route)


def build_runtime_guarded_router(
    router: APIRouter,
    capability: RuntimeCapability,
    *,
    public_route: bool = False,
) -> APIRouter:
    """Clone a router before installing application-local preflight guards."""

    guarded_router = copy(router)
    guarded_router.routes = []
    for source_route in router.routes:
        guarded_route = copy(source_route)
        if isinstance(guarded_route, APIRoute):
            install_runtime_capability_preflight(
                guarded_route,
                capability,
                public_route=public_route,
            )
        guarded_router.routes.append(guarded_route)
    guarded_router._mark_routes_changed()
    return guarded_router
