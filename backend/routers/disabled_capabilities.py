"""Side-effect-free deny routes for capabilities outside the release profile."""
from __future__ import annotations

from collections.abc import Sequence

from fastapi import APIRouter, HTTPException, status


DisabledRoute = tuple[str, str]
LazyCapabilityRoute = tuple[str, str, str]


def _disabled_routes(routes: Sequence[LazyCapabilityRoute]) -> tuple[DisabledRoute, ...]:
    return tuple((method, path) for method, path, _route_name in routes)

MARKET_LAZY_ROUTES: tuple[LazyCapabilityRoute, ...] = (
    ("GET", "/validate/{symbol}", "validate_symbol"),
    ("GET", "/quote/{symbol}", "get_quote"),
    ("GET", "/detect/{symbol}", "detect_asset_type"),
    ("GET", "/calendar", "get_market_calendar"),
)
MARKET_DISABLED_ROUTES = _disabled_routes(MARKET_LAZY_ROUTES)

POSITION_MARKET_ANALYSIS_LAZY_ROUTES: tuple[LazyCapabilityRoute, ...] = (
    ("POST", "/{position_id}/analyze", "analyze_position"),
)
POSITION_MARKET_ANALYSIS_DISABLED_ROUTES = _disabled_routes(
    POSITION_MARKET_ANALYSIS_LAZY_ROUTES
)

BROKER_SYNC_LAZY_ROUTES: tuple[LazyCapabilityRoute, ...] = (
    ("POST", "/ibkr/test", "test_ibkr_flex"),
    ("POST", "/binance/test", "test_binance"),
    ("POST", "/ibkr/sync", "sync_ibkr_flex"),
    ("POST", "/binance/sync", "sync_binance"),
    ("GET", "/runs", "get_sync_runs"),
    ("GET", "/executions", "get_broker_executions"),
)
BROKER_SYNC_DISABLED_ROUTES = _disabled_routes(BROKER_SYNC_LAZY_ROUTES)

AI_INSIGHTS_LAZY_ROUTES: tuple[LazyCapabilityRoute, ...] = (
    ("GET", "", "get_weekly_reports"),
    ("GET", "/{report_id:int}", "get_weekly_report"),
    ("POST", "/generate", "generate_report"),
    ("POST", "/generate-current-week", "generate_current_week_report"),
    ("DELETE", "/{report_id:int}", "delete_weekly_report"),
    ("GET", "/summary/today", "get_today_summary"),
    ("POST", "/summary/generate", "generate_summary"),
    ("POST", "/analyze", "analyze_trading_data"),
    ("GET", "/analyze/history", "list_analysis_history"),
    ("GET", "/analyze/latest/{analysis_type}", "get_latest_analysis"),
)
AI_INSIGHTS_DISABLED_ROUTES = _disabled_routes(AI_INSIGHTS_LAZY_ROUTES)

ADMIN_AI_LAZY_ROUTES: tuple[LazyCapabilityRoute, ...] = (
    ("POST", "/test-llm", "test_llm_connection"),
)
ADMIN_AI_DISABLED_ROUTES = _disabled_routes(ADMIN_AI_LAZY_ROUTES)

INSIGHT_RUNS_LAZY_ROUTES: tuple[LazyCapabilityRoute, ...] = (
    ("GET", "", "list_insight_runs"),
    ("GET", "/{run_public_id}", "get_insight_run"),
)
INSIGHT_RUNS_DISABLED_ROUTES = _disabled_routes(INSIGHT_RUNS_LAZY_ROUTES)

INSIGHT_ARTIFACTS_LAZY_ROUTES: tuple[LazyCapabilityRoute, ...] = (
    ("GET", "/{artifact_public_id}", "get_insight_artifact"),
)
INSIGHT_ARTIFACTS_DISABLED_ROUTES = _disabled_routes(
    INSIGHT_ARTIFACTS_LAZY_ROUTES
)

PDF_EXPORT_LAZY_ROUTES: tuple[LazyCapabilityRoute, ...] = (
    ("GET", "/{report_id:int}/export/pdf", "export_weekly_report_pdf"),
)
PDF_EXPORT_DISABLED_ROUTES = _disabled_routes(PDF_EXPORT_LAZY_ROUTES)

RISK_CARDS_LAZY_ROUTES: tuple[LazyCapabilityRoute, ...] = (
    ("GET", "/summary", "get_risk_summary"),
)
RISK_CARDS_DISABLED_ROUTES = _disabled_routes(RISK_CARDS_LAZY_ROUTES)

OPEN_REGISTRATION_LAZY_ROUTES: tuple[LazyCapabilityRoute, ...] = (
    ("POST", "/register", "register"),
)
OPEN_REGISTRATION_DISABLED_ROUTES = _disabled_routes(
    OPEN_REGISTRATION_LAZY_ROUTES
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
