"""Market-backed position analysis isolated from the journal core router."""
from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User
from observability import get_structured_logger, log_event
from routers.auth import get_current_user
from routers.positions import calculate_drift
from schemas import PositionMarketAnalysisResponse
from services.market_data_access import MarketDataService
from services.public_id_service import resolve_position


router = APIRouter(prefix="/api/positions", tags=["Position Market Analysis"])
logger = get_structured_logger("position_market_analysis")


@router.post("/{position_id}/analyze", response_model=PositionMarketAnalysisResponse)
async def analyze_position(
    position_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    position = resolve_position(db, current_user.id, position_id)
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    start_date = position.opened_at
    end_date = position.closed_at or datetime.now(start_date.tzinfo if start_date else None)
    if not start_date:
        return position
    if start_date > end_date:
        end_date = start_date + timedelta(minutes=1)

    log_event(
        logger,
        "info",
        "position_history_analysis_started",
        position_id=position.id,
        symbol=position.symbol,
        start_date=start_date,
        end_date=end_date,
    )
    history = await MarketDataService(db).get_price_history(
        position.symbol,
        start_date,
        end_date,
    )
    if history:
        highs = [item["high"] for item in history if item.get("high") is not None]
        lows = [item["low"] for item in history if item.get("low") is not None]
        if highs:
            position.max_price_during_hold = max(highs)
        if lows:
            position.min_price_during_hold = min(lows)
        db.commit()
        db.refresh(position)
    else:
        log_event(
            logger,
            "info",
            "position_history_missing",
            position_id=position.id,
            symbol=position.symbol,
        )

    response = {
        "id": position.id,
        "public_id": position.public_id,
        "user_id": position.user_id,
        "account_id": position.account_id,
        "strategy_id": position.strategy_id,
        "symbol": position.symbol,
        "exchange": position.exchange,
        "asset_type": position.asset_type,
        "direction": position.direction.value,
        "status": position.status.value,
        "total_quantity": position.total_quantity,
        "average_entry_price": position.average_entry_price,
        "realized_pnl": position.realized_pnl,
        "current_price": None,
        "unrealized_pnl": None,
        "opened_at": position.opened_at,
        "closed_at": position.closed_at,
        "trade_review": position.trade_review,
        "screenshots": position.screenshots or [],
        "lessons": position.lessons or [],
        "rating": position.rating,
        "created_at": position.created_at,
        "updated_at": position.updated_at,
        "asset_metadata": position.asset_metadata,
        "batches": position.batches,
        "planned_entry_price": position.planned_entry_price,
        "planned_stop_loss": position.planned_stop_loss,
        "planned_take_profit": position.planned_take_profit,
        "checklist_responses": position.checklist_responses,
        "checklist_completed_at": position.checklist_completed_at,
        "drift_analysis": calculate_drift(position),
        "max_price_during_hold": position.max_price_during_hold,
        "min_price_during_hold": position.min_price_during_hold,
    }
    return JSONResponse(content=jsonable_encoder(response))
