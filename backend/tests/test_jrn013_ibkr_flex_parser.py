from __future__ import annotations

from pathlib import Path

import pytest

from app_config.ibkr_flex_provider_evidence import (
    IbkrFlexFieldContract,
    VerifiedIbkrFlexProviderContract,
)
from services.ibkr_flex_parser import (
    IbkrFlexParseError,
    MAX_ATTRIBUTES_PER_NODE,
    MAX_EXECUTIONS,
    MAX_XML_NODES,
    parse_ibkr_flex_xml,
)


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


def trade(
    *,
    execution_id: str = "EXEC-1",
    transaction_id: str = "101",
    account_id: str = "U1234567",
    date_time: str = "20260725;100000",
) -> str:
    return (
        '<Trade accountId="{account_id}" ibExecID="{execution_id}" '
        'transactionID="{transaction_id}" assetCategory="STK" '
        'conid="265598" symbol="AAPL" listingExchange="NASDAQ" '
        'currency="USD" buySell="BUY" quantity="2" tradePrice="200" '
        'dateTime="{date_time}" openCloseIndicator="OPEN" '
        'tradeStatus="EXECUTED" ibCommission="-1.25" '
        'ibCommissionCurrency="USD" />'
    ).format(
        account_id=account_id,
        execution_id=execution_id,
        transaction_id=transaction_id,
        date_time=date_time,
    )


def document(
    events: str,
    *,
    generation: str = "20260725;180000",
    account_id: str = "U1234567",
    statement_attributes: str = "",
    statement_sections: str = "",
) -> str:
    return (
        '<FlexQueryResponse><FlexStatements count="1">'
        '<FlexStatement accountId="{account_id}" fromDate="20260701" '
        'toDate="20260725" whenGenerated="{generation}"'
        '{statement_attributes}>'
        "<Trades>{events}</Trades>"
        "{statement_sections}"
        "</FlexStatement></FlexStatements></FlexQueryResponse>"
    ).format(
        account_id=account_id,
        generation=generation,
        events=events,
        statement_attributes=statement_attributes,
        statement_sections=statement_sections,
    )


def write_xml(tmp_path: Path, content: str, name: str = "statement.xml") -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def test_parses_one_statement_and_stable_execution_identity(
    tmp_path,
    provider_contract,
):
    parsed = parse_ibkr_flex_xml(
        write_xml(tmp_path, document(trade())),
        source_timezone="America/New_York",
        provider_contract=provider_contract,
    )

    assert parsed.normalized_external_account_ref == "U1234567"
    assert parsed.masked_external_account_ref == "****4567"
    assert parsed.coverage_start.isoformat() == "2026-07-01"
    assert parsed.coverage_end_exclusive.isoformat() == "2026-07-26"
    assert len(parsed.events) == 1
    event = parsed.events[0]
    assert event.external_source_event_id == "EXEC-1"
    assert event.external_execution_id == "EXEC-1"
    assert event.transaction_id == "101"
    assert str(event.normalized_fee) == "1.25"
    assert event.occurred_at_utc.isoformat() == "2026-07-25T14:00:00+00:00"


def test_fingerprint_excludes_statement_generation_and_file_provenance(
    tmp_path,
    provider_contract,
):
    first = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(trade(), generation="20260725;180000"),
            "first.xml",
        ),
        source_timezone="America/New_York",
        provider_contract=provider_contract,
    )
    second = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(trade(), generation="20260726;180000"),
            "second.xml",
        ),
        source_timezone="America/New_York",
        provider_contract=provider_contract,
    )

    assert (
        first.events[0].source_payload_fingerprint
        == second.events[0].source_payload_fingerprint
    )
    assert first.generation_order_key != second.generation_order_key


