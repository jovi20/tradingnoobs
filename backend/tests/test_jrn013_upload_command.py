from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from io import BytesIO
import os
import tempfile

import pytest
from fastapi import UploadFile
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app_config.ibkr_flex_provider_evidence import (
    IbkrFlexFieldContract,
    VerifiedIbkrFlexProviderContract,
)
from database import Base, get_db
from main import app
from models import (
    ExternalSourceObservation,
    IdempotencyKey,
    ImportRow,
    ImportSession,
    ImportSourceBinding,
    SourceStatement,
    StatementExecutionSighting,
    TradingAccount,
    User,
)
from services.ibkr_flex_import_service import (
    IbkrFlexImportError,
    stage_and_upload_ibkr_flex_preview,
)
from services.generic_import_service import (
    cleanup_terminal_import_rows,
    expire_due_import_sessions,
)
from services.auth_service import get_current_user


EXTERNAL_ACCOUNT = "U1234567"


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
def provider_contract() -> VerifiedIbkrFlexProviderContract:
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
def owner_graph(db):
    owner = User(
        public_id="upload-command-owner",
        email="upload-command@example.com",
        email_normalized="upload-command@example.com",
        hashed_password="hash",
        timezone="UTC",
    )
    account = TradingAccount(
        public_id="upload-command-account",
        user=owner,
        name="IBKR",
        broker="IBKR",
        currency="USD",
        is_active=True,
        accounting_health="ACCOUNTING_HEALTHY",
        trade_source_state="CLEAN",
        hard_delete_eligible=True,
    )
    db.add_all([owner, account])
    db.commit()
    return owner, account


def statement_xml(*, malformed: bool = False) -> bytes:
    if malformed:
        return b"<FlexQueryResponse>"
    return (
        '<FlexQueryResponse><FlexStatements count="1">'
        f'<FlexStatement accountId="{EXTERNAL_ACCOUNT}" fromDate="20260701" '
        'toDate="20260725" whenGenerated="20260725;180000" '
        'accountInceptionDate="20260701"><Trades>'
        f'<Trade accountId="{EXTERNAL_ACCOUNT}" ibExecID="EXEC-1" '
        'transactionID="101" assetCategory="STK" conid="265598" '
        'symbol="AAPL" listingExchange="NASDAQ" currency="USD" '
        'buySell="BUY" quantity="2" tradePrice="200" '
        'dateTime="20260725;100000" openCloseIndicator="OPEN" '
        'tradeStatus="EXECUTED" ibCommission="-1.25" '
        'ibCommissionCurrency="USD" />'
        "</Trades></FlexStatement></FlexStatements></FlexQueryResponse>"
    ).encode("utf-8")


def upload_file(payload: bytes) -> UploadFile:
    return UploadFile(
        filename="statement.xml",
        file=BytesIO(payload),
        headers={"content-type": "application/xml"},
    )


def run_upload(
    db,
    *,
    owner,
    account,
    provider_contract,
    payload: bytes,
    key: str,
    temp_root,
    now: datetime,
):
    return asyncio.run(
        stage_and_upload_ibkr_flex_preview(
            db,
            user_id=owner.id,
            account_public_id=account.public_id,
            source_timezone="UTC",
            upload=upload_file(payload),
            idempotency_key=key,
            provider_contract=provider_contract,
            now=now,
            temp_root=temp_root,
        )
    )


def test_account_owner_is_checked_before_staging(
    db,
    owner_graph,
    provider_contract,
    tmp_path,
    monkeypatch,
):
    owner, _ = owner_graph
    other = User(
        public_id="prestage-other-user",
        email="prestage-other@example.com",
        email_normalized="prestage-other@example.com",
        hashed_password="hash",
        timezone="UTC",
    )
    other_account = TradingAccount(
        public_id="prestage-other-account",
        user=other,
        name="Other IBKR",
        broker="IBKR",
        currency="USD",
        is_active=True,
    )
    db.add_all([other, other_account])
    db.commit()
    staged = {"called": False}

    async def fail_if_staged(*args, **kwargs):
        del args, kwargs
        staged["called"] = True
        raise AssertionError("invalid account must be rejected before staging")

    monkeypatch.setattr(
        "services.ibkr_flex_import_service.stage_ibkr_flex_upload",
        fail_if_staged,
    )

    for account_public_id in ("missing-account", other_account.public_id):
        upload = upload_file(statement_xml())
        with pytest.raises(IbkrFlexImportError) as failure:
            asyncio.run(
                stage_and_upload_ibkr_flex_preview(
                    db,
                    user_id=owner.id,
                    account_public_id=account_public_id,
                    source_timezone="UTC",
                    upload=upload,
                    idempotency_key=f"prestage-{account_public_id}",
                    provider_contract=provider_contract,
                    temp_root=tmp_path,
                )
            )
        assert failure.value.code == "IMPORT_ACCOUNT_NOT_FOUND"
        assert failure.value.http_status == 404
        assert upload.file.closed

    assert staged["called"] is False
    assert db.query(ImportSession).count() == 0
    assert db.query(IdempotencyKey).count() == 0
    assert list(tmp_path.iterdir()) == []


