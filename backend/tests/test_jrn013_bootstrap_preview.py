from __future__ import annotations

from dataclasses import replace
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
    AccountLedgerEntry,
    AccountLedgerEntryType,
    ExternalExecution,
    ExternalSourceObservation,
    ExternalTradeApplication,
    IdempotencyKey,
    ImportRow,
    ImportSession,
    ImportSourceBinding,
    LedgerPostingKind,
    SourceStatement,
    StatementExecutionSighting,
    TradingAccount,
    Transaction,
    TransactionType,
    User,
)
from services.ibkr_flex_bootstrap_preview_service import (
    IbkrBootstrapPreviewError,
    preview_ibkr_source_bootstrap,
)
from services.ibkr_flex_parser import (
    NormalizedIbkrFlexEvent,
    ParsedIbkrFlexStatement,
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
            "generation_ordering": "UTC_INSTANT_ASC",
            "generation_tie_policy": (
                "SAME_MARKER_DIFFERENT_FILE_CONFLICT"
            ),
            "execution_time_format": "%Y%m%d;%H%M%S",
            "execution_time_semantics": "SOURCE_TIMEZONE_NAIVE",
            "ordinary_trade_kind_from_element": True,
            "correction_element": "TradeCorrection",
            "cancel_bust_element": "TradeCancel",
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
def owner_graph(db):
    owner = User(
        public_id="bootstrap-owner",
        email="bootstrap@example.com",
        email_normalized="bootstrap@example.com",
        hashed_password="hash",
        timezone="UTC",
    )
    other = User(
        public_id="bootstrap-other",
        email="bootstrap-other@example.com",
        email_normalized="bootstrap-other@example.com",
        hashed_password="hash",
        timezone="UTC",
    )
    account = TradingAccount(
        public_id="bootstrap-account",
        user=owner,
        name="IBKR",
        broker="IBKR",
        currency="USD",
        is_active=True,
        accounting_health="ACCOUNTING_HEALTHY",
        trade_source_state="CLEAN",
        hard_delete_eligible=True,
    )
    other_account = TradingAccount(
        public_id="bootstrap-other-account",
        user=other,
        name="Other",
        broker="IBKR",
        currency="USD",
        is_active=True,
        accounting_health="ACCOUNTING_HEALTHY",
        trade_source_state="CLEAN",
        hard_delete_eligible=True,
    )
    db.add_all([owner, other, account, other_account])
    db.commit()
    return owner, other, account, other_account


def make_session(db, *, owner, account, suffix):
    operation = IdempotencyKey(
        user_id=owner.id,
        scope="IBKR_FLEX_UPLOAD_V1",
        key=f"bootstrap-key-{suffix}",
        request_hash=f"sha256:{suffix:0<64}"[:71],
        status="IN_PROGRESS",
    )
    db.add(operation)
    db.flush()
    session = ImportSession(
        public_id=f"bootstrap-session-{suffix}",
        user_id=owner.id,
        account_id=account.id,
        upload_idempotency_id=operation.id,
        adapter_kind="IBKR_FLEX_XML_V1",
        file_format="XML",
        file_hash=f"sha256:{suffix:0<64}"[:71],
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
    row_number,
    event_id,
    transaction_id,
    kind="TRADE",
    target=None,
    quantity="2",
    price="200",
    fingerprint_char="a",
    occurred_minute=0,
):
    return NormalizedIbkrFlexEvent(
        row_number=row_number,
        event_kind=kind,
        external_source_event_id=event_id,
        external_execution_id=event_id if kind == "TRADE" else None,
        affected_external_execution_id=target,
        transaction_id=str(transaction_id),
        source_order_key=f"{transaction_id:020d}|{event_id}",
        conid="265598",
        asset_category="STK",
        symbol="AAPL",
        exchange="NASDAQ",
        currency="USD",
        raw_side="BUY",
        raw_open_close="OPEN",
        quantity=Decimal(quantity),
        price=Decimal(price),
        occurred_at_utc=datetime(
            2026,
            7,
            25,
            14,
            occurred_minute,
            tzinfo=timezone.utc,
        ),
        source_timezone="America/New_York",
        normalized_fee=Decimal("1"),
        fee_currency="USD",
        execution_status="EXECUTED",
        source_payload_fingerprint=(
            f"sha256:{fingerprint_char * 64}"
        ),
        normalized_payload={
            "adapter_kind": "IBKR_FLEX_XML_V1",
            "normalized_external_account_ref": "U1234567",
            "external_source_event_id": event_id,
            "provider_declared_target_id": target,
            "quantity": quantity,
            "price": price,
        },
    )


def parsed(*events, flat="ACCOUNT_INCEPTION"):
    return ParsedIbkrFlexStatement(
        normalized_external_account_ref="U1234567",
        masked_external_account_ref="****4567",
        statement_generation="20260725;180000",
        generation_order_key="2026-07-25T22:00:00+00:00",
        raw_from_date="20260701",
        raw_to_date="20260725",
        coverage_start=date(2026, 7, 1),
        coverage_end_exclusive=date(2026, 7, 26),
        source_timezone="America/New_York",
        events=tuple(events),
        account_inception_date=(
            date(2026, 7, 1)
            if flat == "ACCOUNT_INCEPTION"
            else None
        ),
        flat_boundary_evidence=flat,
    )


def assert_no_permanent_source_truth(db):
    for model in (
        ImportSourceBinding,
        SourceStatement,
        ExternalSourceObservation,
        StatementExecutionSighting,
        ExternalExecution,
        ExternalTradeApplication,
    ):
        assert db.query(model).count() == 0


def test_flat_bootstrap_replays_effective_units_without_source_writes(
    db,
    owner_graph,
    provider_contract,
):
    owner, _, account, _ = owner_graph
    session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="effective",
    )
    first = source_event(
        row_number=1,
        event_id="EXEC-1",
        transaction_id=100,
    )
    second = source_event(
        row_number=2,
        event_id="EXEC-2",
        transaction_id=101,
        quantity="1",
        fingerprint_char="b",
        occurred_minute=1,
    )

    result = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=session,
        parsed=parsed(first, second),
        provider_contract=provider_contract,
    )
    db.commit()

    assert result.status == "PREVIEW_READY"
    assert result.effective_execution_count == 2
    assert [item.action for item in result.items] == ["OPEN", "ADD"]
    assert result.items[1].pre_quantity == Decimal("2")
    assert result.items[1].post_quantity == Decimal("3")
    assert session.source_preview_digest == result.source_preview_digest
    assert db.query(ImportRow).count() == 2
    assert_no_permanent_source_truth(db)
    for row in db.query(ImportRow):
        assert "normalized_external_account_ref" not in (
            row.normalized_values_json
        )
        assert row.normalized_values_json[
            "masked_external_account_ref"
        ] == "****4567"


