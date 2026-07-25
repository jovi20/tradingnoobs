from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from app_config.ibkr_flex_provider_evidence import (
    IbkrFlexFieldContract,
    VerifiedIbkrFlexProviderContract,
)
from services.ibkr_flex_parser import (
    IbkrFlexParseError,
    MAX_ATTRIBUTES_PER_NODE,
    MAX_CONID_LENGTH,
    MAX_CURRENCY_LENGTH,
    MAX_EXECUTIONS,
    MAX_EXECUTION_STATUS_LENGTH,
    MAX_EXCHANGE_CODE_LENGTH,
    MAX_EXTERNAL_ACCOUNT_ID_LENGTH,
    MAX_SOURCE_EVENT_ID_LENGTH,
    MAX_SYMBOL_LENGTH,
    MAX_TRANSACTION_ID_LENGTH,
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


def trade(
    *,
    execution_id: str = "EXEC-1",
    transaction_id: str = "101",
    account_id: str = "U1234567",
    date_time: str = "20260725;100000",
    symbol: str = "AAPL",
    exchange: str = "NASDAQ",
) -> str:
    return (
        '<Trade accountId="{account_id}" ibExecID="{execution_id}" '
        'transactionID="{transaction_id}" assetCategory="STK" '
        'conid="265598" symbol="{symbol}" listingExchange="{exchange}" '
        'currency="USD" buySell="BUY" quantity="2" tradePrice="200" '
        'dateTime="{date_time}" openCloseIndicator="OPEN" '
        'tradeStatus="EXECUTED" ibCommission="-1.25" '
        'ibCommissionCurrency="USD" />'
    ).format(
        account_id=account_id,
        execution_id=execution_id,
        transaction_id=transaction_id,
        date_time=date_time,
        symbol=symbol,
        exchange=exchange,
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


def test_attribute_event_discriminator_and_wire_enums_are_contract_driven(
    tmp_path,
    provider_contract,
):
    payload = provider_contract.field_contract.model_dump()
    payload.update(
        {
            "event_kind_source": "ATTRIBUTE_VALUE",
            "event_kind_field": "transactionType",
            "ordinary_trade_kind_value": "ExchTrade",
            "correction_kind_value": "TradeCorrect",
            "cancel_bust_kind_value": "TradeCancel",
            "correction_element": None,
            "cancel_bust_element": None,
            "side_buy_value": "B",
            "side_sell_value": "S",
            "open_value": "O",
            "close_value": "C",
        }
    )
    attribute_contract = VerifiedIbkrFlexProviderContract(
        query_template_id="SYNTHETIC_ATTRIBUTE_TEST_ONLY",
        query_template_sha256=f"sha256:{'b' * 64}",
        field_contract=IbkrFlexFieldContract.model_validate(payload),
        official_sources=(),
        fixtures=(),
    )
    ordinary = trade().replace(
        "<Trade ",
        '<Trade transactionType="ExchTrade" ',
    ).replace(
        'buySell="BUY"',
        'buySell="B"',
    ).replace(
        'openCloseIndicator="OPEN"',
        'openCloseIndicator="O"',
    )
    correction = (
        '<Trade transactionType="TradeCorrect" accountId="U1234567" '
        'sourceEventID="CORR-1" affectedIBExecID="EXEC-1" '
        'transactionID="102" assetCategory="STK" conid="265598" '
        'symbol="AAPL" listingExchange="NASDAQ" currency="USD" '
        'buySell="S" quantity="2" tradePrice="201" '
        'dateTime="20260725;110000" openCloseIndicator="C" '
        'tradeStatus="CORRECTED" ibCommission="-1.25" '
        'ibCommissionCurrency="USD" />'
    )
    cancel = correction.replace(
        'transactionType="TradeCorrect"',
        'transactionType="TradeCancel"',
    ).replace(
        'sourceEventID="CORR-1"',
        'sourceEventID="CANCEL-1"',
    ).replace(
        'transactionID="102"',
        'transactionID="103"',
    )

    parsed = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(ordinary + correction + cancel),
            "attribute-events.xml",
        ),
        source_timezone="UTC",
        provider_contract=attribute_contract,
    )

    assert [event.event_kind for event in parsed.events] == [
        "TRADE",
        "CORRECTION",
        "CANCEL_BUST",
    ]
    assert parsed.events[0].raw_open_close == "OPEN"
    assert parsed.events[1].raw_side == "SELL"
    assert parsed.events[1].raw_open_close == "CLOSE"
    assert parsed.events[1].affected_external_execution_id == "EXEC-1"

    with pytest.raises(IbkrFlexParseError) as failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                document(
                    ordinary.replace(
                        'transactionType="ExchTrade"',
                        'transactionType="Unknown"',
                    )
                ),
                "unknown-attribute-event.xml",
            ),
            source_timezone="UTC",
            provider_contract=attribute_contract,
        )
    assert failure.value.code == "IBKR_EVENT_KIND_UNSUPPORTED"


