from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from database import Base
from models import (
    ExternalExecution,
    ExternalSourceObservation,
    ExternalTradeApplication,
    IdempotencyKey,
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
from services.source_reconciliation_service import (
    build_source_case_snapshot,
    create_or_attach_source_case,
    recompute_source_health,
    supersede_source_case_with_later_sighting,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


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
def owner_graph(db):
    first = User(
        public_id="jrn013-user-1",
        email="jrn013-1@example.com",
        email_normalized="jrn013-1@example.com",
        hashed_password="hash",
        timezone="UTC",
    )
    second = User(
        public_id="jrn013-user-2",
        email="jrn013-2@example.com",
        email_normalized="jrn013-2@example.com",
        hashed_password="hash",
        timezone="UTC",
    )
    accounts = [
        TradingAccount(
            public_id=f"jrn013-account-{index}",
            user=owner,
            name=f"Account {index}",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        for index, owner in ((1, first), (2, first), (3, second))
    ]
    db.add_all([first, second, *accounts])
    db.commit()
    return first, second, accounts


def idempotency(db, user: User, suffix: str) -> IdempotencyKey:
    record = IdempotencyKey(
        public_id=f"jrn013-idem-{suffix}",
        user_id=user.id,
        scope="IBKR_FLEX_UPLOAD_V1",
        key=f"key-{suffix}",
        request_hash=f"sha256:{suffix:0<64}"[:71],
        status="COMPLETED",
        response_json={},
    )
    db.add(record)
    db.flush()
    return record


def import_session(
    db,
    user: User,
    account: TradingAccount,
    suffix: str,
) -> ImportSession:
    record = idempotency(db, user, suffix)
    session = ImportSession(
        public_id=f"jrn013-session-{suffix}",
        user_id=user.id,
        account_id=account.id,
        upload_idempotency_id=record.id,
        adapter_kind="IBKR_FLEX_XML_V1",
        file_format="XML",
        file_hash=f"sha256:{suffix:0<64}"[:71],
        file_size_bytes=100,
        original_filename=f"{suffix}.xml",
        media_type="application/xml",
        status="PREVIEW_READY",
        total_rows=1,
        valid_rows=1,
        error_rows=0,
        warning_rows=0,
        expires_at=datetime.now(timezone.utc) + timedelta(days=1),
    )
    db.add(session)
    db.flush()
    return session


def binding(
    db,
    user: User,
    account: TradingAccount,
    external_ref: str,
) -> ImportSourceBinding:
    value = ImportSourceBinding(
        public_id=f"binding-{user.id}-{account.id}-{external_ref}",
        user_id=user.id,
        account_id=account.id,
        adapter_kind="IBKR_FLEX_XML_V1",
        normalized_external_account_ref=external_ref,
        masked_external_account_ref=f"***{external_ref[-4:]}",
        source_timezone="America/New_York",
        source_health="HEALTHY",
        source_completeness="CURRENT",
    )
    db.add(value)
    db.flush()
    return value


def statement(
    db,
    source_binding: ImportSourceBinding,
    session: ImportSession,
    suffix: str,
) -> SourceStatement:
    value = SourceStatement(
        public_id=f"statement-{source_binding.id}-{suffix}",
        binding_id=source_binding.id,
        user_id=source_binding.user_id,
        account_id=source_binding.account_id,
        import_session_id=session.id,
        file_hash=f"sha256:{suffix:0<64}"[:71],
        statement_generation=f"20260726-{suffix}",
        generation_order_key=f"2026-07-26T00:00:00Z|{suffix}",
        raw_from_date="20260701",
        raw_to_date="20260725",
        coverage_start=date(2026, 7, 1),
        coverage_end_exclusive=date(2026, 7, 26),
        source_timezone="America/New_York",
        normalized_external_account_ref=(
            source_binding.normalized_external_account_ref
        ),
    )
    db.add(value)
    db.flush()
    return value


def observation(
    db,
    source_binding: ImportSourceBinding,
    suffix: str,
    *,
    fingerprint_suffix: str | None = None,
) -> ExternalSourceObservation:
    fingerprint_token = fingerprint_suffix or suffix
    value = ExternalSourceObservation(
        public_id=f"observation-{source_binding.id}-{suffix}-{fingerprint_token}",
        binding_id=source_binding.id,
        user_id=source_binding.user_id,
        account_id=source_binding.account_id,
        event_kind="TRADE",
        external_source_event_id=f"EXEC-{suffix}",
        external_execution_id=f"EXEC-{suffix}",
        fingerprint_version=1,
        source_payload_fingerprint=(
            f"sha256:{fingerprint_token:0<64}"[:71]
        ),
        transaction_id=f"TX-{suffix}",
        source_order_key=f"100|EXEC-{suffix}",
        conid="265598",
        instrument_identity_json={
            "asset_type": "STOCK",
            "market": "US",
            "exchange_code": "NASDAQ",
            "normalized_symbol": "AAPL",
            "instrument_type": "SPOT",
            "quote_currency": "USD",
        },
        raw_side="BUY",
        raw_open_close="OPEN",
        quantity=Decimal("1"),
        price=Decimal("200"),
        occurred_at=datetime(2026, 7, 25, 14, tzinfo=timezone.utc),
        source_timezone="America/New_York",
        currency="USD",
        normalized_fee=Decimal("1"),
        fee_currency="USD",
        execution_status="EXECUTED",
        normalized_payload_json={"ibExecID": f"EXEC-{suffix}"},
    )
    db.add(value)
    db.flush()
    return value


def sighting(
    db,
    source_binding: ImportSourceBinding,
    source_statement: SourceStatement,
    source_observation: ExternalSourceObservation,
    suffix: str,
) -> StatementExecutionSighting:
    value = StatementExecutionSighting(
        public_id=f"sighting-{source_binding.id}-{suffix}",
        binding_id=source_binding.id,
        user_id=source_binding.user_id,
        account_id=source_binding.account_id,
        statement_id=source_statement.id,
        observation_id=source_observation.id,
        external_source_event_id=source_observation.external_source_event_id,
        generation_order_key=source_statement.generation_order_key,
    )
    db.add(value)
    db.flush()
    return value


def test_binding_slots_are_lifetime_unique_per_account_and_external_identity(
    db,
    owner_graph,
):
    first, second, accounts = owner_graph
    binding(db, first, accounts[0], "U1234567")
    db.commit()

    with pytest.raises(IntegrityError):
        binding(db, first, accounts[1], "U1234567")
        db.commit()
    db.rollback()

    with pytest.raises(IntegrityError):
        binding(db, first, accounts[0], "U7654321")
        db.commit()
    db.rollback()

    other_owner = binding(db, second, accounts[2], "U1234567")
    db.commit()
    assert other_owner.id is not None


def test_observation_identity_and_same_binding_graph_are_enforced(
    db,
    owner_graph,
):
    first, _, accounts = owner_graph
    first_binding = binding(db, first, accounts[0], "U1111111")
    second_binding = binding(db, first, accounts[1], "U2222222")
    first_session = import_session(db, first, accounts[0], "first")
    first_statement = statement(db, first_binding, first_session, "first")
    first_observation = observation(db, first_binding, "one")
    second_observation = observation(db, second_binding, "two")
    db.commit()

    with pytest.raises(IntegrityError):
        observation(db, first_binding, "one")
        db.commit()
    db.rollback()

    distinct_payload = observation(
        db,
        first_binding,
        "one",
        fingerprint_suffix="changed",
    )
    db.commit()
    assert distinct_payload.id != first_observation.id

    with pytest.raises(IntegrityError):
        sighting(
            db,
            first_binding,
            first_statement,
            second_observation,
            "cross-binding",
        )
        db.commit()
    db.rollback()


def test_source_evidence_is_immutable_and_not_deletable(db, owner_graph):
    first, _, accounts = owner_graph
    source_binding = binding(db, first, accounts[0], "U3333333")
    source_observation = observation(db, source_binding, "immutable")
    db.commit()

    source_observation.price = Decimal("201")
    with pytest.raises(ValueError, match="immutable"):
        db.flush()
    db.rollback()

    source_observation = db.get(
        ExternalSourceObservation,
        source_observation.id,
    )
    db.delete(source_observation)
    with pytest.raises(ValueError, match="append-only"):
        db.flush()
    db.rollback()


def test_execution_application_and_tombstone_constraints(db, owner_graph):
    first, _, accounts = owner_graph
    first_binding = binding(db, first, accounts[0], "U4444444")
    second_binding = binding(db, first, accounts[1], "U5555555")
    first_session = import_session(db, first, accounts[0], "application")
    first_observation = observation(db, first_binding, "application")
    other_observation = observation(db, second_binding, "other")
    execution = ExternalExecution(
        public_id="external-execution-application",
        binding_id=first_binding.id,
        user_id=first.id,
        account_id=accounts[0].id,
        external_execution_id="EXEC-application",
        current_trade_observation_id=first_observation.id,
        disposition="ACTIVE",
    )
    db.add(execution)
    db.flush()
    first_application = ExternalTradeApplication(
        public_id="application-v1",
        binding_id=first_binding.id,
        user_id=first.id,
        account_id=accounts[0].id,
        external_execution_id=execution.id,
        source_observation_id=first_observation.id,
        application_version=1,
        is_active=True,
        derived_direction="LONG",
        derived_action="OPEN",
        pre_quantity=Decimal("0"),
        post_quantity=Decimal("1"),
        applied_import_session_id=first_session.id,
    )
    db.add(first_application)
    db.commit()

    second_application = ExternalTradeApplication(
        public_id="application-v2",
        binding_id=first_binding.id,
        user_id=first.id,
        account_id=accounts[0].id,
        external_execution_id=execution.id,
        source_observation_id=first_observation.id,
        application_version=2,
        is_active=True,
        derived_direction="LONG",
        derived_action="OPEN",
        pre_quantity=Decimal("0"),
        post_quantity=Decimal("1"),
        applied_import_session_id=first_session.id,
    )
    db.add(second_application)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    first_application = db.get(ExternalTradeApplication, first_application.id)
    first_application.is_active = False
    db.add(second_application)
    db.commit()
    assert db.get(ExternalTradeApplication, second_application.id).is_active

    execution = db.get(ExternalExecution, execution.id)
    execution.disposition = "ACCEPTED_TOMBSTONE"
    execution.canceled_by_observation_id = other_observation.id
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_case_episode_partial_uniqueness_and_immutable_evidence(
    db,
    owner_graph,
):
    first, _, accounts = owner_graph
    source_binding = binding(db, first, accounts[0], "U6666666")
    first_session = import_session(db, first, accounts[0], "case-one")
    second_session = import_session(db, first, accounts[0], "case-two")
    first_statement = statement(
        db,
        source_binding,
        first_session,
        "case-one",
    )
    second_statement = statement(
        db,
        source_binding,
        second_session,
        "case-two",
    )
    source_observation = observation(db, source_binding, "case")
    first_sighting = sighting(
        db,
        source_binding,
        first_statement,
        source_observation,
        "case-one",
    )
    second_sighting = sighting(
        db,
        source_binding,
        second_statement,
        source_observation,
        "case-two",
    )
    first_case = SourceReconciliationCase(
        public_id="source-case-one",
        binding_id=source_binding.id,
        user_id=first.id,
        account_id=accounts[0].id,
        conflict_observation_id=source_observation.id,
        trigger_sighting_id=first_sighting.id,
        case_kind="SOURCE_PAYLOAD_CONFLICT",
        state="OPEN",
        against_source_state_schema_version=1,
        against_source_state_hash=f"sha256:{'a' * 64}",
        against_source_state_snapshot_json={"revision": 0},
    )
    db.add(first_case)
    db.commit()

    second_case = SourceReconciliationCase(
        public_id="source-case-two",
        binding_id=source_binding.id,
        user_id=first.id,
        account_id=accounts[0].id,
        conflict_observation_id=source_observation.id,
        trigger_sighting_id=second_sighting.id,
        case_kind="SOURCE_PAYLOAD_CONFLICT",
        state="OPEN",
        against_source_state_schema_version=1,
        against_source_state_hash=f"sha256:{'a' * 64}",
        against_source_state_snapshot_json={"revision": 0},
    )
    db.add(second_case)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()

    first_case = db.get(SourceReconciliationCase, first_case.id)
    first_case.state = "RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY"
    first_case.resolved_at = datetime.now(timezone.utc)
    db.add(second_case)
    db.commit()

    evidence = SourceCaseEvidenceSighting(
        binding_id=source_binding.id,
        user_id=first.id,
        account_id=accounts[0].id,
        case_id=second_case.id,
        sighting_id=second_sighting.id,
    )
    db.add(evidence)
    db.commit()
    db.delete(evidence)
    with pytest.raises(ValueError, match="append-only"):
        db.flush()


def test_case_domain_reuses_episode_attaches_evidence_and_recomputes_health(
    db,
    owner_graph,
):
    first, _, accounts = owner_graph
    source_binding = binding(db, first, accounts[0], "UCASE001")
    first_session = import_session(db, first, accounts[0], "domain-one")
    second_session = import_session(db, first, accounts[0], "domain-two")
    first_statement = statement(
        db,
        source_binding,
        first_session,
        "domain-one",
    )
    second_statement = statement(
        db,
        source_binding,
        second_session,
        "domain-two",
    )
    conflict = observation(db, source_binding, "domain")
    first_sighting = sighting(
        db,
        source_binding,
        first_statement,
        conflict,
        "domain-one",
    )
    second_sighting = sighting(
        db,
        source_binding,
        second_statement,
        conflict,
        "domain-two",
    )
    snapshot = build_source_case_snapshot(
        db,
        binding=source_binding,
        conflict_observation=conflict,
        candidate_external_execution_ids=(),
    )

    created = create_or_attach_source_case(
        db,
        binding=source_binding,
        conflict_observation=conflict,
        trigger_sighting=first_sighting,
        case_kind="SOURCE_PAYLOAD_CONFLICT",
        snapshot=snapshot,
    )
    replay = create_or_attach_source_case(
        db,
        binding=source_binding,
        conflict_observation=conflict,
        trigger_sighting=first_sighting,
        case_kind="SOURCE_PAYLOAD_CONFLICT",
        snapshot=snapshot,
    )
    evidence = create_or_attach_source_case(
        db,
        binding=source_binding,
        conflict_observation=conflict,
        trigger_sighting=second_sighting,
        case_kind="SOURCE_PAYLOAD_CONFLICT",
        snapshot=snapshot,
    )
    db.flush()

    assert created.created
    assert replay.case.id == created.case.id
    assert not replay.created
    assert evidence.case.id == created.case.id
    assert evidence.evidence_attached
    assert (
        db.query(SourceCaseEvidenceSighting)
        .filter(SourceCaseEvidenceSighting.case_id == created.case.id)
        .count()
        == 1
    )
    assert source_binding.source_health == "RECONCILIATION_REQUIRED"

    created.case.state = "DIVERGED_REJECTED"
    assert recompute_source_health(db, binding=source_binding) == (
        "SOURCE_DIVERGED"
    )
    created.case.state = "RESOLVED_APPLIED"
    assert recompute_source_health(db, binding=source_binding) == "HEALTHY"


def test_terminal_episode_allows_new_trigger_and_later_authority_supersedes(
    db,
    owner_graph,
):
    first, _, accounts = owner_graph
    source_binding = binding(db, first, accounts[0], "UCASE002")
    first_session = import_session(db, first, accounts[0], "authority-a")
    later_session = import_session(db, first, accounts[0], "authority-z")
    first_statement = statement(
        db,
        source_binding,
        first_session,
        "authority-a",
    )
    later_statement = statement(
        db,
        source_binding,
        later_session,
        "authority-z",
    )
    conflict = observation(db, source_binding, "authority")
    first_sighting = sighting(
        db,
        source_binding,
        first_statement,
        conflict,
        "authority-a",
    )
    later_sighting = sighting(
        db,
        source_binding,
        later_statement,
        conflict,
        "authority-z",
    )
    snapshot = build_source_case_snapshot(
        db,
        binding=source_binding,
        conflict_observation=conflict,
    )
    first_episode = create_or_attach_source_case(
        db,
        binding=source_binding,
        conflict_observation=conflict,
        trigger_sighting=first_sighting,
        case_kind="CORRECTION",
        snapshot=snapshot,
    )
    assert supersede_source_case_with_later_sighting(
        db,
        binding=source_binding,
        case=first_episode.case,
        winning_sighting=later_sighting,
    )
    assert first_episode.case.state == (
        "RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY"
    )
    assert first_episode.case.winning_sighting_id == later_sighting.id
    assert source_binding.source_health == "HEALTHY"

    later_episode = create_or_attach_source_case(
        db,
        binding=source_binding,
        conflict_observation=conflict,
        trigger_sighting=later_sighting,
        case_kind="CORRECTION",
        snapshot=snapshot,
    )

    assert later_episode.created
    assert later_episode.case.id != first_episode.case.id
    assert not supersede_source_case_with_later_sighting(
        db,
        binding=source_binding,
        case=later_episode.case,
        winning_sighting=first_sighting,
    )
    assert source_binding.source_health == "RECONCILIATION_REQUIRED"

    unrelated_session = import_session(
        db,
        first,
        accounts[0],
        "authority-zz",
    )
    unrelated_statement = statement(
        db,
        source_binding,
        unrelated_session,
        "authority-zz",
    )
    unrelated = observation(db, source_binding, "unrelated-authority")
    unrelated_sighting = sighting(
        db,
        source_binding,
        unrelated_statement,
        unrelated,
        "unrelated-authority",
    )
    assert not supersede_source_case_with_later_sighting(
        db,
        binding=source_binding,
        case=later_episode.case,
        winning_sighting=unrelated_sighting,
    )
    assert later_episode.case.state == "OPEN"

    later_episode.case.case_kind = "TARGET_UNRESOLVED"
    assert not supersede_source_case_with_later_sighting(
        db,
        binding=source_binding,
        case=later_episode.case,
        winning_sighting=later_sighting,
    )


def test_case_snapshot_hash_is_stable_and_tracks_authority_application(
    db,
    owner_graph,
):
    first, _, accounts = owner_graph
    source_binding = binding(db, first, accounts[0], "UCASE003")
    source_session = import_session(db, first, accounts[0], "snapshot")
    current = observation(db, source_binding, "snapshot-current")
    conflict = observation(db, source_binding, "snapshot-conflict")
    execution = ExternalExecution(
        binding_id=source_binding.id,
        user_id=first.id,
        account_id=accounts[0].id,
        external_execution_id="EXEC-snapshot-current",
        current_trade_observation_id=current.id,
        disposition="ACTIVE",
    )
    db.add(execution)
    db.flush()
    application = ExternalTradeApplication(
        binding_id=source_binding.id,
        user_id=first.id,
        account_id=accounts[0].id,
        external_execution_id=execution.id,
        source_observation_id=current.id,
        application_version=1,
        is_active=True,
        derived_direction="LONG",
        derived_action="OPEN",
        pre_quantity=Decimal("0"),
        post_quantity=Decimal("1"),
        applied_import_session_id=source_session.id,
    )
    db.add(application)
    db.flush()

    first_snapshot = build_source_case_snapshot(
        db,
        binding=source_binding,
        conflict_observation=conflict,
        target_execution=execution,
        group_state={"append_boundary": "100|EXEC-snapshot-current"},
    )
    replay_snapshot = build_source_case_snapshot(
        db,
        binding=source_binding,
        conflict_observation=conflict,
        target_execution=execution,
        group_state={"append_boundary": "100|EXEC-snapshot-current"},
    )
    assert replay_snapshot.digest == first_snapshot.digest
    assert replay_snapshot.payload == first_snapshot.payload

    application.is_active = False
    application.superseded_at = datetime.now(timezone.utc)
    replacement = ExternalTradeApplication(
        binding_id=source_binding.id,
        user_id=first.id,
        account_id=accounts[0].id,
        external_execution_id=execution.id,
        source_observation_id=current.id,
        application_version=2,
        is_active=True,
        derived_direction="LONG",
        derived_action="ADD",
        pre_quantity=Decimal("1"),
        post_quantity=Decimal("2"),
        applied_import_session_id=source_session.id,
    )
    db.add(replacement)
    db.flush()

    changed_snapshot = build_source_case_snapshot(
        db,
        binding=source_binding,
        conflict_observation=conflict,
        target_execution=execution,
        group_state={"append_boundary": "100|EXEC-snapshot-current"},
    )
    assert changed_snapshot.digest != first_snapshot.digest
    assert (
        changed_snapshot.payload["authority_target"]["active_application"][
            "application_version"
        ]
        == 2
    )


def test_coverage_acceptance_requires_same_binding_statement(
    db,
    owner_graph,
):
    first, _, accounts = owner_graph
    first_binding = binding(db, first, accounts[0], "U7777777")
    second_binding = binding(db, first, accounts[1], "U8888888")
    first_session = import_session(db, first, accounts[0], "coverage-one")
    second_session = import_session(db, first, accounts[1], "coverage-two")
    second_statement = statement(
        db,
        second_binding,
        second_session,
        "coverage-two",
    )
    operation = idempotency(db, first, "coverage-confirm")
    db.commit()

    acceptance = StatementCoverageAcceptance(
        public_id="coverage-acceptance-cross-binding",
        binding_id=first_binding.id,
        user_id=first.id,
        account_id=accounts[0].id,
        statement_id=second_statement.id,
        import_session_id=first_session.id,
        operation_idempotency_id=operation.id,
        accepted_source_state_revision=1,
    )
    db.add(acceptance)
    with pytest.raises(IntegrityError):
        db.commit()


def test_alembic_installs_database_append_only_guards(tmp_path):
    database_path = tmp_path / "jrn013-guards.db"
    environment = os.environ.copy()
    environment["DATABASE_URL"] = f"sqlite:///{database_path}"
    environment["PYTHONPATH"] = str(REPO_ROOT / "backend")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "backend/alembic.ini",
            "upgrade",
            "head",
        ],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr

    with sqlite3.connect(database_path) as connection:
        source_tables = (
            "source_statements",
            "external_source_observations",
            "statement_execution_sightings",
            "statement_coverage_acceptances",
            "source_case_evidence_sightings",
        )
        expected_triggers = {
            f"trg_{table_name}_no_{operation}"
            for table_name in source_tables
            for operation in ("update", "delete")
        }
        installed_triggers = {
            row[0]
            for row in connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'trigger'
                  AND name LIKE 'trg_%_no_%'
                """
            )
        }
        assert expected_triggers <= installed_triggers
        connection.execute(
            """
            INSERT INTO external_source_observations (
                id, public_id, binding_id, user_id, account_id, event_kind,
                external_source_event_id, external_execution_id,
                fingerprint_version, source_payload_fingerprint,
                transaction_id, source_order_key, conid,
                instrument_identity_json, raw_side, raw_open_close,
                quantity, price, occurred_at, source_timezone, currency,
                normalized_fee, fee_currency, execution_status,
                normalized_payload_json
            ) VALUES (
                1, 'guard-observation', 1, 1, 1, 'TRADE',
                'EXEC-GUARD', 'EXEC-GUARD', 1,
                'sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa',
                'TX-GUARD', '1|EXEC-GUARD', '265598', '{}', 'BUY', 'OPEN',
                1, 100, '2026-07-25T14:00:00+00:00',
                'America/New_York', 'USD', 1, 'USD', 'EXECUTED', '{}'
            )
            """
        )
        connection.commit()
        with pytest.raises(
            sqlite3.IntegrityError,
            match="external_source_observations is append-only",
        ):
            connection.execute(
                """
                UPDATE external_source_observations
                SET price = 101
                WHERE id = 1
                """
            )
        connection.rollback()
        with pytest.raises(
            sqlite3.IntegrityError,
            match="external_source_observations is append-only",
        ):
            connection.execute(
                "DELETE FROM external_source_observations WHERE id = 1"
            )