def test_duplicate_provider_order_is_allowed_only_across_independent_groups(
    db,
    owner_graph,
    provider_contract,
):
    owner, _, account, _ = owner_graph
    tied_first = source_event(
        row_number=1,
        event_id="EXEC-TIE-1",
        transaction_id=100,
    )
    tied_second = source_event(
        row_number=2,
        event_id="EXEC-TIE-2",
        transaction_id=100,
        fingerprint_char="b",
    )
    conflicted_session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="order-tie-conflict",
    )
    conflicted = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=conflicted_session,
        parsed=parsed(tied_first, tied_second),
        provider_contract=provider_contract,
    )

    assert conflicted.status == "CONFLICTED"
    assert conflicted.conflict_reason == "UNSUPPORTED_ORDER_CONFLICT"
    assert {
        item.conflict_reason for item in conflicted.items
    } == {"UNSUPPORTED_ORDER_CONFLICT"}
    assert_no_permanent_source_truth(db)

    independent_session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="order-tie-independent",
    )
    independent_second = replace(
        tied_second,
        conid="272093",
        symbol="MSFT",
    )
    independent = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=independent_session,
        parsed=parsed(tied_first, independent_second),
        provider_contract=provider_contract,
    )

    assert independent.status == "PREVIEW_READY"
    assert [item.action for item in independent.items] == ["OPEN", "OPEN"]
    assert_no_permanent_source_truth(db)


