from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import os
import tempfile

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

import services.ibkr_flex_preview_service as preview_service
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
    StatementCoverageAcceptance,
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
from services.source_preview_projection_service import (
    build_source_preview_projection,
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
            "execution_status_source": "ATTRIBUTE_VALUE",
            "execution_status_field": "tradeStatus",
            "commission_field": "ibCommission",
            "commission_currency_field": "ibCommissionCurrency",
            "commission_charge_sign": "NEGATIVE",
            "commission_currency_semantics": "MUST_EQUAL_TRADE_CURRENCY",
            "side_buy_value": "BUY",
            "side_sell_value": "SELL",
            "open_value": "OPEN",
            "close_value": "CLOSE",
            "statement_to_date_inclusive": True,
            "statement_date_semantics": "SOURCE_TIMEZONE_LOCAL_DATE",
            "statement_date_format": "%Y%m%d",
            "generation_time_format": "%Y%m%d;%H%M%S",
            "generation_time_semantics": "SOURCE_TIMEZONE_NAIVE",
            "generation_ordering": "UTC_INSTANT_ASC",
            "generation_tie_policy": (
                "SAME_MARKER_DIFFERENT_FILE_CONFLICT"
            ),
            "execution_time_format": "%Y%m%d;%H%M%S",
            "execution_time_semantics": "SOURCE_TIMEZONE_NAIVE",
            "event_kind_source": "ELEMENT_NAME",
            "correction_element": "TradeCorrection",
            "cancel_bust_element": "TradeCancel",
            "change_identity_semantics": "DISTINCT_EVENT_AND_TARGET",
            "change_event_id_field": "sourceEventID",
            "affected_execution_id_field": "affectedIBExecID",
            "account_inception_date_field": "accountInceptionDate",
            "open_positions_element": "OpenPositions",
            "open_position_element": "OpenPosition",
            "open_positions_snapshot_date_field": "snapshotDate",
            "open_position_quantity_field": "position",
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
        accepted_coverage_start=None,
        accepted_coverage_through_exclusive=None,
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
        parsed=parsed_statement(
            event,
            generation="2026-07-25T22:00:00+00:00",
            coverage_start=date(2026, 7, 1),
            coverage_end=date(2026, 7, 26),
        ),
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
    statement = db.query(SourceStatement).filter_by(
        public_id=result.statement_public_id
    ).one()
    db.add(
        StatementCoverageAcceptance(
            binding_id=binding.id,
            user_id=user.id,
            account_id=account.id,
            statement_id=statement.id,
            import_session_id=session.id,
            operation_idempotency_id=session.upload_idempotency_id,
            accepted_source_state_revision=1,
        )
    )
    binding.accepted_coverage_start = date(2026, 7, 1)
    binding.accepted_coverage_through_exclusive = date(2026, 7, 26)
    binding.source_completeness = "CURRENT"
    db.commit()
    return event, observation, execution


def preview_empty_statement(
    db,
    *,
    graph,
    provider_contract,
    suffix,
    coverage_start,
    coverage_end,
):
    user, _, account, _, binding = graph
    session = make_session(db, user=user, account=account, suffix=suffix)
    result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=session,
        parsed=parsed_statement(
            generation=f"2026-07-26T22:00:{len(suffix):02d}+00:00",
            coverage_start=coverage_start,
            coverage_end=coverage_end,
        ),
        provider_contract=provider_contract,
    )
    return session, result


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


def test_same_generation_different_files_create_persistent_conflict(
    db,
    source_graph,
    provider_contract,
):
    user, _, account, _, binding = source_graph
    generation = "2026-07-27T22:00:00+00:00"
    first_session = make_session(
        db,
        user=user,
        account=account,
        suffix="generation-first",
    )
    first = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=first_session,
        parsed=parsed_statement(
            source_event(event_id="EXEC-GEN-1", transaction_id="201"),
            generation=generation,
        ),
        provider_contract=provider_contract,
    )
    assert first.items[0].classification == "NEW"
    assert first_session.error_code == "SOURCE_COVERAGE_GAP"

    second_session = make_session(
        db,
        user=user,
        account=account,
        suffix="generation-second",
    )
    second = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=second_session,
        parsed=parsed_statement(
            source_event(event_id="EXEC-GEN-2", transaction_id="202"),
            generation=generation,
        ),
        provider_contract=provider_contract,
    )

    assert second.status == "CONFLICTED"
    assert second_session.error_code == "SOURCE_GENERATION_CONFLICT"
    assert second.items[0].classification == "SOURCE_GENERATION_CONFLICT"
    assert db.query(SourceStatement).count() == 2
    assert db.query(SourceReconciliationCase).filter_by(
        case_kind="SOURCE_GENERATION_CONFLICT",
    ).count() == 1
    assert binding.source_health == "RECONCILIATION_REQUIRED"


