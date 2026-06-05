"""
Trading Noobs Backend - Main Application Entry Point
# Trigger Reload 3
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app_bootstrap import bootstrap_schema_if_enabled, resolve_auto_create_schema_enabled
from config import get_settings
from database import engine, Base
from routers import auth, strategies, dashboard, daily, settings as settings_router, insights, accounts, admin, positions, market, journal, transactions, timeline, trading_positions, insight_artifacts

app_settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events"""
    # Startup: temporary bootstrap guard until Alembic owns schema changes
    bootstrap_schema_if_enabled(
        metadata=Base.metadata,
        engine=engine,
        enabled=resolve_auto_create_schema_enabled(
            env_name=app_settings.env_name,
            explicit=app_settings.auto_create_schema,
        ),
    )
    yield
    # Shutdown: cleanup if needed


app = FastAPI(
    title="Trading Noobs API",
    description="交易日志系统 - 记录、分析和复盘美股与加密货币交易",
    version="1.0.0",
    lifespan=lifespan
)

# CORS Configuration
origins = [origin.strip() for origin in app_settings.cors_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(strategies.router)
app.include_router(dashboard.router)
app.include_router(daily.router)
app.include_router(settings_router.router)
app.include_router(insights.router)
app.include_router(accounts.router)
app.include_router(admin.router)
app.include_router(positions.router)
app.include_router(market.router)
app.include_router(journal.router)
app.include_router(transactions.router)
app.include_router(timeline.router)
app.include_router(trading_positions.router)
app.include_router(insight_artifacts.router)
app.include_router(insight_artifacts.artifact_router)


@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "app": "Trading Noobs API",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health_check():
    """API health check"""
    return {"status": "ok"}
