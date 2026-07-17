"""
Trading Noobs Backend - Legacy to Truth Sync Service
"""
from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import uuid

from sqlalchemy.orm import Session

from app_config.release_contract import (
    JOURNAL_BETA_CONTRACT,
    ReleaseContractViolation,
    require_allowed_asset_type,
    require_allowed_instrument_type,
    require_allowed_market,
    require_exchange_code,
    require_normalized_symbol,
    require_release_currency,
)
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
    TradingAccount,
    TradingPosition,
    TradingPositionSide,
    TradingPositionStatus,
)
from services.trading_accounting_service import AccountingEvent, calculate_fifo_position_accounting


LEGACY_TRUTH_NAMESPACE = uuid.UUID("7db5f25d-3f43-4e32-a8e3-bd245f7d7001")
_JOURNAL_IDENTITY_METADATA_KEY = "journal_identity_v1"
_ALLOWED_INSTRUMENT_COMBINATIONS = frozenset(
    (item.asset_type, item.instrument_type, item.market)
    for item in JOURNAL_BETA_CONTRACT.instruments.allowed_combinations
)


@dataclass(frozen=True)
class LegacyInstrumentIdentity:
    asset_type: str
    market: str
    exchange_code: str
    normalized_symbol: str
    instrument_type: str
    quote_currency: str


def _deterministic_public_id(kind: str, source: str) -> str:
    return str(uuid.uuid5(LEGACY_TRUTH_NAMESPACE, f"{kind}:{source}"))


def legacy_position_truth_public_id(legacy_position: Position) -> str:
    return _deterministic_public_id("trading_position", legacy_position.public_id or str(legacy_position.id))


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


def validate_legacy_instrument_identity(
    *,
    position_asset_type: object,
    account_currency: object,
    symbol: object,
    exchange_code: object,
    metadata_core_type: object | None = None,
    metadata_market: object | None = None,
    metadata_currency: object | None = None,
    metadata_instrument: object | None = None,
) -> LegacyInstrumentIdentity:
    """Resolve and validate the legacy fields used to create canonical instrument truth."""
    normalized_symbol = require_normalized_symbol(symbol)
    exchange_code = require_exchange_code(exchange_code)
    position_asset_type = require_allowed_asset_type(position_asset_type)
    asset_type = (
        require_allowed_asset_type(metadata_core_type)
        if metadata_core_type is not None
        else position_asset_type
    )
    if asset_type != position_asset_type:
        raise ReleaseContractViolation(
            "INSTRUMENT_IDENTITY_MISMATCH",
            "asset_metadata.core_type",
            metadata_core_type,
        )

    account_currency = require_release_currency(account_currency, field="account.currency")
    raw_quote_currency = (
        metadata_currency if metadata_currency is not None else account_currency
    )
    quote_currency = require_release_currency(
        getattr(raw_quote_currency, "value", raw_quote_currency),
        field="asset_metadata.currency",
    )
    if quote_currency != account_currency:
        raise ReleaseContractViolation(
            "INSTRUMENT_IDENTITY_MISMATCH",
            "asset_metadata.currency",
            metadata_currency,
        )

    market = (
        require_allowed_market(metadata_market, field="asset_metadata.market")
        if metadata_market is not None
        else ("CRYPTO" if asset_type == "CRYPTO" else "US")
    )

    instrument_type = (
        require_allowed_instrument_type(
            metadata_instrument,
            field="asset_metadata.instrument",
        )
        if metadata_instrument is not None
        else TradeInstrumentType.SPOT.value
    )
    if (asset_type, instrument_type, market) not in _ALLOWED_INSTRUMENT_COMBINATIONS:
        raise ReleaseContractViolation(
            "UNSUPPORTED_INSTRUMENT_COMBINATION",
            "asset_metadata.market",
            metadata_market,
        )

    return LegacyInstrumentIdentity(
        asset_type=asset_type,
        market=market,
        exchange_code=exchange_code,
        normalized_symbol=normalized_symbol,
        instrument_type=instrument_type,
        quote_currency=quote_currency,
    )


def _identity_payload(identity: LegacyInstrumentIdentity) -> dict[str, str]:
    return {
        "asset_type": identity.asset_type,
        "market": identity.market,
        "exchange_code": identity.exchange_code,
        "normalized_symbol": identity.normalized_symbol,
        "instrument_type": identity.instrument_type,
        "quote_currency": identity.quote_currency,
    }


def _asset_matches_identity(
    asset: AssetMaster,
    identity: LegacyInstrumentIdentity,
) -> bool:
    return (
        _enum_value(asset.asset_type, "") == identity.asset_type
        and _enum_value(asset.quote_currency, "") == identity.quote_currency
        and isinstance(asset.metadata_json, dict)
        and asset.metadata_json.get(_JOURNAL_IDENTITY_METADATA_KEY)
        == _identity_payload(identity)
    )


