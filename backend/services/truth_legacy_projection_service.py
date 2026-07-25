"""Compatibility projection from TradingPosition truth accounting to legacy Position reads."""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy import or_
from sqlalchemy.orm import Session

from models import (
    Position,
    PositionStatus,
    Strategy,
    TradingAccount,
    TradingPosition,
    TradingPositionStatus,
)
from services.legacy_truth_sync_service import legacy_position_truth_public_id


def resolve_truth_position_for_legacy(
    db: Session,
    *,
    user_id: int,
    legacy_position: Position,
) -> TradingPosition | None:
    if legacy_position.user_id != user_id:
        return None

    return db.query(TradingPosition).join(
        TradingAccount,
        TradingPosition.account_id == TradingAccount.id,
    ).outerjoin(
        Strategy,
        TradingPosition.strategy_id == Strategy.id,
    ).filter(
        TradingPosition.public_id == legacy_position_truth_public_id(legacy_position),
        TradingPosition.user_id == user_id,
        TradingPosition.account_id == legacy_position.account_id,
        TradingAccount.user_id == user_id,
        or_(
            TradingPosition.strategy_id.is_(None),
            Strategy.user_id == user_id,
        ),
    ).first()


def resolve_legacy_position_for_truth(
    db: Session,
    *,
    truth_position: TradingPosition,
) -> Position | None:
    candidates = db.query(Position).join(
        TradingAccount,
        Position.account_id == TradingAccount.id,
    ).outerjoin(
        Strategy,
        Position.strategy_id == Strategy.id,
    ).filter(
        Position.user_id == truth_position.user_id,
        Position.account_id == truth_position.account_id,
        TradingAccount.user_id == truth_position.user_id,
        or_(
            Position.strategy_id.is_(None),
            Strategy.user_id == truth_position.user_id,
        ),
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
    if legacy_position is None:
        legacy_position = resolve_legacy_position_for_truth(
            db,
            truth_position=truth_position,
        )
    elif (
        legacy_position.user_id != truth_position.user_id
        or legacy_position.account_id != truth_position.account_id
        or db.query(TradingAccount.id).filter(
            TradingAccount.id == truth_position.account_id,
            TradingAccount.user_id == truth_position.user_id,
        ).first() is None
    ):
        return None
    if legacy_position is None:
        return None

    quantity_opened = Decimal(str(truth_position.quantity_opened or 0))
    quantity_closed = Decimal(str(truth_position.quantity_closed or 0))
    legacy_position.total_quantity = max(Decimal("0"), quantity_opened - quantity_closed)
    legacy_position.average_entry_price = truth_position.avg_open_price
    legacy_position.realized_pnl = truth_position.realized_pnl_net or Decimal("0")
    legacy_position.status = (
        PositionStatus.CLOSED
        if truth_position.status in {
            TradingPositionStatus.CLOSED,
            TradingPositionStatus.VOID,
        }
        else PositionStatus.OPEN
    )
    legacy_position.opened_at = truth_position.opened_at
    legacy_position.closed_at = truth_position.closed_at
    return legacy_position


def resolve_user_truth_positions_for_legacy(
    db: Session,
    *,
    user_id: int,
) -> dict[int, TradingPosition]:
    legacy_positions = db.query(Position).join(
        TradingAccount,
        Position.account_id == TradingAccount.id,
    ).outerjoin(
        Strategy,
        Position.strategy_id == Strategy.id,
    ).filter(
        Position.user_id == user_id,
        TradingAccount.user_id == user_id,
        or_(Position.strategy_id.is_(None), Strategy.user_id == user_id),
    ).all()
    legacy_by_truth_public_id = {
        legacy_position_truth_public_id(position): position
        for position in legacy_positions
    }
    truth_positions = db.query(TradingPosition).join(
        TradingAccount,
        TradingPosition.account_id == TradingAccount.id,
    ).outerjoin(
        Strategy,
        TradingPosition.strategy_id == Strategy.id,
    ).filter(
        TradingPosition.user_id == user_id,
        TradingAccount.user_id == user_id,
        or_(
            TradingPosition.strategy_id.is_(None),
            Strategy.user_id == user_id,
        ),
    ).all()

    return {
        legacy_position.id: truth_position
        for truth_position in truth_positions
        if (
            (legacy_position := legacy_by_truth_public_id.get(truth_position.public_id))
            is not None
            and legacy_position.account_id == truth_position.account_id
        )
    }


def exclude_void_truth_legacy_positions(
    db: Session,
    *,
    user_id: int,
    positions: list[Position],
) -> list[Position]:
    truth_by_legacy_id = resolve_user_truth_positions_for_legacy(
        db,
        user_id=user_id,
    )
    return [
        position
        for position in positions
        if (
            truth_by_legacy_id.get(position.id) is None
            or truth_by_legacy_id[position.id].status != TradingPositionStatus.VOID
        )
    ]


def project_user_truth_positions_to_legacy(
    db: Session,
    *,
    user_id: int,
) -> dict[int, TradingPosition]:
    truth_by_legacy_id = resolve_user_truth_positions_for_legacy(
        db,
        user_id=user_id,
    )

    for legacy_position_id, truth_position in truth_by_legacy_id.items():
        legacy_position = db.query(Position).filter(
            Position.id == legacy_position_id
        ).one()
        project_truth_accounting_to_legacy(
            db,
            truth_position=truth_position,
            legacy_position=legacy_position,
        )

    db.flush()
    return truth_by_legacy_id
