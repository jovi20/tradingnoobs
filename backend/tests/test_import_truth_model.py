from datetime import datetime, timezone

from models import AccountLedgerEntry, OutboxEvent, Position, PositionEvent, TradeBatch, TradingPosition
from schemas import BatchTypeEnum, PositionDirectionEnum
from services.import_service import ImportService


def test_import_save_trade_writes_trading_truth_model_not_legacy_batches(db_session):
    service = ImportService(db_session)

    service._save_trade(
        {
            "symbol": "AAPL",
            "direction": PositionDirectionEnum.LONG,
            "type": BatchTypeEnum.ENTRY,
            "price": 100.0,
            "quantity": 10.0,
            "entry_time": datetime(2026, 1, 1, tzinfo=timezone.utc),
            "reason": "Breakout entry",
            "emotion": "focused",
            "confidence": 4,
            "planned_entry_price": 99.0,
            "planned_stop_loss": 92.0,
        },
        account_id=1,
        user_id=1,
    )
    service._save_trade(
        {
            "symbol": "AAPL",
            "direction": PositionDirectionEnum.LONG,
            "type": BatchTypeEnum.EXIT,
            "price": 115.0,
            "quantity": 10.0,
            "entry_time": datetime(2026, 1, 10, tzinfo=timezone.utc),
            "reason": "Target reached",
            "emotion": "calm",
            "confidence": 4,
        },
        account_id=1,
        user_id=1,
    )

    position = db_session.query(TradingPosition).one()
    events = db_session.query(PositionEvent).filter_by(position_id=position.id).all()

    assert db_session.query(Position).count() == 0
    assert db_session.query(TradeBatch).count() == 0
    assert position.status == "CLOSED"
    assert [event.event_type for event in events] == ["OPEN", "CLOSE"]
    assert db_session.query(AccountLedgerEntry).filter_by(related_position_id=position.id).count() == 2
    assert db_session.query(OutboxEvent).filter_by(aggregate_public_id=position.public_id).count() == 2
