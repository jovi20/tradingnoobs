"""Machine-verifiable provider evidence gate for IBKR Flex XML V1."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Literal
from urllib.parse import urlparse

from lxml import etree
from pydantic import BaseModel, ConfigDict, ValidationError


EVIDENCE_PATH = Path(__file__).with_name(
    "ibkr_flex_v1_provider_evidence.json"
)
FIXTURE_ROOT = (
    Path(__file__).resolve().parents[1]
    / "tests"
    / "fixtures"
    / "ibkr_flex_v1"
)
SHA256_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
REQUIRED_SEMANTICS = frozenset(
    {
        "BASIC_EXECUTION_FIELDS",
        "GENERATION_ORDERING",
        "FLAT_BOUNDARY",
        "TRANSACTION_AND_OPEN_CLOSE",
        "CORRECTION_CANCEL_TARGETS",
        "COMMISSION_SIGN_CURRENCY",
        "COVERAGE_INCLUSIVITY_TIMEZONE",
    }
)


class _EvidenceModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class IbkrFlexFieldContract(_EvidenceModel):
    statement_element: str
    events_container_element: str
    trade_element: str
    account_field: str
    from_date_field: str
    to_date_field: str
    generation_field: str
    execution_id_field: str
    transaction_id_field: str
    asset_category_field: str
    conid_field: str
    symbol_field: str
    exchange_field: str
    currency_field: str
    side_field: str
    quantity_field: str
    price_field: str
    trade_time_field: str
    open_close_field: str
    execution_status_field: str
    commission_field: str
    commission_currency_field: str
    statement_to_date_inclusive: bool
    statement_date_format: str
    generation_time_format: str
    generation_ordering: Literal["UTC_INSTANT_ASC"]
    generation_tie_policy: Literal[
        "SAME_MARKER_DIFFERENT_FILE_CONFLICT"
    ]
    execution_time_format: str
    execution_time_semantics: Literal["SOURCE_TIMEZONE_NAIVE"]
    ordinary_trade_kind_from_element: Literal[True]
    correction_element: str
    cancel_bust_element: str
    change_event_id_field: str
    affected_execution_id_field: str
    account_inception_date_field: str
    open_positions_element: str
    open_position_element: str
    open_positions_snapshot_date_field: str
    open_position_quantity_field: str


class OfficialEvidenceExcerpt(_EvidenceModel):
    semantic: str
    locator: str
    quote: str
    wire_tokens: tuple[str, ...] = ()


class OfficialEvidenceSource(_EvidenceModel):
    url: str
    title: str
    retrieved_at: date
    artifact_relative_path: str
    artifact_sha256: str
    excerpts: tuple[OfficialEvidenceExcerpt, ...]


class RealFixtureEvidence(_EvidenceModel):
    relative_path: str
    sha256: str
    classification: Literal["REDACTED_REAL"]
    redacted: Literal[True]
    query_template_id: str
    semantics: tuple[str, ...]


class IbkrFlexProviderEvidenceManifest(_EvidenceModel):
    schema_version: Literal[1]
    adapter_kind: Literal["IBKR_FLEX_XML_V1"]
    status: Literal["UNVERIFIED", "VERIFIED"]
    query_template_id: str | None
    query_template_relative_path: str | None = None
    query_template_sha256: str | None
    field_contract: IbkrFlexFieldContract | None
    official_sources: tuple[OfficialEvidenceSource, ...]
    fixtures: tuple[RealFixtureEvidence, ...]
    unverified_reasons: tuple[str, ...]


@dataclass(frozen=True)
class VerifiedIbkrFlexProviderContract:
    query_template_id: str
    query_template_sha256: str
    field_contract: IbkrFlexFieldContract
    official_sources: tuple[OfficialEvidenceSource, ...]
    fixtures: tuple[RealFixtureEvidence, ...]


class IbkrProviderEvidenceError(ValueError):
    code = "IBKR_PROVIDER_CONTRACT_UNVERIFIED"

    def __init__(self, reasons: tuple[str, ...]):
        self.reasons = reasons
        super().__init__("; ".join(reasons))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def _evidence_path(
    *,
    relative_path: str,
    resolved_root: Path,
    label: str,
) -> tuple[Path | None, str | None]:
    candidate = (resolved_root / relative_path).resolve()
    if not candidate.is_relative_to(resolved_root):
        return None, f"{label} escapes the evidence root: {relative_path}"
    if not candidate.is_file():
        return None, f"{label} is missing: {relative_path}"
    return candidate, None


def _local_name(element: etree._Element) -> str:
    return etree.QName(element).localname


def _elements(root: etree._Element, name: str) -> list[etree._Element]:
    return [element for element in root.iter() if _local_name(element) == name]


def _required_attributes(
    element: etree._Element,
    names: tuple[str, ...],
) -> bool:
    return all((element.attrib.get(name) or "").strip() for name in names)


@dataclass(frozen=True)
class _FixtureShape:
    path: str
    generation: datetime | None
    coverage_start: date | None
    coverage_end: date | None


def _validate_fixture_semantics(
    path: Path,
    *,
    relative_path: str,
    semantics: tuple[str, ...],
    contract: IbkrFlexFieldContract,
) -> tuple[list[str], _FixtureShape]:
    reasons: list[str] = []
    empty_shape = _FixtureShape(relative_path, None, None, None)
    try:
        parser = etree.XMLParser(
            resolve_entities=False,
            no_network=True,
            load_dtd=False,
            recover=False,
        )
        root = etree.fromstring(path.read_bytes(), parser=parser)
    except (OSError, etree.XMLSyntaxError) as exc:
        return [f"Fixture is not valid XML: {relative_path}: {exc}"], empty_shape

    statements = _elements(root, contract.statement_element)
    if len(statements) != 1:
        return [
            f"Fixture must contain exactly one {contract.statement_element}: "
            f"{relative_path}"
        ], empty_shape
    statement = statements[0]
    trades = _elements(root, contract.trade_element)
    corrections = _elements(root, contract.correction_element)
    cancels = _elements(root, contract.cancel_bust_element)

    generation: datetime | None = None
    coverage_start: date | None = None
    coverage_end: date | None = None
    try:
        generation = datetime.strptime(
            statement.attrib[contract.generation_field],
            contract.generation_time_format,
        )
    except (KeyError, ValueError):
        reasons.append(
            f"Fixture has invalid generation marker: {relative_path}"
        )
    try:
        coverage_start = datetime.strptime(
            statement.attrib[contract.from_date_field],
            contract.statement_date_format,
        ).date()
        coverage_end = datetime.strptime(
            statement.attrib[contract.to_date_field],
            contract.statement_date_format,
        ).date()
    except (KeyError, ValueError):
        reasons.append(f"Fixture has invalid statement coverage: {relative_path}")

    claimed = set(semantics)
    if "BASIC_EXECUTION_FIELDS" in claimed:
        required_trade_fields = (
            contract.execution_id_field,
            contract.transaction_id_field,
            contract.asset_category_field,
            contract.conid_field,
            contract.symbol_field,
            contract.exchange_field,
            contract.currency_field,
            contract.side_field,
            contract.quantity_field,
            contract.price_field,
            contract.trade_time_field,
            contract.open_close_field,
            contract.execution_status_field,
        )
        if not trades or not any(
            _required_attributes(trade, required_trade_fields)
            for trade in trades
        ):
            reasons.append(
                f"Fixture does not prove BASIC_EXECUTION_FIELDS: {relative_path}"
            )
    if "TRANSACTION_AND_OPEN_CLOSE" in claimed:
        if not trades or not any(
            _required_attributes(
                trade,
                (
                    contract.transaction_id_field,
                    contract.open_close_field,
                ),
            )
            for trade in trades
        ):
            reasons.append(
                "Fixture does not prove TRANSACTION_AND_OPEN_CLOSE: "
                f"{relative_path}"
            )
    if "COMMISSION_SIGN_CURRENCY" in claimed:
        if not trades or not any(
            _required_attributes(
                trade,
                (
                    contract.commission_field,
                    contract.commission_currency_field,
                ),
            )
            for trade in trades
        ):
            reasons.append(
                f"Fixture does not prove COMMISSION_SIGN_CURRENCY: {relative_path}"
            )
    if "CORRECTION_CANCEL_TARGETS" in claimed:
        changes = corrections + cancels
        if not changes or not all(
            _required_attributes(
                change,
                (
                    contract.change_event_id_field,
                    contract.affected_execution_id_field,
                ),
            )
            for change in changes
        ):
            reasons.append(
                f"Fixture does not prove CORRECTION_CANCEL_TARGETS: {relative_path}"
            )
    if "FLAT_BOUNDARY" in claimed:
        inception = (
            statement.attrib.get(contract.account_inception_date_field) or ""
        ).strip()
        snapshots = _elements(root, contract.open_positions_element)
        has_snapshot = any(
            (snapshot.attrib.get(contract.open_positions_snapshot_date_field) or "")
            .strip()
            for snapshot in snapshots
        )
        if not inception and not has_snapshot:
            reasons.append(
                f"Fixture does not prove FLAT_BOUNDARY: {relative_path}"
            )
    if "COVERAGE_INCLUSIVITY_TIMEZONE" in claimed and (
        coverage_start is None or coverage_end is None
    ):
        reasons.append(
            "Fixture does not prove COVERAGE_INCLUSIVITY_TIMEZONE: "
            f"{relative_path}"
        )

    return reasons, _FixtureShape(
        relative_path,
        generation,
        coverage_start,
        coverage_end,
    )


def read_provider_evidence_manifest(
    path: Path = EVIDENCE_PATH,
) -> IbkrFlexProviderEvidenceManifest:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return IbkrFlexProviderEvidenceManifest.model_validate(payload)
    except (OSError, json.JSONDecodeError, ValidationError) as exc:
        raise IbkrProviderEvidenceError(
            ("Provider evidence manifest is unreadable or invalid",)
        ) from exc


def _official_source_host_is_allowed(source: OfficialEvidenceSource) -> bool:
    parsed = urlparse(source.url)
    hostname = (parsed.hostname or "").lower()
    if (
        hostname == "interactivebrokers.com"
        or hostname.endswith(".interactivebrokers.com")
        or hostname == "ibkrguides.com"
        or hostname.endswith(".ibkrguides.com")
        or hostname == "ibkrcampus.com"
        or hostname.endswith(".ibkrcampus.com")
        or hostname == "interactivebrokers.github.io"
    ):
        return True
    path_parts = tuple(
        part.lower() for part in parsed.path.split("/") if part
    )
    return (
        hostname == "github.com"
        and bool(path_parts)
        and path_parts[0] == "interactivebrokers"
    )


def _validate_official_source(
    source: OfficialEvidenceSource,
    *,
    resolved_root: Path,
) -> tuple[list[str], set[str], set[str]]:
    reasons: list[str] = []
    parsed = urlparse(source.url)
    if parsed.scheme != "https":
        reasons.append(f"Official evidence must use HTTPS: {source.url}")
    if not _official_source_host_is_allowed(source):
        reasons.append(
            f"Official evidence must be hosted by IBKR: {source.url}"
        )
    if not SHA256_PATTERN.fullmatch(source.artifact_sha256):
        reasons.append(
            f"Invalid official artifact SHA-256: "
            f"{source.artifact_relative_path}"
        )
        return reasons, set(), set()
    artifact, path_reason = _evidence_path(
        relative_path=source.artifact_relative_path,
        resolved_root=resolved_root,
        label="Official evidence artifact",
    )
    if path_reason:
        reasons.append(path_reason)
        return reasons, set(), set()
    assert artifact is not None
    if _sha256(artifact) != source.artifact_sha256:
        reasons.append(
            f"Official evidence artifact hash mismatch: "
            f"{source.artifact_relative_path}"
        )
        return reasons, set(), set()
    try:
        artifact_text = artifact.read_text(encoding="utf-8")
    except (OSError, UnicodeError):
        reasons.append(
            f"Official evidence artifact must be retained as UTF-8 text: "
            f"{source.artifact_relative_path}"
        )
        return reasons, set(), set()

    verified_semantics: set[str] = set()
    verified_wire_tokens: set[str] = set()
    if not source.excerpts:
        reasons.append(
            f"Official evidence has no reviewed excerpts: {source.url}"
        )
    for excerpt in source.excerpts:
        if excerpt.semantic not in REQUIRED_SEMANTICS:
            reasons.append(
                f"Unknown official evidence semantic "
                f"{excerpt.semantic}: {source.url}"
            )
            continue
        if not excerpt.locator.strip() or not excerpt.quote.strip():
            reasons.append(
                f"Official evidence excerpt is incomplete for "
                f"{excerpt.semantic}: {source.url}"
            )
            continue
        if excerpt.quote not in artifact_text:
            reasons.append(
                f"Official evidence quote is absent from retained artifact "
                f"for {excerpt.semantic}: {source.url}"
            )
            continue
        invalid_tokens = sorted(
            token
            for token in excerpt.wire_tokens
            if not token.strip()
            or token not in excerpt.quote
            or token not in artifact_text
        )
        if invalid_tokens:
            reasons.append(
                "Official evidence wire tokens are absent from the retained "
                f"quote for {excerpt.semantic}: {source.url}: "
                + ", ".join(invalid_tokens)
            )
            continue
        verified_semantics.add(excerpt.semantic)
        verified_wire_tokens.update(excerpt.wire_tokens)
    if reasons:
        return reasons, set(), set()
    return reasons, verified_semantics, verified_wire_tokens


def required_provider_wire_tokens(
    contract: IbkrFlexFieldContract,
) -> set[str]:
    """Return provider-controlled XML names and values consumed by V1."""
    return {
        contract.statement_element,
        contract.events_container_element,
        contract.trade_element,
        contract.account_field,
        contract.from_date_field,
        contract.to_date_field,
        contract.generation_field,
        contract.execution_id_field,
        contract.transaction_id_field,
        contract.asset_category_field,
        contract.conid_field,
        contract.symbol_field,
        contract.exchange_field,
        contract.currency_field,
        contract.side_field,
        contract.quantity_field,
        contract.price_field,
        contract.trade_time_field,
        contract.open_close_field,
        contract.execution_status_field,
        contract.commission_field,
        contract.commission_currency_field,
        contract.correction_element,
        contract.cancel_bust_element,
        contract.change_event_id_field,
        contract.affected_execution_id_field,
        contract.account_inception_date_field,
        contract.open_positions_element,
        contract.open_position_element,
        contract.open_positions_snapshot_date_field,
        contract.open_position_quantity_field,
        "BUY",
        "SELL",
        "OPEN",
        "CLOSE",
    }


def verify_provider_evidence(
    manifest: IbkrFlexProviderEvidenceManifest,
    *,
    fixture_root: Path = FIXTURE_ROOT,
) -> VerifiedIbkrFlexProviderContract:
    reasons: list[str] = []
    if manifest.status != "VERIFIED":
        reasons.extend(
            manifest.unverified_reasons
            or ("Provider evidence manifest is not VERIFIED",)
        )
    if not manifest.query_template_id:
        reasons.append("Frozen query_template_id is missing")
    if not manifest.query_template_sha256 or not SHA256_PATTERN.fullmatch(
        manifest.query_template_sha256
    ):
        reasons.append("Frozen query template SHA-256 is missing or invalid")
    if manifest.field_contract is None:
        reasons.append("Frozen field contract is missing")

    resolved_root = fixture_root.resolve()
    if not manifest.query_template_relative_path:
        reasons.append("Frozen query template artifact path is missing")
    elif manifest.query_template_sha256 and SHA256_PATTERN.fullmatch(
        manifest.query_template_sha256
    ):
        template_path, reason = _evidence_path(
            relative_path=manifest.query_template_relative_path,
            resolved_root=resolved_root,
            label="Query template artifact",
        )
        if reason:
            reasons.append(reason)
        elif (
            template_path is not None
            and _sha256(template_path) != manifest.query_template_sha256
        ):
            reasons.append("Query template artifact hash mismatch")

    official_semantics: set[str] = set()
    official_wire_tokens: set[str] = set()
    for source in manifest.official_sources:
        (
            source_reasons,
            source_semantics,
            source_wire_tokens,
        ) = _validate_official_source(
            source,
            resolved_root=resolved_root,
        )
        reasons.extend(source_reasons)
        official_semantics.update(source_semantics)
        official_wire_tokens.update(source_wire_tokens)

    fixture_semantics: set[str] = set()
    fixture_shapes: list[tuple[RealFixtureEvidence, _FixtureShape]] = []
    for fixture in manifest.fixtures:
        fixture_semantics.update(fixture.semantics)
        if fixture.query_template_id != manifest.query_template_id:
            reasons.append(
                f"Fixture query template mismatch: {fixture.relative_path}"
            )
        if not SHA256_PATTERN.fullmatch(fixture.sha256):
            reasons.append(f"Invalid fixture SHA-256: {fixture.relative_path}")
            continue
        candidate, reason = _evidence_path(
            relative_path=fixture.relative_path,
            resolved_root=resolved_root,
            label="Fixture",
        )
        if reason:
            reasons.append(reason)
            continue
        assert candidate is not None
        if _sha256(candidate) != fixture.sha256:
            reasons.append(f"Fixture hash mismatch: {fixture.relative_path}")
            continue
        if manifest.field_contract is not None:
            semantic_reasons, shape = _validate_fixture_semantics(
                candidate,
                relative_path=fixture.relative_path,
                semantics=fixture.semantics,
                contract=manifest.field_contract,
            )
            reasons.extend(semantic_reasons)
            fixture_shapes.append((fixture, shape))

    generation_shapes = [
        shape
        for fixture, shape in fixture_shapes
        if "GENERATION_ORDERING" in fixture.semantics
        and shape.generation is not None
        and shape.coverage_start is not None
        and shape.coverage_end is not None
    ]
    generation_pair_proven = any(
        left.generation != right.generation
        and left.coverage_start <= right.coverage_end
        and right.coverage_start <= left.coverage_end
        for index, left in enumerate(generation_shapes)
        for right in generation_shapes[index + 1 :]
    )
    if "GENERATION_ORDERING" in fixture_semantics and not generation_pair_proven:
        reasons.append(
            "Real fixtures do not include an overlapping pair with distinct "
            "generation markers"
        )

    missing_official = sorted(REQUIRED_SEMANTICS - official_semantics)
    if missing_official:
        reasons.append(
            "Official evidence missing semantics: "
            + ", ".join(missing_official)
        )
    if manifest.field_contract is not None:
        missing_wire_tokens = sorted(
            required_provider_wire_tokens(manifest.field_contract)
            - official_wire_tokens
        )
        if missing_wire_tokens:
            reasons.append(
                "Official evidence missing exact provider wire tokens: "
                + ", ".join(missing_wire_tokens)
            )
    missing_fixture = sorted(REQUIRED_SEMANTICS - fixture_semantics)
    if missing_fixture:
        reasons.append(
            "Real fixtures missing semantics: " + ", ".join(missing_fixture)
        )

    if reasons:
        raise IbkrProviderEvidenceError(tuple(dict.fromkeys(reasons)))

    assert manifest.query_template_id is not None
    assert manifest.query_template_sha256 is not None
    assert manifest.field_contract is not None
    return VerifiedIbkrFlexProviderContract(
        query_template_id=manifest.query_template_id,
        query_template_sha256=manifest.query_template_sha256,
        field_contract=manifest.field_contract,
        official_sources=manifest.official_sources,
        fixtures=manifest.fixtures,
    )


def require_verified_ibkr_flex_provider_contract(
) -> VerifiedIbkrFlexProviderContract:
    return verify_provider_evidence(read_provider_evidence_manifest())