def _require_proven_legacy_identity(
    db: Session,
    legacy_position: Position,
    identity: LegacyInstrumentIdentity,
    *,
    expected_identity: LegacyInstrumentIdentity | None,
) -> None:
    if expected_identity is not None:
        if identity != expected_identity:
            raise ReleaseContractViolation(
                "INSTRUMENT_IDENTITY_MISMATCH",
                "position.exchange",
                legacy_position.exchange,
            )
        return

    existing_asset = (
        db.query(AssetMaster)
        .filter(AssetMaster.canonical_code == identity.normalized_symbol)
        .first()
    )
    if existing_asset is not None and _asset_matches_identity(existing_asset, identity):
        return

    raise ReleaseContractViolation(
        "LEGACY_INSTRUMENT_IDENTITY_UNPROVEN",
        "position.exchange",
        legacy_position.exchange,
    )


def _ensure_asset_master(
    db: Session,
    legacy_position: Position,
    identity: LegacyInstrumentIdentity,
) -> AssetMaster:
    canonical_code = identity.normalized_symbol
    asset = db.query(AssetMaster).filter(AssetMaster.canonical_code == canonical_code).first()
    if asset:
        if not _asset_matches_identity(asset, identity):
            raise ReleaseContractViolation(
                "INSTRUMENT_IDENTITY_MISMATCH",
                "asset_master.canonical_code",
                canonical_code,
            )
        return asset

    metadata = legacy_position.asset_metadata
    asset = AssetMaster(
        public_id=_deterministic_public_id("asset_master", canonical_code),
        canonical_code=canonical_code,
        display_symbol=canonical_code,
        name=metadata.name if metadata and metadata.name else canonical_code,
        asset_type=identity.asset_type,
        quote_currency=identity.quote_currency,
        status="ACTIVE",
        sector=metadata.sector if metadata else None,
        industry=None,
        metadata_json={
            _JOURNAL_IDENTITY_METADATA_KEY: _identity_payload(identity),
        },
    )
    db.add(asset)
    db.flush()
    return asset


def _ensure_trade_instrument(
    db: Session,
    asset: AssetMaster,
    identity: LegacyInstrumentIdentity,
) -> TradeInstrument:
    contract_symbol = identity.normalized_symbol
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
        public_id=_deterministic_public_id(
            "trade_instrument",
            "|".join(_identity_payload(identity).values()),
        ),
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


def sync_legacy_position_to_truth(
    db: Session,
    legacy_position_id: int,
    *,
    expected_identity: LegacyInstrumentIdentity | None = None,
) -> TradingPosition:
    legacy_position = (
        db.query(Position)
        .filter(Position.id == legacy_position_id)
        .first()
    )
    if not legacy_position:
        raise ValueError(f"Legacy position {legacy_position_id} not found")

    account = (
        db.query(TradingAccount)
        .filter(TradingAccount.id == legacy_position.account_id)
        .first()
    )
    if account is None:
        raise ValueError(
            f"Trading account {legacy_position.account_id} for legacy position "
            f"{legacy_position_id} not found"
        )
    if legacy_position.user_id != account.user_id:
        raise ValueError(
            f"Legacy position {legacy_position_id} and trading account "
            f"{account.id} have different owners"
        )

    metadata = legacy_position.asset_metadata
    identity = validate_legacy_instrument_identity(
        position_asset_type=legacy_position.asset_type,
        account_currency=account.currency,
        symbol=legacy_position.symbol,
        exchange_code=legacy_position.exchange,
        metadata_core_type=metadata.core_type if metadata else None,
        metadata_market=metadata.market if metadata else None,
        metadata_currency=metadata.currency if metadata else None,
        metadata_instrument=metadata.instrument if metadata else None,
    )
    _require_proven_legacy_identity(
        db,
        legacy_position,
        identity,
        expected_identity=expected_identity,
    )

    truth_public_id = legacy_position_truth_public_id(legacy_position)
    truth_position = db.query(TradingPosition).filter(
        TradingPosition.public_id == truth_public_id
    ).first()
    if truth_position is not None and (
        truth_position.user_id != legacy_position.user_id
        or truth_position.account_id != account.id
    ):
        raise ValueError(
            f"Trading position {truth_public_id} ownership does not match "
            f"legacy position {legacy_position_id}"
        )

    asset = _ensure_asset_master(db, legacy_position, identity)
    instrument = _ensure_trade_instrument(db, asset, identity)

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
    truth_position.base_currency = identity.quote_currency
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


def sync_all_legacy_positions_to_truth(
    db: Session,
    legacy_position_ids: list[int] | None = None,
    *,
    expected_identities: dict[int, LegacyInstrumentIdentity] | None = None,
) -> dict[str, int]:
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
        truth_public_id = legacy_position_truth_public_id(legacy_position)
        existed = db.query(TradingPosition.id).filter(TradingPosition.public_id == truth_public_id).first() is not None
        try:
            sync_legacy_position_to_truth(
                db,
                legacy_position_id,
                expected_identity=(expected_identities or {}).get(legacy_position_id),
            )
            if existed:
                summary["updated_positions"] += 1
            else:
                summary["created_positions"] += 1
        except Exception:
            db.rollback()
            summary["errors"] += 1

    return summary