def test_same_generation_empty_files_are_statement_level_conflict(
    db,
    source_graph,
    provider_contract,
):
    user, _, account, _, binding = source_graph
    generation = "2026-07-27T23:00:00+00:00"
    first_session = make_session(
        db,
        user=user,
        account=account,
        suffix="empty-generation-first",
    )
    first = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=first_session,
        parsed=parsed_statement(generation=generation),
        provider_contract=provider_contract,
    )
    assert first_session.error_code == "SOURCE_COVERAGE_GAP"

    second_session = make_session(
        db,
        user=user,
        account=account,
        suffix="empty-generation-second",
    )
    second = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=second_session,
        parsed=parsed_statement(generation=generation),
        provider_contract=provider_contract,
    )

    assert second.status == "CONFLICTED"
    assert second.items == ()
    assert second_session.error_code == "SOURCE_GENERATION_CONFLICT"
    assert db.query(SourceStatement).count() == 2
    assert db.query(SourceReconciliationCase).count() == 0
    assert binding.source_completeness == "PENDING_IMPORT"


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


def test_same_file_reupload_reuses_statement_observation_and_sighting(
    db,
    source_graph,
    provider_contract,
):
    user, _, account, _, binding = source_graph
    file_hash = f"sha256:{'a' * 64}"
    event = source_event(event_id="EXEC-SAME-FILE", transaction_id="205")
    parsed = parsed_statement(
        event,
        generation="2026-07-26T22:00:05+00:00",
    )
    first_session = make_session(
        db,
        user=user,
        account=account,
        suffix="same-file-first",
        file_hash=file_hash,
    )
    first = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=first_session,
        parsed=parsed,
        provider_contract=provider_contract,
    )
    db.commit()

    second_session = make_session(
        db,
        user=user,
        account=account,
        suffix="same-file-second",
        file_hash=file_hash,
    )
    second = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=second_session,
        parsed=parsed,
        provider_contract=provider_contract,
    )
    db.commit()

    assert first.items[0].classification == "NEW"
    assert second.items[0].classification == "NEW"
    assert second_session.error_code != "SOURCE_GENERATION_CONFLICT"
    assert db.query(SourceStatement).count() == 1
    assert db.query(ExternalSourceObservation).count() == 1
    assert db.query(StatementExecutionSighting).count() == 1


def test_fingerprint_version_change_never_silently_matches_accepted_observation(
    db,
    source_graph,
    provider_contract,
    monkeypatch,
):
    accepted, _, _ = seed_accepted_execution(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
    )
    user, _, account, _, binding = source_graph
    monkeypatch.setattr(preview_service, "SOURCE_FINGERPRINT_VERSION", 2)
    session = make_session(
        db,
        user=user,
        account=account,
        suffix="fingerprint-v2",
    )
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
        parsed=parsed_statement(
            repeated,
            generation="2026-07-26T23:00:00+00:00",
        ),
        provider_contract=provider_contract,
    )
    db.commit()

    assert result.items[0].classification == "SOURCE_PAYLOAD_CONFLICT"
    assert {
        observation.fingerprint_version
        for observation in db.query(ExternalSourceObservation).all()
    } == {1, 2}
    assert db.query(SourceReconciliationCase).filter_by(
        case_kind="SOURCE_PAYLOAD_CONFLICT",
    ).count() == 1


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
        parsed=parsed_statement(
            missing_target,
            generation="2026-07-26T22:00:01+00:00",
        ),
        provider_contract=provider_contract,
    )
    db.commit()
    assert missing_result.items[0].classification == "TARGET_UNRESOLVED"
    assert db.query(SourceReconciliationCase).count() == 2


