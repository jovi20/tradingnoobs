from __future__ import annotations

import json
import os
import stat
from pathlib import Path
import sys

from lxml import etree
import pytest

from app_config.ibkr_flex_evidence_redaction import (
    IbkrEvidenceRedactionError,
    redact_ibkr_flex_statements,
)
from app_config.ibkr_flex_provider_evidence import IbkrFlexFieldContract
from scripts.redact_ibkr_flex_evidence import main as redaction_main


def field_contract() -> IbkrFlexFieldContract:
    return IbkrFlexFieldContract.model_validate(
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
            "quantity_sign_semantics": "POSITIVE_MAGNITUDE",
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
            "generation_tie_policy": "SAME_MARKER_DIFFERENT_FILE_CONFLICT",
            "execution_time_format": "%Y%m%d;%H%M%S",
            "execution_time_semantics": "SOURCE_TIMEZONE_NAIVE",
            "event_kind_source": "ELEMENT_NAME",
            "correction_element": "TradeCorrection",
            "cancel_bust_element": "TradeCancel",
            "change_identity_semantics": "DISTINCT_EVENT_AND_TARGET",
            "change_event_id_field": "sourceEventID",
            "affected_execution_id_field": "affectedIBExecID",
            "account_inception_source": "STATEMENT_ATTRIBUTE",
            "account_inception_date_field": "accountInceptionDate",
            "open_positions_element": "OpenPositions",
            "open_position_element": "OpenPosition",
            "open_positions_snapshot_date_source": "CONTAINER_ATTRIBUTE",
            "open_positions_snapshot_date_field": "snapshotDate",
            "open_position_quantity_field": "position",
        }
    )


def statement_xml(event: str, *, generation: str) -> str:
    return f"""\
<FlexQueryResponse responseAccount="PRIVATE">
  <!-- PRIVATE COMMENT -->
  <FlexStatements>
    <FlexStatement
      accountId="U1234567"
      accountName="Jane Doe"
      fromDate="20260701"
      toDate="20260731"
      whenGenerated="{generation}"
      accountInceptionDate="20200101"
    >
      PRIVATE TEXT
      <Trades>{event}</Trades>
      <PrivateSection><SecretName>Jane Doe</SecretName></PrivateSection>
    </FlexStatement>
  </FlexStatements>
</FlexQueryResponse>
"""


def trade_event() -> str:
    return """\
<Trade accountId="U1234567" ibExecID="EXEC-PRIVATE-1"
 transactionID="20" assetCategory="STK" conid="265598" symbol="AAPL"
 listingExchange="NASDAQ" currency="USD" buySell="BUY" quantity="2"
 tradePrice="200.25" dateTime="20260701;093000"
 openCloseIndicator="OPEN" tradeStatus="EXECUTED"
 ibCommission="-1.25" ibCommissionCurrency="USD" />
"""


def correction_event(*, source_id: str = "CORR-PRIVATE-1") -> str:
    return f"""\
<TradeCorrection accountId="U1234567" sourceEventID="{source_id}"
 affectedIBExecID="EXEC-PRIVATE-1" transactionID="10"
 assetCategory="STK" conid="265598" symbol="AAPL"
 listingExchange="NASDAQ" currency="USD" buySell="BUY" quantity="2"
 tradePrice="201.25" dateTime="20260731;160000"
 openCloseIndicator="OPEN" tradeStatus="CORRECTED"
 ibCommission="-1.25" ibCommissionCurrency="USD" />
"""


def parse(path: Path) -> etree._Element:
    return etree.fromstring(path.read_bytes())