def test_complete_correction_chain_folds_to_winning_economic_unit(
    db,
    owner_graph,
    provider_contract,
):
    owner, _, account, _ = owner_graph
    session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="correction",
    )
    trade = source_event(
        row_number=1,
        event_id="EXEC-1",
        transaction_id=100,
    )
    correction = source_event(
        row_number=2,
        event_id="CORR-1",
        transaction_id=101,
        kind="CORRECTION",
        target="EXEC-1",
        quantity="3",
        price="201",
        fingerprint_char="c",
        occurred_minute=1,
    )

    result = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=session,
        parsed=parsed(trade, correction),
        provider_contract=provider_contract,
    )

    assert [item.classification for item in result.items] == [
        "BOOTSTRAP_SUPERSEDED",
        "BOOTSTRAP_EFFECTIVE_NEW",
    ]
    assert result.items[1].economic_execution_id == "EXEC-1"
    assert result.items[1].action == "OPEN"
    assert result.items[1].post_quantity == Decimal("3")
    assert_no_permanent_source_truth(db)


def test_same_id_provider_declared_correction_is_a_valid_chain(
    db,
    owner_graph,
    provider_contract,
):
    owner, _, account, _ = owner_graph
    session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="same-id-correction",
    )
    trade = source_event(
        row_number=1,
        event_id="EXEC-1",
        transaction_id=100,
    )
    correction = source_event(
        row_number=2,
        event_id="EXEC-1",
        transaction_id=101,
        kind="CORRECTION",
        target="EXEC-1",
        quantity="3",
        fingerprint_char="e",
        occurred_minute=1,
    )

    result = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=session,
        parsed=parsed(trade, correction),
        provider_contract=provider_contract,
    )

    assert result.status == "PREVIEW_READY"
    assert [item.classification for item in result.items] == [
        "BOOTSTRAP_SUPERSEDED",
        "BOOTSTRAP_EFFECTIVE_NEW",
    ]
    assert result.items[1].economic_execution_id == "EXEC-1"
    assert_no_permanent_source_truth(db)


def test_complete_cancel_chain_becomes_accepted_tombstone(
    db,
    owner_graph,
    provider_contract,
):
    owner, _, account, _ = owner_graph
    session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="cancel",
    )
    trade = source_event(
        row_number=1,
        event_id="EXEC-1",
        transaction_id=100,
    )
    cancel = source_event(
        row_number=2,
        event_id="CANCEL-1",
        transaction_id=101,
        kind="CANCEL_BUST",
        target="EXEC-1",
        fingerprint_char="d",
        occurred_minute=1,
    )

    result = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=session,
        parsed=parsed(trade, cancel),
        provider_contract=provider_contract,
    )

    assert result.status == "PREVIEW_READY"
    assert result.effective_execution_count == 0
    assert result.accepted_tombstone_count == 1
    assert [item.classification for item in result.items] == [
        "BOOTSTRAP_SUPERSEDED",
        "BOOTSTRAP_ACCEPTED_TOMBSTONE",
    ]
    assert_no_permanent_source_truth(db)


@pytest.mark.parametrize(
    ("events", "reason"),
    [
        (
            (
                source_event(
                    row_number=1,
                    event_id="EXEC-1",
                    transaction_id=100,
                ),
                source_event(
                    row_number=2,
                    event_id="EXEC-1",
                    transaction_id=101,
                    fingerprint_char="b",
                    occurred_minute=1,
                ),
            ),
            "PAYLOAD_ID_COLLISION",
        ),
        (
            (
                source_event(
                    row_number=1,
                    event_id="CORR-1",
                    transaction_id=100,
                    kind="CORRECTION",
                    target="MISSING",
                ),
            ),
            "TARGET_UNRESOLVED",
        ),
    ],
)
def test_bootstrap_conflict_keeps_only_session_evidence(
    db,
    owner_graph,
    provider_contract,
    events,
    reason,
):
    owner, _, account, _ = owner_graph
    session = make_session(
        db,
        owner=owner,
        account=account,
        suffix=reason.lower(),
    )

    result = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=session,
        parsed=parsed(*events),
        provider_contract=provider_contract,
    )
    db.commit()

    assert result.status == "CONFLICTED"
    assert result.conflict_reason == reason
    assert session.error_code == "SOURCE_BOOTSTRAP_CONFLICT"
    assert all(
        item.classification == "SOURCE_BOOTSTRAP_CONFLICT"
        for item in result.items
    )
    assert db.query(ImportRow).count() == len(events)
    assert_no_permanent_source_truth(db)