def test_bootstrap_upload_persists_masked_replayable_preview_only(
    db,
    owner_graph,
    provider_contract,
    tmp_path,
):
    owner, account = owner_graph
    now = datetime(2026, 7, 26, tzinfo=timezone.utc)
    first = run_upload(
        db,
        owner=owner,
        account=account,
        provider_contract=provider_contract,
        payload=statement_xml(),
        key="bootstrap-upload-key",
        temp_root=tmp_path,
        now=now,
    )

    assert first.http_status == 201
    assert first.replayed is False
    assert first.body["status"] == "PREVIEW_READY"
    assert first.body["source_preview"]["mode"] == "BOOTSTRAP"
    assert first.body["source_preview"]["masked_external_account_ref"] == "****4567"
    assert EXTERNAL_ACCOUNT not in str(first.body)
    assert db.query(ImportSession).count() == 1
    assert db.query(ImportRow).count() == 1
    assert db.query(ImportSourceBinding).count() == 0
    assert db.query(SourceStatement).count() == 0
    assert db.query(ExternalSourceObservation).count() == 0
    assert account.hard_delete_eligible is False
    assert list(tmp_path.iterdir()) == []

    assert expire_due_import_sessions(
        db,
        now=now + timedelta(days=2),
    ) == 1
    db.commit()
    replay = run_upload(
        db,
        owner=owner,
        account=account,
        provider_contract=provider_contract,
        payload=statement_xml(),
        key="bootstrap-upload-key",
        temp_root=tmp_path,
        now=now + timedelta(days=2),
    )
    assert replay.replayed is True
    assert replay.body == first.body
    assert db.query(ImportSession).count() == 1
    assert db.query(ImportSession).one().status == "EXPIRED"
    assert list(tmp_path.iterdir()) == []


def test_same_key_with_different_file_hash_is_rejected(
    db,
    owner_graph,
    provider_contract,
    tmp_path,
):
    owner, account = owner_graph
    now = datetime(2026, 7, 26, tzinfo=timezone.utc)
    run_upload(
        db,
        owner=owner,
        account=account,
        provider_contract=provider_contract,
        payload=statement_xml(),
        key="collision-key",
        temp_root=tmp_path,
        now=now,
    )

    with pytest.raises(IbkrFlexImportError) as failure:
        run_upload(
            db,
            owner=owner,
            account=account,
            provider_contract=provider_contract,
            payload=statement_xml().replace(b'tradePrice="200"', b'tradePrice="201"'),
            key="collision-key",
            temp_root=tmp_path,
            now=now,
        )
    assert failure.value.code == "IDEMPOTENCY_KEY_REUSED"
    assert failure.value.http_status == 409
    db.rollback()
    assert db.query(ImportSession).count() == 1
    assert list(tmp_path.iterdir()) == []


