"""Secure, provider-contract-bound parser for local IBKR Flex XML files."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal, InvalidOperation
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Literal

from lxml import etree

from app_config.ibkr_flex_provider_evidence import (
    VerifiedIbkrFlexProviderContract,
)
from app_config.release_contract import JOURNAL_BETA_CONTRACT
from services.timezone_service import (
    LocalDateTimeError,
    normalize_iana_timezone,
    normalize_user_datetime_to_utc,
)


MAX_FILE_BYTES = JOURNAL_BETA_CONTRACT.imports.common_limits.max_file_bytes
MAX_EXECUTIONS = (
    JOURNAL_BETA_CONTRACT.imports.common_limits.max_rows_or_executions
)
MAX_XML_NODES = 20_000
MAX_ATTRIBUTES_PER_NODE = 80
MAX_XML_DEPTH = 16
MAX_FIELD_LENGTH = 2_048
MAX_EXTERNAL_ACCOUNT_ID_LENGTH = 255
MAX_SOURCE_EVENT_ID_LENGTH = 255
MAX_TRANSACTION_ID_LENGTH = 255
MAX_SOURCE_ORDER_KEY_LENGTH = 512
MAX_CONID_LENGTH = 100
MAX_CURRENCY_LENGTH = 10
MAX_EXECUTION_STATUS_LENGTH = 100
SOURCE_FINGERPRINT_VERSION = 1
ASCII_INTEGER_PATTERN = re.compile(r"^[0-9]+$")


class IbkrFlexParseError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class NormalizedIbkrFlexEvent:
    row_number: int
    event_kind: str
    external_source_event_id: str
    external_execution_id: str | None
    affected_external_execution_id: str | None
    transaction_id: str
    source_order_key: str
    conid: str
    asset_category: str
    symbol: str
    exchange: str
    currency: str
    raw_side: str
    raw_open_close: str
    quantity: Decimal
    price: Decimal
    occurred_at_utc: datetime
    source_timezone: str
    normalized_fee: Decimal
    fee_currency: str
    execution_status: str
    source_payload_fingerprint: str
    normalized_payload: dict[str, Any]


@dataclass(frozen=True)
class ParsedIbkrFlexStatement:
    normalized_external_account_ref: str
    masked_external_account_ref: str
    statement_generation: str
    generation_order_key: str
    raw_from_date: str
    raw_to_date: str
    coverage_start: date
    coverage_end_exclusive: date
    source_timezone: str
    events: tuple[NormalizedIbkrFlexEvent, ...]
    account_inception_date: date | None = None
    open_positions_snapshot_date: date | None = None
    open_positions_nonzero_count: int | None = None
    flat_boundary_evidence: Literal[
        "ACCOUNT_INCEPTION",
        "EMPTY_OPEN_POSITIONS",
        "UNPROVEN",
    ] = "UNPROVEN"


def _local_name(element: etree._Element) -> str:
    return etree.QName(element).localname


def _required_attribute(
    element: etree._Element,
    field_name: str,
    *,
    code: str = "IBKR_REQUIRED_FIELD_MISSING",
) -> str:
    raw = element.attrib.get(field_name)
    value = (raw or "").strip()
    if not value:
        raise IbkrFlexParseError(
            code,
            f"Required IBKR field is missing: {field_name}",
        )
    if len(value) > MAX_FIELD_LENGTH:
        raise IbkrFlexParseError(
            "IBKR_FIELD_TOO_LONG",
            f"IBKR field exceeds {MAX_FIELD_LENGTH} characters: {field_name}",
        )
    return value


def _optional_attribute(element: etree._Element, field_name: str) -> str | None:
    raw = element.attrib.get(field_name)
    if raw is None:
        return None
    value = raw.strip()
    if len(value) > MAX_FIELD_LENGTH:
        raise IbkrFlexParseError(
            "IBKR_FIELD_TOO_LONG",
            f"IBKR field exceeds {MAX_FIELD_LENGTH} characters: {field_name}",
        )
    return value or None


def _require_max_length(
    value: str,
    *,
    field_name: str,
    max_length: int,
) -> str:
    if len(value) > max_length:
        raise IbkrFlexParseError(
            "IBKR_FIELD_TOO_LONG",
            f"IBKR field exceeds {max_length} characters: {field_name}",
        )
    return value


def _parse_positive_decimal(value: str, *, field_name: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise IbkrFlexParseError(
            "IBKR_INVALID_DECIMAL",
            f"IBKR field must be numeric: {field_name}",
        ) from exc
    if not parsed.is_finite() or parsed <= 0:
        raise IbkrFlexParseError(
            "IBKR_INVALID_DECIMAL",
            f"IBKR field must be finite and positive: {field_name}",
        )
    return parsed


def _parse_fee(value: str | None, *, field_name: str) -> Decimal:
    if value is None:
        return Decimal("0")
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise IbkrFlexParseError(
            "IBKR_INVALID_COMMISSION",
            f"IBKR commission must be numeric: {field_name}",
        ) from exc
    if not parsed.is_finite():
        raise IbkrFlexParseError(
            "IBKR_INVALID_COMMISSION",
            f"IBKR commission must be finite: {field_name}",
        )
    return abs(parsed)


def _parse_finite_decimal(value: str, *, field_name: str) -> Decimal:
    try:
        parsed = Decimal(value)
    except InvalidOperation as exc:
        raise IbkrFlexParseError(
            "IBKR_INVALID_DECIMAL",
            f"IBKR field must be numeric: {field_name}",
        ) from exc
    if not parsed.is_finite():
        raise IbkrFlexParseError(
            "IBKR_INVALID_DECIMAL",
            f"IBKR field must be finite: {field_name}",
        )
    return parsed


def _parse_local_time(
    value: str,
    *,
    format_string: str,
    timezone_name: str,
    field_name: str,
) -> datetime:
    try:
        parsed = datetime.strptime(value, format_string)
        return normalize_user_datetime_to_utc(
            parsed,
            timezone_name=timezone_name,
        )
    except LocalDateTimeError as exc:
        raise IbkrFlexParseError(exc.code, str(exc)) from exc
    except ValueError as exc:
        raise IbkrFlexParseError(
            "IBKR_INVALID_DATETIME",
            f"IBKR field has an invalid datetime: {field_name}",
        ) from exc


def _parse_statement_date(
    value: str,
    *,
    format_string: str,
    field_name: str,
) -> date:
    try:
        return datetime.strptime(value, format_string).date()
    except ValueError as exc:
        raise IbkrFlexParseError(
            "IBKR_INVALID_STATEMENT_DATE",
            f"IBKR field has an invalid date: {field_name}",
        ) from exc


def _mask_account_ref(value: str) -> str:
    if len(value) <= 4:
        return "*" * len(value)
    return "*" * (len(value) - 4) + value[-4:]


def _canonical_fingerprint(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _reject_prohibited_xml(raw: bytes) -> None:
    lowered = raw.lower()
    prohibited = (
        (b"<!doctype", "DTD"),
        (b"<!entity", "entity"),
        (b"<xi:include", "XInclude"),
        (b"http://www.w3.org/2001/xinclude", "XInclude"),
    )
    for token, label in prohibited:
        if token in lowered:
            raise IbkrFlexParseError(
                "IBKR_UNSAFE_XML",
                f"IBKR XML must not contain {label}",
            )


def _validate_xml_shape(root: etree._Element) -> None:
    count = 0
    stack: list[tuple[etree._Element, int]] = [(root, 1)]
    while stack:
        element, depth = stack.pop()
        count += 1
        if count > MAX_XML_NODES:
            raise IbkrFlexParseError(
                "IBKR_XML_NODE_LIMIT_EXCEEDED",
                f"IBKR XML must not exceed {MAX_XML_NODES} nodes",
            )
        if depth > MAX_XML_DEPTH:
            raise IbkrFlexParseError(
                "IBKR_XML_DEPTH_LIMIT_EXCEEDED",
                f"IBKR XML must not exceed depth {MAX_XML_DEPTH}",
            )
        if len(element.attrib) > MAX_ATTRIBUTES_PER_NODE:
            raise IbkrFlexParseError(
                "IBKR_XML_ATTRIBUTE_LIMIT_EXCEEDED",
                "IBKR XML element has too many attributes",
            )
        for key, value in element.attrib.items():
            if len(key) > MAX_FIELD_LENGTH or len(value) > MAX_FIELD_LENGTH:
                raise IbkrFlexParseError(
                    "IBKR_FIELD_TOO_LONG",
                    "IBKR XML attribute exceeds the field length limit",
                )
        if element.text and len(element.text) > MAX_FIELD_LENGTH:
            raise IbkrFlexParseError(
                "IBKR_FIELD_TOO_LONG",
                "IBKR XML text exceeds the field length limit",
            )
        children = [
            child
            for child in element
            if isinstance(child.tag, str)
        ]
        stack.extend((child, depth + 1) for child in children)


def _event_kind(
    element_name: str,
    contract: VerifiedIbkrFlexProviderContract,
) -> str | None:
    fields = contract.field_contract
    if element_name == fields.trade_element:
        return "TRADE"
    if element_name == fields.correction_element:
        return "CORRECTION"
    if element_name == fields.cancel_bust_element:
        return "CANCEL_BUST"
    return None


def parse_ibkr_flex_xml(
    path: Path,
    *,
    source_timezone: str,
    provider_contract: VerifiedIbkrFlexProviderContract,
) -> ParsedIbkrFlexStatement:
    try:
        source_timezone = normalize_iana_timezone(source_timezone)
    except ValueError as exc:
        raise IbkrFlexParseError(
            "IBKR_SOURCE_TIMEZONE_INVALID",
            "IBKR source timezone must be a valid IANA timezone",
        ) from exc
    size = path.stat().st_size
    if size > MAX_FILE_BYTES:
        raise IbkrFlexParseError(
            "IMPORT_FILE_TOO_LARGE",
            f"IBKR XML must not exceed {MAX_FILE_BYTES} bytes",
        )
    raw = path.read_bytes()
    _reject_prohibited_xml(raw)
    parser = etree.XMLParser(
        resolve_entities=False,
        load_dtd=False,
        no_network=True,
        huge_tree=False,
        recover=False,
        remove_comments=True,
    )
    try:
        root = etree.fromstring(raw, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise IbkrFlexParseError(
            "INVALID_IBKR_XML",
            "IBKR Flex XML is malformed",
        ) from exc
    tree = root.getroottree()
    if tree.docinfo.doctype:
        raise IbkrFlexParseError(
            "IBKR_UNSAFE_XML",
            "IBKR XML must not contain a DTD",
        )
    _validate_xml_shape(root)

    fields = provider_contract.field_contract
    statements = [
        item
        for item in root.iter()
        if _local_name(item) == fields.statement_element
    ]
    if len(statements) != 1:
        raise IbkrFlexParseError(
            "IBKR_STATEMENT_COUNT_INVALID",
            "IBKR XML must contain exactly one FlexStatement",
        )
    statement = statements[0]
    raw_account_ref = _require_max_length(
        _required_attribute(statement, fields.account_field),
        field_name=fields.account_field,
        max_length=MAX_EXTERNAL_ACCOUNT_ID_LENGTH,
    )
    if not raw_account_ref.isascii():
        raise IbkrFlexParseError(
            "IBKR_ACCOUNT_ID_INVALID",
            "IBKR external account identity must be ASCII",
        )
    account_ref = raw_account_ref.upper()
    account_values = {
        value.strip().upper()
        for item in root.iter()
        if (value := item.attrib.get(fields.account_field))
    }
    if any(not value.isascii() for value in account_values):
        raise IbkrFlexParseError(
            "IBKR_ACCOUNT_ID_INVALID",
            "IBKR external account identity must be ASCII",
        )
    if account_values != {account_ref}:
        raise IbkrFlexParseError(
            "IBKR_MULTIPLE_ACCOUNTS",
            "IBKR XML must contain exactly one external account",
        )
    raw_from_date = _required_attribute(statement, fields.from_date_field)
    raw_to_date = _required_attribute(statement, fields.to_date_field)
    generation = _required_attribute(statement, fields.generation_field)
    coverage_start = _parse_statement_date(
        raw_from_date,
        format_string=fields.statement_date_format,
        field_name=fields.from_date_field,
    )
    raw_coverage_end = _parse_statement_date(
        raw_to_date,
        format_string=fields.statement_date_format,
        field_name=fields.to_date_field,
    )
    coverage_end_exclusive = raw_coverage_end + (
        timedelta(days=1)
        if fields.statement_to_date_inclusive
        else timedelta(0)
    )
    if coverage_start >= coverage_end_exclusive:
        raise IbkrFlexParseError(
            "IBKR_STATEMENT_COVERAGE_INVALID",
            "IBKR statement coverage must be a non-empty interval",
        )
    raw_inception_date = _optional_attribute(
        statement,
        fields.account_inception_date_field,
    )
    account_inception_date = (
        _parse_statement_date(
            raw_inception_date,
            format_string=fields.statement_date_format,
            field_name=fields.account_inception_date_field,
        )
        if raw_inception_date is not None
        else None
    )

    open_positions_containers = [
        item
        for item in statement.iter()
        if _local_name(item) == fields.open_positions_element
    ]
    if len(open_positions_containers) > 1:
        raise IbkrFlexParseError(
            "IBKR_OPEN_POSITIONS_SNAPSHOT_INVALID",
            "IBKR statement must contain at most one OpenPositions snapshot",
        )
    open_positions_snapshot_date: date | None = None
    open_positions_nonzero_count: int | None = None
    if open_positions_containers:
        container = open_positions_containers[0]
        raw_snapshot_date = _required_attribute(
            container,
            fields.open_positions_snapshot_date_field,
            code="IBKR_OPEN_POSITIONS_SNAPSHOT_INVALID",
        )
        open_positions_snapshot_date = _parse_statement_date(
            raw_snapshot_date,
            format_string=fields.statement_date_format,
            field_name=fields.open_positions_snapshot_date_field,
        )
        if open_positions_snapshot_date != coverage_start:
            raise IbkrFlexParseError(
                "IBKR_OPEN_POSITIONS_SNAPSHOT_INVALID",
                "IBKR OpenPositions snapshot must be at statement fromDate",
            )
        open_positions_nonzero_count = 0
        for position in container:
            if not isinstance(position.tag, str):
                continue
            if _local_name(position) != fields.open_position_element:
                raise IbkrFlexParseError(
                    "IBKR_OPEN_POSITIONS_SNAPSHOT_INVALID",
                    "IBKR OpenPositions snapshot contains an unknown element",
                )
            position_account = _optional_attribute(
                position,
                fields.account_field,
            )
            if (
                position_account is not None
                and position_account.upper() != account_ref
            ):
                raise IbkrFlexParseError(
                    "IBKR_MULTIPLE_ACCOUNTS",
                    "IBKR XML must contain exactly one external account",
                )
            position_quantity = _parse_finite_decimal(
                _required_attribute(
                    position,
                    fields.open_position_quantity_field,
                    code="IBKR_OPEN_POSITIONS_SNAPSHOT_INVALID",
                ),
                field_name=fields.open_position_quantity_field,
            )
            if position_quantity != 0:
                open_positions_nonzero_count += 1

    if (
        account_inception_date is not None
        and coverage_start <= account_inception_date
    ):
        flat_boundary_evidence = "ACCOUNT_INCEPTION"
    elif (
        open_positions_snapshot_date == coverage_start
        and open_positions_nonzero_count == 0
    ):
        flat_boundary_evidence = "EMPTY_OPEN_POSITIONS"
    else:
        flat_boundary_evidence = "UNPROVEN"
    generation_utc = _parse_local_time(
        generation,
        format_string=fields.generation_time_format,
        timezone_name=source_timezone,
        field_name=fields.generation_field,
    )
    generation_order_key = generation_utc.isoformat()

    containers = [
        item
        for item in statement.iter()
        if _local_name(item) == fields.events_container_element
    ]
    if len(containers) > 1:
        raise IbkrFlexParseError(
            "IBKR_EVENT_CONTAINER_COUNT_INVALID",
            "IBKR statement must contain at most one execution container",
        )
    event_elements: list[tuple[etree._Element, str]] = []
    if containers:
        for element in containers[0]:
            if not isinstance(element.tag, str):
                continue
            kind = _event_kind(_local_name(element), provider_contract)
            if kind is None:
                raise IbkrFlexParseError(
                    "IBKR_EVENT_KIND_UNSUPPORTED",
                    f"Unsupported IBKR event element: {_local_name(element)}",
                )
            event_elements.append((element, kind))
    if len(event_elements) > MAX_EXECUTIONS:
        raise IbkrFlexParseError(
            "IBKR_EXECUTION_LIMIT_EXCEEDED",
            f"IBKR statement must not exceed {MAX_EXECUTIONS} executions",
        )

    normalized_events: list[NormalizedIbkrFlexEvent] = []
    for row_number, (element, kind) in enumerate(event_elements, start=1):
        row_account = _optional_attribute(element, fields.account_field)
        if row_account is not None and row_account != account_ref:
            raise IbkrFlexParseError(
                "IBKR_MULTIPLE_ACCOUNTS",
                "IBKR XML must contain exactly one external account",
            )
        if kind == "TRADE":
            source_event_id = _require_max_length(
                _required_attribute(
                    element,
                    fields.execution_id_field,
                    code="IBKR_EXECUTION_ID_MISSING",
                ),
                field_name=fields.execution_id_field,
                max_length=MAX_SOURCE_EVENT_ID_LENGTH,
            )
            external_execution_id = source_event_id
            affected_execution_id = None
        else:
            source_event_id = _require_max_length(
                _required_attribute(
                    element,
                    fields.change_event_id_field,
                    code="IBKR_CHANGE_EVENT_ID_MISSING",
                ),
                field_name=fields.change_event_id_field,
                max_length=MAX_SOURCE_EVENT_ID_LENGTH,
            )
            external_execution_id = None
            affected_execution_id = _optional_attribute(
                element,
                fields.affected_execution_id_field,
            )
            if affected_execution_id is not None:
                affected_execution_id = _require_max_length(
                    affected_execution_id,
                    field_name=fields.affected_execution_id_field,
                    max_length=MAX_SOURCE_EVENT_ID_LENGTH,
                )

        transaction_id = _require_max_length(
            _required_attribute(
                element,
                fields.transaction_id_field,
            ),
            field_name=fields.transaction_id_field,
            max_length=MAX_TRANSACTION_ID_LENGTH,
        )
        if not ASCII_INTEGER_PATTERN.fullmatch(transaction_id):
            raise IbkrFlexParseError(
                "IBKR_TRANSACTION_ID_INVALID",
                "IBKR transactionID must be numeric",
            )
        numeric_transaction_id = int(transaction_id)
        asset_category = _required_attribute(
            element,
            fields.asset_category_field,
        ).upper()
        conid = _require_max_length(
            _required_attribute(element, fields.conid_field),
            field_name=fields.conid_field,
            max_length=MAX_CONID_LENGTH,
        )
        symbol = _required_attribute(element, fields.symbol_field).upper()
        exchange = _required_attribute(element, fields.exchange_field).upper()
        currency = _require_max_length(
            _required_attribute(
                element,
                fields.currency_field,
            ).upper(),
            field_name=fields.currency_field,
            max_length=MAX_CURRENCY_LENGTH,
        )
        side = _required_attribute(element, fields.side_field).upper()
        if side not in {"BUY", "SELL"}:
            raise IbkrFlexParseError(
                "IBKR_SIDE_UNSUPPORTED",
                f"Unsupported IBKR side: {side}",
            )
        open_close = _required_attribute(
            element,
            fields.open_close_field,
        ).upper()
        if open_close not in {"OPEN", "CLOSE"}:
            raise IbkrFlexParseError(
                "IBKR_OPEN_CLOSE_UNSUPPORTED",
                f"Unsupported IBKR open/close indicator: {open_close}",
            )
        quantity = _parse_positive_decimal(
            _required_attribute(element, fields.quantity_field),
            field_name=fields.quantity_field,
        )
        price = _parse_positive_decimal(
            _required_attribute(element, fields.price_field),
            field_name=fields.price_field,
        )
        occurred_at = _parse_local_time(
            _required_attribute(element, fields.trade_time_field),
            format_string=fields.execution_time_format,
            timezone_name=source_timezone,
            field_name=fields.trade_time_field,
        )
        status = _require_max_length(
            _required_attribute(
                element,
                fields.execution_status_field,
            ).upper(),
            field_name=fields.execution_status_field,
            max_length=MAX_EXECUTION_STATUS_LENGTH,
        )
        fee = _parse_fee(
            _optional_attribute(element, fields.commission_field),
            field_name=fields.commission_field,
        )
        fee_currency = (
            _optional_attribute(element, fields.commission_currency_field)
            or currency
        ).upper()
        fee_currency = _require_max_length(
            fee_currency,
            field_name=fields.commission_currency_field,
            max_length=MAX_CURRENCY_LENGTH,
        )
        if fee and fee_currency != currency:
            raise IbkrFlexParseError(
                "IBKR_COMMISSION_CURRENCY_MISMATCH",
                "IBKR commission currency must equal trade currency",
            )

        fingerprint_payload = {
            "adapter_kind": "IBKR_FLEX_XML_V1",
            "adapter_version": 1,
            "normalized_external_account_ref": account_ref,
            "event_kind": kind,
            "external_source_event_id": source_event_id,
            "external_execution_id": external_execution_id,
            "affected_external_execution_id": affected_execution_id,
            "transaction_id": str(numeric_transaction_id),
            "asset_category": asset_category,
            "conid": conid,
            "symbol": symbol,
            "exchange": exchange,
            "raw_side": side,
            "raw_open_close": open_close,
            "quantity": format(quantity, "f"),
            "price": format(price, "f"),
            "occurred_at_utc": occurred_at.isoformat(),
            "source_timezone": source_timezone,
            "currency": currency,
            "normalized_fee": format(fee, "f"),
            "fee_currency": fee_currency,
            "execution_status": status,
            "provider_declared_target_id": affected_execution_id,
        }
        fingerprint = _canonical_fingerprint(fingerprint_payload)
        source_order_key = (
            f"{numeric_transaction_id:020d}|{source_event_id}"
        )
        _require_max_length(
            source_order_key,
            field_name="source_order_key",
            max_length=MAX_SOURCE_ORDER_KEY_LENGTH,
        )
        normalized_events.append(
            NormalizedIbkrFlexEvent(
                row_number=row_number,
                event_kind=kind,
                external_source_event_id=source_event_id,
                external_execution_id=external_execution_id,
                affected_external_execution_id=affected_execution_id,
                transaction_id=str(numeric_transaction_id),
                source_order_key=source_order_key,
                conid=conid,
                asset_category=asset_category,
                symbol=symbol,
                exchange=exchange,
                currency=currency,
                raw_side=side,
                raw_open_close=open_close,
                quantity=quantity,
                price=price,
                occurred_at_utc=occurred_at,
                source_timezone=source_timezone,
                normalized_fee=fee,
                fee_currency=fee_currency,
                execution_status=status,
                source_payload_fingerprint=fingerprint,
                normalized_payload=fingerprint_payload,
            )
        )

    return ParsedIbkrFlexStatement(
        normalized_external_account_ref=account_ref,
        masked_external_account_ref=_mask_account_ref(account_ref),
        statement_generation=generation,
        generation_order_key=generation_order_key,
        raw_from_date=raw_from_date,
        raw_to_date=raw_to_date,
        coverage_start=coverage_start,
        coverage_end_exclusive=coverage_end_exclusive,
        source_timezone=source_timezone,
        account_inception_date=account_inception_date,
        open_positions_snapshot_date=open_positions_snapshot_date,
        open_positions_nonzero_count=open_positions_nonzero_count,
        flat_boundary_evidence=flat_boundary_evidence,
        events=tuple(normalized_events),
    )
