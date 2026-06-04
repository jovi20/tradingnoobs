from dataclasses import dataclass
from decimal import Decimal

from models import AccountLedgerEntry, AssetMaster, OutboxEvent, PositionEvent, TradeInstrument, TradingPosition
from services.identity_service import generate_public_id


MONEY_QUANT = Decimal("0.01")


@dataclass(frozen=True)
class FifoLot:
    quantity: Decimal
    price: Decimal
    fee: Decimal


@dataclass(frozen=True)
class FifoMatchResult:
    realized_pnl_gross: Decimal
    realized_pnl_net: Decimal
    remaining_lots: list[FifoLot]


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANT)


def match_fifo(
    lots: list[FifoLot],
    *,
    close_quantity: Decimal,
    close_price: Decimal,
    close_fee: Decimal,
) -> FifoMatchResult:
    quantity_to_close = close_quantity
    gross_pnl = Decimal("0")
    consumed_open_fees = Decimal("0")
    remaining_lots: list[FifoLot] = []

    for lot in lots:
        if quantity_to_close <= 0:
            remaining_lots.append(lot)
            continue

        matched_quantity = min(lot.quantity, quantity_to_close)
        gross_pnl += matched_quantity * (close_price - lot.price)

        consumed_ratio = matched_quantity / lot.quantity
        consumed_fee = lot.fee * consumed_ratio
        consumed_open_fees += consumed_fee

        remaining_quantity = lot.quantity - matched_quantity
        if remaining_quantity > 0:
            remaining_lots.append(
                FifoLot(
                    quantity=remaining_quantity,
                    price=lot.price,
                    fee=_money(lot.fee - consumed_fee),
                )
            )

        quantity_to_close -= matched_quantity

    if quantity_to_close > 0:
        raise ValueError("close_quantity exceeds available FIFO lots")

    realized_pnl_gross = _money(gross_pnl)
    realized_pnl_net = _money(gross_pnl - consumed_open_fees - close_fee)

    return FifoMatchResult(
        realized_pnl_gross=realized_pnl_gross,
        realized_pnl_net=realized_pnl_net,
        remaining_lots=remaining_lots,
    )


