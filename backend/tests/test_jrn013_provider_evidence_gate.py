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
        "account_inception_date_field": "accountInceptionDate",
        "open_positions_element": "OpenPositions",
        "open_position_element": "OpenPosition",
        "open_positions_snapshot_date_field": "snapshotDate",
        "open_position_quantity_field": "position",
    }


def statement_xml(*, generation: str, to_date: str) -> bytes:
    return f"""
<FlexQueryResponse>
  <FlexStatements>
    <FlexStatement
      accountId="REDACTED"
      fromDate="20260701"
      toDate="{to_date}"
      whenGenerated="{generation}"
      accountInceptionDate="20200101"
    >
      <Trades>
        <Trade
          ibExecID="REDACTED-EXEC-1"
          transactionID="100"
          assetCategory="STK"
          conid="REDACTED-CONID"
          symbol="REDACTED"
          listingExchange="NASDAQ"
          currency="USD"
          buySell="BUY"
          quantity="1"
          tradePrice="100"
          dateTime="20260701;093000"
          openCloseIndicator="O"
          tradeStatus="EXECUTED"
          ibCommission="-1"
          ibCommissionCurrency="USD"
        />
        <TradeCorrection
          sourceEventID="REDACTED-CORRECTION-1"
          affectedIBExecID="REDACTED-EXEC-1"
        />
      </Trades>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>
""".strip().encode("utf-8")


def verified_payload(
    first_fixture_hash: str,
    second_fixture_hash: str,
    template_hash: str,
) -> dict:
    semantics = sorted(REQUIRED_SEMANTICS)
    return {
        "schema_version": 1,
        "adapter_kind": "IBKR_FLEX_XML_V1",
        "status": "VERIFIED",
        "query_template_id": "JOURNAL_FLEX_V1",
        "query_template_relative_path": "query-template.json",
        "query_template_sha256": template_hash,
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
                "relative_path": "statement-1.xml",
                "sha256": first_fixture_hash,
                "classification": "REDACTED_REAL",
                "redacted": True,
                "query_template_id": "JOURNAL_FLEX_V1",
                "semantics": semantics,
            },
            {
                "relative_path": "statement-2.xml",
                "sha256": second_fixture_hash,
                "classification": "REDACTED_REAL",
                "redacted": True,
                "query_template_id": "JOURNAL_FLEX_V1",
                "semantics": ["GENERATION_ORDERING"],
            }
        ],
        "unverified_reasons": [],
    }


def test_repository_manifest_fails_closed():
    with pytest.raises(IbkrProviderEvidenceError) as failure:
        require_verified_ibkr_flex_provider_contract()
    assert "No frozen IBKR Flex Query template" in str(failure.value)


def test_complete_official_and_real_fixture_evidence_can_verify(tmp_path):
    template = tmp_path / "query-template.json"
    template.write_bytes(b'{"query":"JOURNAL_FLEX_V1"}')
    first = tmp_path / "statement-1.xml"
    first.write_bytes(
        statement_xml(generation="20260702;120000", to_date="20260701")
    )
    second = tmp_path / "statement-2.xml"
    second.write_bytes(
        statement_xml(generation="20260703;120000", to_date="20260702")
    )
    hashes = [
        "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        for path in (first, second, template)
    ]
    manifest = IbkrFlexProviderEvidenceManifest.model_validate(
        verified_payload(*hashes)
    )

    contract = verify_provider_evidence(manifest, fixture_root=tmp_path)

    assert contract.query_template_id == "JOURNAL_FLEX_V1"
    assert contract.field_contract.execution_id_field == "ibExecID"


def test_fixture_hash_and_semantic_gaps_fail_closed(tmp_path):
    template = tmp_path / "query-template.json"
    template.write_bytes(b"{}")
    first = tmp_path / "statement-1.xml"
    first.write_bytes(b"<changed />")
    second = tmp_path / "statement-2.xml"
    second.write_bytes(
        statement_xml(generation="20260703;120000", to_date="20260702")
    )
    payload = verified_payload(
        f"sha256:{'b' * 64}",
        "sha256:" + hashlib.sha256(second.read_bytes()).hexdigest(),
        "sha256:" + hashlib.sha256(template.read_bytes()).hexdigest(),
    )
    payload["official_sources"][0]["semantics"] = ["BASIC_EXECUTION_FIELDS"]
    manifest = IbkrFlexProviderEvidenceManifest.model_validate(payload)

    with pytest.raises(IbkrProviderEvidenceError) as failure:
        verify_provider_evidence(manifest, fixture_root=tmp_path)

    assert "Fixture hash mismatch" in str(failure.value)
    assert "Official evidence missing semantics" in str(failure.value)


def test_non_ibkr_official_url_and_fixture_path_escape_are_rejected(tmp_path):
    outside = tmp_path.parent / "outside.xml"
    outside.write_bytes(b"<outside />")
    template = tmp_path / "query-template.json"
    template.write_bytes(b"{}")
    second = tmp_path / "statement-2.xml"
    second.write_bytes(
        statement_xml(generation="20260703;120000", to_date="20260702")
    )
    payload = verified_payload(
        "sha256:" + hashlib.sha256(outside.read_bytes()).hexdigest(),
        "sha256:" + hashlib.sha256(second.read_bytes()).hexdigest(),
        "sha256:" + hashlib.sha256(template.read_bytes()).hexdigest(),
    )
    payload["official_sources"][0]["url"] = "https://example.com/fields"
    payload["fixtures"][0]["relative_path"] = "../outside.xml"
    manifest = IbkrFlexProviderEvidenceManifest.model_validate(payload)

    with pytest.raises(IbkrProviderEvidenceError) as failure:
        verify_provider_evidence(manifest, fixture_root=tmp_path)

    assert "hosted by IBKR" in str(failure.value)
    assert "escapes the evidence root" in str(failure.value)


def test_semantic_labels_cannot_verify_an_empty_xml_fixture(tmp_path):
    template = tmp_path / "query-template.json"
    template.write_bytes(b"{}")
    first = tmp_path / "statement-1.xml"
    first.write_bytes(b"<redacted-real-fixture />")
    second = tmp_path / "statement-2.xml"
    second.write_bytes(b"<redacted-real-fixture />")
    payload = verified_payload(
        "sha256:" + hashlib.sha256(first.read_bytes()).hexdigest(),
        "sha256:" + hashlib.sha256(second.read_bytes()).hexdigest(),
        "sha256:" + hashlib.sha256(template.read_bytes()).hexdigest(),
    )
    manifest = IbkrFlexProviderEvidenceManifest.model_validate(payload)

    with pytest.raises(IbkrProviderEvidenceError) as failure:
        verify_provider_evidence(manifest, fixture_root=tmp_path)

    assert "exactly one FlexStatement" in str(failure.value)
