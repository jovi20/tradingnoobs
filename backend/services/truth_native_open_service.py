"""Truth-native, single-transaction manual OPEN command."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from models import (
    BatchType,
    Position,
    PositionDirection,
    PositionEvent,
    PositionEventType,
    PositionStatus,
    Strategy,
    TradeBatch,
    TradeSourceState,
    TradingAccount,
    TradingPosition,
    TradingPositionSide,
    TradingPositionStatus,
)
from services.account_ledger_service import require_accounting_healthy
from services.financial_command_service import (
    permanently_forbid_account_hard_delete,
)
from services.instrument_identity_service import (
    InstrumentIdentity,
    get_or_create_journal_instrument,
)
from services.legacy_truth_sync_service import (
    legacy_position_truth_public_id_from_public_id,
)
from services.outbox_service import enqueue_position_event_created_outbox
from services.trading_position_write_service import append_truth_trade_event
from services.truth_legacy_projection_service import (
    project_truth_accounting_to_legacy,
    resolve_legacy_position_for_truth,
)


class TruthNativeOpenError(ValueError):
    code = "TRUTH_NATIVE_OPEN_ERROR"
    http_status = 409


class OpenPositionExistsError(TruthNativeOpenError):
    code = "OPEN_POSITION_EXISTS"

    def __init__(self, position_public_id: str):
        self.position_public_id = position_public_id
        super().__init__("Use ADD for an existing same-side lifecycle")


class PositionChronologyError(TruthNativeOpenError):
    code = "EVENT_CHRONOLOGY_VIOLATION"
    http_status = 422


class SourceBoundAccountError(TruthNativeOpenError):
    code = "SOURCE_BOUND_ACCOUNT"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _enum_value(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def lock_owned_trading_account(
    db: Session,
    *,
    user_id: int,
    account_id: int,
) -> TradingAccount | None:
    return db.query(TradingAccount).filter(
        TradingAccount.id == account_id,
        TradingAccount.user_id == user_id,
    ).with_for_update().first()


def _legacy_reference(
    db: Session,
    position: TradingPosition,
) -> str:
    legacy = resolve_legacy_position_for_truth(
        db,
        truth_position=position,
    )
    return legacy.public_id if legacy is not None else position.public_id


def _find_open_conflict(
    db: Session,
    *,
    account: TradingAccount,
    instrument_id: int,
    side: TradingPositionSide,
) -> TradingPosition | None:
    return db.query(TradingPosition).filter(
        TradingPosition.account_id == account.id,
        TradingPosition.instrument_id == instrument_id,
        TradingPosition.side == side,
        TradingPosition.financially_open.is_(True),
    ).order_by(TradingPosition.id.asc()).first()


def create_truth_native_open(
    db: Session,
    *,
    user_id: int,
    account: TradingAccount,
    strategy: Strategy | None,
    identity: InstrumentIdentity,
    side: TradingPositionSide,
    quantity: Decimal,
    price: Decimal,
    occurred_at: datetime,
    fee_amount: Decimal = Decimal("0"),
    reason: str | None = None,
    emotion: str | None = None,
    confidence: int | None = None,
    planned_entry_price: Decimal | None = None,
    planned_stop_loss: Decimal | None = None,
    planned_take_profit: list[dict] | None = None,
    checklist_responses: dict | None = None,
) -> tuple[Position, TradingPosition, PositionEvent]:
    if account.user_id != user_id:
        raise ValueError("Account owner mismatch")
    if strategy is not None and strategy.user_id != user_id:
        raise ValueError("Strategy owner mismatch")
    require_accounting_healthy(account)
    if _enum_value(account.trade_source_state) == TradeSourceState.SOURCE_BOUND.value:
        raise SourceBoundAccountError("Source-bound accounts reject manual OPEN")

    instrument = get_or_create_journal_instrument(
        db,
        identity=identity,
    )
    conflict = _find_open_conflict(
        db,
        account=account,
        instrument_id=instrument.id,
        side=side,
    )
    if conflict is not None:
        raise OpenPositionExistsError(_legacy_reference(db, conflict))

    last_terminal = db.query(TradingPosition).filter(
        TradingPosition.account_id == account.id,
        TradingPosition.instrument_id == instrument.id,
        TradingPosition.side == side,
        TradingPosition.closed_at.isnot(None),
    ).order_by(TradingPosition.closed_at.desc()).first()
    if (
        last_terminal is not None
        and _as_utc(occurred_at) < _as_utc(last_terminal.closed_at)
    ):
        raise PositionChronologyError(
            "OPEN cannot predate the latest same-side lifecycle terminal time"
        )

    legacy_public_id = str(uuid.uuid4())
    truth_position = TradingPosition(
        public_id=legacy_position_truth_public_id_from_public_id(
            legacy_public_id
        ),
        user_id=user_id,
        account_id=account.id,
        instrument_id=instrument.id,
        strategy_id=strategy.id if strategy else None,
        status=TradingPositionStatus.OPEN,
        side=side,
        opened_at=occurred_at,
        base_currency=account.currency,
        cost_basis_method="FIFO",
        quantity_opened=Decimal("0"),
        quantity_closed=Decimal("0"),
        financially_open=True,
    )
    try:
        with db.begin_nested():
            db.add(truth_position)
            db.flush()
    except IntegrityError:
        conflict = _find_open_conflict(
            db,
            account=account,
            instrument_id=instrument.id,
            side=side,
        )
        if conflict is not None:
            raise OpenPositionExistsError(
                _legacy_reference(db, conflict)
            ) from None
        raise

    event = append_truth_trade_event(
        db,
        position=truth_position,
        event_type=PositionEventType.OPEN,
        quantity=quantity,
        price=price,
        currency=account.currency,
        occurred_at=occurred_at,
        fee_amount=fee_amount,
        fee_currency=account.currency,
        reason=reason,
        emotion=emotion,
        confidence=confidence,
        note=reason,
    )
    permanently_forbid_account_hard_delete(account)
    enqueue_position_event_created_outbox(
        db,
        position=truth_position,
        event=event,
    )

    legacy = Position(
        public_id=legacy_public_id,
        user_id=user_id,
        account_id=account.id,
        strategy_id=strategy.id if strategy else None,
        symbol=identity.normalized_symbol,
        exchange=identity.exchange_code,
        asset_type=identity.asset_type,
        asset_metadata_symbol=None,
        direction=PositionDirection(side.value),
        status=PositionStatus.OPEN,
        total_quantity=quantity,
        average_entry_price=price,
        realized_pnl=Decimal("0"),
        opened_at=occurred_at,
        planned_entry_price=planned_entry_price,
        planned_stop_loss=planned_stop_loss,
        planned_take_profit=planned_take_profit,
        checklist_responses=checklist_responses,
    )
    db.add(legacy)
    db.flush()
    db.add(
        TradeBatch(
            public_id=event.public_id,
            position_id=legacy.id,
            type=BatchType.ENTRY,
            price=price,
            quantity=quantity,
            time=occurred_at,
            reason=reason,
            emotion=emotion,
            confidence=confidence,
        )
    )
    project_truth_accounting_to_legacy(
        db,
        truth_position=truth_position,
        legacy_position=legacy,
    )
    account.trade_source_state = TradeSourceState.MANUAL.value
    db.flush()
    return legacy, truth_position, event
