"""
Trading Noobs Backend - TradingPosition Truth Write Service
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func
from sqlalchemy.orm import Session

from app_config.release_contract import JOURNAL_BETA_CONTRACT
from models import (
    PositionEvent,
    PositionEventType,
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

    opening_event = next((event for event in active_events if event.event_type == PositionEventType.OPEN), None)
    position.opening_event_id = opening_event.id if opening_event else None

    if summary.open_quantity == 0 and summary.quantity_opened > 0:
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
) -> PositionEvent:
    require_truth_position_financial_write_allowed(position)
    _require_position_accounting_healthy(db, position)
    if position.status == TradingPositionStatus.CLOSED:
        raise ValueError("Cannot append trade events to a closed trading position")

    if event_type == PositionEventType.CLOSE:
        remaining_open_quantity = _remaining_open_quantity(position)
        if quantity != remaining_open_quantity:
            raise ValueError(
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
    return event


def reverse_latest_truth_trade_event(
    db: Session,
    *,
    position: TradingPosition,
    event: PositionEvent,
    occurred_at: datetime,
    note: str | None = None,
) -> PositionEvent:
    require_truth_position_financial_write_allowed(position)
    _require_position_accounting_healthy(db, position)
    if event.event_type not in TRADE_EVENT_TYPES:
        raise ValueError("Only trade events can be reversed")
    if event.event_type == PositionEventType.OPEN:
        raise ValueError("OPEN events cannot be reversed until position void semantics exist")

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
        raise ValueError("Position event has already been reversed")

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
        raise ValueError("Only the latest active trade event can be reversed")

    reversal_event = PositionEvent(
        user_id=position.user_id,
        position_id=position.id,
        account_id=position.account_id,
        instrument_id=position.instrument_id,
        event_type=PositionEventType.REVERSAL,
        event_time=occurred_at,
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
        note=note or f"Reversal of {event.public_id}",
        is_adjustment=True,
        reverses_event_id=event.id,
    )
    db.add(reversal_event)
    db.flush()
    replay_truth_position_accounting(db, position=position)
    sync_realized_pnl_event_to_account_ledger(db, event=reversal_event, position=position)
    return reversal_event
