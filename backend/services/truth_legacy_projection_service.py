"""Compatibility projection from TradingPosition truth accounting to legacy Position reads."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session

from models import Position, PositionStatus, TradingPosition, TradingPositionStatus
from services.legacy_truth_sync_service import legacy_position_truth_public_id


def resolve_truth_position_for_legacy(
    db: Session,
    *,
    user_id: int,
    legacy_position: Position,
) -> TradingPosition | None:
    return db.query(TradingPosition).filter(
        TradingPosition.public_id == legacy_position_truth_public_id(legacy_position),
        TradingPosition.user_id == user_id,
    ).first()


def resolve_legacy_position_for_truth(
    db: Session,
    *,
    truth_position: TradingPosition,
) -> Position | None:
    candidates = db.query(Position).filter(
        Position.user_id == truth_position.user_id,
        Position.account_id == truth_position.account_id,
    ).all()
    return next(
        (
            legacy_position
            for legacy_position in candidates
            if legacy_position_truth_public_id(legacy_position) == truth_position.public_id
        ),
        None,
    )


def project_truth_accounting_to_legacy(
    db: Session,
    *,
    truth_position: TradingPosition,
    legacy_position: Position | None = None,
) -> Position | None:
    legacy_position = legacy_position or resolve_legacy_position_for_truth(
        db,
        truth_position=truth_position,
    )
    if legacy_position is None:
        return None

    quantity_opened = Decimal(str(truth_position.quantity_opened or 0))
    quantity_closed = Decimal(str(truth_position.quantity_closed or 0))
    legacy_position.total_quantity = max(Decimal("0"), quantity_opened - quantity_closed)
    legacy_position.average_entry_price = truth_position.avg_open_price
    legacy_position.realized_pnl = truth_position.realized_pnl_net or Decimal("0")
    legacy_position.status = (
        PositionStatus.CLOSED
        if truth_position.status == TradingPositionStatus.CLOSED
        else PositionStatus.OPEN
    )
    legacy_position.opened_at = truth_position.opened_at
    legacy_position.closed_at = truth_position.closed_at
    return legacy_position


def project_user_truth_positions_to_legacy(
    db: Session,
    *,
    user_id: int,
) -> dict[int, TradingPosition]:
    legacy_positions = db.query(Position).filter(Position.user_id == user_id).all()
    legacy_by_truth_public_id = {
        legacy_position_truth_public_id(position): position
        for position in legacy_positions
    }
    truth_positions = db.query(TradingPosition).filter(TradingPosition.user_id == user_id).all()
    truth_by_legacy_id: dict[int, TradingPosition] = {}

    for truth_position in truth_positions:
        legacy_position = legacy_by_truth_public_id.get(truth_position.public_id)
        if legacy_position is None:
            continue
        project_truth_accounting_to_legacy(
            db,
            truth_position=truth_position,
            legacy_position=legacy_position,
        )
        truth_by_legacy_id[legacy_position.id] = truth_position

    db.flush()
    return truth_by_legacy_id
