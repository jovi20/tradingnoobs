"""Rebuildable binding-wide source preview projection and digest."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any

from sqlalchemy import and_
from sqlalchemy.orm import Session

from models import (
    ExternalExecution,
    ExternalSourceObservation,
    ExternalTradeApplication,
    ImportSourceBinding,
    SourceCompleteness,
    SourceReconciliationCase,
    SourceStatement,
    StatementCoverageAcceptance,
)
from services.ibkr_flex_identity_service import (
    ibkr_direction_from_source_fields,
)
from services.source_reconciliation_service import NONTERMINAL_CASE_STATES
from services.trade_lifecycle_simulation_service import (
    LifecycleSimulationError,
    derive_broker_lifecycle_step,
)


SOURCE_PREVIEW_SCHEMA_VERSION = 1


class SourcePreviewProjectionError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


@dataclass(frozen=True)
class CoverageInterval:
    statement_public_id: str
    coverage_start: date
    coverage_end_exclusive: date


@dataclass(frozen=True)
class PendingSourceUnit:
    observation_public_id: str
    external_source_event_id: str
    fingerprint_version: int
    source_payload_fingerprint: str
    source_order_key: str
    occurred_at_utc: datetime
    direction: str
    action: str
    pre_quantity: Decimal
    post_quantity: Decimal
    quantity: Decimal
    price: Decimal
    normalized_fee: Decimal


@dataclass(frozen=True)
class SourcePreviewProjection:
    schema_version: int
    digest: str
    accepted_coverage_start: date | None
    accepted_coverage_through_exclusive: date | None
    pending_coverage: tuple[CoverageInterval, ...]
    projected_coverage_through_exclusive: date | None
    coverage_gap: bool
    pending_units: tuple[PendingSourceUnit, ...]
    source_completeness: str
    payload: dict[str, Any]


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return _as_utc(value).isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value.normalize(), "f")
    if isinstance(value, dict):
        return {
            str(key): _json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        _json_value(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _group_key(
    identity: dict[str, Any],
    direction: str,
) -> tuple[str, ...]:
    required = (
        "asset_type",
        "market",
        "exchange_code",
        "normalized_symbol",
        "instrument_type",
        "quote_currency",
    )
    try:
        return tuple(str(identity[field]) for field in required) + (
            direction,
        )
    except KeyError as exc:
        raise SourcePreviewProjectionError(
            "SOURCE_INSTRUMENT_IDENTITY_INVALID",
            "Source observation lacks canonical instrument identity",
        ) from exc


def _observation_order_key(
    observation: ExternalSourceObservation,
) -> tuple[datetime, int, str]:
    try:
        transaction_id = int(observation.transaction_id)
    except (TypeError, ValueError) as exc:
        raise SourcePreviewProjectionError(
            "SOURCE_ORDER_KEY_INVALID",
            "Source observation transaction ID must be numeric",
        ) from exc
    return (
        _as_utc(observation.occurred_at),
        transaction_id,
        (
            observation.external_execution_id
            or observation.external_source_event_id
        ),
    )


def _merge_accepted_coverage(
    intervals: list[CoverageInterval],
) -> tuple[date | None, date | None]:
    if not intervals:
        return None, None
    ordered = sorted(
        intervals,
        key=lambda item: (
            item.coverage_start,
            item.coverage_end_exclusive,
            item.statement_public_id,
        ),
    )
    start = ordered[0].coverage_start
    frontier = ordered[0].coverage_end_exclusive
    for interval in ordered[1:]:
        if interval.coverage_start > frontier:
            raise SourcePreviewProjectionError(
                "ACCEPTED_COVERAGE_GAP",
                "Accepted source coverage contains a permanent gap",
            )
        frontier = max(frontier, interval.coverage_end_exclusive)
    return start, frontier


def _project_pending_coverage(
    *,
    accepted_frontier: date | None,
    pending: list[CoverageInterval],
) -> tuple[date | None, bool]:
    if not pending:
        return accepted_frontier, False
    if accepted_frontier is None:
        return None, True
    frontier = accepted_frontier
    remaining = list(pending)
    while True:
        reachable = [
            interval
            for interval in remaining
            if interval.coverage_start <= frontier
        ]
        if not reachable:
            break
        next_frontier = max(
            [frontier]
            + [
                interval.coverage_end_exclusive
                for interval in reachable
            ]
        )
        remaining = [
            interval for interval in remaining if interval not in reachable
        ]
        if next_frontier == frontier and not remaining:
            break
        frontier = next_frontier
    return frontier, bool(remaining)


def _coverage_projection(
    db: Session,
    *,
    binding: ImportSourceBinding,
) -> tuple[
    date | None,
    date | None,
    tuple[CoverageInterval, ...],
    date | None,
    bool,
]:
    accepted_rows = (
        db.query(SourceStatement)
        .join(
            StatementCoverageAcceptance,
            and_(
                StatementCoverageAcceptance.statement_id
                == SourceStatement.id,
                StatementCoverageAcceptance.binding_id
                == SourceStatement.binding_id,
            ),
        )
        .filter(SourceStatement.binding_id == binding.id)
        .all()
    )
    accepted_intervals = [
        CoverageInterval(
            statement_public_id=statement.public_id,
            coverage_start=statement.coverage_start,
            coverage_end_exclusive=statement.coverage_end_exclusive,
        )
        for statement in accepted_rows
    ]
    accepted_start, accepted_frontier = _merge_accepted_coverage(
        accepted_intervals
    )
    if (
        accepted_start != binding.accepted_coverage_start
        or accepted_frontier
        != binding.accepted_coverage_through_exclusive
    ):
        raise SourcePreviewProjectionError(
            "SOURCE_COVERAGE_PROJECTION_MISMATCH",
            "Binding coverage scalar does not match immutable acceptances",
        )

    pending_rows = (
        db.query(SourceStatement)
        .outerjoin(
            StatementCoverageAcceptance,
            and_(
                StatementCoverageAcceptance.statement_id
                == SourceStatement.id,
                StatementCoverageAcceptance.binding_id
                == SourceStatement.binding_id,
            ),
        )
        .filter(
            SourceStatement.binding_id == binding.id,
            StatementCoverageAcceptance.id.is_(None),
        )
        .all()
    )
    pending = tuple(
        sorted(
            (
                CoverageInterval(
                    statement_public_id=statement.public_id,
                    coverage_start=statement.coverage_start,
                    coverage_end_exclusive=(
                        statement.coverage_end_exclusive
                    ),
                )
                for statement in pending_rows
            ),
            key=lambda item: (
                item.coverage_start,
                item.coverage_end_exclusive,
                item.statement_public_id,
            ),
        )
    )
    projected_frontier, gap = _project_pending_coverage(
        accepted_frontier=accepted_frontier,
        pending=list(pending),
    )
    return (
        accepted_start,
        accepted_frontier,
        pending,
        projected_frontier,
        gap,
    )


def _active_group_state(
    db: Session,
    *,
    binding: ImportSourceBinding,
) -> tuple[
    dict[tuple[str, ...], Decimal],
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
    histories: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for application, observation in ordered:
        key = _group_key(
            observation.instrument_identity_json or {},
            application.derived_direction,
        )
        quantities[key] = Decimal(str(application.post_quantity))
        histories.setdefault(key, []).append(
            {
                "observation_public_id": observation.public_id,
                "external_source_event_id": (
                    observation.external_source_event_id
                ),
                "fingerprint_version": observation.fingerprint_version,
                "source_payload_fingerprint": (
                    observation.source_payload_fingerprint
                ),
                "source_order_key": observation.source_order_key,
                "application_version": application.application_version,
                "derived_direction": application.derived_direction,
                "derived_action": application.derived_action,
                "pre_quantity": application.pre_quantity,
                "post_quantity": application.post_quantity,
            }
        )
    return quantities, histories


def _pending_trade_observations(
    db: Session,
    *,
    binding: ImportSourceBinding,
) -> list[ExternalSourceObservation]:
    rows = (
        db.query(ExternalSourceObservation)
        .outerjoin(
            ExternalExecution,
            and_(
                ExternalExecution.binding_id
                == ExternalSourceObservation.binding_id,
                ExternalExecution.external_execution_id
                == ExternalSourceObservation.external_execution_id,
            ),
        )
        .filter(
            ExternalSourceObservation.binding_id == binding.id,
            ExternalSourceObservation.event_kind == "TRADE",
            ExternalExecution.id.is_(None),
        )
        .all()
    )
    cases = (
        db.query(SourceReconciliationCase, ExternalSourceObservation)
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
    blocked_execution_ids = {
        observation.external_execution_id
        for _case, observation in cases
        if observation.external_execution_id is not None
    }
    by_execution: dict[str, list[ExternalSourceObservation]] = {}
    for observation in rows:
        if observation.external_execution_id is None:
            continue
        by_execution.setdefault(
            observation.external_execution_id,
            [],
        ).append(observation)
    return [
        observations[0]
        for external_execution_id, observations in by_execution.items()
        if len(observations) == 1
        and external_execution_id not in blocked_execution_ids
    ]


def _pending_units(
    db: Session,
    *,
    binding: ImportSourceBinding,
) -> tuple[tuple[PendingSourceUnit, ...], dict[str, Any]]:
    quantities, accepted_histories = _active_group_state(
        db,
        binding=binding,
    )
    observations = sorted(
        _pending_trade_observations(db, binding=binding),
        key=_observation_order_key,
    )
    order_buckets: dict[
        tuple[tuple[str, ...], datetime, int],
        set[tuple[str, str]],
    ] = {}
    for observation in observations:
        provisional_direction = ibkr_direction_from_source_fields(
            observation.raw_side,
            observation.raw_open_close,
        )
        bucket = (
            _group_key(
                observation.instrument_identity_json or {},
                provisional_direction,
            ),
            _as_utc(observation.occurred_at),
            int(observation.transaction_id),
        )
        order_buckets.setdefault(bucket, set()).add(
            (
                observation.external_source_event_id,
                observation.source_payload_fingerprint,
            )
        )
    if any(len(economic_keys) > 1 for economic_keys in order_buckets.values()):
        raise SourcePreviewProjectionError(
            "UNSUPPORTED_ORDER_CONFLICT",
            "Pending source events have a financially significant provider-order tie",
        )
    pending: list[PendingSourceUnit] = []
    for observation in observations:
        provisional_direction = ibkr_direction_from_source_fields(
            observation.raw_side,
            observation.raw_open_close,
        )
        key = _group_key(
            observation.instrument_identity_json or {},
            provisional_direction,
        )
        try:
            step = derive_broker_lifecycle_step(
                current_quantity=quantities.get(key, Decimal("0")),
                side=observation.raw_side,
                open_close=observation.raw_open_close,
                quantity=observation.quantity,
            )
        except LifecycleSimulationError as exc:
            raise SourcePreviewProjectionError(
                "PENDING_LIFECYCLE_INVALID",
                str(exc),
            ) from exc
        quantities[key] = step.post_quantity
        pending.append(
            PendingSourceUnit(
                observation_public_id=observation.public_id,
                external_source_event_id=observation.external_source_event_id,
                fingerprint_version=observation.fingerprint_version,
                source_payload_fingerprint=(
                    observation.source_payload_fingerprint
                ),
                source_order_key=observation.source_order_key,
                occurred_at_utc=_as_utc(observation.occurred_at),
                direction=step.direction,
                action=step.action,
                pre_quantity=step.pre_quantity,
                post_quantity=step.post_quantity,
                quantity=Decimal(str(observation.quantity)),
                price=Decimal(str(observation.price)),
                normalized_fee=Decimal(
                    str(observation.normalized_fee or 0)
                ),
            )
        )
    return tuple(pending), {
        "|".join(key): history
        for key, history in sorted(accepted_histories.items())
    }


def build_source_preview_projection(
    db: Session,
    *,
    binding: ImportSourceBinding,
) -> SourcePreviewProjection:
    db.flush()
    (
        accepted_start,
        accepted_frontier,
        pending_coverage,
        projected_frontier,
        coverage_gap,
    ) = _coverage_projection(db, binding=binding)
    pending_units, accepted_histories = _pending_units(
        db,
        binding=binding,
    )
    completeness = (
        SourceCompleteness.PENDING_IMPORT.value
        if pending_coverage or pending_units
        else SourceCompleteness.CURRENT.value
    )
    payload = _json_value(
        {
            "schema_version": SOURCE_PREVIEW_SCHEMA_VERSION,
            "binding": {
                "public_id": binding.public_id,
                "source_state_revision": binding.source_state_revision,
                "source_health": binding.source_health,
            },
            "accepted_coverage": {
                "start": accepted_start,
                "through_exclusive": accepted_frontier,
            },
            "pending_coverage": [
                {
                    "statement_public_id": interval.statement_public_id,
                    "coverage_start": interval.coverage_start,
                    "coverage_end_exclusive": (
                        interval.coverage_end_exclusive
                    ),
                }
                for interval in pending_coverage
            ],
            "projected_coverage_through_exclusive": projected_frontier,
            "coverage_gap": coverage_gap,
            "accepted_group_history": accepted_histories,
            "pending_units": [
                {
                    "observation_public_id": unit.observation_public_id,
                    "external_source_event_id": (
                        unit.external_source_event_id
                    ),
                    "fingerprint_version": unit.fingerprint_version,
                    "source_payload_fingerprint": (
                        unit.source_payload_fingerprint
                    ),
                    "source_order_key": unit.source_order_key,
                    "occurred_at_utc": unit.occurred_at_utc,
                    "derived_direction": unit.direction,
                    "derived_action": unit.action,
                    "pre_quantity": unit.pre_quantity,
                    "post_quantity": unit.post_quantity,
                    "quantity": unit.quantity,
                    "price": unit.price,
                    "normalized_fee": unit.normalized_fee,
                }
                for unit in pending_units
            ],
            "source_completeness": completeness,
        }
    )
    return SourcePreviewProjection(
        schema_version=SOURCE_PREVIEW_SCHEMA_VERSION,
        digest=_digest(payload),
        accepted_coverage_start=accepted_start,
        accepted_coverage_through_exclusive=accepted_frontier,
        pending_coverage=pending_coverage,
        projected_coverage_through_exclusive=projected_frontier,
        coverage_gap=coverage_gap,
        pending_units=pending_units,
        source_completeness=completeness,
        payload=payload,
    )
