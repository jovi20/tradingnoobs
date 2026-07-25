"""Machine-verifiable provider evidence gate for IBKR Flex XML V1."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import hashlib
import json
from pathlib import Path
import re
from typing import Literal
from urllib.parse import urlparse

from pydantic import BaseModel, ConfigDict


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
    execution_time_format: str
    execution_time_semantics: Literal["SOURCE_TIMEZONE_NAIVE"]
    ordinary_trade_kind_from_element: Literal[True]
    correction_element: str
    cancel_bust_element: str
    change_event_id_field: str
    affected_execution_id_field: str


class OfficialEvidenceSource(_EvidenceModel):
    url: str
    title: str
    retrieved_at: date
    semantics: tuple[str, ...]


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


def read_provider_evidence_manifest(
    path: Path = EVIDENCE_PATH,
) -> IbkrFlexProviderEvidenceManifest:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return IbkrFlexProviderEvidenceManifest.model_validate(payload)


def _official_source_reason(source: OfficialEvidenceSource) -> str | None:
    parsed = urlparse(source.url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https":
        return f"Official evidence must use HTTPS: {source.url}"
    if not (
        hostname == "interactivebrokers.com"
        or hostname.endswith(".interactivebrokers.com")
    ):
        return f"Official evidence must be hosted by IBKR: {source.url}"
    return None


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

    official_semantics: set[str] = set()
    for source in manifest.official_sources:
        official_semantics.update(source.semantics)
        reason = _official_source_reason(source)
        if reason:
            reasons.append(reason)

    fixture_semantics: set[str] = set()
    resolved_root = fixture_root.resolve()
    for fixture in manifest.fixtures:
        fixture_semantics.update(fixture.semantics)
        if fixture.query_template_id != manifest.query_template_id:
            reasons.append(
                f"Fixture query template mismatch: {fixture.relative_path}"
            )
        if not SHA256_PATTERN.fullmatch(fixture.sha256):
            reasons.append(f"Invalid fixture SHA-256: {fixture.relative_path}")
            continue
        candidate = (resolved_root / fixture.relative_path).resolve()
        if not candidate.is_relative_to(resolved_root):
            reasons.append(
                f"Fixture escapes the evidence root: {fixture.relative_path}"
            )
            continue
        if not candidate.is_file():
            reasons.append(f"Fixture is missing: {fixture.relative_path}")
            continue
        if _sha256(candidate) != fixture.sha256:
            reasons.append(f"Fixture hash mismatch: {fixture.relative_path}")

    missing_official = sorted(REQUIRED_SEMANTICS - official_semantics)
    if missing_official:
        reasons.append(
            "Official evidence missing semantics: "
            + ", ".join(missing_official)
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
