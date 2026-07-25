from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import os
import tempfile

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app_config.ibkr_flex_provider_evidence import (
    IbkrFlexFieldContract,
    VerifiedIbkrFlexProviderContract,
)
from database import Base
from models import (
    ExternalExecution,
    ExternalSourceObservation,
    ExternalTradeApplication,
    IdempotencyKey,
    ImportRow,
    ImportSession,
    ImportSourceBinding,
    SourceCaseEvidenceSighting,
    SourceReconciliationCase,
    SourceStatement,
    StatementExecutionSighting,
    TradingAccount,
    User,
)
from services.ibkr_flex_parser import (
    NormalizedIbkrFlexEvent,
    ParsedIbkrFlexStatement,
)
from services.ibkr_flex_preview_service import (
    IbkrFlexPreviewError,
    preview_bound_ibkr_statement,
)


@pytest.fixture()
def db():
    descriptor, path = tempfile.mkstemp(suffix=".db")
    os.close(descriptor)
    engine = create_engine(
        f"sqlite:///{path}",
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        os.remove(path)


@pytest.fixture()
def provider_contract():
    fields = IbkrFlexFieldContract.model_validate(
        {
            "statement_element": "FlexStatement",
            "events_container_element": "Trades",
            "trade_element": "Trade",
            "account_field": "accountId",
            "from_date_field": "fromDate",
            "to_date_field": "toDate",
            "generation_field": "whenGenerated",
            "execution_id_field": "ibExecID",
            "transaction_id_field": "transactionID",
            "asset_category_field": "assetCategory",
            "conid_field": "conid",
            "symbol_field": "symbol",
            "exchange_field": "listingExchange",
            "currency_field": "currency",
            "side_field": "buySell",
            "quantity_field": "quantity",
            "price_field": "tradePrice",
            "trade_time_field": "dateTime",
            "open_close_field": "openCloseIndicator",
            "execution_status_field": "tradeStatus",
            "commission_field": "ibCommission",
            "commission_currency_field": "ibCommissionCurrency",
            "statement_to_date_inclusive": True,
            "statement_date_format": "%Y%m%d",
            "generation_time_format": "%Y%m%d;%H%M%S",
            "execution_time_format": "%Y%m%d;%H%M%S",
            "execution_time_semantics": "SOURCE_TIMEZONE_NAIVE",
            "ordinary_trade_kind_from_element": True,
            "correction_element": "TradeCorrection",
            "cancel_bust_element": "TradeCancel",
            "change_event_id_field": "sourceEventID",
            "affected_execution_id_field": "affectedIBExecID",
        }
    )
    return VerifiedIbkrFlexProviderContract(
        query_template_id="SYNTHETIC_TEST_ONLY",
        query_template_sha256=f"sha256:{'a' * 64}",
        field_contract=fields,
        official_sources=(),
        fixtures=(),
    )


@pytest.fixture()
def source_graph(db):
    user = User(
        public_id="preview-user",
        email="preview@example.com",
        email_normalized="preview@example.com",
        hashed_password="hash",
        timezone="UTC",
    )
    other = User(
        public_id="preview-other",
        email="preview-other@example.com",
        email_normalized="preview-other@example.com",
        hashed_password="hash",
        timezone="UTC",
    )
    account = TradingAccount(
        public_id="preview-account",
        user=user,
        name="IBKR",
        broker="IBKR",
        currency="USD",
        is_active=True,
        trade_source_state="SOURCE_BOUND",
    )
    other_account = TradingAccount(
        public_id="preview-other-account",
        user=other,
        name="Other",
        broker="IBKR",
        currency="USD",
        is_active=True,
        trade_source_state="SOURCE_BOUND",
    )
    db.add_all([user, other, account, other_account])
    db.flush()
    binding = ImportSourceBinding(
        public_id="preview-binding",
        user_id=user.id,
        account_id=account.id,
        adapter_kind="IBKR_FLEX_XML_V1",
        normalized_external_account_ref="U1234567",
        masked_external_account_ref="****4567",
        source_timezone="America/New_York",
        source_health="HEALTHY",
        source_completeness="CURRENT",
        accepted_coverage_start=date(2026, 7, 1),
        accepted_coverage_through_exclusive=date(2026, 7, 26),
        source_state_revision=1,
    )
    db.add(binding)
    db.commit()
    return user, other, account, other_account, binding


def make_session(
    db,
    *,
    user,
    account,
    suffix,
    file_hash=None,
):
    operation = IdempotencyKey(
        user_id=user.id,
        scope="IBKR_FLEX_UPLOAD_V1",
        key=f"key-{suffix}",
        request_hash=f"sha256:{suffix:0<64}"[:71],
        status="IN_PROGRESS",
    )
    db.add(operation)
    db.flush()
    session = ImportSession(
        public_id=f"session-{suffix}",
        user_id=user.id,
        account_id=account.id,
        upload_idempotency_id=operation.id,
        adapter_kind="IBKR_FLEX_XML_V1",
        file_format="XML",
        file_hash=file_hash or f"sha256:{suffix:0<64}"[:71],
        file_size_bytes=100,
        original_filename=f"{suffix}.xml",
        media_type="application/xml",
        status="UPLOADING",
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(session)
    db.flush()
    return session


def source_event(
    *,
    row_number=1,
    event_id="EXEC-NEW",
    transaction_id="200",
    kind="TRADE",
    affected=None,
    side="BUY",
    open_close="OPEN",
    quantity="2",
    price="200",
    occurred_at=None,
    fingerprint=None,
):
    execution_id = event_id if kind == "TRADE" else None
    payload = {
        "adapter_kind": "IBKR_FLEX_XML_V1",
        "external_source_event_id": event_id,
        "affected_external_execution_id": affected,
        "quantity": quantity,
        "price": price,
    }
    return NormalizedIbkrFlexEvent(
        row_number=row_number,
        event_kind=kind,
        external_source_event_id=event_id,
        external_execution_id=execution_id,
        affected_external_execution_id=affected,
        transaction_id=transaction_id,
        source_order_key=f"{int(transaction_id):020d}|{event_id}",
        conid="265598",
        asset_category="STK",
        symbol="AAPL",
        exchange="NASDAQ",
        currency="USD",
        raw_side=side,
        raw_open_close=open_close,
        quantity=Decimal(quantity),
        price=Decimal(price),
        occurred_at_utc=occurred_at
        or datetime(2026, 7, 26, 14, tzinfo=timezone.utc),
        source_timezone="America/New_York",
        normalized_fee=Decimal("1"),
        fee_currency="USD",
        execution_status="EXECUTED",
        source_payload_fingerprint=fingerprint
        or f"sha256:{event_id.lower().replace('-', '0'):0<64}"[:71],
        normalized_payload=payload,
    )


def parsed_statement(
    *events,
    generation="2026-07-26T22:00:00+00:00",
    coverage_start=date(2026, 7, 20),
    coverage_end=date(2026, 7, 27),
    external_account="U1234567",
):
    return ParsedIbkrFlexStatement(
        normalized_external_account_ref=external_account,
        masked_external_account_ref="****4567",
        statement_generation=generation,
        generation_order_key=generation,
        raw_from_date=coverage_start.strftime("%Y%m%d"),
        raw_to_date=(coverage_end - timedelta(days=1)).strftime("%Y%m%d"),
        coverage_start=coverage_start,
        coverage_end_exclusive=coverage_end,
        source_timezone="America/New_York",
        events=tuple(events),
    )


def seed_accepted_execution(
    db,
    *,
    graph,
    provider_contract,
):
    user, _, account, _, binding = graph
    session = make_session(db, user=user, account=account, suffix="accepted")
    event = source_event(
        event_id="EXEC-ACCEPTED",
        transaction_id="100",
        occurred_at=datetime(2026, 7, 25, 14, tzinfo=timezone.utc),
    )
    result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=session,
        parsed=parsed_statement(event, generation="2026-07-25T22:00:00+00:00"),
        provider_contract=provider_contract,
    )
    observation = db.query(ExternalSourceObservation).filter_by(
        public_id=result.items[0].observation_public_id
    ).one()
    execution = ExternalExecution(
        binding_id=binding.id,
        user_id=user.id,
        account_id=account.id,
        external_execution_id=event.external_execution_id,
        current_trade_observation_id=observation.id,
        disposition="ACTIVE",
    )
    db.add(execution)
    db.flush()
    application = ExternalTradeApplication(
        binding_id=binding.id,
        user_id=user.id,
        account_id=account.id,
        external_execution_id=execution.id,
        source_observation_id=observation.id,
        application_version=1,
        is_active=True,
        derived_direction="LONG",
        derived_action="OPEN",
        pre_quantity=Decimal("0"),
        post_quantity=Decimal("2"),
        applied_import_session_id=session.id,
    )
    db.add(application)
    binding.source_completeness = "CURRENT"
    db.commit()
    return event, observation, execution


def test_bound_preview_persists_new_statement_evidence_and_derives_add(
    db,
    source_graph,
    provider_contract,
):
    accepted, _, _ = seed_accepted_execution(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
    )
    user, _, account, _, binding = source_graph
    session = make_session(db, user=user, account=account, suffix="new")
    new = source_event(
        event_id="EXEC-NEW",
        transaction_id="200",
        quantity="1",
        occurred_at=accepted.occurred_at_utc + timedelta(days=1),
    )

    result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=session,
        parsed=parsed_statement(new),
        provider_contract=provider_contract,
    )
    db.commit()

    assert result.status == "PREVIEW_READY"
    assert result.source_completeness == "PENDING_IMPORT"
    assert result.source_health == "HEALTHY"
    assert result.items[0].classification == "NEW"
    assert result.items[0].direction == "LONG"
    assert result.items[0].action == "ADD"
    assert result.items[0].pre_quantity == Decimal("2")
    assert result.items[0].post_quantity == Decimal("3")
    assert db.query(SourceStatement).count() == 2
    assert db.query(ExternalSourceObservation).count() == 2
    assert db.query(StatementExecutionSighting).count() == 2
    assert db.query(ImportRow).filter_by(session_id=session.id).count() == 1
    assert db.query(ExternalExecution).count() == 1
    assert db.query(SourceReconciliationCase).count() == 0