def test_event_kind_status_and_same_id_change_target_are_contract_driven(
    tmp_path,
    provider_contract,
):
    payload = provider_contract.field_contract.model_dump()
    payload.update(
        {
            "execution_status_source": "EVENT_KIND",
            "execution_status_field": None,
            "change_identity_semantics": "EVENT_ID_IS_TARGET",
            "affected_execution_id_field": None,
        }
    )
    contract = VerifiedIbkrFlexProviderContract(
        query_template_id="SYNTHETIC_SAME_ID_TEST_ONLY",
        query_template_sha256=f"sha256:{'d' * 64}",
        field_contract=IbkrFlexFieldContract.model_validate(payload),
        official_sources=(),
        fixtures=(),
    )
    ordinary = trade().replace(' tradeStatus="EXECUTED"', "")
    correction = (
        '<TradeCorrection accountId="U1234567" sourceEventID="EXEC-1" '
        'transactionID="102" assetCategory="STK" conid="265598" '
        'symbol="AAPL" listingExchange="NASDAQ" currency="USD" '
        'buySell="BUY" quantity="2" tradePrice="201" '
        'dateTime="20260725;110000" openCloseIndicator="OPEN" '
        'ibCommission="-1.25" ibCommissionCurrency="USD" />'
    )

    parsed = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(ordinary + correction),
            "same-id-change.xml",
        ),
        source_timezone="UTC",
        provider_contract=contract,
    )

    assert [event.execution_status for event in parsed.events] == [
        "TRADE",
        "CORRECTION",
    ]
    assert parsed.events[1].external_source_event_id == "EXEC-1"
    assert parsed.events[1].affected_external_execution_id == "EXEC-1"


@pytest.mark.parametrize(
    "overrides",
    (
        {
            "event_kind_source": "ATTRIBUTE_VALUE",
            "correction_element": None,
            "cancel_bust_element": None,
        },
        {
            "event_kind_source": "ATTRIBUTE_VALUE",
            "event_kind_field": "transactionType",
            "ordinary_trade_kind_value": "Trade",
            "correction_kind_value": "Trade",
            "cancel_bust_kind_value": "TradeCancel",
            "correction_element": None,
            "cancel_bust_element": None,
        },
        {
            "event_kind_source": "ELEMENT_NAME",
            "event_kind_field": "transactionType",
            "ordinary_trade_kind_value": "Trade",
        },
        {"open_value": "O", "close_value": "O"},
        {
            "execution_status_source": "EVENT_KIND",
            "execution_status_field": "tradeStatus",
        },
        {
            "change_identity_semantics": "EVENT_ID_IS_TARGET",
            "affected_execution_id_field": "affectedIBExecID",
        },
    ),
)
def test_invalid_event_and_enum_contracts_fail_at_manifest_boundary(
    provider_contract,
    overrides,
):
    payload = provider_contract.field_contract.model_dump()
    payload.update(overrides)

    with pytest.raises(ValidationError):
        IbkrFlexFieldContract.model_validate(payload)