@pytest.mark.parametrize(
    ("content", "source_timezone", "code"),
    (
        (
            document(trade()).replace(
                ' whenGenerated="20260725;180000"',
                "",
            ),
            "UTC",
            "IBKR_REQUIRED_FIELD_MISSING",
        ),
        (
            document(trade(), generation="not-a-time"),
            "UTC",
            "IBKR_INVALID_DATETIME",
        ),
        (
            document(trade()).replace(
                'fromDate="20260701"',
                'fromDate="not-a-date"',
            ),
            "UTC",
            "IBKR_INVALID_STATEMENT_DATE",
        ),
        (
            document(trade()).replace(
                'fromDate="20260701"',
                'fromDate="20260726"',
            ),
            "UTC",
            "IBKR_STATEMENT_COVERAGE_INVALID",
        ),
        (
            document(trade()),
            "Not/A_Timezone",
            "IBKR_SOURCE_TIMEZONE_INVALID",
        ),
        (
            document(trade(), generation="20261101;013000"),
            "America/New_York",
            "AMBIGUOUS_LOCAL_TIME",
        ),
        (
            document(trade(), generation="20260308;023000"),
            "America/New_York",
            "NONEXISTENT_LOCAL_TIME",
        ),
    ),
)
def test_statement_time_and_coverage_metadata_fail_closed(
    tmp_path,
    provider_contract,
    content,
    source_timezone,
    code,
):
    with pytest.raises(IbkrFlexParseError) as failure:
        parse_ibkr_flex_xml(
            write_xml(tmp_path, content),
            source_timezone=source_timezone,
            provider_contract=provider_contract,
        )
    assert failure.value.code == code


def test_flat_boundary_is_proven_by_account_inception(
    tmp_path,
    provider_contract,
):
    parsed = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(
                trade(),
                statement_attributes=' accountInceptionDate="20260701"',
            ),
        ),
        source_timezone="UTC",
        provider_contract=provider_contract,
    )

    assert parsed.account_inception_date.isoformat() == "2026-07-01"
    assert parsed.flat_boundary_evidence == "ACCOUNT_INCEPTION"
    assert parsed.open_positions_snapshot_date is None


def test_flat_boundary_requires_explicit_empty_from_date_snapshot(
    tmp_path,
    provider_contract,
):
    empty = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(
                trade(),
                statement_sections=(
                    '<OpenPositions snapshotDate="20260701" />'
                ),
            ),
            "empty-positions.xml",
        ),
        source_timezone="UTC",
        provider_contract=provider_contract,
    )
    assert empty.flat_boundary_evidence == "EMPTY_OPEN_POSITIONS"
    assert empty.open_positions_nonzero_count == 0

    nonzero = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(
                trade(),
                statement_sections=(
                    '<OpenPositions snapshotDate="20260701">'
                    '<OpenPosition accountId="U1234567" position="2" />'
                    "</OpenPositions>"
                ),
            ),
            "nonzero-positions.xml",
        ),
        source_timezone="UTC",
        provider_contract=provider_contract,
    )
    assert nonzero.flat_boundary_evidence == "UNPROVEN"
    assert nonzero.open_positions_nonzero_count == 1

    missing = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(trade()),
            "missing-positions.xml",
        ),
        source_timezone="UTC",
        provider_contract=provider_contract,
    )
    assert missing.flat_boundary_evidence == "UNPROVEN"
    assert missing.open_positions_nonzero_count is None


@pytest.mark.parametrize(
    "snapshot",
    [
        '<OpenPositions snapshotDate="20260630" />',
        '<OpenPositions snapshotDate="20260701"><Unexpected /></OpenPositions>',
        (
            '<OpenPositions snapshotDate="20260701">'
            '<OpenPosition accountId="U1234567" position="NaN" />'
            "</OpenPositions>"
        ),
    ],
)
def test_invalid_open_positions_snapshot_fails_closed(
    tmp_path,
    provider_contract,
    snapshot,
):
    with pytest.raises(IbkrFlexParseError) as failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                document(trade(), statement_sections=snapshot),
            ),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert failure.value.code in {
        "IBKR_OPEN_POSITIONS_SNAPSHOT_INVALID",
        "IBKR_INVALID_DECIMAL",
    }


