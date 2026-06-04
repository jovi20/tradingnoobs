from datetime import datetime, timezone
from decimal import Decimal

from models import AccountLedgerEntry, AssetMaster, OutboxEvent, PositionEvent, TradeInstrument, TradingPosition
from services.trading_accounting_service import FifoLot, TradingAccountingService, match_fifo


def test_match_fifo_realizes_pnl_from_oldest_lots_first():
    lots = [
        FifoLot(quantity=Decimal("10"), price=Decimal("100"), fee=Decimal("1.00")),
        FifoLot(quantity=Decimal("5"), price=Decimal("110"), fee=Decimal("0.50")),
    ]

    result = match_fifo(lots, close_quantity=Decimal("12"), close_price=Decimal("120"), close_fee=Decimal("1.20"))

    assert result.realized_pnl_gross == Decimal("220.00")
    assert result.realized_pnl_net == Decimal("217.60")
    assert result.remaining_lots == [
        FifoLot(quantity=Decimal("3"), price=Decimal("110"), fee=Decimal("0.30")),
    ]


def test_truth_model_tables_are_registered():
    assert AssetMaster.__tablename__ == "asset_master"
    assert TradeInstrument.__tablename__ == "trade_instruments"
    assert TradingPosition.__tablename__ == "trading_positions"
    assert PositionEvent.__tablename__ == "position_events"
    assert AccountLedgerEntry.__tablename__ == "account_ledger_entries"
    assert OutboxEvent.__tablename__ == "outbox_events"


def test_open_add_reduce_close_writes_events_ledger_and_outbox(db_session):
    service = TradingAccountingService(db_session)
    opened_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    position = service.open_position(
        user_id=1,
        account_id=1,
        symbol="AAPL",
        side="LONG",
        quantity=Decimal("10"),
        price=Decimal("100"),
        fee=Decimal("1.00"),
        event_time=opened_at,
        thesis="Breakout setup",
    )
    service.add_to_position(
        position_public_id=position.public_id,
        quantity=Decimal("5"),
        price=Decimal("110"),
        fee=Decimal("0.50"),
        event_time=opened_at,
    )
    service.reduce_position(
        position_public_id=position.public_id,
        quantity=Decimal("12"),
        price=Decimal("120"),
        fee=Decimal("1.20"),
        event_time=opened_at,
    )
    service.close_position(
        position_public_id=position.public_id,
        quantity=Decimal("3"),
        price=Decimal("115"),
        fee=Decimal("0.30"),
        event_time=opened_at,
    )

    stored_position = db_session.query(TradingPosition).filter_by(public_id=position.public_id).one()
    events = db_session.query(PositionEvent).filter_by(position_id=stored_position.id).order_by(PositionEvent.event_time).all()
    ledger_entries = db_session.query(AccountLedgerEntry).filter_by(related_position_id=stored_position.id).all()
    outbox_events = db_session.query(OutboxEvent).filter_by(aggregate_public_id=stored_position.public_id).all()

    assert stored_position.status == "CLOSED"
    assert stored_position.quantity_opened == Decimal("15.00000000")
    assert stored_position.quantity_closed == Decimal("15.00000000")
    assert stored_position.realized_pnl_gross == Decimal("235.00000000")
    assert stored_position.realized_pnl_net == Decimal("232.00000000")
    assert [event.event_type for event in events] == ["OPEN", "ADD", "REDUCE", "CLOSE"]
    assert len(ledger_entries) == 4
    assert len(outbox_events) == 4