def test_exact_repeat_is_already_imported_with_new_generation_sighting(
    db,
    source_graph,
    provider_contract,
):
    accepted, observation, _ = seed_accepted_execution(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
    )
    user, _, account, _, binding = source_graph
    session = make_session(db, user=user, account=account, suffix="repeat")
    repeated = source_event(
        event_id=accepted.external_source_event_id,
        transaction_id=accepted.transaction_id,
        occurred_at=accepted.occurred_at_utc,
        fingerprint=accepted.source_payload_fingerprint,
    )
    result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=session,
        parsed=parsed_statement(repeated),
        provider_contract=provider_contract,
    )
    db.commit()

    assert result.items[0].classification == "ALREADY_IMPORTED"
    assert result.status == "PREVIEW_READY"
    assert db.query(ExternalSourceObservation).count() == 1
    assert (
        db.query(StatementExecutionSighting)
        .filter_by(observation_id=observation.id)
        .count()
        == 2
    )
    assert db.query(SourceReconciliationCase).count() == 0


def test_same_or_later_payload_change_creates_case_and_freezes_health(
    db,
    source_graph,
    provider_contract,
):
    accepted, _, _ = seed_accepted_execution(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
    )
    user, _, account, _, binding = source_graph
    session = make_session(db, user=user, account=account, suffix="conflict")
    changed = source_event(
        event_id=accepted.external_source_event_id,
        transaction_id=accepted.transaction_id,
        occurred_at=accepted.occurred_at_utc,
        quantity="3",
        fingerprint=f"sha256:{'f' * 64}",
    )
    result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=session,
        parsed=parsed_statement(changed),
        provider_contract=provider_contract,
    )
    db.commit()

    assert result.status == "CONFLICTED"
    assert result.items[0].classification == "SOURCE_PAYLOAD_CONFLICT"
    assert result.source_health == "RECONCILIATION_REQUIRED"
    case = db.query(SourceReconciliationCase).one()
    assert case.case_kind == "SOURCE_PAYLOAD_CONFLICT"
    assert case.state == "OPEN"
    assert case.against_source_state_snapshot_json["authority_target"][
        "external_execution_id"
    ] == "EXEC-ACCEPTED"


