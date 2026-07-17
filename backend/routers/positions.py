"""
Trading Noobs Backend - Positions Router
Handles Position CRUD and Batch operations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from decimal import Decimal, InvalidOperation
import csv
import io
from datetime import datetime

from app_config.release_contract import (
    JOURNAL_BETA_CONTRACT,
    RAW_ASSET_TYPE_INPUT_PATTERN,
    RAW_CURRENCY_INPUT_PATTERN,
    RAW_INSTRUMENT_TYPE_INPUT_PATTERN,
    RAW_MARKET_INPUT_PATTERN,
    ReleaseContractViolation,
    release_violation_detail,
    require_allowed_asset_type,
    require_allowed_market,
    require_exchange_code,
    require_normalized_symbol,
    require_release_currency,
)
from database import get_db
from observability import get_structured_logger, log_event
from routers.auth import get_current_user
from models import (
    User, Position, TradeBatch, TradingAccount,
    PositionStatus, PositionDirection, BatchType
)
from schemas import (
    PositionCreate, PositionUpdate, PositionResponse, PositionListResponse,
    TradeBatchCreate, TradeBatchUpdate, TradeBatchResponse,
    PositionStatusEnum,
)
from models import TradingPosition, TradingPositionStatus
from release_profile import RuntimeCapability
from services.capability_service import is_effective_capability_enabled
from services.public_id_service import resolve_position, resolve_trade_batch, resolve_trading_account
from services.legacy_truth_sync_service import (
    LegacyInstrumentIdentity,
    sync_legacy_position_to_truth,
    validate_legacy_instrument_identity,
)
from services.position_instrument_projection_service import (
    PositionInstrumentProjection,
    project_position_instrument,
)
from services.trading_position_read_service import (
    CanonicalAccountingUnresolvedError,
    build_trading_position_lifecycle_payload,
    canonical_accounting_unresolved_detail,
)
from services.truth_legacy_projection_service import (
    resolve_user_truth_positions_for_legacy,
    resolve_truth_position_for_legacy,
)
from services.trading_accounting_service import (
    AccountingEvent,
    calculate_fifo_position_accounting,
)

router = APIRouter(prefix="/api/positions", tags=["positions"])
logger = get_structured_logger("positions")

def _release_contract_value(callable_, *args, **kwargs):
    try:
        return callable_(*args, **kwargs)
    except ReleaseContractViolation as violation:
        raise HTTPException(
            status_code=422,
            detail=release_violation_detail(violation),
        ) from violation


def _enum_value(value):
    return value.value if hasattr(value, "value") else str(value)


def _truth_position_is_financially_open(truth_position: TradingPosition) -> bool:
    """Conservatively derive slot occupancy from canonical accounting truth."""
    if (
        truth_position.quantity_opened is None
        or truth_position.quantity_closed is None
    ):
        return True
    try:
        quantity_opened = Decimal(str(truth_position.quantity_opened))
        quantity_closed = Decimal(str(truth_position.quantity_closed))
        remaining_quantity = quantity_opened - quantity_closed
        if not all(
            quantity.is_finite()
            for quantity in (quantity_opened, quantity_closed, remaining_quantity)
        ):
            return True
        if quantity_opened < 0 or quantity_closed < 0 or remaining_quantity < 0:
            return True
        if remaining_quantity > 0:
            return True
    except (InvalidOperation, TypeError, ValueError):
        return True

    # A zero-quantity lifecycle is released only when canonical truth proves
    # that it is closed (or archived after close). Corrupt/partial truth stays
    # occupied so it cannot authorize a duplicate OPEN.
    return truth_position.status not in {
        TradingPositionStatus.CLOSED,
        TradingPositionStatus.ARCHIVED,
    }


def _legacy_position_is_potentially_open(position: Position) -> bool:
    """Keep legacy-only lifecycle decisions conservative until canonicalized."""
    try:
        open_quantity = Decimal(str(position.total_quantity or 0))
        if not open_quantity.is_finite():
            return True
        return position.status == PositionStatus.OPEN or open_quantity != 0
    except (InvalidOperation, TypeError, ValueError):
        return True


def _position_direction(
    position: Position,
    truth_position: TradingPosition | None,
) -> PositionDirection:
    if truth_position is not None:
        return PositionDirection(_enum_value(truth_position.side))
    return position.direction


def _position_response_status(
    position: Position,
    truth_position: TradingPosition | None,
) -> str:
    if truth_position is None:
        return _enum_value(position.status)
    return (
        PositionStatus.OPEN.value
        if _truth_position_is_financially_open(truth_position)
        else PositionStatus.CLOSED.value
    )


def _batch_response_payload(batch: TradeBatch) -> dict:
    return {
        "id": batch.id,
        "public_id": batch.public_id,
        "position_id": batch.position_id,
        "type": _enum_value(batch.type),
        "price": batch.price,
        "quantity": batch.quantity,
        "time": batch.time,
        "reason": batch.reason,
        "emotion": batch.emotion,
        "confidence": batch.confidence,
        "pnl": batch.pnl,
        "created_at": batch.created_at,
    }


def _position_list_response_payload(
    db: Session,
    position: Position,
    *,
    truth_position: TradingPosition | None,
    instrument_projection: PositionInstrumentProjection | None = None,
) -> dict:
    projection = instrument_projection or project_position_instrument(
        db,
        position,
        truth_position=truth_position,
    )
    identity = projection.identity if projection else None
    if (
        truth_position is not None
        and truth_position.quantity_opened is not None
        and truth_position.quantity_closed is not None
    ):
        quantity_opened = Decimal(str(truth_position.quantity_opened))
        quantity_closed = Decimal(str(truth_position.quantity_closed))
        total_quantity = max(Decimal("0"), quantity_opened - quantity_closed)
        average_entry_price = truth_position.avg_open_price
        realized_pnl = truth_position.realized_pnl_net or Decimal("0")
        opened_at = truth_position.opened_at
        closed_at = truth_position.closed_at
    else:
        total_quantity = position.total_quantity
        average_entry_price = position.average_entry_price
        realized_pnl = position.realized_pnl
        opened_at = position.opened_at
        closed_at = position.closed_at
    return {
        "id": position.id,
        "public_id": position.public_id,
        "truth_position_public_id": truth_position.public_id if truth_position else None,
        "account_id": position.account_id,
        "symbol": identity.normalized_symbol if identity else position.symbol,
        "exchange": identity.exchange_code if identity else position.exchange,
        "asset_type": identity.asset_type if identity else position.asset_type,
        "direction": _enum_value(_position_direction(position, truth_position)),
        "status": _position_response_status(position, truth_position),
        "total_quantity": total_quantity,
        "average_entry_price": average_entry_price,
        "realized_pnl": realized_pnl,
        "opened_at": opened_at,
        "closed_at": closed_at,
        "created_at": position.created_at,
        "asset_metadata": projection.response_metadata() if projection else None,
        "batches": [_batch_response_payload(batch) for batch in position.batches],
    }


def _position_response_payload(
    db: Session,
    position: Position,
    *,
    truth_position: TradingPosition | None,
) -> dict:
    payload = _position_list_response_payload(
        db,
        position,
        truth_position=truth_position,
    )
    payload.update(
        {
            "user_id": position.user_id,
            "strategy_id": position.strategy_id,
            "trade_review": position.trade_review,
            "screenshots": position.screenshots or [],
            "lessons": position.lessons or [],
            "rating": position.rating,
            "updated_at": position.updated_at,
            "planned_entry_price": position.planned_entry_price,
            "planned_stop_loss": position.planned_stop_loss,
            "planned_take_profit": position.planned_take_profit,
            "checklist_responses": position.checklist_responses,
            "checklist_completed_at": position.checklist_completed_at,
            "drift_analysis": calculate_drift(
                position,
                direction=_position_direction(position, truth_position),
            ),
        }
    )
    return payload


def _normalize_market_filter(value: str | None) -> str | None:
    return (
        _release_contract_value(require_allowed_market, value)
        if value is not None
        else None
    )


def _matching_open_positions(
    db: Session,
    *,
    user_id: int,
    account: TradingAccount,
    identity: LegacyInstrumentIdentity,
    direction: PositionDirection,
) -> list[Position]:
    candidates = (
        db.query(Position)
        .filter(
            Position.user_id == user_id,
            Position.account_id == account.id,
        )
        .order_by(Position.id.asc())
        .all()
    )
    matches: list[Position] = []
    for position in candidates:
        truth_position = resolve_truth_position_for_legacy(
            db,
            user_id=user_id,
            legacy_position=position,
        )
        candidate_direction = _position_direction(position, truth_position)
        candidate_is_open = (
            _truth_position_is_financially_open(truth_position)
            if truth_position is not None
            else _legacy_position_is_potentially_open(position)
        )
        if candidate_direction != direction or not candidate_is_open:
            continue

        projection = project_position_instrument(
            db,
            position,
            truth_position=truth_position,
        )
        if projection is None or projection.source == "VALIDATED_PREUPGRADE_TRUTH":
            candidate_symbols = set()
            if projection is not None:
                candidate_symbols.add(projection.identity.normalized_symbol)
            raw_candidate_symbols = [position.symbol]
            if truth_position is not None and truth_position.instrument is not None:
                raw_candidate_symbols.append(truth_position.instrument.contract_symbol)
            for raw_candidate_symbol in raw_candidate_symbols:
                try:
                    candidate_symbols.add(require_normalized_symbol(raw_candidate_symbol))
                except ReleaseContractViolation:
                    continue
            if identity.normalized_symbol in candidate_symbols:
                raise ReleaseContractViolation(
                    JOURNAL_BETA_CONTRACT.instruments.legacy_unproven_error,
                    "position.exchange",
                    position.exchange,
                )
            continue
        if projection.identity == identity:
            matches.append(position)
    return matches


def _raise_open_position_conflict(matches: list[Position]) -> None:
    if len(matches) > 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "AMBIGUOUS_OPEN_POSITION",
                "message": "Multiple open lifecycles match the same instrument identity and side",
            },
        )
    if matches:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "OPEN_POSITION_EXISTS",
                "message": "Use ADD for an existing same-side lifecycle",
                "position_public_id": matches[0].public_id,
            },
        )


def recalculate_position(position: Position, db: Session):
    """
    Recalculate legacy position aggregates after batch changes using the shared
    FIFO accounting service.
    """
    # Sort batches chronologically (handle mixed timezone-aware and naive datetimes)
    def get_sortable_time(batch):
        t = batch.time
        if t is None:
            return datetime.min
        # Remove timezone info for comparison if present
        if hasattr(t, 'tzinfo') and t.tzinfo is not None:
            return t.replace(tzinfo=None)
        return t

    batches = sorted(position.batches, key=get_sortable_time)
    batch_event_ids: dict[TradeBatch, str] = {}
    accounting_events: list[AccountingEvent] = []

    for index, batch in enumerate(batches):
        event_public_id = batch.public_id or (str(batch.id) if batch.id else f"legacy-batch-{index}")
        batch_event_ids[batch] = event_public_id
        accounting_events.append(
            AccountingEvent(
                public_id=event_public_id,
                event_type="ADD" if _enum_value(batch.type) == BatchType.ENTRY.value else "REDUCE",
                quantity=Decimal(str(batch.quantity)),
                price=Decimal(str(batch.price)),
            )
        )

    summary = calculate_fifo_position_accounting(
        accounting_events,
        side=_enum_value(position.direction),
    )

    for batch in batches:
        result = summary.event_results.get(batch_event_ids[batch])
        if not result:
            continue
        batch.pnl = result.realized_pnl_gross

    # Update Position attributes
    position.total_quantity = summary.open_quantity
    position.average_entry_price = summary.remaining_avg_open_price if summary.open_quantity > 0 else summary.avg_open_price
    position.realized_pnl = summary.realized_pnl_gross
    
    # Auto-close if quantity is <= 0
    if position.total_quantity <= 0:
        position.status = PositionStatus.CLOSED
        from datetime import datetime, timezone
        position.closed_at = datetime.now(timezone.utc)
    else:
        position.status = PositionStatus.OPEN
        position.closed_at = None


def calculate_drift(
    position: Position,
    *,
    direction: PositionDirection | None = None,
) -> dict:
    """
    Calculate drift between planned and actual execution.
    Returns a dict with drift analysis metrics.
    """
    drift = {
        "has_planned_data": False,
        "has_drift": False,
        "entry_drift_pct": None,
        "entry_drift_direction": None,  # "above" or "below" planned
        "stop_loss_risk_pct": None,
        "execution_quality": None  # "good", "fair", "poor"
    }
    
    # Check if planned data exists
    if not position.planned_entry_price and not position.planned_stop_loss:
        return drift
    
    drift["has_planned_data"] = True
    actual_entry = float(position.average_entry_price) if position.average_entry_price else None
    planned_entry = float(position.planned_entry_price) if position.planned_entry_price else None
    planned_stop = float(position.planned_stop_loss) if position.planned_stop_loss else None
    effective_direction = direction or position.direction
    
    # Calculate entry drift
    if actual_entry and planned_entry and planned_entry > 0:
        entry_diff = actual_entry - planned_entry
        entry_drift_pct = (entry_diff / planned_entry) * 100
        drift["entry_drift_pct"] = round(entry_drift_pct, 2)
        drift["entry_drift_direction"] = "above" if entry_diff > 0 else "below" if entry_diff < 0 else "on_target"
        
        # For LONG, buying below plan is good; for SHORT, selling above plan is good
        is_favorable = (effective_direction == PositionDirection.LONG and entry_diff < 0) or \
                       (effective_direction == PositionDirection.SHORT and entry_diff > 0)
        
        abs_drift = abs(entry_drift_pct)
        if abs_drift <= 0.5:
            drift["execution_quality"] = "excellent"
        elif abs_drift <= 2.0 or is_favorable:
            drift["execution_quality"] = "good"
        elif abs_drift <= 5.0:
            drift["execution_quality"] = "fair"
        else:
            drift["execution_quality"] = "poor"
        
        if abs_drift > 0.1:  # More than 0.1% drift
            drift["has_drift"] = True
    
    # Calculate stop loss risk percentage
    if actual_entry and planned_stop and actual_entry > 0:
        if effective_direction == PositionDirection.LONG:
            risk_pct = ((actual_entry - planned_stop) / actual_entry) * 100
        else:  # SHORT
            risk_pct = ((planned_stop - actual_entry) / actual_entry) * 100
        drift["stop_loss_risk_pct"] = round(risk_pct, 2)
    
    return drift


@router.get("", response_model=List[PositionListResponse])
async def list_positions(
    status: Optional[PositionStatusEnum] = None,
    symbol: Optional[str] = None,
    account_id: Optional[int] = None,
    asset_type: Optional[str] = None, # Stock, Crypto
    core_type: Optional[str] = None,
    market: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all positions for the current user"""
    truth_by_legacy_id = resolve_user_truth_positions_for_legacy(
        db,
        user_id=current_user.id,
    )
    from sqlalchemy.orm import joinedload
    query = db.query(Position).options(
        joinedload(Position.batches),
        joinedload(Position.asset_metadata),
        joinedload(Position.trading_account),
    ).join(
        TradingAccount,
        Position.account_id == TradingAccount.id,
    ).filter(
        Position.user_id == current_user.id,
        TradingAccount.user_id == current_user.id,
    )
    
    if account_id:
        query = query.filter(Position.account_id == account_id)
    
    canonical_asset_type = (
        _release_contract_value(require_allowed_asset_type, asset_type)
        if asset_type
        else None
    )
    canonical_core_type = (
        _release_contract_value(require_allowed_asset_type, core_type)
        if core_type
        else None
    )
    canonical_market = _normalize_market_filter(market)
    canonical_symbol_substring = symbol.casefold() if symbol else None
    canonical_status = status.value if status else None

    positions = query.order_by(desc(Position.opened_at)).all()
    result = []
    for pos in positions:
        truth_position = truth_by_legacy_id.get(pos.id)
        projection = project_position_instrument(
            db,
            pos,
            truth_position=truth_position,
        )
        if canonical_status and _position_response_status(pos, truth_position) != canonical_status:
            continue
        if canonical_symbol_substring and (
            projection is None
            or canonical_symbol_substring
            not in projection.identity.normalized_symbol.casefold()
        ):
            continue
        if canonical_asset_type and (
            projection is None or projection.identity.asset_type != canonical_asset_type
        ):
            continue
        if canonical_core_type and (
            projection is None or projection.identity.asset_type != canonical_core_type
        ):
            continue
        if canonical_market and (
            projection is None or projection.identity.market != canonical_market
        ):
            continue
        result.append(
            _position_list_response_payload(
                db,
                pos,
                truth_position=truth_position,
                instrument_projection=projection,
            )
        )

    return result


