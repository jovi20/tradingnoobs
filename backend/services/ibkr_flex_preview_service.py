"""Owner-bound persistent preview for an existing IBKR source binding."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session

from app_config.ibkr_flex_provider_evidence import (
    VerifiedIbkrFlexProviderContract,
)
from models import (
    ExternalExecution,
    ExternalSourceObservation,
    ExternalTradeApplication,
    ImportAdapterKind,
    ImportRow,
    ImportSession,
    ImportSessionStatus,
    ImportSourceBinding,
    SourceReconciliationCase,
    SourceStatement,
    StatementExecutionSighting,
    TradeSourceState,
    TradingAccount,
)
from services.generic_import_service import transition_import_session
from services.ibkr_flex_parser import (
    NormalizedIbkrFlexEvent,
    ParsedIbkrFlexStatement,
    SOURCE_FINGERPRINT_VERSION,
)
from services.ibkr_flex_identity_service import (
    IbkrFlexIdentityError,
    derive_ibkr_instrument_identity,
    ibkr_direction_from_source_fields,
    ibkr_group_key,
    ibkr_provisional_direction,
)
from services.source_reconciliation_service import (
    NONTERMINAL_CASE_STATES,
    build_source_case_snapshot,
    create_or_attach_source_case,
    recompute_source_health,
    supersede_source_case_with_later_sighting,
)
from services.source_preview_projection_service import (
    SourcePreviewProjectionError,
    build_source_preview_projection,
)
from services.trade_lifecycle_simulation_service import (
    LifecycleSimulationError,
    LifecycleStep,
    derive_broker_lifecycle_step,
)


CONFLICT_CLASSIFICATIONS = frozenset(
    {
        "SOURCE_PAYLOAD_CONFLICT",
        "LATE_NEW",
        "CORRECTION",
        "CANCEL_BUST",
        "TARGET_UNRESOLVED",
        "SOURCE_GENERATION_CONFLICT",
        "UNSUPPORTED_CROSS_ZERO",
        "UNSUPPORTED_ORDER_CONFLICT",
    }
)
class IbkrFlexPreviewError(ValueError):
    def __init__(self, code: str, message: str, *, http_status: int = 422):
        self.code = code
        self.http_status = http_status
        super().__init__(message)


@dataclass(frozen=True)
class BoundPreviewItem:
    row_number: int
    external_source_event_id: str
    observation_public_id: str
    sighting_public_id: str
    classification: str
    direction: str | None
    action: str | None
    pre_quantity: Decimal | None
    post_quantity: Decimal | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class BoundPreviewResult:
    session_public_id: str
    statement_public_id: str
    binding_public_id: str
    masked_external_account_ref: str
    status: str
    source_health: str
    source_completeness: str
    coverage_gap: bool
    source_preview_schema_version: int
    source_preview_digest: str
    pending_statement_count: int
    pending_execution_count: int
    items: tuple[BoundPreviewItem, ...]


@dataclass(frozen=True)
class _PersistedEvent:
    event: NormalizedIbkrFlexEvent
    observation: ExternalSourceObservation
    sighting: StatementExecutionSighting
    observation_known_before: bool
    sighting_known_before: bool
    duplicate_in_statement: bool


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _instrument_identity(event: NormalizedIbkrFlexEvent) -> dict[str, str]:
    try:
        return derive_ibkr_instrument_identity(event)
    except IbkrFlexIdentityError as exc:
        raise IbkrFlexPreviewError(exc.code, str(exc)) from exc


def _group_key(
    identity: dict[str, str],
    direction: str,
) -> tuple[str, ...]:
    return ibkr_group_key(identity, direction)


def _event_order_key(
    event: NormalizedIbkrFlexEvent,
) -> tuple[datetime, int, str]:
    return (
        _as_utc(event.occurred_at_utc),
        int(event.transaction_id),
        event.external_source_event_id,
    )


def _observation_order_key(
    observation: ExternalSourceObservation,
) -> tuple[datetime, int, str]:
    return (
        _as_utc(observation.occurred_at),
        int(observation.transaction_id),
        (
            observation.external_execution_id
            or observation.external_source_event_id
        ),
    )


def _require_owner_graph(
    *,
    account: TradingAccount,
    binding: ImportSourceBinding,
    session: ImportSession,
    parsed: ParsedIbkrFlexStatement,
    provider_contract: VerifiedIbkrFlexProviderContract,
) -> None:
    if not isinstance(provider_contract, VerifiedIbkrFlexProviderContract):
        raise IbkrFlexPreviewError(
            "IBKR_PROVIDER_CONTRACT_UNVERIFIED",
            "IBKR provider contract must be verified before preview",
            http_status=404,
        )
    if (
        session.user_id != account.user_id
        or session.account_id != account.id
        or binding.user_id != account.user_id
        or binding.account_id != account.id
    ):
        raise IbkrFlexPreviewError(
            "IMPORT_SESSION_NOT_FOUND",
            "IBKR preview graph is not owner-bound",
            http_status=404,
        )
    if (
        session.adapter_kind != ImportAdapterKind.IBKR_FLEX_XML_V1.value
        or binding.adapter_kind != ImportAdapterKind.IBKR_FLEX_XML_V1.value
    ):
        raise IbkrFlexPreviewError(
            "SOURCE_ADAPTER_MISMATCH",
            "IBKR preview requires the frozen Flex adapter",
            http_status=409,
        )
    if session.status != ImportSessionStatus.UPLOADING.value:
        raise IbkrFlexPreviewError(
            "IMPORT_SESSION_STATE_CONFLICT",
            "IBKR preview session is not uploading",
            http_status=409,
        )
    if not account.is_active or binding.archived_at is not None:
        raise IbkrFlexPreviewError(
            "ACCOUNT_ARCHIVED",
            "Archived source accounts are read-only",
            http_status=409,
        )
    if account.trade_source_state != TradeSourceState.SOURCE_BOUND.value:
        raise IbkrFlexPreviewError(
            "SOURCE_BINDING_STATE_MISMATCH",
            "Existing-binding preview requires a source-bound account",
            http_status=409,
        )
    if (
        parsed.normalized_external_account_ref
        != binding.normalized_external_account_ref
        or parsed.source_timezone != binding.source_timezone
    ):
        raise IbkrFlexPreviewError(
            "ACCOUNT_MISMATCH",
            "Statement source identity does not match the account binding",
            http_status=409,
        )


def _get_or_create_statement(
    db: Session,
    *,
    binding: ImportSourceBinding,
    session: ImportSession,
    parsed: ParsedIbkrFlexStatement,
) -> SourceStatement:
    statement = (
        db.query(SourceStatement)
        .filter(
            SourceStatement.binding_id == binding.id,
            SourceStatement.file_hash == session.file_hash,
        )
        .one_or_none()
    )
    if statement is not None:
        immutable_values = (
            statement.statement_generation,
            statement.generation_order_key,
            statement.coverage_start,
            statement.coverage_end_exclusive,
            statement.normalized_external_account_ref,
        )
        parsed_values = (
            parsed.statement_generation,
            parsed.generation_order_key,
            parsed.coverage_start,
            parsed.coverage_end_exclusive,
            parsed.normalized_external_account_ref,
        )
        if immutable_values != parsed_values:
            raise IbkrFlexPreviewError(
                "SOURCE_FILE_HASH_CONFLICT",
                "Existing source file hash has different statement content",
                http_status=409,
            )
        return statement

    statement = SourceStatement(
        binding_id=binding.id,
        user_id=binding.user_id,
        account_id=binding.account_id,
        import_session_id=session.id,
        file_hash=session.file_hash,
        statement_generation=parsed.statement_generation,
        generation_order_key=parsed.generation_order_key,
        raw_from_date=parsed.raw_from_date,
        raw_to_date=parsed.raw_to_date,
        coverage_start=parsed.coverage_start,
        coverage_end_exclusive=parsed.coverage_end_exclusive,
        source_timezone=parsed.source_timezone,
        normalized_external_account_ref=(
            parsed.normalized_external_account_ref
        ),
    )
    db.add(statement)
    db.flush()
    return statement


def _has_conflicting_generation(
    db: Session,
    *,
    binding: ImportSourceBinding,
    statement: SourceStatement,
) -> bool:
    return (
        db.query(SourceStatement.id)
        .filter(
            SourceStatement.binding_id == binding.id,
            SourceStatement.generation_order_key
            == statement.generation_order_key,
            SourceStatement.id != statement.id,
            SourceStatement.file_hash != statement.file_hash,
        )
        .first()
        is not None
    )


def _get_or_create_observation(
    db: Session,
    *,
    binding: ImportSourceBinding,
    event: NormalizedIbkrFlexEvent,
    identity: dict[str, str],
) -> tuple[ExternalSourceObservation, bool]:
    observation = (
        db.query(ExternalSourceObservation)
        .filter(
            ExternalSourceObservation.binding_id == binding.id,
            ExternalSourceObservation.external_source_event_id
            == event.external_source_event_id,
            ExternalSourceObservation.fingerprint_version
            == SOURCE_FINGERPRINT_VERSION,
            ExternalSourceObservation.source_payload_fingerprint
            == event.source_payload_fingerprint,
        )
        .one_or_none()
    )
    if observation is not None:
        return observation, True

    observation = ExternalSourceObservation(
        binding_id=binding.id,
        user_id=binding.user_id,
        account_id=binding.account_id,
        event_kind=event.event_kind,
        external_source_event_id=event.external_source_event_id,
        external_execution_id=event.external_execution_id,
        affected_external_execution_id=event.affected_external_execution_id,
        provider_declared_target_id=event.affected_external_execution_id,
        fingerprint_version=SOURCE_FINGERPRINT_VERSION,
        source_payload_fingerprint=event.source_payload_fingerprint,
        transaction_id=event.transaction_id,
        source_order_key=event.source_order_key,
        conid=event.conid,
        instrument_identity_json=identity,
        raw_side=event.raw_side,
        raw_open_close=event.raw_open_close,
        quantity=event.quantity,
        price=event.price,
        occurred_at=event.occurred_at_utc,
        source_timezone=event.source_timezone,
        currency=event.currency,
        normalized_fee=event.normalized_fee,
        fee_currency=event.fee_currency,
        execution_status=event.execution_status,
        normalized_payload_json=event.normalized_payload,
    )
    db.add(observation)
    db.flush()
    return observation, False


def _get_or_create_sighting(
    db: Session,
    *,
    binding: ImportSourceBinding,
    statement: SourceStatement,
    observation: ExternalSourceObservation,
) -> tuple[StatementExecutionSighting, bool]:
    sighting = (
        db.query(StatementExecutionSighting)
        .filter(
            StatementExecutionSighting.statement_id == statement.id,
            StatementExecutionSighting.external_source_event_id
            == observation.external_source_event_id,
            StatementExecutionSighting.observation_id == observation.id,
        )
        .one_or_none()
    )
    if sighting is not None:
        return sighting, True
    sighting = StatementExecutionSighting(
        binding_id=binding.id,
        user_id=binding.user_id,
        account_id=binding.account_id,
        statement_id=statement.id,
        observation_id=observation.id,
        external_source_event_id=observation.external_source_event_id,
        generation_order_key=statement.generation_order_key,
    )
    db.add(sighting)
    db.flush()
    return sighting, False


def _accepted_observation_ids(
    db: Session,
    execution: ExternalExecution,
) -> set[int]:
    ids = {execution.current_trade_observation_id}
    if execution.canceled_by_observation_id is not None:
        ids.add(execution.canceled_by_observation_id)
    ids.update(
        row[0]
        for row in db.query(ExternalTradeApplication.source_observation_id)
        .filter(
            ExternalTradeApplication.binding_id == execution.binding_id,
            ExternalTradeApplication.external_execution_id == execution.id,
        )
        .all()
    )
    return ids


def _latest_authority_generation(
    db: Session,
    *,
    execution: ExternalExecution,
) -> str | None:
    observation_ids = _accepted_observation_ids(db, execution)
    generations = [
        row[0]
        for row in db.query(StatementExecutionSighting.generation_order_key)
        .filter(
            StatementExecutionSighting.binding_id == execution.binding_id,
            StatementExecutionSighting.observation_id.in_(observation_ids),
        )
        .all()
    ]
    return max(generations) if generations else None


def _accepted_exact(
    db: Session,
    *,
    execution: ExternalExecution,
    observation: ExternalSourceObservation,
) -> bool:
    if observation.id == execution.current_trade_observation_id:
        return True
    if observation.id == execution.canceled_by_observation_id:
        return True
    if observation.event_kind == "TRADE":
        return False
    return observation.id in _accepted_observation_ids(db, execution)


def _accepted_identity_has_other_fingerprint(
    db: Session,
    *,
    binding: ImportSourceBinding,
    observation: ExternalSourceObservation,
) -> bool:
    candidates = (
        db.query(ExternalSourceObservation)
        .filter(
            ExternalSourceObservation.binding_id == binding.id,
            ExternalSourceObservation.external_source_event_id
            == observation.external_source_event_id,
            ExternalSourceObservation.id != observation.id,
        )
        .all()
    )
    for candidate in candidates:
        target_id = (
            candidate.affected_external_execution_id
            or candidate.external_execution_id
        )
        if target_id is None:
            continue
        execution = (
            db.query(ExternalExecution)
            .filter(
                ExternalExecution.binding_id == binding.id,
                ExternalExecution.external_execution_id == target_id,
            )
            .one_or_none()
        )
        if execution is not None and _accepted_exact(
            db,
            execution=execution,
            observation=candidate,
        ):
            return True
    return False


def _active_group_state(
    db: Session,
    *,
    binding: ImportSourceBinding,
) -> tuple[
    dict[tuple[str, ...], Decimal],
    dict[tuple[str, ...], tuple[datetime, int, str]],
    dict[tuple[str, ...], list[dict[str, Any]]],
]:
    rows = (
        db.query(ExternalTradeApplication, ExternalSourceObservation)
        .join(
            ExternalSourceObservation,
            ExternalSourceObservation.id
            == ExternalTradeApplication.source_observation_id,
        )
        .filter(
            ExternalTradeApplication.binding_id == binding.id,
            ExternalTradeApplication.is_active.is_(True),
        )
        .all()
    )
    ordered = sorted(rows, key=lambda row: _observation_order_key(row[1]))
    quantities: dict[tuple[str, ...], Decimal] = {}
    boundaries: dict[
        tuple[str, ...], tuple[datetime, int, str]
    ] = {}
    histories: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for application, observation in ordered:
        identity = observation.instrument_identity_json or {}
        key = _group_key(identity, application.derived_direction)
        quantities[key] = Decimal(str(application.post_quantity))
        boundaries[key] = _observation_order_key(observation)
        histories.setdefault(key, []).append(
            {
                "external_source_event_id": (
                    observation.external_source_event_id
                ),
                "fingerprint_version": observation.fingerprint_version,
                "source_payload_fingerprint": (
                    observation.source_payload_fingerprint
                ),
                "source_order_key": observation.source_order_key,
                "application_version": application.application_version,
                "derived_action": application.derived_action,
                "post_quantity": str(application.post_quantity),
            }
        )
    return quantities, boundaries, histories


def _target_execution(
    db: Session,
    *,
    binding: ImportSourceBinding,
    observation: ExternalSourceObservation,
) -> ExternalExecution | None:
    target_id = (
        observation.affected_external_execution_id
        or observation.external_execution_id
    )
    if target_id is None:
        return None
    return (
        db.query(ExternalExecution)
        .filter(
            ExternalExecution.binding_id == binding.id,
            ExternalExecution.external_execution_id == target_id,
        )
        .one_or_none()
    )


def _pending_order_conflict_keys(
    db: Session,
    *,
    binding: ImportSourceBinding,
) -> frozenset[tuple[str, str]]:
    observations = (
        db.query(ExternalSourceObservation)
        .outerjoin(
            ExternalExecution,
            (
                ExternalExecution.binding_id
                == ExternalSourceObservation.binding_id
            )
            & (
                ExternalExecution.external_execution_id
                == ExternalSourceObservation.external_execution_id
            ),
        )
        .filter(
            ExternalSourceObservation.binding_id == binding.id,
            ExternalSourceObservation.event_kind == "TRADE",
            ExternalExecution.id.is_(None),
        )
        .all()
    )
    buckets: dict[
        tuple[tuple[str, ...], datetime, int],
        set[tuple[str, str]],
    ] = {}
    for observation in observations:
        provisional_direction = ibkr_direction_from_source_fields(
            observation.raw_side,
            observation.raw_open_close,
        )
        group = _group_key(
            observation.instrument_identity_json or {},
            provisional_direction,
        )
        bucket = (
            group,
            _as_utc(observation.occurred_at),
            int(observation.transaction_id),
        )
        buckets.setdefault(bucket, set()).add(
            (
                observation.external_source_event_id,
                observation.source_payload_fingerprint,
            )
        )
    return frozenset(
        economic_key
        for economic_keys in buckets.values()
        if len(economic_keys) > 1
        for economic_key in economic_keys
    )


def _classify(
    db: Session,
    *,
    binding: ImportSourceBinding,
    persisted: _PersistedEvent,
    target: ExternalExecution | None,
    group_boundary: tuple[datetime, int, str] | None,
    statement_event_fingerprints: dict[str, set[str]],
) -> str:
    observation = persisted.observation
    event = persisted.event
    if target is not None and _accepted_exact(
        db,
        execution=target,
        observation=observation,
    ):
        return "ALREADY_IMPORTED"

    latest_generation = (
        _latest_authority_generation(db, execution=target)
        if target is not None
        else None
    )
    strictly_earlier = (
        latest_generation is not None
        and persisted.sighting.generation_order_key < latest_generation
    )

    if event.event_kind != "TRADE":
        if event.affected_external_execution_id is None or target is None:
            if _accepted_identity_has_other_fingerprint(
                db,
                binding=binding,
                observation=observation,
            ):
                return "SOURCE_PAYLOAD_CONFLICT"
            return "TARGET_UNRESOLVED"
        if strictly_earlier:
            return (
                "KNOWN_HISTORICAL_OBSERVATION"
                if persisted.observation_known_before
                else "STALE_SOURCE_OBSERVATION"
            )
        if _accepted_identity_has_other_fingerprint(
            db,
            binding=binding,
            observation=observation,
        ):
            return "SOURCE_PAYLOAD_CONFLICT"
        return event.event_kind

    fingerprints = statement_event_fingerprints.setdefault(
        event.external_source_event_id,
        set(),
    )
    fingerprints.add(event.source_payload_fingerprint)
    if len(fingerprints) > 1:
        return "SOURCE_PAYLOAD_CONFLICT"
    if target is not None:
        if strictly_earlier:
            return (
                "KNOWN_HISTORICAL_OBSERVATION"
                if persisted.observation_known_before
                else "STALE_SOURCE_OBSERVATION"
            )
        return "SOURCE_PAYLOAD_CONFLICT"
    if group_boundary is not None and _event_order_key(event) <= group_boundary:
        return "LATE_NEW"
    return "NEW"


def _supersede_older_authority_cases(
    db: Session,
    *,
    binding: ImportSourceBinding,
    persisted: _PersistedEvent,
) -> None:
    observation = persisted.observation
    authority_id = (
        observation.affected_external_execution_id
        or observation.external_execution_id
    )
    if authority_id is None:
        return
    cases = (
        db.query(SourceReconciliationCase)
        .join(
            ExternalSourceObservation,
            ExternalSourceObservation.id
            == SourceReconciliationCase.conflict_observation_id,
        )
        .filter(
            SourceReconciliationCase.binding_id == binding.id,
            SourceReconciliationCase.state.in_(NONTERMINAL_CASE_STATES),
        )
        .all()
    )
    for case in cases:
        conflict = db.get(
            ExternalSourceObservation,
            case.conflict_observation_id,
        )
        if conflict is None:
            continue
        conflict_authority = (
            conflict.affected_external_execution_id
            or conflict.external_execution_id
        )
        if conflict_authority == authority_id:
            supersede_source_case_with_later_sighting(
                db,
                binding=binding,
                case=case,
                winning_sighting=persisted.sighting,
            )


def _persist_import_rows(
    db: Session,
    *,
    session: ImportSession,
    masked_external_account_ref: str,
    persisted_events: list[_PersistedEvent],
    items_by_row: dict[int, BoundPreviewItem],
) -> None:
    existing_rows = {
        row.row_number: row
        for row in db.query(ImportRow)
        .filter(ImportRow.session_id == session.id)
        .all()
    }
    for persisted in persisted_events:
        item = items_by_row[persisted.event.row_number]
        warnings = list(item.warnings)
        safe_payload = {
            key: value
            for key, value in persisted.event.normalized_payload.items()
            if key != "normalized_external_account_ref"
        }
        normalized = {
            **safe_payload,
            "masked_external_account_ref": masked_external_account_ref,
            "classification": item.classification,
            "observation_public_id": item.observation_public_id,
            "sighting_public_id": item.sighting_public_id,
            "derived_direction": item.direction,
            "derived_action": item.action,
            "pre_quantity": (
                str(item.pre_quantity)
                if item.pre_quantity is not None
                else None
            ),
            "post_quantity": (
                str(item.post_quantity)
                if item.post_quantity is not None
                else None
            ),
        }
        raw = {
            "event_kind": persisted.event.event_kind,
            "external_source_event_id": (
                persisted.event.external_source_event_id
            ),
            "source_payload_fingerprint": (
                persisted.event.source_payload_fingerprint
            ),
        }
        row = existing_rows.get(persisted.event.row_number)
        if row is None:
            db.add(
                ImportRow(
                    session_id=session.id,
                    user_id=session.user_id,
                    account_id=session.account_id,
                    adapter_kind=session.adapter_kind,
                    file_hash=session.file_hash,
                    row_number=persisted.event.row_number,
                    raw_values_json=raw,
                    normalized_values_json=normalized,
                    validation_errors_json=[],
                    warnings_json=warnings,
                    is_valid=item.classification
                    not in CONFLICT_CLASSIFICATIONS,
                )
            )
        else:
            row.raw_values_json = raw
            row.normalized_values_json = normalized
            row.validation_errors_json = []
            row.warnings_json = warnings
            row.is_valid = (
                item.classification not in CONFLICT_CLASSIFICATIONS
            )


def preview_bound_ibkr_statement(
    db: Session,
    *,
    account: TradingAccount,
    binding: ImportSourceBinding,
    session: ImportSession,
    parsed: ParsedIbkrFlexStatement,
    provider_contract: VerifiedIbkrFlexProviderContract,
    now: datetime | None = None,
) -> BoundPreviewResult:
    _require_owner_graph(
        account=account,
        binding=binding,
        session=session,
        parsed=parsed,
        provider_contract=provider_contract,
    )
    for event in parsed.events:
        if event.currency != account.currency:
            raise IbkrFlexPreviewError(
                "ACCOUNT_CURRENCY_MISMATCH",
                "IBKR execution currency must equal account currency",
            )

    statement = _get_or_create_statement(
        db,
        binding=binding,
        session=session,
        parsed=parsed,
    )
    generation_conflict = _has_conflicting_generation(
        db,
        binding=binding,
        statement=statement,
    )
    persisted_events: list[_PersistedEvent] = []
    statement_seen: set[tuple[str, str]] = set()
    for event in parsed.events:
        identity = _instrument_identity(event)
        observation, observation_known = _get_or_create_observation(
            db,
            binding=binding,
            event=event,
            identity=identity,
        )
        sighting, sighting_known = _get_or_create_sighting(
            db,
            binding=binding,
            statement=statement,
            observation=observation,
        )
        duplicate_key = (
            event.external_source_event_id,
            event.source_payload_fingerprint,
        )
        duplicate = duplicate_key in statement_seen
        statement_seen.add(duplicate_key)
        persisted_events.append(
            _PersistedEvent(
                event=event,
                observation=observation,
                sighting=sighting,
                observation_known_before=observation_known,
                sighting_known_before=sighting_known,
                duplicate_in_statement=duplicate,
            )
        )

    quantities, boundaries, histories = _active_group_state(
        db,
        binding=binding,
    )
    order_conflict_keys = _pending_order_conflict_keys(
        db,
        binding=binding,
    )
    statement_fingerprints: dict[str, set[str]] = {}
    items_by_row: dict[int, BoundPreviewItem] = {}
    economic_items: dict[tuple[str, str], BoundPreviewItem] = {}
    for persisted in sorted(
        persisted_events,
        key=lambda item: _event_order_key(item.event),
    ):
        event = persisted.event
        economic_key = (
            event.external_source_event_id,
            event.source_payload_fingerprint,
        )
        if persisted.duplicate_in_statement:
            original = economic_items[economic_key]
            items_by_row[event.row_number] = BoundPreviewItem(
                row_number=event.row_number,
                external_source_event_id=original.external_source_event_id,
                observation_public_id=original.observation_public_id,
                sighting_public_id=original.sighting_public_id,
                classification=original.classification,
                direction=original.direction,
                action=original.action,
                pre_quantity=original.pre_quantity,
                post_quantity=original.post_quantity,
                warnings=tuple(
                    dict.fromkeys(
                        (*original.warnings, "DUPLICATE_SOURCE_EVENT")
                    )
                ),
            )
            continue
        identity = persisted.observation.instrument_identity_json
        provisional_direction = ibkr_provisional_direction(event)
        key = _group_key(identity, provisional_direction)
        target = _target_execution(
            db,
            binding=binding,
            observation=persisted.observation,
        )
        classification = (
            "SOURCE_GENERATION_CONFLICT"
            if generation_conflict
            else _classify(
                db,
                binding=binding,
                persisted=persisted,
                target=target,
                group_boundary=boundaries.get(key),
                statement_event_fingerprints=statement_fingerprints,
            )
        )
        if (
            classification == "NEW"
            and (
                economic_key in order_conflict_keys
                or (
                    key in boundaries
                    and _event_order_key(event)[:2]
                    == boundaries[key][:2]
                )
            )
        ):
            classification = "UNSUPPORTED_ORDER_CONFLICT"
        step: LifecycleStep | None = None
        if classification == "NEW":
            try:
                step = derive_broker_lifecycle_step(
                    current_quantity=quantities.get(key, Decimal("0")),
                    side=event.raw_side,
                    open_close=event.raw_open_close,
                    quantity=event.quantity,
                )
                quantities[key] = step.post_quantity
            except LifecycleSimulationError:
                classification = "UNSUPPORTED_CROSS_ZERO"

        if classification in CONFLICT_CLASSIFICATIONS:
            _supersede_older_authority_cases(
                db,
                binding=binding,
                persisted=persisted,
            )
            snapshot = build_source_case_snapshot(
                db,
                binding=binding,
                conflict_observation=persisted.observation,
                target_execution=target,
                group_state={
                    "group_key": list(key),
                    "accepted_history": histories.get(key, []),
                    "append_boundary": (
                        [
                            boundaries[key][0].isoformat(),
                            boundaries[key][1],
                            boundaries[key][2],
                        ]
                        if key in boundaries
                        else None
                    ),
                },
            )
            create_or_attach_source_case(
                db,
                binding=binding,
                conflict_observation=persisted.observation,
                trigger_sighting=persisted.sighting,
                case_kind=classification,
                snapshot=snapshot,
            )

        warnings: list[str] = []
        if persisted.duplicate_in_statement:
            warnings.append("DUPLICATE_SOURCE_EVENT")
        if classification in {
            "KNOWN_HISTORICAL_OBSERVATION",
            "STALE_SOURCE_OBSERVATION",
        }:
            warnings.append(classification)
        item = BoundPreviewItem(
            row_number=event.row_number,
            external_source_event_id=event.external_source_event_id,
            observation_public_id=persisted.observation.public_id,
            sighting_public_id=persisted.sighting.public_id,
            classification=classification,
            direction=step.direction if step else provisional_direction,
            action=step.action if step else None,
            pre_quantity=step.pre_quantity if step else None,
            post_quantity=step.post_quantity if step else None,
            warnings=tuple(warnings),
        )
        items_by_row[event.row_number] = item
        economic_items[economic_key] = item

    recompute_source_health(db, binding=binding)
    try:
        projection = build_source_preview_projection(
            db,
            binding=binding,
        )
    except SourcePreviewProjectionError as exc:
        raise IbkrFlexPreviewError(exc.code, str(exc)) from exc
    binding.source_completeness = projection.source_completeness
    session.source_preview_schema_version = projection.schema_version
    session.source_preview_digest = projection.digest

    if generation_conflict:
        status = ImportSessionStatus.CONFLICTED.value
        session.error_code = "SOURCE_GENERATION_CONFLICT"
        session.error_message = (
            "Different source files use the same statement generation marker"
        )
    elif projection.coverage_gap:
        status = ImportSessionStatus.CONFLICTED.value
        session.error_code = "SOURCE_COVERAGE_GAP"
        session.error_message = (
            "Statement coverage does not overlap or touch accepted coverage"
        )
    elif any(
        item.classification in CONFLICT_CLASSIFICATIONS
        for item in items_by_row.values()
    ):
        status = ImportSessionStatus.CONFLICTED.value
        session.error_code = "SOURCE_RECONCILIATION_REQUIRED"
        session.error_message = "Statement contains source reconciliation conflicts"
    else:
        status = ImportSessionStatus.PREVIEW_READY.value
        session.error_code = None
        session.error_message = None

    _persist_import_rows(
        db,
        session=session,
        masked_external_account_ref=binding.masked_external_account_ref,
        persisted_events=persisted_events,
        items_by_row=items_by_row,
    )
    session.total_rows = len(persisted_events)
    session.valid_rows = sum(
        item.classification not in CONFLICT_CLASSIFICATIONS
        for item in items_by_row.values()
    )
    session.error_rows = len(persisted_events) - session.valid_rows
    session.warning_rows = sum(bool(item.warnings) for item in items_by_row.values())
    transition_import_session(
        db,
        session=session,
        from_status=ImportSessionStatus.UPLOADING.value,
        to_status=status,
        now=now,
    )
    db.flush()
    return BoundPreviewResult(
        session_public_id=session.public_id,
        statement_public_id=statement.public_id,
        binding_public_id=binding.public_id,
        masked_external_account_ref=binding.masked_external_account_ref,
        status=status,
        source_health=binding.source_health,
        source_completeness=binding.source_completeness,
        coverage_gap=projection.coverage_gap,
        source_preview_schema_version=projection.schema_version,
        source_preview_digest=projection.digest,
        pending_statement_count=len(projection.pending_coverage),
        pending_execution_count=len(projection.pending_units),
        items=tuple(
            items_by_row[row_number]
            for row_number in sorted(items_by_row)
        ),
    )
