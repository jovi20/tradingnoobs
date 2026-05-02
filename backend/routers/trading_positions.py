"""
Trading Noobs Backend - TradingPosition Truth Read Router
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from database import get_db
from models import User
from services.auth_service import get_current_user
from services.trading_position_read_service import build_trading_position_lifecycle_payload, resolve_truth_position_by_public_id

router = APIRouter(prefix="/api/trading-positions", tags=["Trading Positions"])


@router.get("/{position_public_id}/lifecycle")
def get_trading_position_lifecycle(
    position_public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    truth_position = resolve_truth_position_by_public_id(db, current_user.id, position_public_id)
    if not truth_position:
        raise HTTPException(status_code=404, detail="Trading position not found")

    data = build_trading_position_lifecycle_payload(truth_position)

    return JSONResponse(
        content=jsonable_encoder(
            {
                "data": data,
                "meta": {
                    "as_of": truth_position.updated_at or truth_position.created_at,
                    "generated_at": truth_position.updated_at or truth_position.created_at,
                    "freshness": "FRESH",
                    "source": "DERIVED",
                    "maturity": "EARLY_SIGNAL",
                    "value_status": "FINAL",
                },
            }
        )
    )