def test_open_position_records_decision_quality_fields_on_event(db_session):
    service = TradingAccountingService(db_session)
    opened_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    position = service.open_position(
        user_id=1,
        account_id=1,
        symbol="MSFT",
        side="LONG",
        quantity=Decimal("8"),
        price=Decimal("250"),
        fee=Decimal("1.00"),
        event_time=opened_at,
        thesis="Cloud margin expansion",
        edge_source="earnings_revision",
        disconfirming_evidence="Azure growth decelerates below 20%",
        invalidation_rule="Close below 200-day moving average",
        expected_holding_period="4-8 weeks",
        planned_exit_rule="Trim half at 2R and trail remainder",
        sizing_rationale="Half size until post-earnings volatility settles",
        checklist_snapshot={"trend": True, "volume": True, "risk_reward": "2.5R"},
    )

    event = db_session.query(PositionEvent).filter_by(position_id=position.id, event_type="OPEN").one()

    assert event.thesis == "Cloud margin expansion"
    assert event.edge_source == "earnings_revision"
    assert event.disconfirming_evidence == "Azure growth decelerates below 20%"
    assert event.invalidation_rule == "Close below 200-day moving average"
    assert event.expected_holding_period == "4-8 weeks"
    assert event.planned_exit_rule == "Trim half at 2R and trail remainder"
    assert event.sizing_rationale == "Half size until post-earnings volatility settles"
    assert event.checklist_snapshot == {"trend": True, "volume": True, "risk_reward": "2.5R"}


def test_dividend_fee_and_cash_adjustment_are_ledger_truth(db_session):
    service = TradingAccountingService(db_session)
    event_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    position = service.open_position(
        user_id=1,
        account_id=1,
        symbol="NVDA",
        side="LONG",
        quantity=Decimal("2"),
        price=Decimal("500"),
        fee=Decimal("1.00"),
        event_time=event_time,
        thesis="Acceleration in AI infrastructure demand",
    )

    dividend = service.record_dividend(
        user_id=1,
        account_id=1,
        amount=Decimal("4.20"),
        currency="USD",
        occurred_at=event_time,
        position_public_id=position.public_id,
    )
    fee = service.record_fee(
        user_id=1,
        account_id=1,
        amount=Decimal("2.10"),
        currency="USD",
        occurred_at=event_time,
        position_public_id=position.public_id,
        reason="ADR custody fee",
    )
    adjustment = service.record_cash_adjustment(
        user_id=1,
        account_id=1,
        amount=Decimal("-15.00"),
        currency="USD",
        occurred_at=event_time,
        reason="Manual reconciliation",
    )

    assert dividend.entry_type == "DIVIDEND"
    assert dividend.amount == Decimal("4.20000000")
    assert dividend.related_position_id == position.id
    assert fee.entry_type == "FEE"
    assert fee.amount == Decimal("-2.10000000")
    assert fee.related_position_id == position.id
    assert adjustment.entry_type == "CASH_ADJUSTMENT"
    assert adjustment.amount == Decimal("-15.00000000")
    assert adjustment.related_position_id is None

    outbox_events = db_session.query(OutboxEvent).filter(OutboxEvent.event_type.like("account_ledger.%")).all()
    assert len(outbox_events) == 3


def test_unrealized_pnl_uses_remaining_fifo_lots_without_mutating_position(db_session):
    service = TradingAccountingService(db_session)
    event_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    position = service.open_position(
        user_id=1,
        account_id=1,
        symbol="AMD",
        side="LONG",
        quantity=Decimal("10"),
        price=Decimal("100"),
        fee=Decimal("1.00"),
        event_time=event_time,
        thesis="Data center GPU share gain",
    )
    service.add_to_position(
        position_public_id=position.public_id,
        quantity=Decimal("5"),
        price=Decimal("110"),
        fee=Decimal("0.50"),
        event_time=event_time,
    )
    service.reduce_position(
        position_public_id=position.public_id,
        quantity=Decimal("12"),
        price=Decimal("120"),
        fee=Decimal("1.20"),
        event_time=event_time,
    )
    event_count = db_session.query(PositionEvent).filter_by(position_id=position.id).count()
    ledger_count = db_session.query(AccountLedgerEntry).filter_by(related_position_id=position.id).count()
    outbox_count = db_session.query(OutboxEvent).filter_by(aggregate_public_id=position.public_id).count()

    result = service.calculate_unrealized_pnl(
        position_public_id=position.public_id,
        current_price=Decimal("125"),
        fx_rate=Decimal("1"),
    )

    assert result == {"unrealized_pnl_gross": Decimal("45.00"), "unrealized_pnl_net": Decimal("44.70")}
    assert db_session.query(PositionEvent).filter_by(position_id=position.id).count() == event_count
    assert db_session.query(AccountLedgerEntry).filter_by(related_position_id=position.id).count() == ledger_count
    assert db_session.query(OutboxEvent).filter_by(aggregate_public_id=position.public_id).count() == outbox_count
