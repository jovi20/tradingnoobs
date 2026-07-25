"""Trading Noobs backend application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app_bootstrap import bootstrap_schema_if_enabled, resolve_auto_create_schema_enabled
from config import get_settings, validate_release_settings
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
    validate_release_settings(app_settings)
    bootstrap_schema_if_enabled(
        metadata=Base.metadata,
        engine=engine,
        enabled=resolve_auto_create_schema_enabled(
            env_name=app_settings.env_name,
            explicit=app_settings.auto_create_schema,
        ),
    )
    from services.generic_import_service import scavenge_orphan_import_files

    scavenge_orphan_import_files()
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
        import_sessions,
        journal,
        open_registration,
        positions,
        settings as settings_router,
        strategies,
        timeline,
        trading_positions,
        transactions,
    )

    for router in (
        auth.router,
        dashboard.router,
        settings_router.router,
        admin.router,
        open_registration.router,
        timeline.build_router(
            include_ai_contract=False,
            include_optional_event_contract=False,
        ),
    ):
        application.include_router(router)

    from services.timezone_service import require_journal_write_timezone

    for router in (
        strategies.router,
        daily.router,
        accounts.router,
        import_sessions.router,
        positions.router,
        journal.router,
        transactions.router,
        trading_positions.router,
    ):
        application.include_router(
            router,
            dependencies=[Depends(require_journal_write_timezone)],
        )

    from routers.disabled_capabilities import (
        ADMIN_AI_DISABLED_ROUTES,
        ADMIN_AI_LAZY_ROUTES,
        AI_INSIGHTS_DISABLED_ROUTES,
        AI_INSIGHTS_LAZY_ROUTES,
        BROKER_SYNC_DISABLED_ROUTES,
        BROKER_SYNC_LAZY_ROUTES,
        GENERIC_BOOTSTRAP_DISABLED_ROUTES,
        INSIGHT_ARTIFACTS_DISABLED_ROUTES,
        INSIGHT_ARTIFACTS_LAZY_ROUTES,
        INSIGHT_RUNS_DISABLED_ROUTES,
        INSIGHT_RUNS_LAZY_ROUTES,
        MARKET_DISABLED_ROUTES,
        MARKET_LAZY_ROUTES,
        PDF_EXPORT_DISABLED_ROUTES,
        PDF_EXPORT_LAZY_ROUTES,
        POSITION_MARKET_ANALYSIS_DISABLED_ROUTES,
        POSITION_MARKET_ANALYSIS_LAZY_ROUTES,
        RISK_CARDS_DISABLED_ROUTES,
        RISK_CARDS_LAZY_ROUTES,
        build_disabled_capability_router,
    )

    application.include_router(
        build_disabled_capability_router(
            prefix="/api/positions",
            capability="GENERIC_BOOTSTRAP",
            routes=GENERIC_BOOTSTRAP_DISABLED_ROUTES,
        )
    )

    def runtime_dependencies(capability: RuntimeCapability):
        from routers.capability_dependencies import require_runtime_capability

        return [Depends(require_runtime_capability(capability))]

    def public_runtime_dependencies(capability: RuntimeCapability):
        from routers.capability_dependencies import require_public_runtime_capability

        return [Depends(require_public_runtime_capability(capability))]

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

    def include_runtime_guarded_router(
        router,
        *,
        capability: RuntimeCapability,
        public_route: bool = False,
    ) -> None:
        from routers.capability_preflight import build_runtime_guarded_router

        dependencies = (
            public_runtime_dependencies(capability)
            if public_route
            else runtime_dependencies(capability)
        )
        application.include_router(
            build_runtime_guarded_router(
                router,
                capability,
                public_route=public_route,
            ),
            dependencies=dependencies,
        )

    def include_allowlisted_lazy_routes(
        *,
        prefix: str,
        capability: RuntimeCapability,
        module_name: str,
        router_attribute: str,
        lazy_routes,
        disabled_routes,
        public_route: bool = False,
    ) -> None:
        if not is_capability_enabled(capability, profile=profile):
            include_disabled_routes(
                prefix=prefix,
                capability=capability,
                routes=disabled_routes,
            )
            return

        from routers.lazy_capabilities import build_lazy_capability_router

        include_runtime_guarded_router(
            build_lazy_capability_router(
                prefix=prefix,
                module_name=module_name,
                router_attribute=router_attribute,
                routes=lazy_routes,
            ),
            capability=capability,
            public_route=public_route,
        )

    include_allowlisted_lazy_routes(
        prefix="/api/admin",
        capability=RuntimeCapability.AI_INSIGHTS,
        module_name="routers.admin_ai",
        router_attribute="router",
        lazy_routes=ADMIN_AI_LAZY_ROUTES,
        disabled_routes=ADMIN_AI_DISABLED_ROUTES,
    )
    include_allowlisted_lazy_routes(
        prefix="/api/insights",
        capability=RuntimeCapability.AI_INSIGHTS,
        module_name="routers.insights",
        router_attribute="router",
        lazy_routes=AI_INSIGHTS_LAZY_ROUTES,
        disabled_routes=AI_INSIGHTS_DISABLED_ROUTES,
    )
    include_allowlisted_lazy_routes(
        prefix="/api/v1/insights/runs",
        capability=RuntimeCapability.AI_INSIGHTS,
        module_name="routers.insight_artifacts",
        router_attribute="router",
        lazy_routes=INSIGHT_RUNS_LAZY_ROUTES,
        disabled_routes=INSIGHT_RUNS_DISABLED_ROUTES,
    )
    include_allowlisted_lazy_routes(
        prefix="/api/v1/insights/artifacts",
        capability=RuntimeCapability.AI_INSIGHTS,
        module_name="routers.insight_artifacts",
        router_attribute="artifact_router",
        lazy_routes=INSIGHT_ARTIFACTS_LAZY_ROUTES,
        disabled_routes=INSIGHT_ARTIFACTS_DISABLED_ROUTES,
    )
    include_allowlisted_lazy_routes(
        prefix="/api/insights",
        capability=RuntimeCapability.PDF_EXPORT,
        module_name="routers.pdf_export",
        router_attribute="router",
        lazy_routes=PDF_EXPORT_LAZY_ROUTES,
        disabled_routes=PDF_EXPORT_DISABLED_ROUTES,
    )
    include_allowlisted_lazy_routes(
        prefix="/api/risk",
        capability=RuntimeCapability.RISK_CARDS,
        module_name="routers.risk",
        router_attribute="router",
        lazy_routes=RISK_CARDS_LAZY_ROUTES,
        disabled_routes=RISK_CARDS_DISABLED_ROUTES,
    )
    include_allowlisted_lazy_routes(
        prefix="/api/market",
        capability=RuntimeCapability.MARKET,
        module_name="routers.market",
        router_attribute="router",
        lazy_routes=MARKET_LAZY_ROUTES,
        disabled_routes=MARKET_DISABLED_ROUTES,
    )
    include_allowlisted_lazy_routes(
        prefix="/api/positions",
        capability=RuntimeCapability.MARKET,
        module_name="routers.position_market_analysis",
        router_attribute="router",
        lazy_routes=POSITION_MARKET_ANALYSIS_LAZY_ROUTES,
        disabled_routes=POSITION_MARKET_ANALYSIS_DISABLED_ROUTES,
    )
    include_allowlisted_lazy_routes(
        prefix="/api/broker-sync",
        capability=RuntimeCapability.BROKER_SYNC,
        module_name="routers.broker_sync",
        router_attribute="router",
        lazy_routes=BROKER_SYNC_LAZY_ROUTES,
        disabled_routes=BROKER_SYNC_DISABLED_ROUTES,
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
