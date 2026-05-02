"""
Trading Noobs Backend - Trading Accounting Service

Centralizes trading PnL/cost-basis math. V1 intentionally starts with a pure
FIFO core so routers and read models can move off scattered average-cost logic.
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable


OPEN_EVENT_TYPES = {"OPEN", "ADD"}
CLOSE_EVENT_TYPES = {"REDUCE", "CLOSE"}


@dataclass(frozen=True)
class AccountingEvent:
    public_id: str
    event_type: str
    quantity: Decimal
    price: Decimal
    fee_amount: Decimal = Decimal("0")
    fx_rate_to_account_ccy: Decimal = Decimal("1")


@dataclass(frozen=True)
class AccountingEventResult:
    event_public_id: str
    realized_pnl_gross: Decimal
    realized_pnl_net: Decimal
    fee_amount_account_ccy: Decimal
    quantity_closed: Decimal


@dataclass(frozen=True)
class PositionAccountingSummary:
    quantity_opened: Decimal
    quantity_closed: Decimal
    open_quantity: Decimal
    avg_open_price: Decimal
    avg_close_price: Decimal
    realized_pnl_gross: Decimal
    realized_pnl_net: Decimal
    total_fees: Decimal
    event_results: dict[str, AccountingEventResult]


@dataclass
class _FifoLot:
    quantity: Decimal
    price: Decimal


def _to_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _event_type(value) -> str:
    return value.value if hasattr(value, "value") else str(value)


def calculate_fifo_position_accounting(
    events: Iterable[AccountingEvent],
    *,
    side: str,
) -> PositionAccountingSummary:
    lots: list[_FifoLot] = []
    quantity_opened = Decimal("0")
    quantity_closed = Decimal("0")
    opened_notional = Decimal("0")
    closed_notional = Decimal("0")
    realized_gross_total = Decimal("0")
    total_fees = Decimal("0")
    event_results: dict[str, AccountingEventResult] = {}
    side_value = _event_type(side).upper()

    for event in events:
        event_type = _event_type(event.event_type).upper()
        quantity = _to_decimal(event.quantity)
        price = _to_decimal(event.price)
        fee_account_ccy = _to_decimal(event.fee_amount) * _to_decimal(event.fx_rate_to_account_ccy)
        total_fees += fee_account_ccy

        if event_type in OPEN_EVENT_TYPES:
            lots.append(_FifoLot(quantity=quantity, price=price))
            quantity_opened += quantity
            opened_notional += quantity * price
            event_results[event.public_id] = AccountingEventResult(
                event_public_id=event.public_id,
                realized_pnl_gross=Decimal("0"),
                realized_pnl_net=Decimal("0"),
                fee_amount_account_ccy=fee_account_ccy,
                quantity_closed=Decimal("0"),
            )
            continue

        if event_type not in CLOSE_EVENT_TYPES:
            event_results[event.public_id] = AccountingEventResult(
                event_public_id=event.public_id,
                realized_pnl_gross=Decimal("0"),
                realized_pnl_net=Decimal("0"),
                fee_amount_account_ccy=fee_account_ccy,
                quantity_closed=Decimal("0"),
            )
            continue

        remaining = quantity
        event_realized_gross = Decimal("0")
        while remaining > 0:
            if not lots:
                raise ValueError(f"Cannot close {quantity} units without enough FIFO lots")

            lot = lots[0]
            matched = min(lot.quantity, remaining)
            if side_value == "SHORT":
                event_realized_gross += (lot.price - price) * matched
            else:
                event_realized_gross += (price - lot.price) * matched

            lot.quantity -= matched
            remaining -= matched
            if lot.quantity == 0:
                lots.pop(0)

        quantity_closed += quantity
        closed_notional += quantity * price
        realized_gross_total += event_realized_gross
        event_results[event.public_id] = AccountingEventResult(
            event_public_id=event.public_id,
            realized_pnl_gross=event_realized_gross,
            realized_pnl_net=event_realized_gross - fee_account_ccy,
            fee_amount_account_ccy=fee_account_ccy,
            quantity_closed=quantity,
        )

    open_quantity = sum((lot.quantity for lot in lots), Decimal("0"))
    avg_open_price = opened_notional / quantity_opened if quantity_opened else Decimal("0")
    avg_close_price = closed_notional / quantity_closed if quantity_closed else Decimal("0")

    return PositionAccountingSummary(
        quantity_opened=quantity_opened,
        quantity_closed=quantity_closed,
        open_quantity=open_quantity,
        avg_open_price=avg_open_price,
        avg_close_price=avg_close_price,
        realized_pnl_gross=realized_gross_total,
        realized_pnl_net=realized_gross_total - total_fees,
        total_fees=total_fees,
        event_results=event_results,
    )