@pytest.mark.parametrize(
    "field_name",
    (
        "event_kind_source",
        "side_buy_value",
        "side_sell_value",
        "open_value",
        "close_value",
    ),
)
def test_wire_contract_strategy_and_enums_are_required(
    provider_contract,
    field_name,
):
    payload = provider_contract.field_contract.model_dump()
    payload.pop(field_name)

    with pytest.raises(ValidationError):
        IbkrFlexFieldContract.model_validate(payload)


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


def test_fingerprint_payload_covers_source_contract_and_excludes_derived_state(
    tmp_path,
    provider_contract,
):
    parsed = parse_ibkr_flex_xml(
        write_xml(tmp_path, document(trade()), "fingerprint-contract.xml"),
        source_timezone="America/New_York",
        provider_contract=provider_contract,
    )
    payload = parsed.events[0].normalized_payload

    assert set(payload) == {
        "adapter_kind",
        "adapter_version",
        "normalized_external_account_ref",
        "event_kind",
        "external_source_event_id",
        "external_execution_id",
        "affected_external_execution_id",
        "transaction_id",
        "asset_category",
        "conid",
        "symbol",
        "exchange",
        "raw_side",
        "raw_open_close",
        "quantity",
        "price",
        "occurred_at_utc",
        "source_timezone",
        "currency",
        "normalized_fee",
        "fee_currency",
        "execution_status",
        "provider_declared_target_id",
    }
    assert {
        "statement_generation",
        "generation_order_key",
        "file_hash",
        "row_number",
        "derived_direction",
        "derived_action",
        "pre_quantity",
        "post_quantity",
        "user_selected_target",
    }.isdisjoint(payload)


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


@pytest.mark.parametrize(
    ("old", "new", "code"),
    (
        ('buySell="BUY"', 'buySell="HOLD"', "IBKR_SIDE_UNSUPPORTED"),
        (
            'openCloseIndicator="OPEN"',
            'openCloseIndicator="UNKNOWN"',
            "IBKR_OPEN_CLOSE_UNSUPPORTED",
        ),
    ),
)
def test_unknown_side_and_open_close_fail_closed(
    tmp_path,
    provider_contract,
    old,
    new,
    code,
):
    with pytest.raises(IbkrFlexParseError) as failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                document(trade()).replace(old, new),
                f"{code.lower()}.xml",
            ),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert failure.value.code == code


def test_commission_sign_is_driven_by_the_frozen_contract(
    tmp_path,
    provider_contract,
):
    positive_commission = trade().replace(
        'ibCommission="-1.25"',
        'ibCommission="1.25"',
    )
    with pytest.raises(IbkrFlexParseError) as failure:
        parse_ibkr_flex_xml(
            write_xml(
                tmp_path,
                document(positive_commission),
                "wrong-commission-sign.xml",
            ),
            source_timezone="UTC",
            provider_contract=provider_contract,
        )
    assert failure.value.code == "IBKR_COMMISSION_SIGN_UNSUPPORTED"

    payload = provider_contract.field_contract.model_dump()
    payload["commission_charge_sign"] = "POSITIVE"
    positive_contract = VerifiedIbkrFlexProviderContract(
        query_template_id="SYNTHETIC_POSITIVE_COMMISSION_TEST_ONLY",
        query_template_sha256=f"sha256:{'c' * 64}",
        field_contract=IbkrFlexFieldContract.model_validate(payload),
        official_sources=(),
        fixtures=(),
    )
    parsed = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(positive_commission),
            "positive-commission.xml",
        ),
        source_timezone="UTC",
        provider_contract=positive_contract,
    )
    assert str(parsed.events[0].normalized_fee) == "1.25"