@pytest.mark.parametrize("kind", ("CORRECTION", "CANCEL_BUST"))
def test_accepted_change_replay_stale_and_payload_conflict_follow_authority(
    db,
    source_graph,
    provider_contract,
    kind,
):
    accepted, _, execution = seed_accepted_execution(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
    )
    user, _, account, _, binding = source_graph
    accepted_change = source_event(
        event_id=f"{kind}-ACCEPTED",
        transaction_id="110",
        kind=kind,
        affected=accepted.external_execution_id,
        occurred_at=accepted.occurred_at_utc + timedelta(hours=1),
        fingerprint=f"sha256:{'a' * 64}",
    )
    accepted_session = make_session(
        db,
        user=user,
        account=account,
        suffix=f"{kind.lower()}-accepted",
    )
    accepted_preview = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=accepted_session,
        parsed=parsed_statement(
            accepted_change,
            generation="2026-07-25T23:00:00+00:00",
        ),
        provider_contract=provider_contract,
    )
    accepted_observation = db.query(ExternalSourceObservation).filter_by(
        public_id=accepted_preview.items[0].observation_public_id
    ).one()
    accepted_case = db.query(SourceReconciliationCase).one()
    accepted_case.state = "RESOLVED_APPLIED"
    accepted_case.resolved_at = datetime.now(timezone.utc)
    if kind == "CORRECTION":
        execution.current_trade_observation_id = accepted_observation.id
    else:
        execution.disposition = "ACCEPTED_TOMBSTONE"
        execution.canceled_by_observation_id = accepted_observation.id
    db.commit()

    exact_session = make_session(
        db,
        user=user,
        account=account,
        suffix=f"{kind.lower()}-exact",
    )
    exact = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=exact_session,
        parsed=parsed_statement(
            accepted_change,
            generation="2026-07-26T00:00:00+00:00",
        ),
        provider_contract=provider_contract,
    )
    db.commit()
    assert exact.items[0].classification == "ALREADY_IMPORTED"
    assert db.query(ExternalSourceObservation).count() == 2
    assert db.query(StatementExecutionSighting).filter_by(
        observation_id=accepted_observation.id,
    ).count() == 2

    stale_session = make_session(
        db,
        user=user,
        account=account,
        suffix=f"{kind.lower()}-stale",
    )
    stale_change = source_event(
        event_id=f"{kind}-STALE",
        transaction_id="109",
        kind=kind,
        affected=accepted.external_execution_id,
        occurred_at=accepted.occurred_at_utc + timedelta(minutes=30),
        fingerprint=f"sha256:{'b' * 64}",
    )
    stale = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=stale_session,
        parsed=parsed_statement(
            stale_change,
            generation="2026-07-25T22:30:00+00:00",
        ),
        provider_contract=provider_contract,
    )
    db.commit()
    assert stale.items[0].classification == "STALE_SOURCE_OBSERVATION"
    assert db.query(SourceReconciliationCase).count() == 1

    changed_session = make_session(
        db,
        user=user,
        account=account,
        suffix=f"{kind.lower()}-changed",
    )
    changed_change = source_event(
        event_id=accepted_change.external_source_event_id,
        transaction_id=accepted_change.transaction_id,
        kind=kind,
        affected=accepted.external_execution_id,
        occurred_at=accepted_change.occurred_at_utc,
        price="201",
        fingerprint=f"sha256:{'c' * 64}",
    )
    changed = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=changed_session,
        parsed=parsed_statement(
            changed_change,
            generation="2026-07-26T01:00:00+00:00",
        ),
        provider_contract=provider_contract,
    )
    db.commit()
    assert changed.items[0].classification == "SOURCE_PAYLOAD_CONFLICT"
    assert db.query(SourceReconciliationCase).filter_by(
        case_kind="SOURCE_PAYLOAD_CONFLICT",
    ).count() == 1


