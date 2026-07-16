"""Trading Noobs backend application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app_bootstrap import bootstrap_schema_if_enabled, resolve_auto_create_schema_enabled
from config import get_settings
from database import Base, engine
from observability import add_error_handlers, add_observability_middleware
from release_profile import (
    ReleaseProfile,
    bind_release_profile,
    is_capability_enabled,
    parse_release_profile,
    RuntimeCapability,
)


app_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    bootstrap_schema_if_enabled(
        metadata=Base.metadata,
        engine=engine,
        enabled=resolve_auto_create_schema_enabled(
            env_name=app_settings.env_name,
            explicit=app_settings.auto_create_schema,
        ),
    )
    yield


def create_app(release_profile: ReleaseProfile | str | None = None) -> FastAPI:
    profile = parse_release_profile(release_profile or app_settings.release_profile)
    application = FastAPI(
        title="Trading Noobs API",
        description="交易日志系统 - 记录、分析和复盘交易",
        version="1.0.0",
        lifespan=lifespan,
    )
    application.state.release_profile = profile.value

    origins = [origin.strip() for origin in app_settings.cors_origins.split(",")]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    add_observability_middleware(application)
    add_error_handlers(application)

    @application.middleware("http")
    async def bind_static_release_profile(request, call_next):
        with bind_release_profile(profile):
            return await call_next(request)

    from routers import (
        accounts,
        admin,
        auth,
        daily,
        dashboard,
        journal,
        positions,
        settings as settings_router,
        strategies,
        timeline,
        trading_positions,
        transactions,
    )

    for router in (
        auth.router,
        strategies.router,
        dashboard.router,
        daily.router,
        settings_router.router,
        accounts.router,
        admin.router,
        positions.router,
        journal.router,
        transactions.router,
        timeline.router,
        trading_positions.router,
    ):
        application.include_router(router)

    from routers.disabled_capabilities import (
        AI_INSIGHTS_DISABLED_ROUTES,
        BROKER_SYNC_DISABLED_ROUTES,
        INSIGHT_ARTIFACTS_DISABLED_ROUTES,
        INSIGHT_RUNS_DISABLED_ROUTES,
        MARKET_DISABLED_ROUTES,
        PDF_EXPORT_DISABLED_ROUTES,
        RISK_CARDS_DISABLED_ROUTES,
        build_disabled_capability_router,
    )

    def runtime_dependencies(capability: RuntimeCapability):
        from routers.capability_dependencies import require_runtime_capability

        return [Depends(require_runtime_capability(capability))]

    def include_disabled_routes(
        *,
        prefix: str,
        capability: RuntimeCapability,
        routes,
    ) -> None:
        application.include_router(
            build_disabled_capability_router(
                prefix=prefix,
                capability=capability.value,
                routes=routes,
            )
        )

    if is_capability_enabled(RuntimeCapability.AI_INSIGHTS, profile=profile):
        from routers import insight_artifacts, insights

        dependencies = runtime_dependencies(RuntimeCapability.AI_INSIGHTS)
        application.include_router(insights.router, dependencies=dependencies)
        application.include_router(insight_artifacts.router, dependencies=dependencies)
        application.include_router(
            insight_artifacts.artifact_router,
            dependencies=dependencies,
        )
    else:
        include_disabled_routes(
            prefix="/api/insights",
            capability=RuntimeCapability.AI_INSIGHTS,
            routes=AI_INSIGHTS_DISABLED_ROUTES,
        )
        include_disabled_routes(
            prefix="/api/v1/insights/runs",
            capability=RuntimeCapability.AI_INSIGHTS,
            routes=INSIGHT_RUNS_DISABLED_ROUTES,
        )
        include_disabled_routes(
            prefix="/api/v1/insights/artifacts",
            capability=RuntimeCapability.AI_INSIGHTS,
            routes=INSIGHT_ARTIFACTS_DISABLED_ROUTES,
        )

    if is_capability_enabled(RuntimeCapability.PDF_EXPORT, profile=profile):
        from routers import pdf_export

        application.include_router(
            pdf_export.router,
            dependencies=runtime_dependencies(RuntimeCapability.PDF_EXPORT),
        )
    else:
        include_disabled_routes(
            prefix="/api/insights",
            capability=RuntimeCapability.PDF_EXPORT,
            routes=PDF_EXPORT_DISABLED_ROUTES,
        )

    if is_capability_enabled(RuntimeCapability.RISK_CARDS, profile=profile):
        from routers import risk

        application.include_router(
            risk.router,
            dependencies=runtime_dependencies(RuntimeCapability.RISK_CARDS),
        )
    else:
        include_disabled_routes(
            prefix="/api/risk",
            capability=RuntimeCapability.RISK_CARDS,
            routes=RISK_CARDS_DISABLED_ROUTES,
        )

    if is_capability_enabled(RuntimeCapability.MARKET, profile=profile):
        from routers import market

        application.include_router(
            market.router,
            dependencies=runtime_dependencies(RuntimeCapability.MARKET),
        )
    else:
        include_disabled_routes(
            prefix="/api/market",
            capability=RuntimeCapability.MARKET,
            routes=MARKET_DISABLED_ROUTES,
        )

    if is_capability_enabled(RuntimeCapability.BROKER_SYNC, profile=profile):
        from routers import broker_sync

        application.include_router(
            broker_sync.router,
            dependencies=runtime_dependencies(RuntimeCapability.BROKER_SYNC),
        )
    else:
        include_disabled_routes(
            prefix="/api/broker-sync",
            capability=RuntimeCapability.BROKER_SYNC,
            routes=BROKER_SYNC_DISABLED_ROUTES,
        )

    @application.get("/")
    async def root():
        return {
            "status": "healthy",
            "app": "Trading Noobs API",
            "version": "1.0.0",
            "release_profile": profile.value,
        }

    @application.get("/api/health")
    async def health_check():
        return {"status": "ok", "release_profile": profile.value}

    return application


app = create_app()