@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single position with all batches"""
    from sqlalchemy.orm import joinedload
    position = resolve_position(db, current_user.id, position_id)
    if position:
        position = db.query(Position).options(
            joinedload(Position.batches),
            joinedload(Position.asset_metadata),
            joinedload(Position.trading_account),
        ).join(
            TradingAccount,
            Position.account_id == TradingAccount.id,
        ).filter(
            Position.id == position.id,
            Position.user_id == current_user.id,
            TradingAccount.user_id == current_user.id,
        ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    truth_position = resolve_truth_position_for_legacy(
        db,
        user_id=current_user.id,
        legacy_position=position,
    )
    return _position_response_payload(
        db,
        position,
        truth_position=truth_position,
    )


@router.get("/{position_id}/truth-lifecycle")
async def get_position_truth_lifecycle(
    position_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    legacy_position = resolve_position(db, current_user.id, position_id)
    if not legacy_position:
        raise HTTPException(status_code=404, detail="Position not found")

    truth_position = resolve_truth_position_for_legacy(
        db,
        user_id=current_user.id,
        legacy_position=legacy_position,
    )
    if truth_position is None:
        raise HTTPException(
            status_code=404,
            detail="Position truth lifecycle not found",
        )
    try:
        data = build_trading_position_lifecycle_payload(
            db,
            truth_position,
            include_ai_sidecar=is_effective_capability_enabled(
                db,
                RuntimeCapability.AI_INSIGHTS,
                actor_key=current_user.public_id,
            ),
        )
    except CanonicalAccountingUnresolvedError as exc:
        raise HTTPException(
            status_code=409,
            detail=canonical_accounting_unresolved_detail(exc),
        ) from exc
    return JSONResponse(
        content=jsonable_encoder(
            {
                "data": data,
                "meta": {
                    "as_of": truth_position.updated_at or truth_position.created_at,
                    "generated_at": truth_position.updated_at or truth_position.created_at,
                    "freshness": "FRESH",
                    "source": "DERIVED",
                    "maturity": "EARLY_SIGNAL",
                    "value_status": "FINAL",
                },
            }
        )
    )


@router.post("", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def create_position(
    position_data: PositionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new position with the first entry batch"""
    # Verify account belongs to user
    account = db.query(TradingAccount).filter(
        TradingAccount.id == position_data.account_id,
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=400, detail="Invalid account_id")
    
    _release_contract_value(
        require_release_currency,
        account.currency,
        field="account.currency",
    )
    detected_type = _release_contract_value(
        require_allowed_asset_type,
        position_data.asset_type,
    )
    symbol_upper = _release_contract_value(
        require_normalized_symbol,
        position_data.symbol,
    )
    exchange_code = _release_contract_value(
        require_exchange_code,
        position_data.exchange_code,
    )

    metadata_create = position_data.asset_metadata.model_dump()
    identity = _release_contract_value(
        validate_legacy_instrument_identity,
        position_asset_type=detected_type,
        account_currency=account.currency,
        symbol=symbol_upper,
        exchange_code=exchange_code,
        metadata_core_type=metadata_create["core_type"],
        metadata_market=metadata_create["market"],
        metadata_currency=metadata_create["currency"],
        metadata_instrument=metadata_create["instrument"],
    )
    requested_direction = PositionDirection[position_data.direction.value]
    _raise_open_position_conflict(
        _release_contract_value(
            _matching_open_positions,
            db,
            user_id=current_user.id,
            account=account,
            identity=identity,
            direction=requested_direction,
        )
    )
    # The global legacy AssetMetadata(symbol) table is read-only for ordinary
    # users. JRN-007 replaces this bridge with canonical full-identity storage.
    position = Position(
        user_id=current_user.id,
        account_id=position_data.account_id,
        strategy_id=position_data.strategy_id,
        symbol=symbol_upper,
        exchange=exchange_code,
        asset_type=detected_type,
        asset_metadata_symbol=None,
        direction=requested_direction,
        status=PositionStatus.OPEN,
        total_quantity=position_data.quantity,
        average_entry_price=position_data.entry_price,
        realized_pnl=Decimal(0),
        opened_at=position_data.entry_time,
        # Phase 1: Plan Drift Detection
        planned_entry_price=position_data.planned_entry_price,
        planned_stop_loss=position_data.planned_stop_loss,
        planned_take_profit=position_data.planned_take_profit,
        # Phase 1: Checklist Responses
        checklist_responses=position_data.checklist_responses
    )
    db.add(position)
    db.flush()  # Get position ID
    
    # Create first entry batch
    first_batch = TradeBatch(
        position_id=position.id,
        type=BatchType.ENTRY,
        price=position_data.entry_price,
        quantity=position_data.quantity,
        time=position_data.entry_time,
        reason=position_data.entry_reason,
        emotion=position_data.entry_emotion,
        confidence=position_data.entry_confidence
    )
    db.add(first_batch)
    db.flush()

    truth_position = _release_contract_value(
        sync_legacy_position_to_truth,
        db,
        position.id,
        expected_identity=identity,
    )
    db.refresh(position)
    return _position_response_payload(
        db,
        position,
        truth_position=truth_position,
    )