@pytest.mark.parametrize("prior_state", ("OPEN", "DIVERGED_REJECTED"))
def test_strict_later_conflict_closes_old_episode_and_opens_new_one(
    db,
    source_graph,
    provider_contract,
    prior_state,
):
    accepted, _, _ = seed_accepted_execution(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
    )
    user, _, account, _, binding = source_graph
    first_change = source_event(
        event_id="CORR-F2",
        transaction_id="120",
        kind="CORRECTION",
        affected=accepted.external_execution_id,
        occurred_at=accepted.occurred_at_utc + timedelta(hours=2),
        fingerprint=f"sha256:{'2' * 64}",
    )
    first_session = make_session(
        db,
        user=user,
        account=account,
        suffix=f"authority-first-{prior_state.lower()}",
    )
    first = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=first_session,
        parsed=parsed_statement(
            first_change,
            generation="2026-07-26T00:00:00+00:00",
        ),
        provider_contract=provider_contract,
    )
    first_case = db.query(SourceReconciliationCase).one()
    first_case.state = prior_state
    db.commit()

    later_change = source_event(
        event_id="CORR-F3",
        transaction_id="121",
        kind="CORRECTION",
        affected=accepted.external_execution_id,
        occurred_at=accepted.occurred_at_utc + timedelta(hours=3),
        fingerprint=f"sha256:{'3' * 64}",
    )
    later_session = make_session(
        db,
        user=user,
        account=account,
        suffix=f"authority-later-{prior_state.lower()}",
    )
    later = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=later_session,
        parsed=parsed_statement(
            later_change,
            generation="2026-07-26T01:00:00+00:00",
        ),
        provider_contract=provider_contract,
    )
    db.commit()

    db.refresh(first_case)
    assert first.items[0].classification == "CORRECTION"
    assert later.items[0].classification == "CORRECTION"
    assert first_case.state == "RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY"
    assert first_case.winning_sighting_id == db.query(
        StatementExecutionSighting.id
    ).filter_by(public_id=later.items[0].sighting_public_id).scalar()
    open_cases = db.query(SourceReconciliationCase).filter_by(state="OPEN").all()
    assert len(open_cases) == 1
    assert open_cases[0].conflict_observation_id == db.query(
        ExternalSourceObservation.id
    ).filter_by(public_id=later.items[0].observation_public_id).scalar()
    assert binding.source_health == "RECONCILIATION_REQUIRED"

    reassert_session = make_session(
        db,
        user=user,
        account=account,
        suffix=f"authority-reassert-{prior_state.lower()}",
    )
    reasserted = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=reassert_session,
        parsed=parsed_statement(
            first_change,
            generation="2026-07-26T02:00:00+00:00",
        ),
        provider_contract=provider_contract,
    )
    db.commit()

    assert reasserted.items[0].classification == "CORRECTION"
    assert db.query(SourceReconciliationCase).count() == 3
    latest_open = db.query(SourceReconciliationCase).filter_by(
        state="OPEN",
    ).one()
    assert latest_open.conflict_observation_id == db.query(
        ExternalSourceObservation.id
    ).filter_by(public_id=first.items[0].observation_public_id).scalar()
    assert binding.source_health == "RECONCILIATION_REQUIRED"


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
            generation="2026-07-26T22:00:01+00:00",
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
    assert result.pending_execution_count == 1
    assert db.query(ImportRow).count() == 2
    for row in db.query(ImportRow).all():
        assert "normalized_external_account_ref" not in (
            row.normalized_values_json
        )
        assert row.normalized_values_json["masked_external_account_ref"] == (
            "****4567"
        )


