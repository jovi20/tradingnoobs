"""
Trading Noobs Backend - TradingPosition Truth Read Router
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import PositionEvent, User
from schemas import TradingPositionEventNarrativeUpdate
from services.auth_service import get_current_user
from services.trading_position_read_service import build_trading_position_lifecycle_payload, resolve_truth_position_by_public_id

router = APIRouter(prefix="/api/trading-positions", tags=["Trading Positions"])


def _lifecycle_response(truth_position, source: str = "DERIVED") -> JSONResponse:
    data = build_trading_position_lifecycle_payload(truth_position)

    return JSONResponse(
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