def test_existing_binding_upload_uses_bound_preview_and_persists_provenance(
    db,
    owner_graph,
    provider_contract,
    tmp_path,
):
    owner, account = owner_graph
    account.trade_source_state = "SOURCE_BOUND"
    binding = ImportSourceBinding(
        public_id="upload-command-binding",
        user_id=owner.id,
        account_id=account.id,
        adapter_kind="IBKR_FLEX_XML_V1",
        normalized_external_account_ref=EXTERNAL_ACCOUNT,
        masked_external_account_ref="****4567",
        source_timezone="UTC",
        source_health="HEALTHY",
        source_completeness="CURRENT",
        accepted_coverage_start=None,
        accepted_coverage_through_exclusive=None,
        source_state_revision=1,
    )
    db.add(binding)
    db.commit()

    result = run_upload(
        db,
        owner=owner,
        account=account,
        provider_contract=provider_contract,
        payload=statement_xml(),
        key="bound-upload-key",
        temp_root=tmp_path,
        now=datetime(2026, 7, 26, tzinfo=timezone.utc),
    )

    assert result.http_status == 201
    assert result.body["status"] == "CONFLICTED"
    source = result.body["source_preview"]
    assert source["mode"] == "BOUND"
    assert source["binding_public_id"] == binding.public_id
    assert source["pending_statement_count"] == 1
    assert source["pending_execution_count"] == 1
    assert EXTERNAL_ACCOUNT not in str(result.body)
    assert db.query(SourceStatement).count() == 1
    assert db.query(ExternalSourceObservation).count() == 1
    assert db.query(StatementExecutionSighting).count() == 1
    assert db.query(ImportSourceBinding).count() == 1
    assert list(tmp_path.iterdir()) == []

    retention_boundary = datetime(2026, 8, 25, tzinfo=timezone.utc)
    assert cleanup_terminal_import_rows(
        db,
        now=retention_boundary - timedelta(microseconds=1),
    ) == 0
    db.commit()
    assert db.query(ImportRow).count() == 1
    assert db.query(ImportSession).one().rows_cleaned_at is None

    assert cleanup_terminal_import_rows(
        db,
        now=retention_boundary,
    ) == 1
    db.commit()
    assert db.query(ImportRow).count() == 0
    assert db.query(ImportSession).count() == 1
    assert db.query(SourceStatement).count() == 1
    assert db.query(ExternalSourceObservation).count() == 1
    assert db.query(StatementExecutionSighting).count() == 1
    assert db.query(ImportSourceBinding).count() == 1
    assert db.query(IdempotencyKey).count() == 1

    restarted_db = sessionmaker(bind=db.get_bind(), autoflush=False)()
    try:
        restarted_owner = restarted_db.get(User, owner.id)
        restarted_account = restarted_db.get(TradingAccount, account.id)
        replay = run_upload(
            restarted_db,
            owner=restarted_owner,
            account=restarted_account,
            provider_contract=provider_contract,
            payload=statement_xml(),
            key="bound-upload-key",
            temp_root=tmp_path,
            now=datetime(2026, 9, 1, tzinfo=timezone.utc),
        )
        assert replay.replayed is True
        assert replay.body == result.body
        assert restarted_db.query(ImportRow).count() == 0
    finally:
        restarted_db.close()


def test_parse_failure_is_terminal_and_permanently_replayable(
    db,
    owner_graph,
    provider_contract,
    tmp_path,
):
    owner, account = owner_graph
    now = datetime(2026, 7, 26, tzinfo=timezone.utc)
    first = run_upload(
        db,
        owner=owner,
        account=account,
        provider_contract=provider_contract,
        payload=statement_xml(malformed=True),
        key="malformed-key",
        temp_root=tmp_path,
        now=now,
    )

    assert first.http_status == 422
    assert first.body["status"] == "FAILED"
    assert first.body["error"]["code"] == "INVALID_IBKR_XML"
    session = db.query(ImportSession).one()
    assert session.terminal_at.replace(tzinfo=timezone.utc) == now
    assert db.query(ImportRow).count() == 0

    replay = run_upload(
        db,
        owner=owner,
        account=account,
        provider_contract=provider_contract,
        payload=statement_xml(malformed=True),
        key="malformed-key",
        temp_root=tmp_path,
        now=now + timedelta(days=30),
    )
    assert replay.replayed is True
    assert replay.http_status == 422
    assert replay.body == first.body
    assert db.query(IdempotencyKey).one().expires_at is None
    assert list(tmp_path.iterdir()) == []