@pytest.mark.parametrize(
    ("kind", "affected"),
    (("TRADE", None), ("CORRECTION", "EXEC-UNKNOWN")),
)
def test_same_statement_same_event_id_different_payload_persists_both_sightings(
    db,
    source_graph,
    provider_contract,
    kind,
    affected,
):
    user, _, account, _, binding = source_graph
    session = make_session(
        db,
        user=user,
        account=account,
        suffix="payload-collision",
    )
    first = source_event(
        event_id="EXEC-COLLISION",
        row_number=1,
        kind=kind,
        affected=affected,
        fingerprint=f"sha256:{'1' * 64}",
    )
    second = source_event(
        event_id="EXEC-COLLISION",
        row_number=2,
        kind=kind,
        affected=affected,
        price="201",
        fingerprint=f"sha256:{'2' * 64}",
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

    assert result.status == "CONFLICTED"
    assert {
        item.classification for item in result.items
    } == {"SOURCE_PAYLOAD_CONFLICT"}
    assert db.query(ExternalSourceObservation).count() == 2
    assert db.query(StatementExecutionSighting).count() == 2
    assert db.query(SourceReconciliationCase).filter_by(
        case_kind="SOURCE_PAYLOAD_CONFLICT",
    ).count() == 2


def test_duplicate_provider_order_creates_reconciliation_cases(
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
    session = make_session(
        db,
        user=user,
        account=account,
        suffix="provider-order-tie",
    )
    occurred_at = accepted.occurred_at_utc + timedelta(days=1)
    first = source_event(
        event_id="EXEC-TIE-1",
        transaction_id="200",
        quantity="1",
        occurred_at=occurred_at,
        fingerprint=f"sha256:{'5' * 64}",
    )
    second = source_event(
        row_number=2,
        event_id="EXEC-TIE-2",
        transaction_id="200",
        quantity="1",
        occurred_at=occurred_at,
        fingerprint=f"sha256:{'6' * 64}",
    )

    result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=session,
        parsed=parsed_statement(first, second),
        provider_contract=provider_contract,
    )

    assert result.status == "CONFLICTED"
    assert {
        item.classification for item in result.items
    } == {"UNSUPPORTED_ORDER_CONFLICT"}
    assert (
        db.query(SourceReconciliationCase)
        .filter(
            SourceReconciliationCase.case_kind
            == "UNSUPPORTED_ORDER_CONFLICT"
        )
        .count()
        == 2
    )
    assert result.pending_execution_count == 0


def test_new_event_tied_with_accepted_boundary_is_order_conflict(
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
    session = make_session(
        db,
        user=user,
        account=account,
        suffix="accepted-boundary-tie",
    )
    tied = source_event(
        event_id="ZZZ-TIED-WITH-ACCEPTED",
        transaction_id=accepted.transaction_id,
        occurred_at=accepted.occurred_at_utc,
        fingerprint=f"sha256:{'7' * 64}",
    )

    result = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=session,
        parsed=parsed_statement(tied),
        provider_contract=provider_contract,
    )

    assert result.status == "CONFLICTED"
    assert result.items[0].classification == "UNSUPPORTED_ORDER_CONFLICT"
    case = db.query(SourceReconciliationCase).filter(
        SourceReconciliationCase.case_kind
        == "UNSUPPORTED_ORDER_CONFLICT"
    ).one()
    assert case.conflict_observation_id is not None
    assert result.pending_execution_count == 0


def test_binding_wide_projection_digest_is_stable_and_tracks_pending_truth(
    db,
    source_graph,
    provider_contract,
):
    accepted, accepted_observation, execution = seed_accepted_execution(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
    )
    user, _, account, _, binding = source_graph
    first_session = make_session(
        db,
        user=user,
        account=account,
        suffix="digest-one",
    )
    first_event = source_event(
        event_id="EXEC-DIGEST-ONE",
        transaction_id="200",
        quantity="1",
        occurred_at=accepted.occurred_at_utc + timedelta(days=1),
        fingerprint=f"sha256:{'1' * 64}",
    )
    first = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=first_session,
        parsed=parsed_statement(first_event),
        provider_contract=provider_contract,
    )
    rebuilt = build_source_preview_projection(db, binding=binding)

    assert first.source_preview_schema_version == 2
    assert first.source_preview_digest == rebuilt.digest
    assert first_session.source_preview_digest == rebuilt.digest
    assert rebuilt.payload["pending_units"][0]["derived_action"] == "ADD"
    assert rebuilt.payload["pending_units"][0]["pre_quantity"] == "2"
    assert rebuilt.payload["pending_units"][0]["post_quantity"] == "3"

    second_session = make_session(
        db,
        user=user,
        account=account,
        suffix="digest-two",
    )
    second_event = source_event(
        event_id="EXEC-DIGEST-TWO",
        transaction_id="201",
        quantity="1",
        occurred_at=accepted.occurred_at_utc + timedelta(days=1, minutes=1),
        fingerprint=f"sha256:{'2' * 64}",
    )
    second = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=second_session,
        parsed=parsed_statement(
            second_event,
            generation="2026-07-26T22:00:01+00:00",
        ),
        provider_contract=provider_contract,
    )

    assert second.source_preview_digest != first.source_preview_digest
    assert second.pending_execution_count == 2
    assert build_source_preview_projection(db, binding=binding).digest == (
        second.source_preview_digest
    )

    authority_baseline = build_source_preview_projection(
        db,
        binding=binding,
    ).digest
    binding.source_state_revision += 1
    revision_changed = build_source_preview_projection(
        db,
        binding=binding,
    ).digest
    assert revision_changed != authority_baseline
    binding.source_state_revision -= 1

    pending_observation = db.query(ExternalSourceObservation).filter_by(
        public_id=first.items[0].observation_public_id,
    ).one()
    execution.current_trade_observation_id = pending_observation.id
    authority_changed = build_source_preview_projection(
        db,
        binding=binding,
    ).digest
    assert authority_changed != authority_baseline
    execution.current_trade_observation_id = accepted_observation.id

    execution.disposition = "ACCEPTED_TOMBSTONE"
    execution.canceled_by_observation_id = pending_observation.id
    tombstone_changed = build_source_preview_projection(
        db,
        binding=binding,
    ).digest
    assert tombstone_changed != authority_baseline
    execution.disposition = "ACTIVE"
    execution.canceled_by_observation_id = None

    application = db.query(ExternalTradeApplication).filter_by(
        external_execution_id=execution.id,
        is_active=True,
    ).one()
    application.post_quantity = Decimal("3")
    group_boundary_changed = build_source_preview_projection(
        db,
        binding=binding,
    ).digest
    assert group_boundary_changed != authority_baseline


