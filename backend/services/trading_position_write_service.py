"""
Trading Noobs Backend - TradingPosition Truth Write Service
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, text
from sqlalchemy.orm import Session

from app_config.release_contract import JOURNAL_BETA_CONTRACT
from models import (
    BatchType,
    PositionEvent,
    PositionEventType,
    TradeBatch,
    TradeSourceState,
    TradingAccount,
    TradingPosition,
    TradingPositionStatus,
)
from services.account_ledger_service import (
    require_accounting_healthy,
    sync_realized_pnl_event_to_account_ledger,
)
from services.trading_accounting_service import AccountingEvent, calculate_fifo_position_accounting
from services.truth_legacy_projection_service import project_truth_accounting_to_legacy


TRADE_EVENT_TYPES = {
    PositionEventType.OPEN,
    PositionEventType.ADD,
    PositionEventType.REDUCE,
    PositionEventType.CLOSE,
}


class ArchivedTradingPositionWriteError(ValueError):
    http_status = JOURNAL_BETA_CONTRACT.lifecycle.archived_position_mutation.http_status
    code = JOURNAL_BETA_CONTRACT.lifecycle.archived_position_mutation.code
    policy = JOURNAL_BETA_CONTRACT.lifecycle.archived_position_mutation.policy

    def __init__(self, position_public_id: str):
        self.position_public_id = position_public_id
        super().__init__("Archived trading positions are read-only")


class TradeEventChronologyError(ValueError):
    code = "EVENT_CHRONOLOGY_VIOLATION"
    http_status = 422


class TradeEventQuantityError(ValueError):
    code = "INVALID_LIFECYCLE_QUANTITY"
    http_status = 422


class SourceBoundTradeWriteError(ValueError):
    code = "SOURCE_BOUND_ACCOUNT"
    http_status = 409


class PositionLifecycleOrderConflictError(ValueError):
    code = "POSITION_LIFECYCLE_ORDER_CONFLICT"
    http_status = 409


class PositionSideConflictError(ValueError):
    code = "POSITION_SIDE_CONFLICT"
    http_status = 409


class PositionEventReversalError(ValueError):
    code = "POSITION_EVENT_REVERSAL_INVALID"
    http_status = 422


def lock_owned_truth_position(
    db: Session,
    *,
    user_id: int,
    position_public_id: str,
) -> tuple[TradingAccount, TradingPosition] | None:
    account_id_row = db.query(TradingPosition.account_id).filter(
        TradingPosition.public_id == position_public_id,
        TradingPosition.user_id == user_id,
    ).first()
    if account_id_row is None:
        return None

    account = db.query(TradingAccount).filter(
        TradingAccount.id == account_id_row[0],
        TradingAccount.user_id == user_id,
    ).with_for_update().first()
    if account is None:
        return None
    if db.get_bind().dialect.name == "sqlite":
        db.execute(
            text(
                """
                UPDATE trading_accounts
                SET trade_source_state = trade_source_state
                WHERE id = :account_id
                """
            ),
            {"account_id": account.id},
        )

    position = db.query(TradingPosition).filter(
        TradingPosition.public_id == position_public_id,
        TradingPosition.user_id == user_id,
        TradingPosition.account_id == account.id,
    ).with_for_update().first()
    if position is None:
        return None
    return account, position


def require_truth_position_financial_write_allowed(position: TradingPosition) -> None:
    if position.status == TradingPositionStatus.ARCHIVED:
        raise ArchivedTradingPositionWriteError(position.public_id)


def _require_position_accounting_healthy(
    db: Session,
    position: TradingPosition,
) -> None:
    account = db.query(TradingAccount).filter(
        TradingAccount.id == position.account_id,
        TradingAccount.user_id == position.user_id,
    ).one()
    require_accounting_healthy(account)


def _coerce_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _remaining_open_quantity(position: TradingPosition) -> Decimal:
    return _coerce_decimal(position.quantity_opened) - _coerce_decimal(position.quantity_closed)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _active_trade_events(db: Session, position: TradingPosition) -> list[PositionEvent]:
    reversed_event_ids = {
        row[0]
        for row in db.query(PositionEvent.reverses_event_id)
        .filter(
            PositionEvent.position_id == position.id,
            PositionEvent.event_type == PositionEventType.REVERSAL,
            PositionEvent.reverses_event_id.isnot(None),
        )
        .all()
    }
    return [
        event
        for event in (
            db.query(PositionEvent)
            .filter(
                PositionEvent.position_id == position.id,
                PositionEvent.event_type.in_(TRADE_EVENT_TYPES),
            )
            .order_by(
                PositionEvent.event_time.asc(),
                PositionEvent.sequence_no.asc(),
                PositionEvent.id.asc(),
            )
            .all()
        )
        if event.id not in reversed_event_ids
    ]


def _lock_later_non_void_same_side_lifecycles(
    db: Session,
    *,
    position: TradingPosition,
) -> list[TradingPosition]:
    return (
        db.query(TradingPosition)
        .filter(
            TradingPosition.user_id == position.user_id,
            TradingPosition.account_id == position.account_id,
            TradingPosition.instrument_id == position.instrument_id,
            TradingPosition.side == position.side,
            TradingPosition.id != position.id,
            TradingPosition.status != TradingPositionStatus.VOID,
            (
                (TradingPosition.opened_at > position.opened_at)
                | (
                    (TradingPosition.opened_at == position.opened_at)
                    & (TradingPosition.id > position.id)
                )
            ),
        )
        .order_by(TradingPosition.id.asc())
        .with_for_update()
        .all()
    )


def _require_reopen_conflicts_clear(
    db: Session,
    *,
    position: TradingPosition,
) -> None:
    if _lock_later_non_void_same_side_lifecycles(db, position=position):
        raise PositionLifecycleOrderConflictError(
            "A later non-void same-side lifecycle must be voided before this "
            "lifecycle can be reopened"
        )
    other_open = (
        db.query(TradingPosition)
        .filter(
            TradingPosition.user_id == position.user_id,
            TradingPosition.account_id == position.account_id,
            TradingPosition.instrument_id == position.instrument_id,
            TradingPosition.side == position.side,
            TradingPosition.id != position.id,
            TradingPosition.financially_open.is_(True),
            TradingPosition.status != TradingPositionStatus.VOID,
        )
        .order_by(TradingPosition.id.asc())
        .with_for_update()
        .first()
    )
    if other_open is not None:
        raise PositionSideConflictError(
            "Another same-side lifecycle is financially open"
        )


def _project_trade_event_to_legacy_batch(
    db: Session,
    *,
    position: TradingPosition,
    event: PositionEvent,
) -> TradeBatch | None:
    from services.truth_legacy_projection_service import resolve_legacy_position_for_truth

    legacy_position = resolve_legacy_position_for_truth(
        db,
        truth_position=position,
    )
    if legacy_position is None:
        return None

    batch = db.query(TradeBatch).filter(
        TradeBatch.public_id == event.public_id,
        TradeBatch.position_id == legacy_position.id,
    ).first()
    if batch is None:
        batch = TradeBatch(
            public_id=event.public_id,
            position_id=legacy_position.id,
        )
        db.add(batch)
    batch.type = (
        BatchType.ENTRY
        if event.event_type in {PositionEventType.OPEN, PositionEventType.ADD}
        else BatchType.EXIT
    )
    batch.price = event.price
    batch.quantity = event.quantity
    batch.time = event.event_time
    batch.reason = event.reason
    batch.emotion = event.emotion
    batch.confidence = event.confidence
    batch.pnl = (
        event.realized_pnl_net
        if event.event_type in {PositionEventType.REDUCE, PositionEventType.CLOSE}
        else None
    )
    db.flush()
    return batch


def replay_truth_position_accounting(db: Session, *, position: TradingPosition) -> None:
    reversed_event_ids = {
        row[0]
        for row in db.query(PositionEvent.reverses_event_id)
        .filter(
            PositionEvent.position_id == position.id,
            PositionEvent.event_type == PositionEventType.REVERSAL,
            PositionEvent.reverses_event_id.isnot(None),
        )
        .all()
    }
    events = (
        db.query(PositionEvent)
        .filter(
            PositionEvent.position_id == position.id,
            PositionEvent.event_type.in_(TRADE_EVENT_TYPES),
        )
        .order_by(
            PositionEvent.event_time.asc(),
            PositionEvent.sequence_no.asc(),
            PositionEvent.id.asc(),
        )
        .all()
    )
    active_events = [event for event in events if event.id not in reversed_event_ids]

    summary = calculate_fifo_position_accounting(
        [
            AccountingEvent(
                public_id=event.public_id,
                event_type=event.event_type.value,
                quantity=_coerce_decimal(event.quantity),
                price=_coerce_decimal(event.price),
                fee_amount=_coerce_decimal(event.fee_amount),
                fx_rate_to_account_ccy=_coerce_decimal(event.fx_rate_to_account_ccy or 1),
            )
            for event in events
            if event.id not in reversed_event_ids
        ],
        side=position.side.value,
    )

    position.quantity_opened = summary.quantity_opened
    position.quantity_closed = summary.quantity_closed
    position.avg_open_price = summary.remaining_avg_open_price
    position.avg_close_price = summary.avg_close_price
    position.realized_pnl_gross = summary.realized_pnl_gross
    position.realized_pnl_net = summary.realized_pnl_net
    position.total_fees = summary.total_fees
    position.financially_open = summary.open_quantity > 0

    opening_event = next((event for event in active_events if event.event_type == PositionEventType.OPEN), None)
    position.opening_event_id = opening_event.id if opening_event else None

    if not active_events and events:
        latest_reversal = (
            db.query(PositionEvent)
            .filter(
                PositionEvent.position_id == position.id,
                PositionEvent.event_type == PositionEventType.REVERSAL,
                PositionEvent.reverses_event_id.isnot(None),
            )
            .order_by(
                PositionEvent.event_time.desc(),
                PositionEvent.sequence_no.desc(),
                PositionEvent.id.desc(),
            )
            .first()
        )
        position.status = TradingPositionStatus.VOID
        position.closed_at = latest_reversal.event_time if latest_reversal else position.closed_at
        position.closing_event_id = latest_reversal.id if latest_reversal else None
    elif summary.open_quantity == 0 and summary.quantity_opened > 0:
        closing_event = next(
            (event for event in reversed(active_events) if event.event_type in {PositionEventType.REDUCE, PositionEventType.CLOSE}),
            None,
        )
        position.status = TradingPositionStatus.CLOSED
        position.closed_at = closing_event.event_time if closing_event else position.closed_at
        position.closing_event_id = closing_event.id if closing_event else None
    else:
        position.status = TradingPositionStatus.OPEN
        position.closed_at = None
        position.closing_event_id = None

    if position.opened_at and position.closed_at:
        opened_at = position.opened_at
        closed_at = position.closed_at
        if opened_at.tzinfo is None and closed_at.tzinfo is not None:
            opened_at = opened_at.replace(tzinfo=timezone.utc)
        if closed_at.tzinfo is None and opened_at.tzinfo is not None:
            closed_at = closed_at.replace(tzinfo=timezone.utc)
        position.holding_period_seconds = int((closed_at - opened_at).total_seconds())
    else:
        position.holding_period_seconds = None

    for event in active_events:
        result = summary.event_results.get(event.public_id)
        if not result:
            continue
        event.realized_pnl_gross = result.realized_pnl_gross
        event.realized_pnl_net = result.realized_pnl_net

    project_truth_accounting_to_legacy(db, truth_position=position)
    db.flush()

    for event in active_events:
        sync_realized_pnl_event_to_account_ledger(db, event=event, position=position)


def append_truth_trade_event(
    db: Session,
    *,
    position: TradingPosition,
    event_type: PositionEventType,
    quantity: Decimal,
    price: Decimal,
    currency: str,
    occurred_at: datetime,
    fee_amount: Decimal = Decimal("0"),
    fee_currency: str | None = None,
    fx_rate_to_account_ccy: Decimal = Decimal("1"),
    reason: str | None = None,
    emotion: str | None = None,
    confidence: int | None = None,
    note: str | None = None,
    account: TradingAccount | None = None,
) -> PositionEvent:
    require_truth_position_financial_write_allowed(position)
    if account is None:
        account = db.query(TradingAccount).filter(
            TradingAccount.id == position.account_id,
            TradingAccount.user_id == position.user_id,
        ).one()
    if account.id != position.account_id or account.user_id != position.user_id:
        raise ValueError("Trading account and position owner mismatch")
    require_accounting_healthy(account)
    if account.trade_source_state == TradeSourceState.SOURCE_BOUND.value:
        raise SourceBoundTradeWriteError(
            "Source-bound accounts reject manual trade commands"
        )
    if position.status == TradingPositionStatus.CLOSED:
        raise ValueError("Cannot append trade events to a closed trading position")

    active_events = _active_trade_events(db, position)
    if active_events and _as_utc(occurred_at) < _as_utc(active_events[-1].event_time):
        raise TradeEventChronologyError(
            "Trade events cannot predate the latest active lifecycle event"
        )

    if event_type != PositionEventType.OPEN:
        remaining_open_quantity = _remaining_open_quantity(position)
        if remaining_open_quantity <= 0:
            raise TradeEventQuantityError(
                "Trading position has no remaining open quantity"
            )
        if event_type == PositionEventType.REDUCE and quantity >= remaining_open_quantity:
            raise TradeEventQuantityError(
                f"REDUCE event quantity must be less than remaining open quantity ({remaining_open_quantity})"
            )
        if event_type == PositionEventType.CLOSE and quantity != remaining_open_quantity:
            raise TradeEventQuantityError(
                f"CLOSE event quantity must equal remaining open quantity ({remaining_open_quantity})"
            )

    event = PositionEvent(
        user_id=position.user_id,
        position_id=position.id,
        account_id=position.account_id,
        instrument_id=position.instrument_id,
        event_type=event_type,
        event_time=occurred_at,
        sequence_no=(
            db.query(func.max(PositionEvent.sequence_no))
            .filter(PositionEvent.position_id == position.id)
            .scalar()
            or 0
        ) + 1,
        side_effect=position.side.value,
        quantity=quantity,
        price=price,
        currency=currency,
        gross_amount=quantity * price,
        fee_amount=fee_amount,
        fee_currency=fee_currency or currency,
        fx_rate_to_account_ccy=fx_rate_to_account_ccy,
        input_source="MANUAL",
        reason=reason,
        emotion=emotion,
        confidence=confidence,
        note=note,
    )
    db.add(event)
    db.flush()
    replay_truth_position_accounting(db, position=position)
    _project_trade_event_to_legacy_batch(
        db,
        position=position,
        event=event,
    )
    account.trade_source_state = TradeSourceState.MANUAL.value
    db.flush()
    return event


def reverse_latest_truth_trade_event(
    db: Session,
    *,
    position: TradingPosition,
    event: PositionEvent,
    occurred_at: datetime,
    actor_user_id: int,
    request_id: str,
    reason: str,
    note: str | None = None,
) -> PositionEvent:
    require_truth_position_financial_write_allowed(position)
    _require_position_accounting_healthy(db, position)
    if event.event_type not in TRADE_EVENT_TYPES:
        raise PositionEventReversalError("Only trade events can be reversed")
    if event.event_type == PositionEventType.OPEN:
        raise PositionEventReversalError(
            "OPEN must be reversed through whole-position void"
        )

    existing_reversal = (
        db.query(PositionEvent)
        .filter(
            PositionEvent.position_id == position.id,
            PositionEvent.event_type == PositionEventType.REVERSAL,
            PositionEvent.reverses_event_id == event.id,
        )
        .first()
    )
    if existing_reversal:
        raise PositionEventReversalError("Position event has already been reversed")

    reversed_event_ids = {
        row[0]
        for row in db.query(PositionEvent.reverses_event_id)
        .filter(
            PositionEvent.position_id == position.id,
            PositionEvent.event_type == PositionEventType.REVERSAL,
            PositionEvent.reverses_event_id.isnot(None),
        )
        .all()
    }
    active_trade_events = [
        item
        for item in (
            db.query(PositionEvent)
            .filter(
                PositionEvent.position_id == position.id,
                PositionEvent.event_type.in_(TRADE_EVENT_TYPES),
            )
            .order_by(
                PositionEvent.event_time.asc(),
                PositionEvent.sequence_no.asc(),
                PositionEvent.id.asc(),
            )
            .all()
        )
        if item.id not in reversed_event_ids
    ]
    if not active_trade_events or active_trade_events[-1].id != event.id:
        raise PositionEventReversalError(
            "Only the latest active trade event can be reversed"
        )
    normalized_occurred_at = _as_utc(occurred_at)
    if normalized_occurred_at < _as_utc(event.event_time):
        raise TradeEventChronologyError(
            "Trade-event reversal cannot predate the original event"
        )
    if event.event_type in {PositionEventType.REDUCE, PositionEventType.CLOSE}:
        _require_reopen_conflicts_clear(db, position=position)

    reversal_event = PositionEvent(
        user_id=position.user_id,
        position_id=position.id,
        account_id=position.account_id,
        instrument_id=position.instrument_id,
        event_type=PositionEventType.REVERSAL,
        event_time=normalized_occurred_at,
        sequence_no=(
            db.query(func.max(PositionEvent.sequence_no))
            .filter(PositionEvent.position_id == position.id)
            .scalar()
            or 0
        ) + 1,
        side_effect=position.side.value,
        currency=event.currency or position.base_currency,
        gross_amount=-_coerce_decimal(event.gross_amount),
        fee_amount=Decimal("0"),
        fee_currency=event.fee_currency or event.currency or position.base_currency,
        fx_rate_to_account_ccy=_coerce_decimal(event.fx_rate_to_account_ccy or 1),
        realized_pnl_gross=-_coerce_decimal(event.realized_pnl_gross),
        realized_pnl_net=-_coerce_decimal(event.realized_pnl_net),
        input_source="MANUAL",
        actor_user_id=actor_user_id,
        request_id=request_id,
        reason=reason.strip(),
        note=note or f"Reversal of {event.public_id}",
        is_adjustment=True,
        reverses_event_id=event.id,
    )
    db.add(reversal_event)
    db.flush()
    replay_truth_position_accounting(db, position=position)
    sync_realized_pnl_event_to_account_ledger(db, event=reversal_event, position=position)
    return reversal_event


def void_truth_position(
    db: Session,
    *,
    position: TradingPosition,
    occurred_at: datetime,
    actor_user_id: int,
    request_id: str,
    reason: str,
) -> list[PositionEvent]:
    require_truth_position_financial_write_allowed(position)
    _require_position_accounting_healthy(db, position)
    active_trade_events = _active_trade_events(db, position)
    if not active_trade_events:
        raise PositionEventReversalError(
            "Trading position has no active trade events to void"
        )
    if _lock_later_non_void_same_side_lifecycles(db, position=position):
        raise PositionLifecycleOrderConflictError(
            "Later non-void same-side lifecycles must be voided first"
        )

    normalized_occurred_at = _as_utc(occurred_at)
    if normalized_occurred_at < max(
        _as_utc(event.event_time) for event in active_trade_events
    ):
        raise TradeEventChronologyError(
            "Position void cannot predate an active lifecycle event"
        )

    next_sequence = (
        db.query(func.max(PositionEvent.sequence_no))
        .filter(PositionEvent.position_id == position.id)
        .scalar()
        or 0
    ) + 1
    reversals: list[PositionEvent] = []
    for offset, original in enumerate(reversed(active_trade_events)):
        reversal = PositionEvent(
            user_id=position.user_id,
            position_id=position.id,
            account_id=position.account_id,
            instrument_id=position.instrument_id,
            event_type=PositionEventType.REVERSAL,
            event_time=normalized_occurred_at,
            sequence_no=next_sequence + offset,
            side_effect=position.side.value,
            currency=original.currency or position.base_currency,
            gross_amount=-_coerce_decimal(original.gross_amount),
            fee_amount=Decimal("0"),
            fee_currency=(
                original.fee_currency
                or original.currency
                or position.base_currency
            ),
            fx_rate_to_account_ccy=_coerce_decimal(
                original.fx_rate_to_account_ccy or 1
            ),
            realized_pnl_gross=-_coerce_decimal(original.realized_pnl_gross),
            realized_pnl_net=-_coerce_decimal(original.realized_pnl_net),
            input_source="MANUAL",
            actor_user_id=actor_user_id,
            request_id=request_id,
            reason=reason.strip(),
            note=f"Whole-position void reversal of {original.public_id}",
            is_adjustment=True,
            reverses_event_id=original.id,
        )
        db.add(reversal)
        db.flush()
        sync_realized_pnl_event_to_account_ledger(
            db,
            event=reversal,
            position=position,
        )
        reversals.append(reversal)

    replay_truth_position_accounting(db, position=position)
    return reversals