def test_redacts_cross_statement_identity_and_purges_free_form_data(tmp_path):
    first = tmp_path / "private-account-first.xml"
    first.write_text(
        statement_xml(trade_event(), generation="20260801;010000"),
        encoding="utf-8",
    )
    second = tmp_path / "private-account-second.xml"
    second.write_text(
        statement_xml(
            correction_event(),
            generation="20260802;010000",
        ),
        encoding="utf-8",
    )
    output = tmp_path / "redacted"

    report = redact_ibkr_flex_statements(
        (first, second),
        contract=field_contract(),
        output_dir=output,
    )

    payload = b"".join(
        (output / name).read_bytes()
        for name in (
            "statement-001.redacted.xml",
            "statement-002.redacted.xml",
            "redaction-report.json",
        )
    )
    for private_value in (
        b"U1234567",
        b"EXEC-PRIVATE-1",
        b"CORR-PRIVATE-1",
        b"265598",
        b"AAPL",
        b"Jane Doe",
        b"PRIVATE",
        b"private-account",
    ):
        assert private_value not in payload

    first_root = parse(output / "statement-001.redacted.xml")
    second_root = parse(output / "statement-002.redacted.xml")
    trade = first_root.find(".//Trade")
    correction = second_root.find(".//TradeCorrection")
    assert trade is not None
    assert correction is not None
    assert (
        correction.attrib["affectedIBExecID"]
        == trade.attrib["ibExecID"]
    )
    assert (
        correction.attrib["sourceEventID"]
        != correction.attrib["affectedIBExecID"]
    )
    assert trade.attrib["transactionID"] == "100002"
    assert correction.attrib["transactionID"] == "100001"
    assert trade.attrib["dateTime"] == "20260701;093000"
    assert correction.attrib["dateTime"] == "20260731;160000"
    assert trade.attrib["ibCommission"] == "-1.25"
    assert first_root.tag == "FlexStatement"
    assert first_root.attrib["accountId"] == "REDACTED-ACCOUNT-0001"
    assert first_root.text is None
    assert first_root.find(".//PrivateSection") is None

    assert report["status"] == "NOT_PROVIDER_VERIFICATION"
    assert report["fixture_count"] == 2
    assert report["fixtures"][0]["human_review_required"] is True
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert all(
        stat.S_IMODE(path.stat().st_mode) == 0o600
        for path in output.iterdir()
    )


def test_same_id_change_contract_preserves_same_id_linkage(tmp_path):
    contract_payload = field_contract().model_dump()
    contract_payload.update(
        {
            "change_identity_semantics": "EVENT_ID_IS_TARGET",
            "affected_execution_id_field": None,
        }
    )
    contract = IbkrFlexFieldContract.model_validate(contract_payload)
    trade_path = tmp_path / "trade.xml"
    trade_path.write_text(
        statement_xml(trade_event(), generation="20260801;010000"),
        encoding="utf-8",
    )
    change_path = tmp_path / "change.xml"
    same_id_change = correction_event(
        source_id="EXEC-PRIVATE-1"
    ).replace(' affectedIBExecID="EXEC-PRIVATE-1"', "")
    change_path.write_text(
        statement_xml(same_id_change, generation="20260802;010000"),
        encoding="utf-8",
    )
    output = tmp_path / "redacted"

    redact_ibkr_flex_statements(
        (trade_path, change_path),
        contract=contract,
        output_dir=output,
    )

    trade = parse(output / "statement-001.redacted.xml").find(".//Trade")
    correction = parse(
        output / "statement-002.redacted.xml"
    ).find(".//TradeCorrection")
    assert trade is not None
    assert correction is not None
    assert correction.attrib["sourceEventID"] == trade.attrib["ibExecID"]
    assert "affectedIBExecID" not in correction.attrib


@pytest.mark.parametrize(
    "unsafe_xml",
    (
        """\
<!DOCTYPE FlexQueryResponse [<!ENTITY leak "PRIVATE">]>
<FlexQueryResponse><FlexStatement>&leak;</FlexStatement></FlexQueryResponse>
""",
        """\
<FlexQueryResponse xmlns:xi="http://www.w3.org/2001/XInclude">
  <FlexStatement><xi:include href="private.xml" /></FlexStatement>
</FlexQueryResponse>
""",
    ),
)
def test_unsafe_xml_is_rejected_without_creating_output(
    tmp_path,
    unsafe_xml,
):
    source = tmp_path / "unsafe.xml"
    source.write_text(unsafe_xml, encoding="utf-8")
    output = tmp_path / "redacted"

    with pytest.raises(IbkrEvidenceRedactionError):
        redact_ibkr_flex_statements(
            (source,),
            contract=field_contract(),
            output_dir=output,
        )

    assert not output.exists()


def test_namespaced_xml_is_rejected_without_creating_output(tmp_path):
    source = tmp_path / "namespaced.xml"
    source.write_text(
        """\
<FlexQueryResponse xmlns:private="https://private.example/account">
  <FlexStatement><private:Trades /></FlexStatement>
</FlexQueryResponse>
""",
        encoding="utf-8",
    )
    output = tmp_path / "redacted"

    with pytest.raises(
        IbkrEvidenceRedactionError,
        match="must not contain XML namespaces",
    ):
        redact_ibkr_flex_statements(
            (source,),
            contract=field_contract(),
            output_dir=output,
        )

    assert not output.exists()


