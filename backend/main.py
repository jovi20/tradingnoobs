"""Trading Noobs backend application entry point."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
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
        insight_artifacts,
        insights,
        journal,
        positions,
        risk,
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
        insights.router,
        accounts.router,
        admin.router,
        positions.router,
        journal.router,
        transactions.router,
        timeline.router,
        trading_positions.router,
        insight_artifacts.router,
        insight_artifacts.artifact_router,
        risk.router,
    ):
        application.include_router(router)

    if is_capability_enabled(RuntimeCapability.MARKET, profile=profile):
        from routers import market

        application.include_router(market.router)
    else:
        from routers.disabled_capabilities import build_disabled_capability_router

        application.include_router(
            build_disabled_capability_router(prefix="/api/market", capability="MARKET")
        )

    if is_capability_enabled(RuntimeCapability.BROKER_SYNC, profile=profile):
        from routers import broker_sync

        application.include_router(broker_sync.router)
    else:
        from routers.disabled_capabilities import build_disabled_capability_router

        application.include_router(
            build_disabled_capability_router(
                prefix="/api/broker-sync",
                capability="BROKER_SYNC",
            )
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