@router.patch("/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: str,
    position_data: PositionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update position review fields"""
    position = resolve_position(db, current_user.id, position_id)
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    update_data = position_data.model_dump(exclude_unset=True)

    legacy_review_fields = {"trade_review", "lessons", "rating"}
    if legacy_review_fields.intersection(update_data):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "Legacy review writes are disabled on public product routes. "
                "Use the TradingPosition event narrative route for ordinary review and narrative edits."
            ),
        )

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Legacy position updates are disabled on public product routes. "
            "Use canonical event, narrative, and lifecycle commands instead."
        ),
    )


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a position and all its batches"""
    position = resolve_position(db, current_user.id, position_id)
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Legacy position hard deletes are disabled on public product routes. "
            "Use audited truth void/archive semantics instead of deleting the legacy row."
        ),
    )


# ============== Batch Endpoints ==============

@router.get("/{position_id}/batches", response_model=List[TradeBatchResponse])
async def list_batches(
    position_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all batches for a position"""
    position = resolve_position(db, current_user.id, position_id)
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return position.batches


@router.post("/{position_id}/batches", response_model=TradeBatchResponse, status_code=status.HTTP_201_CREATED)
async def add_batch(
    position_id: str,
    batch_data: TradeBatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new batch (entry or exit) to a position"""
    position = resolve_position(db, current_user.id, position_id)
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Legacy batch writes are disabled on public product routes. "
            "Use the TradingPosition event route for ordinary add/reduce/close actions."
        ),
    )