def test_strictly_earlier_unseen_payload_is_stale_without_case(
    db,
    source_graph,
    provider_contract,
):
    accepted, _, _ = seed_accepted_execution(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
    )
    user, _, account, _, binding = source_graph
    session = make_session(db, user=user, account=account, suffix="stale")
    stale = source_event(
        event_id=accepted.external_source_event_id,
        transaction_id=accepted.transaction_id,
        occurred_at=accepted.occurred_at_utc,
        quantity="9",
        fingerprint=f"sha256:{'e' * 64}",
    )
    result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=session,
        parsed=parsed_statement(
            stale,
            generation="2026-07-24T22:00:00+00:00",
        ),
        provider_contract=provider_contract,
    )
    db.commit()

    assert result.items[0].classification == "STALE_SOURCE_OBSERVATION"
    assert result.source_health == "HEALTHY"
    assert db.query(SourceReconciliationCase).count() == 0


def test_correction_never_becomes_new_and_missing_target_is_case(
    db,
    source_graph,
    provider_contract,
):
    user, _, account, _, binding = source_graph
    session = make_session(db, user=user, account=account, suffix="correction")
    correction = source_event(
        event_id="CORR-1",
        transaction_id="300",
        kind="CORRECTION",
        affected="DOES-NOT-EXIST",
        quantity="2",
        fingerprint=f"sha256:{'c' * 64}",
    )
    result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=session,
        parsed=parsed_statement(correction),
        provider_contract=provider_contract,
    )
    db.commit()

    assert result.items[0].classification == "TARGET_UNRESOLVED"
    assert result.status == "CONFLICTED"
    assert db.query(ExternalExecution).count() == 0
    assert db.query(SourceReconciliationCase).one().case_kind == (
        "TARGET_UNRESOLVED"
    )

    missing_target_session = make_session(
        db,
        user=user,
        account=account,
        suffix="missing-target",
    )
    missing_target = source_event(
        event_id="CORR-2",
        transaction_id="301",
        kind="CORRECTION",
        affected=None,
        quantity="2",
        fingerprint=f"sha256:{'d' * 64}",
    )
    missing_result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=missing_target_session,
        parsed=parsed_statement(missing_target),
        provider_contract=provider_contract,
    )
    db.commit()
    assert missing_result.items[0].classification == "TARGET_UNRESOLVED"
    assert db.query(SourceReconciliationCase).count() == 2


