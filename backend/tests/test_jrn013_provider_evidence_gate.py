from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from app_config.ibkr_flex_provider_evidence import (
    REQUIRED_SEMANTICS,
    IbkrFlexProviderEvidenceManifest,
    IbkrProviderEvidenceError,
    require_verified_ibkr_flex_provider_contract,
    verify_provider_evidence,
)


def field_contract() -> dict:
    return {
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


def verified_payload(fixture_hash: str) -> dict:
    semantics = sorted(REQUIRED_SEMANTICS)
    return {
        "schema_version": 1,
        "adapter_kind": "IBKR_FLEX_XML_V1",
        "status": "VERIFIED",
        "query_template_id": "JOURNAL_FLEX_V1",
        "query_template_sha256": f"sha256:{'a' * 64}",
        "field_contract": field_contract(),
        "official_sources": [
            {
                "url": "https://www.interactivebrokers.com/example",
                "title": "IBKR Flex field reference",
                "retrieved_at": "2026-07-26",
                "semantics": semantics,
            }
        ],
        "fixtures": [
            {
                "relative_path": "statement.xml",
                "sha256": fixture_hash,
                "classification": "REDACTED_REAL",
                "redacted": True,
                "query_template_id": "JOURNAL_FLEX_V1",
                "semantics": semantics,
            }
        ],
        "unverified_reasons": [],
    }


def test_repository_manifest_fails_closed():
    with pytest.raises(IbkrProviderEvidenceError) as failure:
        require_verified_ibkr_flex_provider_contract()
    assert "No frozen IBKR Flex Query template" in str(failure.value)


def test_complete_official_and_real_fixture_evidence_can_verify(tmp_path):
    fixture = tmp_path / "statement.xml"
    fixture.write_bytes(b"<redacted-real-fixture />")
    fixture_hash = "sha256:" + hashlib.sha256(
        fixture.read_bytes()
    ).hexdigest()
    manifest = IbkrFlexProviderEvidenceManifest.model_validate(
        verified_payload(fixture_hash)
    )

    contract = verify_provider_evidence(manifest, fixture_root=tmp_path)

    assert contract.query_template_id == "JOURNAL_FLEX_V1"
    assert contract.field_contract.execution_id_field == "ibExecID"


def test_fixture_hash_and_semantic_gaps_fail_closed(tmp_path):
    fixture = tmp_path / "statement.xml"
    fixture.write_bytes(b"<changed />")
    payload = verified_payload(f"sha256:{'b' * 64}")
    payload["official_sources"][0]["semantics"] = ["BASIC_EXECUTION_FIELDS"]
    manifest = IbkrFlexProviderEvidenceManifest.model_validate(payload)

    with pytest.raises(IbkrProviderEvidenceError) as failure:
        verify_provider_evidence(manifest, fixture_root=tmp_path)

    assert "Fixture hash mismatch" in str(failure.value)
    assert "Official evidence missing semantics" in str(failure.value)


def test_non_ibkr_official_url_and_fixture_path_escape_are_rejected(tmp_path):
    outside = tmp_path.parent / "outside.xml"
    outside.write_bytes(b"<outside />")
    fixture_hash = "sha256:" + hashlib.sha256(
        outside.read_bytes()
    ).hexdigest()
    payload = verified_payload(fixture_hash)
    payload["official_sources"][0]["url"] = "https://example.com/fields"
    payload["fixtures"][0]["relative_path"] = "../outside.xml"
    manifest = IbkrFlexProviderEvidenceManifest.model_validate(payload)

    with pytest.raises(IbkrProviderEvidenceError) as failure:
        verify_provider_evidence(manifest, fixture_root=tmp_path)

    assert "hosted by IBKR" in str(failure.value)
    assert "escapes the evidence root" in str(failure.value)