def test_unexpected_upload_failure_closes_handle_and_removes_staged_file(
    db,
    owner_graph,
    provider_contract,
    tmp_path,
    monkeypatch,
):
    owner, account = owner_graph
    upload = upload_file(statement_xml())
    monkeypatch.setattr(
        "services.ibkr_flex_import_service.upload_ibkr_flex_preview",
        lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    with pytest.raises(RuntimeError, match="boom"):
        asyncio.run(
            stage_and_upload_ibkr_flex_preview(
                db,
                user_id=owner.id,
                account_public_id=account.public_id,
                source_timezone="UTC",
                upload=upload,
                idempotency_key="unexpected-failure",
                provider_contract=provider_contract,
                temp_root=tmp_path,
            )
        )

    assert upload.file.closed
    assert list(tmp_path.iterdir()) == []


def test_public_route_fails_closed_before_staging_without_provider_evidence(
    db,
    owner_graph,
    tmp_path,
    monkeypatch,
):
    owner, account = owner_graph
    monkeypatch.setenv("TRADINGNOOBS_IMPORT_TMP_DIR", str(tmp_path))

    def override_get_db():
        yield db

    async def override_get_current_user():
        return owner

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/positions/import/ibkr-flex/upload",
                headers={"Idempotency-Key": "disabled-upload"},
                data={
                    "account_id": account.public_id,
                    "source_timezone": "UTC",
                },
                files={
                    "file": (
                        "statement.xml",
                        statement_xml(),
                        "application/xml",
                    )
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "FEATURE_DISABLED"
    assert db.query(ImportSession).count() == 0
    assert list(tmp_path.iterdir()) == []


def test_verified_public_route_persists_replayable_preview_and_denies_owner_swap(
    db,
    owner_graph,
    provider_contract,
    tmp_path,
    monkeypatch,
):
    owner, account = owner_graph
    other = User(
        public_id="upload-command-other",
        email="upload-command-other@example.com",
        email_normalized="upload-command-other@example.com",
        hashed_password="hash",
        timezone="UTC",
    )
    db.add(other)
    db.commit()
    current_user = {"value": owner}
    monkeypatch.setenv("TRADINGNOOBS_IMPORT_TMP_DIR", str(tmp_path))
    monkeypatch.setattr(
        "routers.import_sessions.require_verified_ibkr_flex_provider_contract",
        lambda: provider_contract,
    )

    def override_get_db():
        yield db

    async def override_get_current_user():
        return current_user["value"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_get_current_user
    try:
        with TestClient(app) as client:
            uploaded = client.post(
                "/api/positions/import/ibkr-flex/upload",
                headers={"Idempotency-Key": "verified-upload"},
                data={
                    "account_id": account.public_id,
                    "source_timezone": "UTC",
                },
                files={
                    "file": (
                        "statement.xml",
                        statement_xml(),
                        "application/xml",
                    )
                },
            )
            assert uploaded.status_code == 201, uploaded.text
            payload = uploaded.json()
            assert payload["adapter_kind"] == "IBKR_FLEX_XML_V1"
            assert payload["file_format"] == "XML"
            assert payload["status"] == "PREVIEW_READY"
            assert payload["confirm_available"] is False
            assert payload["source_preview"]["mode"] == "BOOTSTRAP"
            assert EXTERNAL_ACCOUNT not in uploaded.text

            reloaded = client.get(
                "/api/positions/import/sessions/"
                + payload["session_public_id"]
            )
            assert reloaded.status_code == 200, reloaded.text
            reloaded_payload = reloaded.json()
            assert reloaded_payload["adapter_kind"] == "IBKR_FLEX_XML_V1"
            assert reloaded_payload["file_format"] == "XML"
            assert reloaded_payload["confirm_available"] is False
            assert len(reloaded_payload["rows"]) == 1
            assert EXTERNAL_ACCOUNT not in reloaded.text

            session = (
                db.query(ImportSession)
                .filter(
                    ImportSession.public_id
                    == payload["session_public_id"]
                )
                .one()
            )
            session.status = "CONFLICTED"
            session.error_code = "SOURCE_RECONCILIATION_REQUIRED"
            session.error_message = "Synthetic persisted conflict"
            db.commit()
            conflicted = client.get(
                "/api/positions/import/sessions/"
                + payload["session_public_id"]
            )
            assert conflicted.status_code == 200, conflicted.text
            assert conflicted.json()["status"] == "CONFLICTED"
            assert len(conflicted.json()["rows"]) == 1

            current_user["value"] = other
            denied = client.get(
                "/api/positions/import/sessions/"
                + payload["session_public_id"]
            )
            assert denied.status_code == 404
    finally:
        app.dependency_overrides.clear()

    assert list(tmp_path.iterdir()) == []