@pytest.mark.parametrize(
    ("payload", "code"),
    [
        (
            '<!DOCTYPE x [<!ENTITY e "boom">]><x>&e;</x>',
            "IBKR_UNSAFE_XML",
        ),
        (
            '<x xmlns:xi="http://www.w3.org/2001/XInclude">'
            '<xi:include href="file:///etc/passwd" /></x>',
            "IBKR_UNSAFE_XML",
        ),
        ("<broken>", "INVALID_IBKR_XML"),
    ],
)
def test_rejects_unsafe_or_malformed_xml(
    tmp_path,
    provider_contract,
    payload,
    code,
):
    with pytest.raises(IbkrFlexParseError) as failure:
        parse_ibkr_flex_xml(
            write_xml(tmp_path, payload),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert failure.value.code == code


def test_requires_exactly_one_statement_and_account(
    tmp_path,
    provider_contract,
):
    two_statements = (
        "<FlexQueryResponse>"
        + document("").replace(
            "<FlexQueryResponse>",
            "",
        ).replace("</FlexQueryResponse>", "")
        + document("").replace(
            "<FlexQueryResponse>",
            "",
        ).replace("</FlexQueryResponse>", "")
        + "</FlexQueryResponse>"
    )
    with pytest.raises(IbkrFlexParseError) as count_failure:
        parse_ibkr_flex_xml(
            write_xml(tmp_path, two_statements, "two.xml"),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert count_failure.value.code == "IBKR_STATEMENT_COUNT_INVALID"

    with pytest.raises(IbkrFlexParseError) as account_failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                document(trade(account_id="U9999999")),
                "accounts.xml",
            ),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert account_failure.value.code == "IBKR_MULTIPLE_ACCOUNTS"


def test_missing_execution_id_and_non_numeric_transaction_fail_closed(
    tmp_path,
    provider_contract,
):
    missing_id = trade().replace(' ibExecID="EXEC-1"', "")
    with pytest.raises(IbkrFlexParseError) as identity_failure:
        parse_ibkr_flex_xml(
            write_xml(tmp_path, document(missing_id), "identity.xml"),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert identity_failure.value.code == "IBKR_EXECUTION_ID_MISSING"

    with pytest.raises(IbkrFlexParseError) as order_failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                document(trade(transaction_id="not-numeric")),
                "order.xml",
            ),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert order_failure.value.code == "IBKR_TRANSACTION_ID_INVALID"

    with pytest.raises(IbkrFlexParseError) as signed_order_failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                document(trade(transaction_id="-1")),
                "signed-order.xml",
            ),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert signed_order_failure.value.code == "IBKR_TRANSACTION_ID_INVALID"


def test_change_requires_stable_identity_but_preserves_missing_target(
    tmp_path,
    provider_contract,
):
    correction = (
        '<TradeCorrection accountId="U1234567" sourceEventID="CORR-1" '
        'transactionID="102" assetCategory="STK" conid="265598" '
        'symbol="AAPL" listingExchange="NASDAQ" currency="USD" '
        'buySell="BUY" quantity="2" tradePrice="201" '
        'dateTime="20260725;110000" openCloseIndicator="OPEN" '
        'tradeStatus="CORRECTED" ibCommission="-1.25" '
        'ibCommissionCurrency="USD" />'
    )
    parsed = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(correction),
            "missing-change-target.xml",
        ),
        source_timezone="UTC",
        provider_contract=provider_contract,
    )
    assert parsed.events[0].event_kind == "CORRECTION"
    assert parsed.events[0].external_source_event_id == "CORR-1"
    assert parsed.events[0].affected_external_execution_id is None
    assert parsed.events[0].normalized_payload[
        "provider_declared_target_id"
    ] is None

    missing_identity = correction.replace(
        ' sourceEventID="CORR-1"',
        "",
    )
    with pytest.raises(IbkrFlexParseError) as identity_failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                document(missing_identity),
                "missing-change-id.xml",
            ),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert identity_failure.value.code == "IBKR_CHANGE_EVENT_ID_MISSING"