def test_pending_coverage_fixed_point_handles_adjacent_overlap_gap_and_bridge(
    db,
    source_graph,
    provider_contract,
):
    seed_accepted_execution(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
    )

    _, adjacent = preview_empty_statement(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
        suffix="adjacent",
        coverage_start=date(2026, 7, 26),
        coverage_end=date(2026, 8, 1),
    )
    assert not adjacent.coverage_gap
    assert adjacent.pending_statement_count == 1

    _, overlap = preview_empty_statement(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
        suffix="overlap",
        coverage_start=date(2026, 7, 20),
        coverage_end=date(2026, 8, 2),
    )
    assert not overlap.coverage_gap

    _, gap = preview_empty_statement(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
        suffix="far-gap",
        coverage_start=date(2026, 8, 5),
        coverage_end=date(2026, 8, 10),
    )
    assert gap.coverage_gap
    assert gap.status == "CONFLICTED"

    _, bridge = preview_empty_statement(
        db,
        graph=source_graph,
        provider_contract=provider_contract,
        suffix="bridge-gap",
        coverage_start=date(2026, 8, 2),
        coverage_end=date(2026, 8, 5),
    )
    assert not bridge.coverage_gap
    assert bridge.pending_statement_count == 4
    assert bridge.source_completeness == "PENDING_IMPORT"


def test_projection_rejects_coverage_scalar_without_acceptance(
    db,
    source_graph,
    provider_contract,
):
    user, _, account, _, binding = source_graph
    binding.accepted_coverage_start = date(2026, 7, 1)
    binding.accepted_coverage_through_exclusive = date(2026, 7, 26)
    session = make_session(
        db,
        user=user,
        account=account,
        suffix="scalar-mismatch",
    )

    with pytest.raises(IbkrFlexPreviewError) as mismatch:
        preview_bound_ibkr_statement(
            db,
            account=account,
            binding=binding,
            session=session,
            parsed=parsed_statement(),
            provider_contract=provider_contract,
        )

    assert mismatch.value.code == "SOURCE_COVERAGE_PROJECTION_MISMATCH"


def test_prior_unconfirmed_observation_survives_session_expiry(
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
    first_session = make_session(
        db,
        user=user,
        account=account,
        suffix="unconfirmed-old",
    )
    old = source_event(
        event_id="EXEC-UNCONFIRMED-OLD",
        transaction_id="200",
        quantity="1",
        occurred_at=accepted.occurred_at_utc + timedelta(days=1),
        fingerprint=f"sha256:{'3' * 64}",
    )
    first = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=first_session,
        parsed=parsed_statement(old),
        provider_contract=provider_contract,
    )
    assert first.pending_execution_count == 1
    first_session.status = "EXPIRED"

    second_session = make_session(
        db,
        user=user,
        account=account,
        suffix="unconfirmed-new",
    )
    new = source_event(
        event_id="EXEC-UNCONFIRMED-NEW",
        transaction_id="201",
        quantity="1",
        occurred_at=accepted.occurred_at_utc + timedelta(days=1, minutes=1),
        fingerprint=f"sha256:{'4' * 64}",
    )
    second = preview_bound_ibkr_statement(
        db,
        account=account,
        binding=binding,
        session=second_session,
        parsed=parsed_statement(
            new,
            generation="2026-07-26T22:00:01+00:00",
        ),
        provider_contract=provider_contract,
    )

    assert second.pending_execution_count == 2
    assert {
        unit.external_source_event_id
        for unit in build_source_preview_projection(
            db,
            binding=binding,
        ).pending_units
    } == {"EXEC-UNCONFIRMED-OLD", "EXEC-UNCONFIRMED-NEW"}


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