def test_unproven_flat_boundary_conflicts_and_exact_duplicate_is_one_unit(
    db,
    owner_graph,
    provider_contract,
):
    owner, _, account, _ = owner_graph
    unproven_session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="unproven",
    )
    trade = source_event(
        row_number=1,
        event_id="EXEC-1",
        transaction_id=100,
    )
    unproven = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=unproven_session,
        parsed=parsed(trade, flat="UNPROVEN"),
        provider_contract=provider_contract,
    )
    assert unproven.status == "CONFLICTED"
    assert unproven_session.error_code == "SOURCE_FLAT_BOUNDARY_UNPROVEN"

    duplicate_session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="duplicate",
    )
    duplicate = source_event(
        row_number=2,
        event_id="EXEC-1",
        transaction_id=100,
    )
    result = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=duplicate_session,
        parsed=parsed(trade, duplicate),
        provider_contract=provider_contract,
    )

    assert result.status == "PREVIEW_READY"
    assert result.effective_execution_count == 1
    assert result.items[1].warnings == ("DUPLICATE_SOURCE_EVENT",)
    assert_no_permanent_source_truth(db)


def test_owner_swap_and_prior_completed_trade_import_are_rejected(
    db,
    owner_graph,
    provider_contract,
):
    owner, other, account, other_account = owner_graph
    foreign_session = make_session(
        db,
        owner=other,
        account=other_account,
        suffix="foreign",
    )
    with pytest.raises(IbkrBootstrapPreviewError) as foreign:
        preview_ibkr_source_bootstrap(
            db,
            account=account,
            session=foreign_session,
            parsed=parsed(),
            provider_contract=provider_contract,
        )
    assert foreign.value.code == "IMPORT_SESSION_NOT_FOUND"

    completed = make_session(
        db,
        owner=owner,
        account=account,
        suffix="completed",
    )
    completed.status = "COMPLETED"
    fresh = make_session(
        db,
        owner=owner,
        account=account,
        suffix="fresh",
    )
    with pytest.raises(IbkrBootstrapPreviewError) as ineligible:
        preview_ibkr_source_bootstrap(
            db,
            account=account,
            session=fresh,
            parsed=parsed(),
            provider_contract=provider_contract,
        )
    assert ineligible.value.code == "SOURCE_BOOTSTRAP_NOT_ELIGIBLE"


def test_two_clean_accounts_can_preview_same_external_identity_without_binding(
    db,
    owner_graph,
    provider_contract,
):
    owner, _, first_account, _ = owner_graph
    second_account = TradingAccount(
        public_id="bootstrap-second-owner-account",
        user=owner,
        name="IBKR candidate",
        broker="IBKR",
        currency="USD",
        is_active=True,
        accounting_health="ACCOUNTING_HEALTHY",
        trade_source_state="CLEAN",
        hard_delete_eligible=True,
    )
    db.add(second_account)
    db.commit()
    event = source_event(
        row_number=1,
        event_id="EXEC-PARALLEL-PREVIEW",
        transaction_id=100,
    )
    first_session = make_session(
        db,
        owner=owner,
        account=first_account,
        suffix="parallel-first",
    )
    second_session = make_session(
        db,
        owner=owner,
        account=second_account,
        suffix="parallel-second",
    )

    first = preview_ibkr_source_bootstrap(
        db,
        account=first_account,
        session=first_session,
        parsed=parsed(event),
        provider_contract=provider_contract,
    )
    second = preview_ibkr_source_bootstrap(
        db,
        account=second_account,
        session=second_session,
        parsed=parsed(event),
        provider_contract=provider_contract,
    )
    db.commit()

    assert first.status == second.status == "PREVIEW_READY"
    assert first.source_preview_digest != second.source_preview_digest
    assert db.query(ImportRow).count() == 2
    assert_no_permanent_source_truth(db)


