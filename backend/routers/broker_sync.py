"""
Trading Noobs Backend - Broker trade-record sync router
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from models import User
from schemas import (
    BrokerConnectionTestResponse,
    BrokerExecutionResponse,
    BrokerSyncRequest,
    BrokerSyncRunResponse,
)
from services.auth_service import get_current_user
from services.broker_sync.service import (
    list_executions,
    list_sync_runs,
    sync_binance_executions,
    sync_ibkr_flex_executions,
    test_binance_connection,
    test_ibkr_flex_connection,
)

router = APIRouter(prefix="/api/broker-sync", tags=["Broker Sync"])


@router.post("/ibkr/test", response_model=BrokerConnectionTestResponse)
async def test_ibkr_flex(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await test_ibkr_flex_connection(db, current_user)


@router.post("/binance/test", response_model=BrokerConnectionTestResponse)
async def test_binance(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return await test_binance_connection(db, current_user)


@router.post("/ibkr/sync", response_model=BrokerSyncRunResponse)
async def sync_ibkr_flex(
    payload: BrokerSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return await sync_ibkr_flex_executions(
            db,
            current_user,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"IBKR Flex 成交回补失败：{exc}",
        ) from exc


@router.post("/binance/sync", response_model=BrokerSyncRunResponse)
async def sync_binance(
    payload: BrokerSyncRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        return await sync_binance_executions(
            db,
            current_user,
            start_date=payload.start_date,
            end_date=payload.end_date,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Binance 成交同步失败：{exc}",
        ) from exc


@router.get("/runs", response_model=list[BrokerSyncRunResponse])
async def get_sync_runs(
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_sync_runs(db, current_user, limit=limit)


@router.get("/executions", response_model=list[BrokerExecutionResponse])
async def get_broker_executions(
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_executions(db, current_user, limit=limit)
