"""
Trading Noobs Backend - Legacy to Truth Sync Service
"""
from __future__ import annotations

from decimal import Decimal
import uuid

from sqlalchemy.orm import Session

from models import (
    AccountLedgerEntry,
    AccountLedgerEntryType,
    AssetMaster,
    Position,
    PositionDirection,
    PositionEvent,
    PositionEventType,
    PositionStatus,
    TradeBatch,
    TradeInstrument,
    TradeInstrumentType,
    TradingPosition,
    TradingPositionSide,
    TradingPositionStatus,
)
from services.trading_accounting_service import AccountingEvent, calculate_fifo_position_accounting


LEGACY_TRUTH_NAMESPACE = uuid.UUID("7db5f25d-3f43-4e32-a8e3-bd245f7d7001")


def _deterministic_public_id(kind: str, source: str) -> str:
    return str(uuid.uuid5(LEGACY_TRUTH_NAMESPACE, f"{kind}:{source}"))


def _coerce_decimal(value) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _enum_value(value, default: str) -> str:
    if value is None:
        return default
    return value.value if hasattr(value, "value") else str(value)


def _ensure_asset_master(db: Session, legacy_position: Position) -> AssetMaster:
    canonical_code = legacy_position.symbol.upper()
    asset = db.query(AssetMaster).filter(AssetMaster.canonical_code == canonical_code).first()
    if asset:
        return asset

    metadata = legacy_position.asset_metadata
    asset = AssetMaster(
        public_id=_deterministic_public_id("asset_master", canonical_code),
        canonical_code=canonical_code,
        display_symbol=canonical_code,
        name=metadata.name if metadata and metadata.name else canonical_code,
        asset_type=(
            _enum_value(metadata.core_type, "")
            if metadata and metadata.core_type
            else (legacy_position.asset_type or "STOCK")
        ),
        quote_currency=(
            _enum_value(metadata.currency, "")
            if metadata and metadata.currency
            else (legacy_position.trading_account.currency if legacy_position.trading_account else "USD")
        ),
        status="ACTIVE",
        sector=metadata.sector if metadata else None,
        industry=None,
        metadata_json={},
    )
    db.add(asset)
    db.flush()
    return asset


def _ensure_trade_instrument(db: Session, asset: AssetMaster, legacy_position: Position) -> TradeInstrument:
    contract_symbol = legacy_position.symbol.upper()
    instrument = (
        db.query(TradeInstrument)
        .filter(
            TradeInstrument.asset_id == asset.id,
            TradeInstrument.contract_symbol == contract_symbol,
            TradeInstrument.instrument_type == TradeInstrumentType.SPOT,
        )
        .first()
    )
    if instrument:
        return instrument

    instrument = TradeInstrument(
        public_id=_deterministic_public_id("trade_instrument", contract_symbol),
        asset_id=asset.id,
        instrument_type=TradeInstrumentType.SPOT,
        display_name=asset.name,
        contract_symbol=contract_symbol,
        status="ACTIVE",
    )
    db.add(instrument)
    db.flush()
    return instrument


def _map_position_status(value: PositionStatus) -> TradingPositionStatus:
    if value == PositionStatus.CLOSED:
        return TradingPositionStatus.CLOSED
    return TradingPositionStatus.OPEN


def _map_position_side(value: PositionDirection) -> TradingPositionSide:
    if value == PositionDirection.SHORT:
        return TradingPositionSide.SHORT
    return TradingPositionSide.LONG


def _batch_event_type(batch: TradeBatch, entry_batches: list[TradeBatch], total_entry_qty: Decimal, cumulative_exit_qty: Decimal, legacy_position: Position) -> PositionEventType:
    if batch.type == batch.type.ENTRY:
        if batch.id == entry_batches[0].id:
            return PositionEventType.OPEN
        return PositionEventType.ADD

    next_exit_qty = cumulative_exit_qty + _coerce_decimal(batch.quantity)
    if legacy_position.status == PositionStatus.CLOSED and next_exit_qty >= total_entry_qty:
        return PositionEventType.CLOSE
    return PositionEventType.REDUCE


