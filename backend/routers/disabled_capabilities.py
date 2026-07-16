"""Side-effect-free deny routes for capabilities outside the release profile."""
from __future__ import annotations

from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status


DisabledRoute = tuple[str, str]

MARKET_DISABLED_ROUTES: tuple[DisabledRoute, ...] = (
    ("GET", "/validate/{symbol}"),
    ("GET", "/quote/{symbol}"),
    ("GET", "/detect/{symbol}"),
    ("GET", "/calendar"),
)

BROKER_SYNC_DISABLED_ROUTES: tuple[DisabledRoute, ...] = (
    ("POST", "/ibkr/test"),
    ("POST", "/binance/test"),
    ("POST", "/ibkr/sync"),
    ("POST", "/binance/sync"),
    ("GET", "/runs"),
    ("GET", "/executions"),
)

AI_INSIGHTS_DISABLED_ROUTES: tuple[DisabledRoute, ...] = (
    ("GET", ""),
    ("GET", "/{report_id:int}"),
    ("POST", "/generate"),
    ("POST", "/generate-current-week"),
    ("DELETE", "/{report_id:int}"),
    ("GET", "/summary/today"),
    ("POST", "/summary/generate"),
    ("POST", "/analyze"),
    ("GET", "/analyze/history"),
    ("GET", "/analyze/latest/{analysis_type}"),
)

INSIGHT_RUNS_DISABLED_ROUTES: tuple[DisabledRoute, ...] = (
    ("GET", ""),
    ("GET", "/{run_public_id}"),
)

INSIGHT_ARTIFACTS_DISABLED_ROUTES: tuple[DisabledRoute, ...] = (
    ("GET", "/{artifact_public_id}"),
)

PDF_EXPORT_DISABLED_ROUTES: tuple[DisabledRoute, ...] = (
    ("GET", "/{report_id:int}/export/pdf"),
)

RISK_CARDS_DISABLED_ROUTES: tuple[DisabledRoute, ...] = (
    ("GET", "/summary"),
)


def feature_disabled_detail(capability: str) -> dict[str, str]:
    return {
        "code": "FEATURE_DISABLED",
        "message": "Capability is disabled by deployment or runtime policy",
        "capability": capability,
    }


def raise_feature_disabled(capability: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=feature_disabled_detail(capability),
    )


def build_disabled_capability_router(
    *,
    prefix: str,
    capability: str,
    routes: Sequence[DisabledRoute],
) -> APIRouter:
    router = APIRouter(prefix=prefix, include_in_schema=False)
    prefix_key = prefix.strip("/").replace("/", "_").replace("-", "_") or "root"

    async def deny_known_capability_route():
        raise_feature_disabled(capability)

    for index, (method, path) in enumerate(routes):
        router.add_api_route(
            path,
            deny_known_capability_route,
            methods=[method],
            name=f"disabled_{capability.lower()}_{prefix_key}_{index}",
        )
    return router
