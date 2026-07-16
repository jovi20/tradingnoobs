"""Side-effect-free deny routes for capabilities outside the release profile."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, status


_DENY_METHODS = ["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS"]


def feature_disabled_detail(capability: str) -> dict[str, str]:
    return {
        "code": "FEATURE_DISABLED",
        "message": "Capability is disabled by the deployment release profile",
        "capability": capability,
    }


def raise_feature_disabled(capability: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=feature_disabled_detail(capability),
    )


def build_disabled_capability_router(*, prefix: str, capability: str) -> APIRouter:
    router = APIRouter(prefix=prefix, include_in_schema=False)

    async def deny_capability_root():
        raise_feature_disabled(capability)

    async def deny_capability_path(disabled_path: str):
        del disabled_path
        raise_feature_disabled(capability)

    router.add_api_route("", deny_capability_root, methods=_DENY_METHODS)
    router.add_api_route("/{disabled_path:path}", deny_capability_path, methods=_DENY_METHODS)
    return router