def _sync_position_events(
    db: Session,
    *,
    truth_position: TradingPosition,
    legacy_position: Position,
    instrument: TradeInstrument,
) -> tuple[list[PositionEvent], PositionEvent | None, PositionEvent | None]:
    batches = sorted(legacy_position.batches or [], key=lambda batch: batch.time)
    entry_batches = [batch for batch in batches if batch.type == batch.type.ENTRY]
    total_entry_qty = sum((_coerce_decimal(batch.quantity) for batch in entry_batches), Decimal("0"))
    cumulative_exit_qty = Decimal("0")
    events: list[PositionEvent] = []
    opening_event = None
    closing_event = None

    for batch in batches:
        event_public_id = _deterministic_public_id("position_event", batch.public_id or str(batch.id))
        event = db.query(PositionEvent).filter(PositionEvent.public_id == event_public_id).first()
        if not event:
            event = PositionEvent(public_id=event_public_id)
            db.add(event)

        event_type = _batch_event_type(batch, entry_batches, total_entry_qty, cumulative_exit_qty, legacy_position)
        event.user_id = legacy_position.user_id
        event.position_id = truth_position.id
        event.account_id = legacy_position.account_id
        event.instrument_id = instrument.id
        event.event_type = event_type
        event.event_time = batch.time
        event.side_effect = legacy_position.direction.value
        event.quantity = batch.quantity
        event.price = batch.price
        event.currency = truth_position.base_currency
        event.gross_amount = _coerce_decimal(batch.price) * _coerce_decimal(batch.quantity)
        event.fee_amount = Decimal("0")
        event.fee_currency = truth_position.base_currency
        event.realized_pnl_gross = batch.pnl if batch.type == batch.type.EXIT else Decimal("0")
        event.realized_pnl_net = batch.pnl if batch.type == batch.type.EXIT else Decimal("0")
        event.input_source = "LEGACY_BACKFILL"
        event.reason = batch.reason
        event.emotion = batch.emotion
        event.confidence = batch.confidence
        event.note = batch.reason
        event.checklist_snapshot = legacy_position.checklist_responses if event_type == PositionEventType.OPEN else None
        event.thesis = batch.reason if event_type == PositionEventType.OPEN else None
        event.invalidation_rule = None
        event.expected_holding_period = None
        event.planned_exit_rule = None
        event.sizing_rationale = None
        event.is_adjustment = False
        db.flush()

        if batch.type == batch.type.EXIT:
            cumulative_exit_qty += _coerce_decimal(batch.quantity)

        events.append(event)
        if event_type == PositionEventType.OPEN:
            opening_event = event
        if event_type == PositionEventType.CLOSE:
            closing_event = event

    return events, opening_event, closing_event


def _sync_account_ledger_entries(
    db: Session,
    *,
    truth_position: TradingPosition,
    events: list[PositionEvent],
) -> list[AccountLedgerEntry]:
    ledger_entries: list[AccountLedgerEntry] = []

    for event in events:
        realized_pnl = _coerce_decimal(event.realized_pnl_net)
        if realized_pnl == 0:
            continue

        public_id = _deterministic_public_id("account_ledger_entry", f"{event.public_id}:realized_pnl")
        ledger_entry = db.query(AccountLedgerEntry).filter(AccountLedgerEntry.public_id == public_id).first()
        if not ledger_entry:
            ledger_entry = AccountLedgerEntry(public_id=public_id)
            db.add(ledger_entry)

        ledger_entry.user_id = event.user_id
        ledger_entry.account_id = event.account_id
        ledger_entry.position_id = truth_position.id
        ledger_entry.position_event_id = event.id
        ledger_entry.entry_type = AccountLedgerEntryType.REALIZED_PNL
        ledger_entry.occurred_at = event.event_time
        ledger_entry.currency = event.currency or truth_position.base_currency
        ledger_entry.amount = realized_pnl
        ledger_entry.amount_account_ccy = realized_pnl
        ledger_entry.fx_rate_to_account_ccy = Decimal("1")
        ledger_entry.source = "LEGACY_BACKFILL"
        ledger_entry.source_run_id = event.source_run_id
        ledger_entry.description = f"{truth_position.instrument.contract_symbol} realized PnL"
        ledger_entries.append(ledger_entry)

    db.flush()
    return ledger_entries