@router.delete("/batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a batch from a position"""
    batch = resolve_trade_batch(db, current_user.id, batch_id)
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Legacy batch edits are disabled on public product routes. "
            "Use audited truth event reversal or adjustment flows for ordinary corrections."
        ),
    )


@router.patch("/batches/{batch_id}", response_model=TradeBatchResponse)
async def update_batch(
    batch_id: str,
    batch_data: TradeBatchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a trade batch and recalculate position"""
    batch = resolve_trade_batch(db, current_user.id, batch_id)
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")

    raise HTTPException(
        status_code=status.HTTP_409_CONFLICT,
        detail=(
            "Legacy batch edits are disabled on public product routes. "
            "Use audited truth event reversal or adjustment flows for ordinary corrections."
        ),
    )


# ============== Helper Endpoints ==============

@router.get("/check/open", response_model=Optional[PositionListResponse])
async def check_open_position(
    symbol: str = Query(
        ...,
        json_schema_extra={
            "pattern": JOURNAL_BETA_CONTRACT.instruments.raw_normalized_symbol_input_pattern,
            "x-normalized-pattern": JOURNAL_BETA_CONTRACT.instruments.normalized_symbol_pattern,
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    ),
    account_id: str = Query(..., min_length=1),
    exchange_code: str = Query(
        ...,
        json_schema_extra={
            "pattern": JOURNAL_BETA_CONTRACT.instruments.raw_exchange_code_input_pattern,
            "x-normalized-pattern": JOURNAL_BETA_CONTRACT.instruments.exchange_code_pattern,
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    ),
    direction: PositionDirection = Query(...),
    asset_type: str = Query(
        ...,
        json_schema_extra={
            "pattern": RAW_ASSET_TYPE_INPUT_PATTERN,
            "x-canonical-values": list(JOURNAL_BETA_CONTRACT.instruments.asset_types),
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    ),
    market: str = Query(
        ...,
        json_schema_extra={
            "pattern": RAW_MARKET_INPUT_PATTERN,
            "x-canonical-values": list(JOURNAL_BETA_CONTRACT.instruments.markets),
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    ),
    instrument_type: str = Query(
        ...,
        json_schema_extra={
            "pattern": RAW_INSTRUMENT_TYPE_INPUT_PATTERN,
            "x-canonical-values": list(JOURNAL_BETA_CONTRACT.instruments.instrument_types),
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    ),
    quote_currency: str = Query(
        ...,
        json_schema_extra={
            "pattern": RAW_CURRENCY_INPUT_PATTERN,
            "x-canonical-values": list(JOURNAL_BETA_CONTRACT.currency.account_base_currencies),
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Return an open position only when the complete release identity matches."""
    account = resolve_trading_account(db, current_user.id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    requested_identity = _release_contract_value(
        validate_legacy_instrument_identity,
        position_asset_type=asset_type,
        account_currency=account.currency,
        symbol=symbol,
        exchange_code=exchange_code,
        metadata_core_type=asset_type,
        metadata_market=market,
        metadata_currency=quote_currency,
        metadata_instrument=instrument_type,
    )
    matches = _release_contract_value(
        _matching_open_positions,
        db,
        user_id=current_user.id,
        account=account,
        identity=requested_identity,
        direction=direction,
    )
    if len(matches) > 1:
        _raise_open_position_conflict(matches)
    if not matches:
        return None
    match = matches[0]
    return _position_list_response_payload(
        db,
        match,
        truth_position=resolve_truth_position_for_legacy(
            db,
            user_id=current_user.id,
            legacy_position=match,
        ),
    )


# ============== Export Endpoints ==============

@router.get("/export/csv")
async def export_positions_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all positions and batches to CSV with comprehensive metadata"""
    # Query with all relationships
    from sqlalchemy.orm import joinedload
    positions = db.query(Position).options(
        joinedload(Position.batches),
        joinedload(Position.asset_metadata),
        joinedload(Position.trading_account)
    ).join(
        TradingAccount,
        Position.account_id == TradingAccount.id,
    ).filter(
        Position.user_id == current_user.id,
        TradingAccount.user_id == current_user.id,
    ).order_by(desc(Position.opened_at)).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Position ID', 'Symbol', 'Name', 'Asset Class', 'Asset Type', 'Market', 'Sector', 
        'Exchange/Broker', 'Account', 'Account Type',
        'Direction', 'Status', 
        'Total Quantity', 'Avg Entry Price', 'Realized PnL',
        'Opened At', 'Closed At', 'Position Review', 'Lessons',
        'Planned Entry Price', 'Planned Stop Loss',
        'Batch ID', 'Batch Type', 'Batch Price', 'Batch Quantity',
        'Batch Time', 'Batch PnL', 'Batch Reason', 'Batch Emotion', 'Batch Confidence'
    ])
    
    # Data rows
    for pos in positions:
        # Prepare position-level fields
        lessons_str = ', '.join(pos.lessons) if pos.lessons else ''
        
        # Helper for safe attribute access
        def get_enum_value(val):
            if val is None:
                return ''
            if hasattr(val, 'value'):
                return val.value
            return str(val)

        def get_attr(obj, attr, default=''):
            if obj is None:
                return default
            return getattr(obj, attr, default)

        # Helper for basic formatting
        def fmt_float(val):
            try:
                if val is not None:
                    return float(val)
            except:
                pass
            return 0
            
        def fmt_date(val):
            try:
                if val:
                    return val.isoformat()
            except:
                pass
            return ''

        try:
            # Asset Metadata fields - Use safe access
            meta = pos.asset_metadata
            asset_name = get_attr(meta, 'name')
            asset_core_type = get_enum_value(get_attr(meta, 'core_type', None))
            asset_market = get_enum_value(get_attr(meta, 'market', None))
            asset_sector = get_attr(meta, 'sector')
            
            # Account fields
            account = pos.trading_account
            account_name = get_attr(account, 'name')
            account_type = get_attr(account, 'account_type')
            
            # Position Enum fields
            direction = get_enum_value(pos.direction)
            status = get_enum_value(pos.status)

            # Export position with each batch
            if pos.batches:
                for batch in pos.batches:
                    writer.writerow([
                        pos.id,
                        pos.symbol,
                        asset_name,
                        asset_core_type,
                        get_attr(pos, 'asset_type'), # Granular Asset Type
                        asset_market,
                        asset_sector,
                        get_attr(pos, 'exchange'),
                        account_name,
                        account_type,
                        direction,
                        status,
                        fmt_float(pos.total_quantity),
                        fmt_float(pos.average_entry_price),
                        fmt_float(pos.realized_pnl),
                        fmt_date(pos.opened_at),
                        fmt_date(pos.closed_at),
                        get_attr(pos, 'trade_review'),
                        lessons_str,
                        fmt_float(pos.planned_entry_price),
                        fmt_float(pos.planned_stop_loss),
                        batch.id,
                        get_enum_value(batch.type),
                        fmt_float(batch.price),
                        fmt_float(batch.quantity),
                        fmt_date(batch.time),
                        fmt_float(batch.pnl),
                        get_attr(batch, 'reason'),
                        get_attr(batch, 'emotion'),
                        get_attr(batch, 'confidence')
                    ])
            else:
                # Position without batches
                writer.writerow([
                    pos.id,
                    pos.symbol,
                    asset_name,
                    asset_core_type,
                    asset_market,
                    asset_sector,
                    get_attr(pos, 'exchange'),
                    account_name,
                    account_type,
                    direction,
                    status,
                    fmt_float(pos.total_quantity),
                    fmt_float(pos.average_entry_price),
                    fmt_float(pos.realized_pnl),
                    fmt_date(pos.opened_at),
                    fmt_date(pos.closed_at),
                    get_attr(pos, 'trade_review'),
                    get_attr(pos, 'trade_review'),
                    lessons_str,
                    fmt_float(pos.planned_entry_price),
                    fmt_float(pos.planned_stop_loss),
                    '', '', '', '', '', '', '', '', ''
                ])
        except Exception as e:
            # Log error but skip row to allow partial export
            log_event(logger, "warning", "position_export_row_failed", position_id=pos.id, error=str(e))
            continue
    
    # Prepare response with UTF-8 BOM for Excel compatibility
    output.seek(0)
    csv_content = '\ufeff' + output.getvalue()  # Add BOM for Excel
    filename = f"trading_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([csv_content.encode('utf-8')]),
        media_type="text/csv; charset=utf-8",
        headers={
            "Content-Disposition": f"attachment; filename={filename}",
            "Access-Control-Expose-Headers": "Content-Disposition"
        }
    )