class TradingAccountingService:
    def __init__(self, db_session):
        self.db = db_session

    def open_position(
        self,
        *,
        user_id: int,
        account_id: int,
        symbol: str,
        side: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
        event_time,
        thesis: str | None = None,
        edge_source: str | None = None,
        disconfirming_evidence: str | None = None,
        invalidation_rule: str | None = None,
        expected_holding_period: str | None = None,
        planned_exit_rule: str | None = None,
        sizing_rationale: str | None = None,
        checklist_snapshot: dict | None = None,
    ) -> TradingPosition:
        instrument = self._get_or_create_instrument(symbol)
        position = TradingPosition(
            public_id=generate_public_id(),
            user_id=user_id,
            account_id=account_id,
            instrument_id=instrument.id,
            side=side,
            status="OPEN",
            cost_method="FIFO",
            quantity_opened=quantity,
            quantity_closed=Decimal("0"),
            realized_pnl_gross=Decimal("0"),
            realized_pnl_net=Decimal("0"),
            fifo_lots=[self._lot_to_payload(FifoLot(quantity=quantity, price=price, fee=fee))],
            thesis=thesis,
            opened_at=event_time,
        )
        self.db.add(position)
        self.db.flush()

        self._record_position_event(
            position=position,
            event_type="OPEN",
            quantity=quantity,
            price=price,
            fee=fee,
            event_time=event_time,
            realized_pnl_gross=Decimal("0"),
            realized_pnl_net=Decimal("0"),
            thesis=thesis,
            edge_source=edge_source,
            disconfirming_evidence=disconfirming_evidence,
            invalidation_rule=invalidation_rule,
            expected_holding_period=expected_holding_period,
            planned_exit_rule=planned_exit_rule,
            sizing_rationale=sizing_rationale,
            checklist_snapshot=checklist_snapshot,
            payload={"thesis": thesis},
        )
        self._record_ledger_entry(
            position=position,
            entry_type="OPEN",
            amount=-(quantity * price + fee),
            occurred_at=event_time,
        )
        self._record_outbox_event(position=position, event_type="OPEN", event_time=event_time)
        self.db.flush()
        return position

    def add_to_position(
        self,
        *,
        position_public_id: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
        event_time,
    ) -> TradingPosition:
        position = self._get_open_position(position_public_id)
        position.quantity_opened = self._as_decimal(position.quantity_opened) + quantity
        lots = self._lots_from_payload(position.fifo_lots)
        lots.append(FifoLot(quantity=quantity, price=price, fee=fee))
        position.fifo_lots = [self._lot_to_payload(lot) for lot in lots]

        self._record_position_event(
            position=position,
            event_type="ADD",
            quantity=quantity,
            price=price,
            fee=fee,
            event_time=event_time,
            realized_pnl_gross=Decimal("0"),
            realized_pnl_net=Decimal("0"),
        )
        self._record_ledger_entry(
            position=position,
            entry_type="ADD",
            amount=-(quantity * price + fee),
            occurred_at=event_time,
        )
        self._record_outbox_event(position=position, event_type="ADD", event_time=event_time)
        self.db.flush()
        return position

    def reduce_position(
        self,
        *,
        position_public_id: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
        event_time,
    ) -> TradingPosition:
        position = self._get_open_position(position_public_id)
        match_result = self._apply_fifo_close(position=position, quantity=quantity, price=price, fee=fee)

        self._record_position_event(
            position=position,
            event_type="REDUCE",
            quantity=quantity,
            price=price,
            fee=fee,
            event_time=event_time,
            realized_pnl_gross=match_result.realized_pnl_gross,
            realized_pnl_net=match_result.realized_pnl_net,
        )
        self._record_ledger_entry(
            position=position,
            entry_type="REDUCE",
            amount=quantity * price - fee,
            occurred_at=event_time,
        )
        self._record_outbox_event(position=position, event_type="REDUCE", event_time=event_time)
        self.db.flush()
        return position

    def close_position(
        self,
        *,
        position_public_id: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
        event_time,
    ) -> TradingPosition:
        position = self._get_open_position(position_public_id)
        match_result = self._apply_fifo_close(position=position, quantity=quantity, price=price, fee=fee)
        position.status = "CLOSED"
        position.closed_at = event_time

        self._record_position_event(
            position=position,
            event_type="CLOSE",
            quantity=quantity,
            price=price,
            fee=fee,
            event_time=event_time,
            realized_pnl_gross=match_result.realized_pnl_gross,
            realized_pnl_net=match_result.realized_pnl_net,
        )
        self._record_ledger_entry(
            position=position,
            entry_type="CLOSE",
            amount=quantity * price - fee,
            occurred_at=event_time,
        )
        self._record_outbox_event(position=position, event_type="CLOSE", event_time=event_time)
        self.db.flush()
        return position

    def record_dividend(
        self,
        *,
        user_id: int,
        account_id: int,
        amount: Decimal,
        currency: str,
        occurred_at,
        position_public_id: str | None = None,
    ) -> AccountLedgerEntry:
        position = self._get_position_or_none(position_public_id)
        entry = self._record_account_ledger_entry(
            user_id=user_id,
            account_id=account_id,
            related_position_id=position.id if position else None,
            entry_type="DIVIDEND",
            amount=amount,
            currency=currency,
            occurred_at=occurred_at,
            payload={"position_public_id": position_public_id},
        )
        self._record_ledger_outbox_event(entry=entry, event_type="dividend")
        self.db.flush()
        return entry

    def record_fee(
        self,
        *,
        user_id: int,
        account_id: int,
        amount: Decimal,
        currency: str,
        occurred_at,
        position_public_id: str | None = None,
        reason: str | None = None,
    ) -> AccountLedgerEntry:
        position = self._get_position_or_none(position_public_id)
        entry = self._record_account_ledger_entry(
            user_id=user_id,
            account_id=account_id,
            related_position_id=position.id if position else None,
            entry_type="FEE",
            amount=-abs(amount),
            currency=currency,
            occurred_at=occurred_at,
            payload={"position_public_id": position_public_id, "reason": reason},
        )
        self._record_ledger_outbox_event(entry=entry, event_type="fee")
        self.db.flush()
        return entry

    def record_cash_adjustment(
        self,
        *,
        user_id: int,
        account_id: int,
        amount: Decimal,
        currency: str,
        occurred_at,
        reason: str,
    ) -> AccountLedgerEntry:
        entry = self._record_account_ledger_entry(
            user_id=user_id,
            account_id=account_id,
            related_position_id=None,
            entry_type="CASH_ADJUSTMENT",
            amount=amount,
            currency=currency,
            occurred_at=occurred_at,
            payload={"reason": reason},
        )
        self._record_ledger_outbox_event(entry=entry, event_type="cash_adjustment")
        self.db.flush()
        return entry

    def calculate_unrealized_pnl(
        self,
        *,
        position_public_id: str,
        current_price: Decimal,
        fx_rate: Decimal = Decimal("1"),
    ) -> dict[str, Decimal]:
        position = self.db.query(TradingPosition).filter_by(public_id=position_public_id).one()
        lots = self._lots_from_payload(position.fifo_lots)
        gross_pnl = Decimal("0")
        remaining_open_fees = Decimal("0")

        for lot in lots:
            if position.side == "SHORT":
                gross_pnl += lot.quantity * (lot.price - current_price)
            else:
                gross_pnl += lot.quantity * (current_price - lot.price)
            remaining_open_fees += lot.fee

        gross_pnl *= fx_rate
        net_pnl = gross_pnl - (remaining_open_fees * fx_rate)
        return {
            "unrealized_pnl_gross": _money(gross_pnl),
            "unrealized_pnl_net": _money(net_pnl),
        }

    def _get_or_create_instrument(self, symbol: str) -> TradeInstrument:
        normalized_symbol = symbol.strip().upper()
        instrument = self.db.query(TradeInstrument).filter_by(symbol=normalized_symbol, venue="UNKNOWN").one_or_none()
        if instrument:
            return instrument

        asset = self.db.query(AssetMaster).filter_by(symbol=normalized_symbol).one_or_none()
        if not asset:
            asset = AssetMaster(public_id=generate_public_id(), symbol=normalized_symbol, name=normalized_symbol)
            self.db.add(asset)
            self.db.flush()

        instrument = TradeInstrument(
            public_id=generate_public_id(),
            asset_id=asset.id,
            symbol=normalized_symbol,
            venue="UNKNOWN",
            instrument_type="EQUITY",
            currency=asset.currency,
        )
        self.db.add(instrument)
        self.db.flush()
        return instrument

    def _get_open_position(self, public_id: str) -> TradingPosition:
        position = self.db.query(TradingPosition).filter_by(public_id=public_id).one()
        if position.status != "OPEN":
            raise ValueError("position is not open")
        return position

    def _get_position_or_none(self, public_id: str | None) -> TradingPosition | None:
        if public_id is None:
            return None
        return self.db.query(TradingPosition).filter_by(public_id=public_id).one()

    def _apply_fifo_close(
        self,
        *,
        position: TradingPosition,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
    ) -> FifoMatchResult:
        match_result = match_fifo(
            self._lots_from_payload(position.fifo_lots),
            close_quantity=quantity,
            close_price=price,
            close_fee=fee,
        )
        position.quantity_closed = self._as_decimal(position.quantity_closed) + quantity
        position.realized_pnl_gross = self._as_decimal(position.realized_pnl_gross) + match_result.realized_pnl_gross
        position.realized_pnl_net = self._as_decimal(position.realized_pnl_net) + match_result.realized_pnl_net
        position.fifo_lots = [self._lot_to_payload(lot) for lot in match_result.remaining_lots]
        return match_result

    def _record_position_event(
        self,
        *,
        position: TradingPosition,
        event_type: str,
        quantity: Decimal,
        price: Decimal,
        fee: Decimal,
        event_time,
        realized_pnl_gross: Decimal,
        realized_pnl_net: Decimal,
        thesis: str | None = None,
        edge_source: str | None = None,
        disconfirming_evidence: str | None = None,
        invalidation_rule: str | None = None,
        expected_holding_period: str | None = None,
        planned_exit_rule: str | None = None,
        sizing_rationale: str | None = None,
        checklist_snapshot: dict | None = None,
        payload: dict | None = None,
    ) -> None:
        self.db.add(
            PositionEvent(
                public_id=generate_public_id(),
                position_id=position.id,
                event_type=event_type,
                quantity=quantity,
                price=price,
                fee=fee,
                realized_pnl_gross=realized_pnl_gross,
                realized_pnl_net=realized_pnl_net,
                thesis=thesis,
                edge_source=edge_source,
                disconfirming_evidence=disconfirming_evidence,
                invalidation_rule=invalidation_rule,
                expected_holding_period=expected_holding_period,
                planned_exit_rule=planned_exit_rule,
                sizing_rationale=sizing_rationale,
                checklist_snapshot=checklist_snapshot,
                event_time=event_time,
                payload=payload or {},
            )
        )

    def _record_ledger_entry(
        self,
        *,
        position: TradingPosition,
        entry_type: str,
        amount: Decimal,
        occurred_at,
    ) -> None:
        self._record_account_ledger_entry(
            user_id=position.user_id,
            account_id=position.account_id,
            related_position_id=position.id,
            entry_type=entry_type,
            amount=amount,
            currency="USD",
            occurred_at=occurred_at,
            payload={"position_public_id": position.public_id},
        )

    def _record_account_ledger_entry(
        self,
        *,
        user_id: int,
        account_id: int,
        related_position_id: int | None,
        entry_type: str,
        amount: Decimal,
        currency: str,
        occurred_at,
        payload: dict,
    ) -> AccountLedgerEntry:
        entry = AccountLedgerEntry(
            public_id=generate_public_id(),
            user_id=user_id,
            account_id=account_id,
            related_position_id=related_position_id,
            entry_type=entry_type,
            amount=amount,
            currency=currency,
            occurred_at=occurred_at,
            payload=payload,
        )
        self.db.add(entry)
        self.db.flush()
        return entry

    def _record_outbox_event(self, *, position: TradingPosition, event_type: str, event_time) -> None:
        self.db.add(
            OutboxEvent(
                public_id=generate_public_id(),
                event_type=f"trading_position.{event_type.lower()}",
                aggregate_type="TradingPosition",
                aggregate_public_id=position.public_id,
                payload={
                    "position_public_id": position.public_id,
                    "event_type": event_type,
                    "event_time": event_time.isoformat(),
                },
                status="PENDING",
            )
        )

    def _record_ledger_outbox_event(self, *, entry: AccountLedgerEntry, event_type: str) -> None:
        self.db.add(
            OutboxEvent(
                public_id=generate_public_id(),
                event_type=f"account_ledger.{event_type}",
                aggregate_type="AccountLedgerEntry",
                aggregate_public_id=entry.public_id,
                payload={
                    "ledger_entry_public_id": entry.public_id,
                    "entry_type": entry.entry_type,
                    "amount": str(entry.amount),
                    "currency": entry.currency,
                },
                status="PENDING",
            )
        )

    @staticmethod
    def _as_decimal(value) -> Decimal:
        return value if isinstance(value, Decimal) else Decimal(str(value or "0"))

    @staticmethod
    def _lot_to_payload(lot: FifoLot) -> dict[str, str]:
        return {
            "quantity": str(lot.quantity),
            "price": str(lot.price),
            "fee": str(lot.fee),
        }

    @staticmethod
    def _lots_from_payload(payload: list[dict[str, str]] | None) -> list[FifoLot]:
        return [
            FifoLot(
                quantity=Decimal(lot["quantity"]),
                price=Decimal(lot["price"]),
                fee=Decimal(lot["fee"]),
            )
            for lot in (payload or [])
        ]