def test_source_and_output_parent_symlinks_are_rejected(tmp_path):
    real_source = tmp_path / "statement.xml"
    real_source.write_text(
        statement_xml(trade_event(), generation="20260801;010000"),
        encoding="utf-8",
    )
    linked_source = tmp_path / "linked.xml"
    linked_source.symlink_to(real_source)

    with pytest.raises(
        IbkrEvidenceRedactionError,
        match="must not be a symbolic link",
    ):
        redact_ibkr_flex_statements(
            (linked_source,),
            contract=field_contract(),
            output_dir=tmp_path / "redacted-source",
        )

    real_parent = tmp_path / "real-parent"
    real_parent.mkdir()
    linked_parent = tmp_path / "linked-parent"
    linked_parent.symlink_to(real_parent, target_is_directory=True)
    with pytest.raises(
        IbkrEvidenceRedactionError,
        match="parent must not be a symbolic link",
    ):
        redact_ibkr_flex_statements(
            (real_source,),
            contract=field_contract(),
            output_dir=linked_parent / "redacted-output",
        )


def test_partial_output_is_removed_when_a_write_fails(
    tmp_path,
    monkeypatch,
):
    source = tmp_path / "statement.xml"
    source.write_text(
        statement_xml(trade_event(), generation="20260801;010000"),
        encoding="utf-8",
    )
    output = tmp_path / "redacted"
    real_open = os.open
    output_write_count = 0

    def failing_open(path, flags, mode=0o777):
        nonlocal output_write_count
        if flags & os.O_CREAT:
            output_write_count += 1
        if output_write_count == 2:
            raise OSError("simulated private file write failure")
        return real_open(path, flags, mode)

    monkeypatch.setattr(
        "app_config.ibkr_flex_evidence_redaction.os.open",
        failing_open,
    )

    with pytest.raises(OSError, match="simulated"):
        redact_ibkr_flex_statements(
            (source,),
            contract=field_contract(),
            output_dir=output,
        )

    assert not output.exists()


def test_report_is_machine_readable_but_cannot_claim_verification(tmp_path):
    source = tmp_path / "statement.xml"
    source.write_text(
        statement_xml(trade_event(), generation="20260801;010000"),
        encoding="utf-8",
    )
    output = tmp_path / "redacted"

    redact_ibkr_flex_statements(
        (source,),
        contract=field_contract(),
        output_dir=output,
    )

    report = json.loads(
        (output / "redaction-report.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "NOT_PROVIDER_VERIFICATION"
    assert "query_template_id" not in report
    assert "VERIFIED" not in json.dumps(report)

    with pytest.raises(
        IbkrEvidenceRedactionError,
        match="must not already exist",
    ):
        redact_ibkr_flex_statements(
            (source,),
            contract=field_contract(),
            output_dir=output,
        )


def test_ambiguous_sensitive_field_roles_fail_closed(tmp_path):
    payload = field_contract().model_dump()
    payload["symbol_field"] = payload["conid_field"]
    contract = IbkrFlexFieldContract.model_validate(payload)
    source = tmp_path / "statement.xml"
    source.write_text(
        statement_xml(trade_event(), generation="20260801;010000"),
        encoding="utf-8",
    )
    output = tmp_path / "redacted"

    with pytest.raises(
        IbkrEvidenceRedactionError,
        match="Sensitive field roles must be distinct",
    ):
        redact_ibkr_flex_statements(
            (source,),
            contract=contract,
            output_dir=output,
        )

    assert not output.exists()


def test_cli_accepts_a_manifest_shaped_contract_file(
    tmp_path,
    monkeypatch,
    capsys,
):
    contract_path = tmp_path / "draft-manifest.json"
    contract_path.write_text(
        json.dumps({"field_contract": field_contract().model_dump()}),
        encoding="utf-8",
    )
    source = tmp_path / "statement.xml"
    source.write_text(
        statement_xml(trade_event(), generation="20260801;010000"),
        encoding="utf-8",
    )
    output = tmp_path / "redacted"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "redact_ibkr_flex_evidence.py",
            "--field-contract",
            str(contract_path),
            "--output-dir",
            str(output),
            str(source),
        ],
    )

    assert redaction_main() == 0
    assert "human privacy and provider-contract review remain required" in (
        capsys.readouterr().out
    )
    assert (output / "statement-001.redacted.xml").is_file()
