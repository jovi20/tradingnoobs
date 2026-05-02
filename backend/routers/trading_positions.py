"""
Trading Noobs Backend - TradingPosition Truth Read Router
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import PositionEvent, PositionEventType, User
from schemas import (
    TradingPositionDividendCreate,
    TradingPositionEventNarrativeUpdate,
    TradingPositionManualAdjustmentCreate,
    TradingPositionTradeEventCreate,
    TradingPositionTradeEventReverseCreate,
)
from services.account_ledger_service import (
    sync_dividend_event_to_account_ledger,
    sync_manual_adjustment_event_to_account_ledger,
)
from services.auth_service import get_current_user
from services.trading_position_read_service import build_trading_position_lifecycle_payload, resolve_truth_position_by_public_id
from services.trading_position_write_service import append_truth_trade_event, reverse_latest_truth_trade_event

router = APIRouter(prefix="/api/trading-positions", tags=["Trading Positions"])


def _lifecycle_response(truth_position, source: str = "DERIVED", status_code: int = 200) -> JSONResponse:
    data = build_trading_position_lifecycle_payload(truth_position)

    return JSONResponse(
        status_code=status_code,
        content=jsonable_encoder(
            {
                "data": data,
                "meta": {
                    "as_of": truth_position.updated_at or truth_position.created_at,
                    "generated_at": truth_position.updated_at or truth_position.created_at,
                    "freshness": "FRESH",
                    "source": source,
                    "maturity": "EARLY_SIGNAL",
                    "value_status": "FINAL",
                },
            }
        )
    )


@router.get("/{position_public_id}/lifecycle")
def get_trading_position_lifecycle(
    position_public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    if not truth_position:
        raise HTTPException(status_code=404, detail="Trading position not found")

    return _lifecycle_response(truth_position)


@router.patch("/{position_public_id}/events/{event_public_id}")
def update_trading_position_event_narrative(
    position_public_id: str,
    event_public_id: str,
    payload: TradingPositionEventNarrativeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    if not truth_position:
        raise HTTPException(status_code=404, detail="Trading position not found")

    event = db.query(PositionEvent).filter(
        PositionEvent.public_id == event_public_id,
        PositionEvent.position_id == truth_position.id,
        PositionEvent.user_id == current_user.id,
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Position event not found")

    update_data = payload.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(event, key, value)

    db.commit()

    updated_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    return _lifecycle_response(updated_position, source="MANUAL")


@router.post("/{position_public_id}/events", status_code=201)
def create_trading_position_trade_event(
    position_public_id: str,
    payload: TradingPositionTradeEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    if not truth_position:
        raise HTTPException(status_code=404, detail="Trading position not found")

    try:
        append_truth_trade_event(
            db,
            position=truth_position,
            event_type=PositionEventType(payload.event_type.value),
            quantity=payload.quantity,
            price=payload.price,
            currency=payload.currency,
            occurred_at=payload.occurred_at,
            fee_amount=payload.fee_amount,
            fee_currency=payload.fee_currency,
            fx_rate_to_account_ccy=payload.fx_rate_to_account_ccy,
            reason=payload.reason,
            emotion=payload.emotion,
            confidence=payload.confidence,
            note=payload.note,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()

    updated_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    return _lifecycle_response(updated_position, source="MANUAL", status_code=201)


@router.post("/{position_public_id}/events/{event_public_id}/reverse", status_code=201)
def reverse_trading_position_trade_event(
    position_public_id: str,
    event_public_id: str,
    payload: TradingPositionTradeEventReverseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    if not truth_position:
        raise HTTPException(status_code=404, detail="Trading position not found")

    event = db.query(PositionEvent).filter(
        PositionEvent.public_id == event_public_id,
        PositionEvent.position_id == truth_position.id,
        PositionEvent.user_id == current_user.id,
    ).first()
    if not event:
        raise HTTPException(status_code=404, detail="Position event not found")

    try:
        reverse_latest_truth_trade_event(
            db,
            position=truth_position,
            event=event,
            occurred_at=payload.occurred_at,
            note=payload.note,
        )
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()

    updated_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    return _lifecycle_response(updated_position, source="MANUAL", status_code=201)


@router.post("/{position_public_id}/dividends", status_code=201)
def create_trading_position_dividend(
    position_public_id: str,
    payload: TradingPositionDividendCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    if not truth_position:
        raise HTTPException(status_code=404, detail="Trading position not found")

    event = PositionEvent(
        user_id=current_user.id,
        position_id=truth_position.id,
        account_id=truth_position.account_id,
        instrument_id=truth_position.instrument_id,
        event_type=PositionEventType.DIVIDEND,
        event_time=payload.occurred_at,
        currency=payload.currency,
        gross_amount=payload.amount,
        fx_rate_to_account_ccy=1,
        input_source="MANUAL",
        note=payload.note,
    )
    db.add(event)
    db.flush()
    sync_dividend_event_to_account_ledger(db, event=event)
    db.commit()

    updated_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    return _lifecycle_response(updated_position, source="MANUAL", status_code=201)


@router.post("/{position_public_id}/adjustments", status_code=201)
def create_trading_position_manual_adjustment(
    position_public_id: str,
    payload: TradingPositionManualAdjustmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    if not truth_position:
        raise HTTPException(status_code=404, detail="Trading position not found")

    if payload.amount == 0:
        raise HTTPException(status_code=422, detail="Manual adjustment amount cannot be zero")

    event = PositionEvent(
        user_id=current_user.id,
        position_id=truth_position.id,
        account_id=truth_position.account_id,
        instrument_id=truth_position.instrument_id,
        event_type=PositionEventType.MANUAL_ADJUSTMENT,
        event_time=payload.occurred_at,
        currency=payload.currency,
        gross_amount=payload.amount,
        fx_rate_to_account_ccy=payload.fx_rate_to_account_ccy,
        input_source="MANUAL",
        note=payload.note,
        is_adjustment=True,
    )
    db.add(event)
    db.flush()
    sync_manual_adjustment_event_to_account_ledger(db, event=event)
    db.commit()

    updated_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    return _lifecycle_response(updated_position, source="MANUAL", status_code=201)
