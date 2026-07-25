"""Session-only preview for first-time IBKR source bootstrap."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy.orm import Session

from app_config.ibkr_flex_provider_evidence import (
    VerifiedIbkrFlexProviderContract,
)
from models import (
    AccountLedgerEntry,
    AccountingHealth,
    ExternalTradeApplication,
    ImportAdapterKind,
    ImportRow,
    ImportSession,
    ImportSessionStatus,
    ImportSourceBinding,
    LedgerPostingKind,
    Position,
    PositionEvent,
    TradeSourceState,
    TradingAccount,
    TradingPosition,
    Transaction,
)
from services.generic_import_service import transition_import_session
from services.ibkr_flex_identity_service import (
    IbkrFlexIdentityError,
    derive_ibkr_instrument_identity,
    ibkr_ambiguous_order_keys,
    ibkr_group_key,
    ibkr_provisional_direction,
)
from services.ibkr_flex_parser import (
    NormalizedIbkrFlexEvent,
    ParsedIbkrFlexStatement,
)
from services.trade_lifecycle_simulation_service import (
    LifecycleSimulationError,
    derive_broker_lifecycle_step,
)


BOOTSTRAP_PREVIEW_SCHEMA_VERSION = 1
ALLOWED_PRE_BIND_POSTING_KINDS = frozenset(
    {
        LedgerPostingKind.OPENING_BALANCE.value,
        LedgerPostingKind.DEPOSIT.value,
        LedgerPostingKind.WITHDRAWAL.value,
        LedgerPostingKind.INTEREST.value,
        LedgerPostingKind.ACCOUNT_FEE.value,
    }
)


class IbkrBootstrapPreviewError(ValueError):
    def __init__(self, code: str, message: str, *, http_status: int = 422):
        self.code = code
        self.http_status = http_status
        super().__init__(message)


@dataclass(frozen=True)
class BootstrapPreviewItem:
    row_number: int
    external_source_event_id: str
    source_payload_fingerprint: str
    classification: str
    economic_execution_id: str | None
    direction: str | None
    action: str | None
    pre_quantity: Decimal | None
    post_quantity: Decimal | None
    conflict_reason: str | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class BootstrapPreviewResult:
    session_public_id: str
    account_public_id: str
    masked_external_account_ref: str
    status: str
    flat_boundary_evidence: str
    source_preview_schema_version: int
    source_preview_digest: str
    effective_execution_count: int
    accepted_tombstone_count: int
    conflict_reason: str | None
    items: tuple[BootstrapPreviewItem, ...]


@dataclass
class _Lineage:
    economic_execution_id: str
    nodes: list[NormalizedIbkrFlexEvent]
    current: NormalizedIbkrFlexEvent
    tombstoned: bool = False


def _enum_value(value: object) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _order_key(event: NormalizedIbkrFlexEvent) -> tuple[Any, ...]:
    return (
        _as_utc(event.occurred_at_utc),
        int(event.transaction_id),
        event.external_source_event_id,
        event.source_payload_fingerprint,
    )


def _decimal_text(value: Decimal) -> str:
    return format(value.normalize(), "f")


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _require_owner_graph(
    db: Session,
    *,
    account: TradingAccount,
    session: ImportSession,
    parsed: ParsedIbkrFlexStatement,
    provider_contract: VerifiedIbkrFlexProviderContract,
) -> dict[str, Any]:
    if not isinstance(provider_contract, VerifiedIbkrFlexProviderContract):
        raise IbkrBootstrapPreviewError(
            "IBKR_PROVIDER_CONTRACT_UNVERIFIED",
            "IBKR provider contract must be verified before preview",
            http_status=404,
        )
    if (
        session.user_id != account.user_id
        or session.account_id != account.id
    ):
        raise IbkrBootstrapPreviewError(
            "IMPORT_SESSION_NOT_FOUND",
            "IBKR preview graph is not owner-bound",
            http_status=404,
        )
    if session.adapter_kind != ImportAdapterKind.IBKR_FLEX_XML_V1.value:
        raise IbkrBootstrapPreviewError(
            "SOURCE_ADAPTER_MISMATCH",
            "IBKR bootstrap requires the frozen Flex adapter",
            http_status=409,
        )
    if session.status != ImportSessionStatus.UPLOADING.value:
        raise IbkrBootstrapPreviewError(
            "IMPORT_SESSION_STATE_CONFLICT",
            "IBKR preview session is not uploading",
            http_status=409,
        )
    if not account.is_active:
        raise IbkrBootstrapPreviewError(
            "ACCOUNT_ARCHIVED",
            "Archived accounts are read-only",
            http_status=409,
        )
    if (
        _enum_value(account.accounting_health)
        != AccountingHealth.HEALTHY.value
    ):
        raise IbkrBootstrapPreviewError(
            "ACCOUNTING_RECONCILIATION_REQUIRED",
            "Account accounting must be healthy before source bootstrap",
            http_status=409,
        )
    if (
        _enum_value(account.trade_source_state)
        != TradeSourceState.CLEAN.value
    ):
        raise IbkrBootstrapPreviewError(
            "SOURCE_BOOTSTRAP_NOT_ELIGIBLE",
            "First source preview requires a CLEAN account",
            http_status=409,
        )
    history_checks = (
        db.query(TradingPosition.id).filter(
            TradingPosition.user_id == account.user_id,
            TradingPosition.account_id == account.id,
        ),
        db.query(Position.id).filter(
            Position.user_id == account.user_id,
            Position.account_id == account.id,
        ),
        db.query(PositionEvent.id).filter(
            PositionEvent.user_id == account.user_id,
            PositionEvent.account_id == account.id,
        ),
        db.query(ExternalTradeApplication.id).filter(
            ExternalTradeApplication.user_id == account.user_id,
            ExternalTradeApplication.account_id == account.id,
        ),
        db.query(ImportSourceBinding.id).filter(
            ImportSourceBinding.account_id == account.id,
        ),
        db.query(ImportSession.id).filter(
            ImportSession.user_id == account.user_id,
            ImportSession.account_id == account.id,
            ImportSession.id != session.id,
            ImportSession.status == ImportSessionStatus.COMPLETED.value,
        ),
    )
    if any(query.first() is not None for query in history_checks):
        raise IbkrBootstrapPreviewError(
            "SOURCE_BOOTSTRAP_NOT_ELIGIBLE",
            "Account already has trade or source history",
            http_status=409,
        )
    disallowed_cash_fact = db.query(AccountLedgerEntry.id).filter(
        AccountLedgerEntry.user_id == account.user_id,
        AccountLedgerEntry.account_id == account.id,
        (
            AccountLedgerEntry.posting_kind.notin_(
                tuple(ALLOWED_PRE_BIND_POSTING_KINDS)
            )
            | (AccountLedgerEntry.currency != account.currency)
        ),
    ).first()
    wrong_currency_transaction = db.query(Transaction.id).filter(
        Transaction.account_id == account.id,
        Transaction.currency != account.currency,
    ).first()
    if (
        disallowed_cash_fact is not None
        or wrong_currency_transaction is not None
    ):
        raise IbkrBootstrapPreviewError(
            "SOURCE_BOOTSTRAP_NOT_ELIGIBLE",
            "Account has incompatible pre-bind financial history",
            http_status=409,
        )
    identity_conflict = db.query(ImportSourceBinding.id).filter(
        ImportSourceBinding.user_id == account.user_id,
        ImportSourceBinding.adapter_kind
        == ImportAdapterKind.IBKR_FLEX_XML_V1.value,
        ImportSourceBinding.normalized_external_account_ref
        == parsed.normalized_external_account_ref,
    ).first()
    if identity_conflict is not None:
        raise IbkrBootstrapPreviewError(
            "SOURCE_EXTERNAL_ACCOUNT_ALREADY_BOUND",
            "IBKR external account is already bound",
            http_status=409,
        )
    return {
        "account_public_id": account.public_id,
        "is_active": bool(account.is_active),
        "accounting_health": _enum_value(account.accounting_health),
        "trade_source_state": _enum_value(account.trade_source_state),
        "hard_delete_eligible": bool(account.hard_delete_eligible),
        "cash_transaction_count": db.query(Transaction.id).filter(
            Transaction.account_id == account.id
        ).count(),
        "cash_ledger_count": db.query(AccountLedgerEntry.id).filter(
            AccountLedgerEntry.user_id == account.user_id,
            AccountLedgerEntry.account_id == account.id,
        ).count(),
    }


def _unique_events(
    events: tuple[NormalizedIbkrFlexEvent, ...],
) -> tuple[
    list[NormalizedIbkrFlexEvent],
    dict[tuple[str, str], int],
]:
    unique: dict[
        tuple[str, str],
        NormalizedIbkrFlexEvent,
    ] = {}
    counts: dict[tuple[str, str], int] = {}
    for event in events:
        key = (
            event.external_source_event_id,
            event.source_payload_fingerprint,
        )
        unique.setdefault(key, event)
        counts[key] = counts.get(key, 0) + 1
    return sorted(unique.values(), key=_order_key), counts


def _fold_change_chains(
    events: list[NormalizedIbkrFlexEvent],
) -> tuple[
    list[_Lineage],
    dict[tuple[str, str], str],
    str | None,
]:
    by_identity: dict[str, _Lineage] = {}
    lineages: list[_Lineage] = []
    classifications: dict[tuple[str, str], str] = {}
    conflict_reason: str | None = None

    for event in events:
        key = (
            event.external_source_event_id,
            event.source_payload_fingerprint,
        )
        if event.event_kind == "TRADE":
            if event.external_source_event_id in by_identity:
                conflict_reason = "PAYLOAD_ID_COLLISION"
                break
            lineage = _Lineage(
                economic_execution_id=event.external_source_event_id,
                nodes=[event],
                current=event,
            )
            lineages.append(lineage)
            by_identity[event.external_source_event_id] = lineage
            continue

        target_id = event.affected_external_execution_id
        if target_id is None or target_id not in by_identity:
            conflict_reason = "TARGET_UNRESOLVED"
            break
        lineage = by_identity[target_id]
        if lineage.tombstoned:
            conflict_reason = "CHANGE_AFTER_TOMBSTONE"
            break
        if _order_key(event) <= _order_key(lineage.current):
            conflict_reason = "AMBIGUOUS_CHANGE_ORDER"
            break
        existing = by_identity.get(event.external_source_event_id)
        if existing is not None and existing is not lineage:
            conflict_reason = "PAYLOAD_ID_COLLISION"
            break

        lineage.nodes.append(event)
        lineage.current = event
        by_identity[event.external_source_event_id] = lineage
        if event.event_kind == "CANCEL_BUST":
            lineage.tombstoned = True

    if conflict_reason is not None:
        return lineages, classifications, conflict_reason

    for lineage in lineages:
        for node in lineage.nodes[:-1]:
            classifications[
                (
                    node.external_source_event_id,
                    node.source_payload_fingerprint,
                )
            ] = "BOOTSTRAP_SUPERSEDED"
        winner = lineage.nodes[-1]
        classifications[
            (
                winner.external_source_event_id,
                winner.source_payload_fingerprint,
            )
        ] = (
            "BOOTSTRAP_ACCEPTED_TOMBSTONE"
            if lineage.tombstoned
            else "BOOTSTRAP_EFFECTIVE_NEW"
        )
    return lineages, classifications, None


def _simulate_effective_units(
    lineages: list[_Lineage],
) -> tuple[
    dict[tuple[str, str], dict[str, Any]],
    str | None,
]:
    quantities: dict[tuple[str, ...], Decimal] = {}
    applications: dict[tuple[str, str], dict[str, Any]] = {}
    active = sorted(
        (lineage for lineage in lineages if not lineage.tombstoned),
        key=lambda lineage: _order_key(lineage.current),
    )
    for lineage in active:
        event = lineage.current
        try:
            identity = derive_ibkr_instrument_identity(event)
        except IbkrFlexIdentityError as exc:
            return {}, exc.code
        provisional_direction = ibkr_provisional_direction(event)
        group = ibkr_group_key(identity, provisional_direction)
        try:
            step = derive_broker_lifecycle_step(
                current_quantity=quantities.get(group, Decimal("0")),
                side=event.raw_side,
                open_close=event.raw_open_close,
                quantity=event.quantity,
            )
        except LifecycleSimulationError:
            return {}, "UNSUPPORTED_CROSS_ZERO"
        quantities[group] = step.post_quantity
        applications[
            (
                event.external_source_event_id,
                event.source_payload_fingerprint,
            )
        ] = {
            "economic_execution_id": lineage.economic_execution_id,
            "instrument_identity": identity,
            "direction": step.direction,
            "action": step.action,
            "pre_quantity": step.pre_quantity,
            "post_quantity": step.post_quantity,
        }
    return applications, None


def _persist_rows(
    db: Session,
    *,
    session: ImportSession,
    parsed: ParsedIbkrFlexStatement,
    items: list[BootstrapPreviewItem],
) -> None:
    existing = {
        row.row_number: row
        for row in db.query(ImportRow).filter(
            ImportRow.session_id == session.id
        )
    }
    events = {event.row_number: event for event in parsed.events}
    for item in items:
        event = events[item.row_number]
        normalized = {
            key: value
            for key, value in event.normalized_payload.items()
            if key != "normalized_external_account_ref"
        }
        normalized.update(
            {
                "masked_external_account_ref": (
                    parsed.masked_external_account_ref
                ),
                "classification": item.classification,
                "economic_execution_id": item.economic_execution_id,
                "derived_direction": item.direction,
                "derived_action": item.action,
                "pre_quantity": (
                    _decimal_text(item.pre_quantity)
                    if item.pre_quantity is not None
                    else None
                ),
                "post_quantity": (
                    _decimal_text(item.post_quantity)
                    if item.post_quantity is not None
                    else None
                ),
                "conflict_reason": item.conflict_reason,
            }
        )
        values = {
            "raw_values_json": {
                "event_kind": event.event_kind,
                "external_source_event_id": (
                    event.external_source_event_id
                ),
                "source_payload_fingerprint": (
                    event.source_payload_fingerprint
                ),
            },
            "normalized_values_json": normalized,
            "validation_errors_json": (
                [
                    {
                        "code": "SOURCE_BOOTSTRAP_CONFLICT",
                        "message": item.conflict_reason,
                    }
                ]
                if item.conflict_reason
                else []
            ),
            "warnings_json": list(item.warnings),
            "is_valid": item.conflict_reason is None,
        }
        row = existing.get(item.row_number)
        if row is None:
            db.add(
                ImportRow(
                    session_id=session.id,
                    user_id=session.user_id,
                    account_id=session.account_id,
                    adapter_kind=session.adapter_kind,
                    file_hash=session.file_hash,
                    row_number=item.row_number,
                    **values,
                )
            )
        else:
            for field, value in values.items():
                setattr(row, field, value)


def preview_ibkr_source_bootstrap(
    db: Session,
    *,
    account: TradingAccount,
    session: ImportSession,
    parsed: ParsedIbkrFlexStatement,
    provider_contract: VerifiedIbkrFlexProviderContract,
    now: datetime | None = None,
) -> BootstrapPreviewResult:
    eligibility = _require_owner_graph(
        db,
        account=account,
        session=session,
        parsed=parsed,
        provider_contract=provider_contract,
    )
    for event in parsed.events:
        if event.currency != account.currency:
            raise IbkrBootstrapPreviewError(
                "ACCOUNT_CURRENCY_MISMATCH",
                "IBKR execution currency must equal account currency",
            )

    unique_events, duplicate_counts = _unique_events(parsed.events)
    first_row_by_key: dict[tuple[str, str], int] = {}
    for event in parsed.events:
        first_row_by_key.setdefault(
            (
                event.external_source_event_id,
                event.source_payload_fingerprint,
            ),
            event.row_number,
        )
    try:
        ambiguous_order_keys = ibkr_ambiguous_order_keys(unique_events)
    except IbkrFlexIdentityError as exc:
        ambiguous_order_keys = frozenset()
        conflict_reason = exc.code
    else:
        conflict_reason = (
            "UNSUPPORTED_ORDER_CONFLICT"
            if ambiguous_order_keys
            else None
        )
    if conflict_reason is None:
        lineages, classifications, conflict_reason = _fold_change_chains(
            unique_events
        )
    else:
        lineages = []
        classifications = {}
    applications: dict[tuple[str, str], dict[str, Any]] = {}
    if conflict_reason is None:
        applications, conflict_reason = _simulate_effective_units(lineages)
    if (
        conflict_reason is None
        and parsed.flat_boundary_evidence == "UNPROVEN"
    ):
        conflict_reason = "FLAT_BOUNDARY_UNPROVEN"

    lineage_by_node: dict[tuple[str, str], _Lineage] = {}
    for lineage in lineages:
        for node in lineage.nodes:
            lineage_by_node[
                (
                    node.external_source_event_id,
                    node.source_payload_fingerprint,
                )
            ] = lineage
    items: list[BootstrapPreviewItem] = []
    for event in parsed.events:
        key = (
            event.external_source_event_id,
            event.source_payload_fingerprint,
        )
        application = applications.get(key)
        lineage = lineage_by_node.get(key)
        warnings = (
            ("DUPLICATE_SOURCE_EVENT",)
            if duplicate_counts[key] > 1
            and event.row_number != first_row_by_key[key]
            else ()
        )
        items.append(
            BootstrapPreviewItem(
                row_number=event.row_number,
                external_source_event_id=event.external_source_event_id,
                source_payload_fingerprint=(
                    event.source_payload_fingerprint
                ),
                classification=(
                    "SOURCE_BOOTSTRAP_CONFLICT"
                    if conflict_reason
                    else classifications[key]
                ),
                economic_execution_id=(
                    application["economic_execution_id"]
                    if application
                    else (
                        lineage.economic_execution_id
                        if lineage
                        else None
                    )
                ),
                direction=(
                    application["direction"] if application else None
                ),
                action=application["action"] if application else None,
                pre_quantity=(
                    application["pre_quantity"] if application else None
                ),
                post_quantity=(
                    application["post_quantity"] if application else None
                ),
                conflict_reason=conflict_reason,
                warnings=warnings,
            )
        )

    payload = {
        "schema_version": BOOTSTRAP_PREVIEW_SCHEMA_VERSION,
        "account_eligibility": eligibility,
        "account_eligibility_hash": _canonical_digest(eligibility),
        "external_account_identity_hash": (
            "sha256:"
            + hashlib.sha256(
                parsed.normalized_external_account_ref.encode("ascii")
            ).hexdigest()
        ),
        "statement": {
            "generation_order_key": parsed.generation_order_key,
            "coverage_start": parsed.coverage_start.isoformat(),
            "coverage_end_exclusive": (
                parsed.coverage_end_exclusive.isoformat()
            ),
            "source_timezone": parsed.source_timezone,
            "flat_boundary_evidence": parsed.flat_boundary_evidence,
            "account_inception_date": (
                parsed.account_inception_date.isoformat()
                if parsed.account_inception_date
                else None
            ),
            "open_positions_snapshot_date": (
                parsed.open_positions_snapshot_date.isoformat()
                if parsed.open_positions_snapshot_date
                else None
            ),
            "open_positions_nonzero_count": (
                parsed.open_positions_nonzero_count
            ),
        },
        "folded_items": [],
    }
    item_by_key = {
        (
            item.external_source_event_id,
            item.source_payload_fingerprint,
        ): item
        for item in items
    }
    for event in unique_events:
        key = (
            event.external_source_event_id,
            event.source_payload_fingerprint,
        )
        item = item_by_key[key]
        payload["folded_items"].append(
            {
                "event_kind": event.event_kind,
                "external_source_event_id": item.external_source_event_id,
                "source_payload_fingerprint": (
                    item.source_payload_fingerprint
                ),
                "source_order_key": event.source_order_key,
                "occurred_at_utc": _as_utc(
                    event.occurred_at_utc
                ).isoformat(),
                "quantity": _decimal_text(event.quantity),
                "price": _decimal_text(event.price),
                "normalized_fee": _decimal_text(event.normalized_fee),
                "classification": item.classification,
                "economic_execution_id": item.economic_execution_id,
                "direction": item.direction,
                "action": item.action,
                "pre_quantity": (
                    _decimal_text(item.pre_quantity)
                    if item.pre_quantity is not None
                    else None
                ),
                "post_quantity": (
                    _decimal_text(item.post_quantity)
                    if item.post_quantity is not None
                    else None
                ),
                "conflict_reason": item.conflict_reason,
                "duplicate_count": duplicate_counts[key],
            }
        )
    digest = _canonical_digest(payload)
    session.source_preview_schema_version = BOOTSTRAP_PREVIEW_SCHEMA_VERSION
    session.source_preview_digest = digest
    _persist_rows(
        db,
        session=session,
        parsed=parsed,
        items=items,
    )
    session.total_rows = len(items)
    session.valid_rows = sum(item.conflict_reason is None for item in items)
    session.error_rows = len(items) - session.valid_rows
    session.warning_rows = sum(bool(item.warnings) for item in items)

    if conflict_reason:
        status = ImportSessionStatus.CONFLICTED.value
        session.error_code = (
            "SOURCE_FLAT_BOUNDARY_UNPROVEN"
            if conflict_reason == "FLAT_BOUNDARY_UNPROVEN"
            else "SOURCE_BOOTSTRAP_CONFLICT"
        )
        session.error_message = conflict_reason
    else:
        status = ImportSessionStatus.PREVIEW_READY.value
        session.error_code = None
        session.error_message = None
    transition_import_session(
        db,
        session=session,
        from_status=ImportSessionStatus.UPLOADING.value,
        to_status=status,
        now=now,
    )
    db.flush()
    return BootstrapPreviewResult(
        session_public_id=session.public_id,
        account_public_id=account.public_id,
        masked_external_account_ref=parsed.masked_external_account_ref,
        status=status,
        flat_boundary_evidence=parsed.flat_boundary_evidence,
        source_preview_schema_version=BOOTSTRAP_PREVIEW_SCHEMA_VERSION,
        source_preview_digest=digest,
        effective_execution_count=sum(
            not lineage.tombstoned for lineage in lineages
        ) if conflict_reason is None else 0,
        accepted_tombstone_count=sum(
            lineage.tombstoned for lineage in lineages
        ) if conflict_reason is None else 0,
        conflict_reason=conflict_reason,
        items=tuple(items),
    )