def test_unknown_asset_category_becomes_session_only_terminal_conflict(
    db,
    owner_graph,
    provider_contract,
):
    owner, _, account, _ = owner_graph
    session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="unknown-asset",
    )
    event = replace(
        source_event(
            row_number=1,
            event_id="EXEC-UNKNOWN-ASSET",
            transaction_id=100,
        ),
        asset_category="FUT",
    )

    result = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=session,
        parsed=parsed(event),
        provider_contract=provider_contract,
    )
    db.commit()

    assert result.status == "CONFLICTED"
    assert result.conflict_reason == "UNSUPPORTED_ASSET_TYPE"
    assert session.error_code == "SOURCE_BOOTSTRAP_CONFLICT"
    assert db.query(ImportRow).count() == 1
    assert not db.query(ImportRow).one().is_valid
    assert_no_permanent_source_truth(db)


def test_bootstrap_digest_is_stable_and_covers_fee_and_fingerprint(
    db,
    owner_graph,
    provider_contract,
):
    owner, _, account, _ = owner_graph
    first_session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="digest-first",
    )
    event = source_event(
        row_number=1,
        event_id="EXEC-DIGEST",
        transaction_id=100,
    )
    first = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=first_session,
        parsed=parsed(event),
        provider_contract=provider_contract,
    )
    db.commit()
    db.expire_all()
    assert db.get(ImportSession, first_session.id).source_preview_digest == (
        first.source_preview_digest
    )

    second_session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="digest-second",
    )
    second = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=second_session,
        parsed=parsed(event),
        provider_contract=provider_contract,
    )
    assert second.source_preview_digest == first.source_preview_digest

    changed_session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="digest-changed",
    )
    changed_event = replace(
        event,
        normalized_fee=Decimal("2"),
        source_payload_fingerprint=f"sha256:{'f' * 64}",
    )
    changed = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=changed_session,
        parsed=parsed(changed_event),
        provider_contract=provider_contract,
    )
    assert changed.source_preview_digest != first.source_preview_digest


def test_same_currency_cash_facts_are_allowed_but_trade_postings_are_not(
    db,
    owner_graph,
    provider_contract,
):
    owner, _, account, _ = owner_graph
    transaction = Transaction(
        public_id="bootstrap-deposit",
        account_id=account.id,
        type=TransactionType.DEPOSIT,
        amount=Decimal("100"),
        currency="USD",
        date=datetime(2026, 7, 1, tzinfo=timezone.utc),
    )
    db.add(transaction)
    db.flush()
    db.add(
        AccountLedgerEntry(
            public_id="bootstrap-deposit-ledger",
            user_id=owner.id,
            account_id=account.id,
            transaction_id=transaction.id,
            entry_type=AccountLedgerEntryType.DEPOSIT,
            source_fact_public_id=transaction.public_id,
            posting_kind=LedgerPostingKind.DEPOSIT.value,
            occurred_at=transaction.date,
            currency="USD",
            amount=Decimal("100"),
        )
    )
    db.commit()
    allowed_session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="cash-allowed",
    )
    allowed = preview_ibkr_source_bootstrap(
        db,
        account=account,
        session=allowed_session,
        parsed=parsed(),
        provider_contract=provider_contract,
    )
    assert allowed.status == "PREVIEW_READY"

    db.add(
        AccountLedgerEntry(
            public_id="bootstrap-trade-ledger",
            user_id=owner.id,
            account_id=account.id,
            entry_type=AccountLedgerEntryType.REALIZED_PNL,
            source_fact_public_id="bootstrap-trade-fact",
            posting_kind=LedgerPostingKind.REALIZED_GROSS.value,
            occurred_at=datetime(2026, 7, 2, tzinfo=timezone.utc),
            currency="USD",
            amount=Decimal("1"),
        )
    )
    db.commit()
    rejected_session = make_session(
        db,
        owner=owner,
        account=account,
        suffix="cash-rejected",
    )
    with pytest.raises(IbkrBootstrapPreviewError) as rejected:
        preview_ibkr_source_bootstrap(
            db,
            account=account,
            session=rejected_session,
            parsed=parsed(),
            provider_contract=provider_contract,
        )
    assert rejected.value.code == "SOURCE_BOOTSTRAP_NOT_ELIGIBLE"