@pytest.mark.parametrize(
    ("raw_transaction_id", "normalized_id", "order_prefix"),
    (
        ("000101", "101", "00000000000000000101"),
        (
            "1234567890123456789012345",
            "1234567890123456789012345",
            "1234567890123456789012345",
        ),
    ),
)
def test_source_order_key_normalizes_without_truncating_numeric_transaction_id(
    tmp_path,
    provider_contract,
    raw_transaction_id,
    normalized_id,
    order_prefix,
):
    parsed = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(trade(transaction_id=raw_transaction_id)),
            f"order-{normalized_id}.xml",
        ),
        source_timezone="UTC",
        provider_contract=provider_contract,
    )
    event = parsed.events[0]
    assert event.transaction_id == normalized_id
    assert event.source_order_key == f"{order_prefix}|EXEC-1"


def test_persisted_source_field_widths_fail_before_database_writes(
    tmp_path,
    provider_contract,
):
    exact_event_id = "E" * MAX_SOURCE_EVENT_ID_LENGTH
    exact_transaction_id = "1" * MAX_TRANSACTION_ID_LENGTH
    exact = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(
                trade(
                    execution_id=exact_event_id,
                    transaction_id=exact_transaction_id,
                )
            ),
            "persisted-width-exact.xml",
        ),
        source_timezone="UTC",
        provider_contract=provider_contract,
    )
    assert exact.events[0].external_source_event_id == exact_event_id
    assert len(exact.events[0].source_order_key) == 511

    exact_identity = parse_ibkr_flex_xml(
        write_xml(
            tmp_path,
            document(
                trade(
                    symbol="S" * MAX_SYMBOL_LENGTH,
                    exchange="E" * MAX_EXCHANGE_CODE_LENGTH,
                )
            ),
            "persisted-identity-width-exact.xml",
        ),
        source_timezone="UTC",
        provider_contract=provider_contract,
    )
    assert len(exact_identity.events[0].symbol) == MAX_SYMBOL_LENGTH
    assert (
        len(exact_identity.events[0].exchange)
        == MAX_EXCHANGE_CODE_LENGTH
    )

    long_account = "U" * (MAX_EXTERNAL_ACCOUNT_ID_LENGTH + 1)
    long_target = "T" * (MAX_SOURCE_EVENT_ID_LENGTH + 1)
    correction = (
        '<TradeCorrection accountId="U1234567" sourceEventID="CORR-LONG" '
        f'affectedIBExecID="{long_target}" transactionID="102" '
        'assetCategory="STK" conid="265598" symbol="AAPL" '
        'listingExchange="NASDAQ" currency="USD" buySell="BUY" '
        'quantity="2" tradePrice="201" dateTime="20260725;110000" '
        'openCloseIndicator="OPEN" tradeStatus="CORRECTED" '
        'ibCommission="-1.25" ibCommissionCurrency="USD" />'
    )
    overlong_documents = (
        document(
            trade(execution_id="E" * (MAX_SOURCE_EVENT_ID_LENGTH + 1))
        ),
        document(
            trade(transaction_id="1" * (MAX_TRANSACTION_ID_LENGTH + 1))
        ),
        document(trade()).replace(
            'conid="265598"',
            f'conid="{"1" * (MAX_CONID_LENGTH + 1)}"',
        ),
        document(trade()).replace(
            'currency="USD"',
            f'currency="{"X" * (MAX_CURRENCY_LENGTH + 1)}"',
        ),
        document(trade()).replace(
            'tradeStatus="EXECUTED"',
            f'tradeStatus="{"X" * (MAX_EXECUTION_STATUS_LENGTH + 1)}"',
        ),
        document(trade(symbol="S" * (MAX_SYMBOL_LENGTH + 1))),
        document(
            trade(exchange="E" * (MAX_EXCHANGE_CODE_LENGTH + 1))
        ),
        document(
            trade(account_id=long_account),
            account_id=long_account,
        ),
        document(correction),
    )
    for index, content in enumerate(overlong_documents):
        with pytest.raises(IbkrFlexParseError) as failure:
            parse_ibkr_flex_xml(
                write_xml(
                    tmp_path,
                    content,
                    f"persisted-width-{index}.xml",
                ),
                source_timezone="UTC",
                provider_contract=provider_contract,
            )
        assert failure.value.code == "IBKR_FIELD_TOO_LONG"


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