def _apply_fifo_accounting(
    *,
    truth_position: TradingPosition,
    events: list[PositionEvent],
) -> None:
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
            for event in sorted(events, key=lambda item: (item.event_time, item.id))
        ],
        side=truth_position.side.value,
    )

    truth_position.quantity_opened = summary.quantity_opened
    truth_position.quantity_closed = summary.quantity_closed
    truth_position.avg_open_price = summary.avg_open_price
    truth_position.avg_close_price = summary.avg_close_price
    truth_position.realized_pnl_gross = summary.realized_pnl_gross
    truth_position.realized_pnl_net = summary.realized_pnl_net
    truth_position.total_fees = summary.total_fees

    for event in events:
        result = summary.event_results.get(event.public_id)
        if not result:
            continue
        event.realized_pnl_gross = result.realized_pnl_gross
        event.realized_pnl_net = result.realized_pnl_net


def sync_legacy_position_to_truth(db: Session, legacy_position_id: int) -> TradingPosition:
    legacy_position = (
        db.query(Position)
        .filter(Position.id == legacy_position_id)
        .first()
    )
    if not legacy_position:
        raise ValueError(f"Legacy position {legacy_position_id} not found")

    asset = _ensure_asset_master(db, legacy_position)
    instrument = _ensure_trade_instrument(db, asset, legacy_position)

    truth_public_id = _deterministic_public_id("trading_position", legacy_position.public_id or str(legacy_position.id))
    truth_position = db.query(TradingPosition).filter(TradingPosition.public_id == truth_public_id).first()
    if not truth_position:
        truth_position = TradingPosition(public_id=truth_public_id)
        db.add(truth_position)

    truth_position.user_id = legacy_position.user_id
    truth_position.account_id = legacy_position.account_id
    truth_position.instrument_id = instrument.id
    truth_position.strategy_id = legacy_position.strategy_id
    truth_position.status = _map_position_status(legacy_position.status)
    truth_position.side = _map_position_side(legacy_position.direction)
    truth_position.opened_at = legacy_position.opened_at
    truth_position.closed_at = legacy_position.closed_at
    truth_position.base_currency = (
        _enum_value(legacy_position.asset_metadata.currency, "")
        if legacy_position.asset_metadata and legacy_position.asset_metadata.currency
        else (legacy_position.trading_account.currency if legacy_position.trading_account else "USD")
    )
    truth_position.cost_basis_method = "FIFO"
    if legacy_position.closed_at and legacy_position.opened_at:
        truth_position.holding_period_seconds = int((legacy_position.closed_at - legacy_position.opened_at).total_seconds())
    else:
        truth_position.holding_period_seconds = None
    db.flush()

    events, opening_event, closing_event = _sync_position_events(
        db,
        truth_position=truth_position,
        legacy_position=legacy_position,
        instrument=instrument,
    )
    truth_position.opening_event_id = opening_event.id if opening_event else None
    truth_position.closing_event_id = closing_event.id if closing_event else None
    _apply_fifo_accounting(truth_position=truth_position, events=events)
    db.flush()
    _sync_account_ledger_entries(db, truth_position=truth_position, events=events)

    db.commit()
    db.refresh(truth_position)
    return truth_position


def sync_all_legacy_positions_to_truth(db: Session, legacy_position_ids: list[int] | None = None) -> dict[str, int]:
    query = db.query(Position.id).order_by(Position.id.asc())
    if legacy_position_ids:
        query = query.filter(Position.id.in_(legacy_position_ids))

    ids = [row[0] for row in query.all()]
    summary = {
        "processed": 0,
        "created_positions": 0,
        "updated_positions": 0,
        "errors": 0,
    }

    for legacy_position_id in ids:
        summary["processed"] += 1
        legacy_position = db.query(Position).filter(Position.id == legacy_position_id).first()
        truth_public_id = _deterministic_public_id("trading_position", legacy_position.public_id or str(legacy_position.id))
        existed = db.query(TradingPosition.id).filter(TradingPosition.public_id == truth_public_id).first() is not None
        try:
            sync_legacy_position_to_truth(db, legacy_position_id)
            if existed:
                summary["updated_positions"] += 1
            else:
                summary["created_positions"] += 1
        except Exception:
            db.rollback()
            summary["errors"] += 1

    return summary
