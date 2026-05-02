"""
Trading Noobs Backend - TradingPosition Truth Write Service
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from models import PositionEvent, PositionEventType, TradingPosition, TradingPositionStatus
from services.account_ledger_service import sync_realized_pnl_event_to_account_ledger
from services.trading_accounting_service import AccountingEvent, calculate_fifo_position_accounting


TRADE_EVENT_TYPES = {
    PositionEventType.OPEN,
    PositionEventType.ADD,
    PositionEventType.REDUCE,
    PositionEventType.CLOSE,
}


def _coerce_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _remaining_open_quantity(position: TradingPosition) -> Decimal:
    return _coerce_decimal(position.quantity_opened) - _coerce_decimal(position.quantity_closed)


def replay_truth_position_accounting(db: Session, *, position: TradingPosition) -> None:
    events = (
        db.query(PositionEvent)
        .filter(
            PositionEvent.position_id == position.id,
            PositionEvent.event_type.in_(TRADE_EVENT_TYPES),
        )
        .order_by(PositionEvent.event_time.asc(), PositionEvent.id.asc())
        .all()
    )

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

    opening_event = next((event for event in events if event.event_type == PositionEventType.OPEN), None)
    position.opening_event_id = opening_event.id if opening_event else None

    if summary.open_quantity == 0 and summary.quantity_opened > 0:
        closing_event = next(
            (event for event in reversed(events) if event.event_type in {PositionEventType.REDUCE, PositionEventType.CLOSE}),
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

    for event in events:
        result = summary.event_results.get(event.public_id)
        if not result:
            continue
        event.realized_pnl_gross = result.realized_pnl_gross
        event.realized_pnl_net = result.realized_pnl_net

    db.flush()

    for event in events:
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
