from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session

from database import get_db
from models import AccountLedgerEntry, PositionEvent, TradeInstrument, TradingPosition, User
from routers.auth import get_current_user
from schemas import AccountLedgerAdjustmentCreate, TradingPositionCreate, TradingPositionEventCreate
from services.trading_accounting_service import TradingAccountingService


router = APIRouter(prefix="/api/v1/trading-positions", tags=["v1-trading-positions"])


def _serialize_position(db: Session, position: TradingPosition) -> dict:
    instrument = db.query(TradeInstrument).filter_by(id=position.instrument_id).one()
    events = db.query(PositionEvent).filter_by(position_id=position.id).order_by(PositionEvent.event_time).all()
    ledger_entries = db.query(AccountLedgerEntry).filter_by(related_position_id=position.id).all()

    return jsonable_encoder(
        {
            "public_id": position.public_id,
            "symbol": instrument.symbol,
            "side": position.side,
            "status": position.status,
            "cost_method": position.cost_method,
            "quantity_opened": position.quantity_opened,
            "quantity_closed": position.quantity_closed,
            "realized_pnl_gross": position.realized_pnl_gross,
            "realized_pnl_net": position.realized_pnl_net,
            "thesis": position.thesis,
            "opened_at": position.opened_at,
            "closed_at": position.closed_at,
            "events": [
                {
                    "public_id": event.public_id,
                    "event_type": event.event_type,
                    "quantity": event.quantity,
                    "price": event.price,
                    "fee": event.fee,
                    "realized_pnl_gross": event.realized_pnl_gross,
                    "realized_pnl_net": event.realized_pnl_net,
                    "thesis": event.thesis,
                    "edge_source": event.edge_source,
                    "disconfirming_evidence": event.disconfirming_evidence,
                    "invalidation_rule": event.invalidation_rule,
                    "expected_holding_period": event.expected_holding_period,
                    "planned_exit_rule": event.planned_exit_rule,
                    "sizing_rationale": event.sizing_rationale,
                    "checklist_snapshot": event.checklist_snapshot,
                    "event_time": event.event_time,
                }
                for event in events
            ],
            "ledger_entries": [
                {
                    "public_id": entry.public_id,
                    "entry_type": entry.entry_type,
                    "amount": entry.amount,
                    "currency": entry.currency,
                    "occurred_at": entry.occurred_at,
                }
                for entry in ledger_entries
            ],
        }
    )


def _get_user_position(db: Session, current_user: User, position_public_id: str) -> TradingPosition:
    position = db.query(TradingPosition).filter_by(
        public_id=position_public_id,
        user_id=current_user.id,
    ).one_or_none()
    if not position:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trading position not found")
    return position


@router.post("", status_code=status.HTTP_201_CREATED)
def create_trading_position(
    position_data: TradingPositionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = TradingAccountingService(db)
    position = service.open_position(
        user_id=current_user.id,
        account_id=position_data.account_id,
        symbol=position_data.symbol,
        side=position_data.side.value,
        quantity=position_data.quantity,
        price=position_data.price,
        fee=position_data.fee,
        event_time=position_data.event_time,
        thesis=position_data.thesis,
        edge_source=position_data.edge_source,
        disconfirming_evidence=position_data.disconfirming_evidence,
        invalidation_rule=position_data.invalidation_rule,
        expected_holding_period=position_data.expected_holding_period,
        planned_exit_rule=position_data.planned_exit_rule,
        sizing_rationale=position_data.sizing_rationale,
        checklist_snapshot=position_data.checklist_snapshot,
    )
    db.commit()
    return _serialize_position(db, position)


@router.get("")
def list_trading_positions(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    positions = db.query(TradingPosition).filter_by(user_id=current_user.id).order_by(TradingPosition.opened_at.desc()).all()
    return [_serialize_position(db, position) for position in positions]


@router.get("/{position_public_id}")
def get_trading_position(
    position_public_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _serialize_position(db, _get_user_position(db, current_user, position_public_id))


@router.post("/{position_public_id}/add")
def add_to_trading_position(
    position_public_id: str,
    event_data: TradingPositionEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_user_position(db, current_user, position_public_id)
    position = TradingAccountingService(db).add_to_position(
        position_public_id=position_public_id,
        quantity=event_data.quantity,
        price=event_data.price,
        fee=event_data.fee,
        event_time=event_data.event_time,
    )
    db.commit()
    return _serialize_position(db, position)


@router.post("/{position_public_id}/reduce")
def reduce_trading_position(
    position_public_id: str,
    event_data: TradingPositionEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_user_position(db, current_user, position_public_id)
    position = TradingAccountingService(db).reduce_position(
        position_public_id=position_public_id,
        quantity=event_data.quantity,
        price=event_data.price,
        fee=event_data.fee,
        event_time=event_data.event_time,
    )
    db.commit()
    return _serialize_position(db, position)


@router.post("/{position_public_id}/close")
def close_trading_position(
    position_public_id: str,
    event_data: TradingPositionEventCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_user_position(db, current_user, position_public_id)
    position = TradingAccountingService(db).close_position(
        position_public_id=position_public_id,
        quantity=event_data.quantity,
        price=event_data.price,
        fee=event_data.fee,
        event_time=event_data.event_time,
    )
    db.commit()
    return _serialize_position(db, position)


@router.post("/{position_public_id}/dividends")
def record_dividend(
    position_public_id: str,
    adjustment: AccountLedgerAdjustmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_user_position(db, current_user, position_public_id)
    entry = TradingAccountingService(db).record_dividend(
        user_id=current_user.id,
        account_id=adjustment.account_id,
        amount=adjustment.amount,
        currency=adjustment.currency,
        occurred_at=adjustment.occurred_at,
        position_public_id=position_public_id,
    )
    db.commit()
    return jsonable_encoder({"public_id": entry.public_id, "entry_type": entry.entry_type})


@router.post("/{position_public_id}/fees")
def record_fee(
    position_public_id: str,
    adjustment: AccountLedgerAdjustmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_user_position(db, current_user, position_public_id)
    entry = TradingAccountingService(db).record_fee(
        user_id=current_user.id,
        account_id=adjustment.account_id,
        amount=adjustment.amount,
        currency=adjustment.currency,
        occurred_at=adjustment.occurred_at,
        position_public_id=position_public_id,
        reason=adjustment.reason,
    )
    db.commit()
    return jsonable_encoder({"public_id": entry.public_id, "entry_type": entry.entry_type})


@router.post("/ledger-adjustments")
def record_cash_adjustment(
    adjustment: AccountLedgerAdjustmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    entry = TradingAccountingService(db).record_cash_adjustment(
        user_id=current_user.id,
        account_id=adjustment.account_id,
        amount=adjustment.amount,
        currency=adjustment.currency,
        occurred_at=adjustment.occurred_at,
        reason=adjustment.reason or "Manual adjustment",
    )
    db.commit()
    return jsonable_encoder({"public_id": entry.public_id, "entry_type": entry.entry_type})
