"""Prepare privacy-reviewed IBKR Flex fixtures without claiming verification."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import stat
from typing import Iterable

from lxml import etree

from app_config.ibkr_flex_provider_evidence import IbkrFlexFieldContract


MAX_SOURCE_BYTES = 10 * 1024 * 1024
MAX_XML_NODES = 20_000
XINCLUDE_NAMESPACE = "http://www.w3.org/2001/XInclude"


class IbkrEvidenceRedactionError(ValueError):
    """Raised when source evidence cannot be safely redacted."""


@dataclass(frozen=True)
class _ParsedSource:
    root: etree._Element


def _local_name(element: etree._Element) -> str:
    return etree.QName(element).localname


def _read_source_bytes(path: Path) -> bytes:
    try:
        source_stat = path.lstat()
        if stat.S_ISLNK(source_stat.st_mode):
            raise IbkrEvidenceRedactionError(
                "Source statement must not be a symbolic link"
            )
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        try:
            opened_stat = os.fstat(descriptor)
            if not stat.S_ISREG(opened_stat.st_mode):
                raise IbkrEvidenceRedactionError(
                    "Source statement must be a regular file"
                )
            source = os.fdopen(descriptor, "rb")
            descriptor = -1
            with source:
                raw = source.read(MAX_SOURCE_BYTES + 1)
        finally:
            if descriptor >= 0:
                os.close(descriptor)
    except IbkrEvidenceRedactionError:
        raise
    except OSError as exc:
        raise IbkrEvidenceRedactionError(
            "Source statement cannot be read"
        ) from exc
    if len(raw) > MAX_SOURCE_BYTES:
        raise IbkrEvidenceRedactionError(
            f"Source statement exceeds {MAX_SOURCE_BYTES} bytes"
        )
    return raw


def _parse_source(
    path: Path,
    contract: IbkrFlexFieldContract,
) -> _ParsedSource:
    raw = _read_source_bytes(path)

    parser = etree.XMLParser(
        resolve_entities=False,
        no_network=True,
        load_dtd=False,
        recover=False,
        remove_comments=True,
        remove_pis=True,
        huge_tree=False,
    )
    try:
        root = etree.fromstring(raw, parser=parser)
    except etree.XMLSyntaxError as exc:
        raise IbkrEvidenceRedactionError(
            "Source statement is not valid safe XML"
        ) from exc
    if root.getroottree().docinfo.doctype:
        raise IbkrEvidenceRedactionError(
            "Source statement must not contain a DTD"
        )

    elements = list(root.iter())
    if len(elements) > MAX_XML_NODES:
        raise IbkrEvidenceRedactionError(
            f"Source statement exceeds {MAX_XML_NODES} XML nodes"
        )
    if any(
        etree.QName(element).namespace
        or any(etree.QName(name).namespace for name in element.attrib)
        for element in elements
        if isinstance(element.tag, str)
    ):
        raise IbkrEvidenceRedactionError(
            "Source statement must not contain XML namespaces"
        )
    if any(
        etree.QName(element).namespace == XINCLUDE_NAMESPACE
        for element in elements
        if isinstance(element.tag, str)
    ):
        raise IbkrEvidenceRedactionError(
            "Source statement must not contain XInclude"
        )
    statements = [
        element
        for element in elements
        if isinstance(element.tag, str)
        and _local_name(element) == contract.statement_element
    ]
    if len(statements) != 1:
        raise IbkrEvidenceRedactionError(
            "Source statement must contain exactly one configured "
            "statement element"
        )
    statement = etree.fromstring(etree.tostring(statements[0]))
    return _ParsedSource(root=statement)


def _configured_attribute_names(
    contract: IbkrFlexFieldContract,
) -> set[str]:
    payload = contract.model_dump()
    return {
        value
        for key, value in payload.items()
        if key.endswith("_field") and isinstance(value, str) and value
    }


def _configured_element_names(
    contract: IbkrFlexFieldContract,
) -> set[str]:
    names = {
        contract.statement_element,
        contract.events_container_element,
        contract.trade_element,
        contract.open_positions_element,
        contract.open_position_element,
    }
    if contract.correction_element:
        names.add(contract.correction_element)
    if contract.cancel_bust_element:
        names.add(contract.cancel_bust_element)
    if contract.account_inception_element:
        names.add(contract.account_inception_element)
    return names


def _remove_unconfigured_subtrees(
    root: etree._Element,
    allowed_elements: set[str],
) -> None:
    for parent in tuple(root.iter()):
        if not isinstance(parent.tag, str):
            continue
        for child in tuple(parent):
            if (
                isinstance(child.tag, str)
                and _local_name(child) not in allowed_elements
            ):
                parent.remove(child)


def _validate_redaction_field_roles(
    contract: IbkrFlexFieldContract,
) -> None:
    identity_fields = {
        contract.execution_id_field,
        contract.change_event_id_field,
    }
    if contract.affected_execution_id_field:
        identity_fields.add(contract.affected_execution_id_field)
    distinct_roles = {
        "account": contract.account_field,
        "transaction": contract.transaction_id_field,
        "conid": contract.conid_field,
        "symbol": contract.symbol_field,
    }
    role_values = tuple(distinct_roles.values())
    if (
        len(set(role_values)) != len(role_values)
        or identity_fields.intersection(role_values)
    ):
        raise IbkrEvidenceRedactionError(
            "Sensitive field roles must be distinct except within the "
            "shared execution/change identity namespace"
        )


def _collect_values(
    sources: Iterable[_ParsedSource],
    field_names: set[str],
) -> set[str]:
    return {
        value.strip()
        for source in sources
        for element in source.root.iter()
        if isinstance(element.tag, str)
        for field_name in field_names
        if (value := element.attrib.get(field_name))
        and value.strip()
    }


def _alias_map(
    values: Iterable[str],
    *,
    prefix: str,
) -> dict[str, str]:
    return {
        value: f"{prefix}-{index:04d}"
        for index, value in enumerate(sorted(set(values)), start=1)
    }


def _transaction_alias_map(values: Iterable[str]) -> dict[str, str]:
    normalized = set(values)
    if any(not value.isascii() or not value.isdigit() for value in normalized):
        raise IbkrEvidenceRedactionError(
            "Transaction identities must be ASCII integers"
        )
    ordered = sorted(normalized, key=lambda value: (int(value), value))
    return {
        value: str(100_000 + index)
        for index, value in enumerate(ordered, start=1)
    }


def _sha256_bytes(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def _write_private_file(path: Path, payload: bytes) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as destination:
            destination.write(payload)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        try:
            path.unlink()
        except OSError:
            pass
        raise


def redact_ibkr_flex_statements(
    statement_paths: Iterable[Path],
    *,
    contract: IbkrFlexFieldContract,
    output_dir: Path,
) -> dict:
    """Write redacted fixture candidates and a non-verifying review report."""
    paths = tuple(Path(path) for path in statement_paths)
    if not paths:
        raise IbkrEvidenceRedactionError(
            "At least one source statement is required"
        )
    if output_dir.exists():
        raise IbkrEvidenceRedactionError(
            "Output directory must not already exist"
        )
    if not output_dir.parent.is_dir():
        raise IbkrEvidenceRedactionError(
            "Output directory parent does not exist"
        )
    if output_dir.parent.is_symlink():
        raise IbkrEvidenceRedactionError(
            "Output directory parent must not be a symbolic link"
        )

    _validate_redaction_field_roles(contract)
    sources = tuple(_parse_source(path, contract) for path in paths)
    allowed_attributes = _configured_attribute_names(contract)
    allowed_elements = _configured_element_names(contract)
    id_fields = {
        contract.execution_id_field,
        contract.change_event_id_field,
    }
    if contract.affected_execution_id_field:
        id_fields.add(contract.affected_execution_id_field)

    accounts = _alias_map(
        _collect_values(sources, {contract.account_field}),
        prefix="REDACTED-ACCOUNT",
    )
    identities = _alias_map(
        _collect_values(sources, id_fields),
        prefix="REDACTED-ID",
    )
    transactions = _transaction_alias_map(
        _collect_values(sources, {contract.transaction_id_field})
    )
    conids = _alias_map(
        _collect_values(sources, {contract.conid_field}),
        prefix="REDACTED-CONID",
    )
    symbols = _alias_map(
        _collect_values(sources, {contract.symbol_field}),
        prefix="REDACTED-SYMBOL",
    )
    replacements = {
        contract.account_field: accounts,
        contract.execution_id_field: identities,
        contract.change_event_id_field: identities,
        contract.transaction_id_field: transactions,
        contract.conid_field: conids,
        contract.symbol_field: symbols,
    }
    if contract.affected_execution_id_field:
        replacements[contract.affected_execution_id_field] = identities

    rendered_fixtures: list[tuple[str, bytes, int]] = []
    for index, source in enumerate(sources, start=1):
        removed_attribute_count = 0
        _remove_unconfigured_subtrees(source.root, allowed_elements)
        for element in source.root.iter():
            if not isinstance(element.tag, str):
                continue
            element.text = None
            element.tail = None
            for attribute_name in tuple(element.attrib):
                if attribute_name not in allowed_attributes:
                    del element.attrib[attribute_name]
                    removed_attribute_count += 1
                    continue
                raw_value = element.attrib[attribute_name].strip()
                mapping = replacements.get(attribute_name)
                if mapping is not None and raw_value:
                    element.attrib[attribute_name] = mapping[raw_value]
        rendered = etree.tostring(
            source.root,
            encoding="UTF-8",
            xml_declaration=True,
            pretty_print=False,
        )
        rendered_fixtures.append(
            (
                f"statement-{index:03d}.redacted.xml",
                rendered,
                removed_attribute_count,
            )
        )

    contract_payload = json.dumps(
        contract.model_dump(mode="json"),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    fixtures = [
        {
            "relative_path": filename,
            "sha256": _sha256_bytes(payload),
            "classification": "REDACTED_REAL_CANDIDATE",
            "human_review_required": True,
            "removed_attribute_count": removed_count,
        }
        for filename, payload, removed_count in rendered_fixtures
    ]
    report = {
        "schema_version": 1,
        "status": "NOT_PROVIDER_VERIFICATION",
        "field_contract_sha256": _sha256_bytes(contract_payload),
        "fixture_count": len(fixtures),
        "fixtures": fixtures,
        "preserved_sensitive_categories": [
            "statement and execution dates/times",
            "quantities, prices, fees, and currencies",
            "provider event, side, open-close, and status values",
        ],
        "review_requirements": [
            "Inspect every output fixture before adding it to the repository.",
            "Confirm no free-form provider field contains personal data.",
            "Bind reviewed fixtures to the frozen query template and manifest.",
            "Do not change provider manifest status based on this report alone.",
        ],
    }
    report_payload = (
        json.dumps(report, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    ).encode("utf-8")

    output_dir.mkdir(mode=0o700)
    try:
        os.chmod(output_dir, 0o700)
        for filename, payload, _ in rendered_fixtures:
            _write_private_file(output_dir / filename, payload)
        _write_private_file(
            output_dir / "redaction-report.json",
            report_payload,
        )
    except Exception:
        for path in output_dir.iterdir():
            if path.is_file() and not path.is_symlink():
                path.unlink()
        output_dir.rmdir()
        raise
    return report