def test_unknown_event_and_hidden_second_account_fail_closed(
    tmp_path,
    provider_contract,
):
    with pytest.raises(IbkrFlexParseError) as event_failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                document('<UnknownEvent accountId="U1234567" />'),
                "unknown.xml",
            ),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert event_failure.value.code == "IBKR_EVENT_KIND_UNSUPPORTED"

    hidden_account = (
        '<Metadata accountId="U9999999" />'
        + document(trade()).replace(
            "<FlexQueryResponse>",
            "",
        ).replace("</FlexQueryResponse>", "")
    )
    with pytest.raises(IbkrFlexParseError) as account_failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                f"<FlexQueryResponse>{hidden_account}</FlexQueryResponse>",
                "hidden-account.xml",
            ),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert account_failure.value.code == "IBKR_MULTIPLE_ACCOUNTS"


def test_execution_count_depth_and_field_limits(
    tmp_path,
    provider_contract,
):
    exact_limit = "".join(
        trade(execution_id=f"EXACT-{index}", transaction_id=str(index))
        for index in range(MAX_EXECUTIONS)
    )
    parsed = parse_ibkr_flex_xml(
        write_xml(tmp_path, document(exact_limit), "exact-limit.xml"),
        source_timezone="UTC",
        provider_contract=provider_contract,
    )
    assert len(parsed.events) == MAX_EXECUTIONS

    too_many = "".join(
        trade(execution_id=f"EXEC-{index}", transaction_id=str(index))
        for index in range(MAX_EXECUTIONS + 1)
    )
    with pytest.raises(IbkrFlexParseError) as count_failure:
        parse_ibkr_flex_xml(
            write_xml(tmp_path, document(too_many), "many.xml"),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert count_failure.value.code == "IBKR_EXECUTION_LIMIT_EXCEEDED"

    deep = "<n>" * 20 + "</n>" * 20
    with pytest.raises(IbkrFlexParseError) as depth_failure:
        parse_ibkr_flex_xml(
            write_xml(tmp_path, deep, "deep.xml"),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert depth_failure.value.code == "IBKR_XML_DEPTH_LIMIT_EXCEEDED"

    long_symbol = trade().replace('symbol="AAPL"', f'symbol="{"A" * 2049}"')
    with pytest.raises(IbkrFlexParseError) as field_failure:
        parse_ibkr_flex_xml(
            write_xml(tmp_path, document(long_symbol), "long.xml"),
            source_timezone="UTC",
            provider_contract=provider_contract,
    )
    assert field_failure.value.code == "IBKR_FIELD_TOO_LONG"

    too_many_nodes = "<n/>" * MAX_XML_NODES
    with pytest.raises(IbkrFlexParseError) as node_failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                f"<root>{too_many_nodes}</root>",
                "nodes.xml",
            ),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert node_failure.value.code == "IBKR_XML_NODE_LIMIT_EXCEEDED"

    attributes = " ".join(
        f'a{index}="{index}"'
        for index in range(MAX_ATTRIBUTES_PER_NODE + 1)
    )
    with pytest.raises(IbkrFlexParseError) as attribute_failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                f"<root {attributes}/>",
                "attributes.xml",
            ),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert (
        attribute_failure.value.code
        == "IBKR_XML_ATTRIBUTE_LIMIT_EXCEEDED"
    )


def test_dst_fold_and_gap_are_rejected(tmp_path, provider_contract):
    ambiguous = trade(date_time="20261101;013000")
    with pytest.raises(IbkrFlexParseError) as fold_failure:
        parse_ibkr_flex_xml(
            write_xml(tmp_path, document(ambiguous), "fold.xml"),
            source_timezone="America/New_York",
            provider_contract=provider_contract,
        )
    assert fold_failure.value.code == "AMBIGUOUS_LOCAL_TIME"

    nonexistent = trade(date_time="20260308;023000")
    with pytest.raises(IbkrFlexParseError) as gap_failure:
        parse_ibkr_flex_xml(
            write_xml(tmp_path, document(nonexistent), "gap.xml"),
            source_timezone="America/New_York",
            provider_contract=provider_contract,
        )
    assert gap_failure.value.code == "NONEXISTENT_LOCAL_TIME"