def test_late_new_and_coverage_gap_are_fail_closed(
    db,
    source_graph,
    provider_contract,
):
    accepted, _, _ = seed_accepted_execution(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
    )
    user, _, account, _, binding = source_graph
    late_session = make_session(db, user=user, account=account, suffix="late")
    late = source_event(
        event_id="EXEC-LATE",
        transaction_id="50",
        occurred_at=accepted.occurred_at_utc - timedelta(days=1),
    )
    late_result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=late_session,
        parsed=parsed_statement(late),
        provider_contract=provider_contract,
    )
    assert late_result.items[0].classification == "LATE_NEW"
    assert late_result.status == "CONFLICTED"

    gap_session = make_session(db, user=user, account=account, suffix="gap")
    gap_result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=gap_session,
        parsed=parsed_statement(
            coverage_start=date(2026, 8, 1),
            coverage_end=date(2026, 8, 2),
        ),
        provider_contract=provider_contract,
    )
    db.commit()
    assert gap_result.coverage_gap
    assert gap_result.status == "CONFLICTED"
    assert gap_session.error_code == "SOURCE_COVERAGE_GAP"


def test_duplicate_same_payload_combines_evidence_and_warns(
    db,
    source_graph,
    provider_contract,
):
    user, _, account, _, binding = source_graph
    session = make_session(db, user=user, account=account, suffix="duplicate")
    first = source_event(event_id="EXEC-DUP", row_number=1)
    second = source_event(
        event_id="EXEC-DUP",
        row_number=2,
        fingerprint=first.source_payload_fingerprint,
    )
    result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=session,
        parsed=parsed_statement(first, second),
        provider_contract=provider_contract,
    )
    db.commit()

    assert [item.classification for item in result.items] == ["NEW", "NEW"]
    assert result.items[1].warnings == ("DUPLICATE_SOURCE_EVENT",)
    assert result.items[0].pre_quantity == result.items[1].pre_quantity
    assert result.items[0].post_quantity == result.items[1].post_quantity
    assert db.query(ExternalSourceObservation).count() == 1
    assert db.query(StatementExecutionSighting).count() == 1
    assert db.query(ImportRow).count() == 2
    for row in db.query(ImportRow).all():
        assert "normalized_external_account_ref" not in (
            row.normalized_values_json
        )
        assert row.normalized_values_json["masked_external_account_ref"] == (
            "****4567"
        )


def test_owner_source_and_currency_mismatch_leave_no_source_evidence(
    db,
    source_graph,
    provider_contract,
):
    user, other, account, other_account, binding = source_graph
    foreign_session = make_session(
        db,
        user=other,
        account=other_account,
        suffix="foreign",
    )
    with pytest.raises(IbkrFlexPreviewError) as foreign:
        preview_bound_ibkr_statement(
            db,
            account=other_account,
            binding=binding,
            session=foreign_session,
            parsed=parsed_statement(source_event()),
            provider_contract=provider_contract,
        )
    assert foreign.value.code == "IMPORT_SESSION_NOT_FOUND"

    mismatch_session = make_session(
        db,
        user=user,
        account=account,
        suffix="mismatch",
    )
    with pytest.raises(IbkrFlexPreviewError) as mismatch:
        preview_bound_ibkr_statement(
            db,
            account=account,
            binding=binding,
            session=mismatch_session,
            parsed=parsed_statement(
                source_event(),
                external_account="U9999999",
            ),
            provider_contract=provider_contract,
        )
    assert mismatch.value.code == "ACCOUNT_MISMATCH"
    assert db.query(SourceStatement).count() == 0
