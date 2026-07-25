"""Source reconciliation episode and health domain operations."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from typing import Any, Iterable

from sqlalchemy.orm import Session

from models import (
    ExternalExecution,
    ExternalSourceObservation,
    ExternalTradeApplication,
    ImportSourceBinding,
    SourceCaseEvidenceSighting,
    SourceHealth,
    SourceReconciliationCase,
    SourceReconciliationState,
    StatementExecutionSighting,
)


CASE_SNAPSHOT_SCHEMA_VERSION = 1
NONTERMINAL_CASE_STATES = frozenset(
    {
        SourceReconciliationState.OPEN.value,
        SourceReconciliationState.RESOLVING.value,
        SourceReconciliationState.DIVERGED_REJECTED.value,
    }
)


@dataclass(frozen=True)
class SourceStateSnapshot:
    schema_version: int
    payload: dict[str, Any]
    digest: str


@dataclass(frozen=True)
class CaseEpisodeResult:
    case: SourceReconciliationCase
    created: bool
    evidence_attached: bool


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        normalized = (
            value.replace(tzinfo=timezone.utc)
            if value.tzinfo is None
            else value.astimezone(timezone.utc)
        )
        return normalized.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, dict):
        return {
            str(key): _json_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def _canonical_digest(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        _json_value(payload),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("ascii")
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _observation_state(
    observation: ExternalSourceObservation | None,
) -> dict[str, Any] | None:
    if observation is None:
        return None
    return {
        "public_id": observation.public_id,
        "event_kind": observation.event_kind,
        "external_source_event_id": observation.external_source_event_id,
        "external_execution_id": observation.external_execution_id,
        "affected_external_execution_id": (
            observation.affected_external_execution_id
        ),
        "fingerprint_version": observation.fingerprint_version,
        "source_payload_fingerprint": observation.source_payload_fingerprint,
        "source_order_key": observation.source_order_key,
    }


def _authority_scope(
    observation: ExternalSourceObservation,
) -> tuple[str, str]:
    target = (
        observation.affected_external_execution_id
        or observation.external_execution_id
    )
    if target is not None:
        return ("EXTERNAL_EXECUTION", target)
    return ("SOURCE_EVENT", observation.external_source_event_id)


def build_source_case_snapshot(
    db: Session,
    *,
    binding: ImportSourceBinding,
    conflict_observation: ExternalSourceObservation,
    target_execution: ExternalExecution | None = None,
    candidate_external_execution_ids: Iterable[str] = (),
    group_state: dict[str, Any] | None = None,
) -> SourceStateSnapshot:
    if (
        conflict_observation.binding_id != binding.id
        or conflict_observation.user_id != binding.user_id
        or conflict_observation.account_id != binding.account_id
    ):
        raise ValueError("Conflict observation and source binding owner mismatch")
    if target_execution is not None and (
        target_execution.binding_id != binding.id
        or target_execution.user_id != binding.user_id
        or target_execution.account_id != binding.account_id
    ):
        raise ValueError("Target execution and source binding owner mismatch")

    candidate_ids = sorted(set(candidate_external_execution_ids))
    if candidate_ids:
        owned_count = (
            db.query(ExternalExecution.id)
            .filter(
                ExternalExecution.binding_id == binding.id,
                ExternalExecution.user_id == binding.user_id,
                ExternalExecution.account_id == binding.account_id,
                ExternalExecution.external_execution_id.in_(candidate_ids),
            )
            .count()
        )
        if owned_count != len(candidate_ids):
            raise ValueError("Candidate execution scope is not owner-bound")

    current_observation = None
    canceled_by_observation = None
    active_application = None
    if target_execution is not None:
        current_observation = db.get(
            ExternalSourceObservation,
            target_execution.current_trade_observation_id,
        )
        if target_execution.canceled_by_observation_id is not None:
            canceled_by_observation = db.get(
                ExternalSourceObservation,
                target_execution.canceled_by_observation_id,
            )
        active_application = (
            db.query(ExternalTradeApplication)
            .filter(
                ExternalTradeApplication.binding_id == binding.id,
                ExternalTradeApplication.external_execution_id
                == target_execution.id,
                ExternalTradeApplication.is_active.is_(True),
            )
            .one_or_none()
        )

    candidate_digest = (
        _canonical_digest({"external_execution_ids": candidate_ids})
        if candidate_ids
        else None
    )
    payload = {
        "schema_version": CASE_SNAPSHOT_SCHEMA_VERSION,
        "binding": {
            "public_id": binding.public_id,
            "source_state_revision": binding.source_state_revision,
        },
        "conflict_observation": _observation_state(conflict_observation),
        "authority_target": (
            {
                "external_execution_id": target_execution.external_execution_id,
                "disposition": target_execution.disposition,
                "current_trade_observation": _observation_state(
                    current_observation
                ),
                "canceled_by_observation": _observation_state(
                    canceled_by_observation
                ),
                "active_application": (
                    {
                        "public_id": active_application.public_id,
                        "application_version": (
                            active_application.application_version
                        ),
                        "source_observation_id": (
                            active_application.source_observation_id
                        ),
                        "derived_direction": (
                            active_application.derived_direction
                        ),
                        "derived_action": active_application.derived_action,
                        "pre_quantity": active_application.pre_quantity,
                        "post_quantity": active_application.post_quantity,
                    }
                    if active_application is not None
                    else None
                ),
            }
            if target_execution is not None
            else None
        ),
        "target_unresolved": (
            {
                "target": None,
                "candidate_count": len(candidate_ids),
                "candidate_execution_ids_digest": candidate_digest,
            }
            if target_execution is None
            else None
        ),
        "group_state": group_state,
    }
    normalized = _json_value(payload)
    return SourceStateSnapshot(
        schema_version=CASE_SNAPSHOT_SCHEMA_VERSION,
        payload=normalized,
        digest=_canonical_digest(normalized),
    )


def recompute_source_health(
    db: Session,
    *,
    binding: ImportSourceBinding,
) -> str:
    db.flush()
    states = {
        row[0]
        for row in db.query(SourceReconciliationCase.state)
        .filter(SourceReconciliationCase.binding_id == binding.id)
        .all()
    }
    if SourceReconciliationState.DIVERGED_REJECTED.value in states:
        health = SourceHealth.SOURCE_DIVERGED.value
    elif states.intersection(
        {
            SourceReconciliationState.OPEN.value,
            SourceReconciliationState.RESOLVING.value,
        }
    ):
        health = SourceHealth.RECONCILIATION_REQUIRED.value
    else:
        health = SourceHealth.HEALTHY.value
    binding.source_health = health
    return health


def _attach_case_evidence(
    db: Session,
    *,
    case: SourceReconciliationCase,
    sighting: StatementExecutionSighting,
) -> bool:
    if sighting.id == case.trigger_sighting_id:
        return False
    existing = (
        db.query(SourceCaseEvidenceSighting.id)
        .filter(
            SourceCaseEvidenceSighting.case_id == case.id,
            SourceCaseEvidenceSighting.sighting_id == sighting.id,
        )
        .first()
    )
    if existing is not None:
        return False
    db.add(
        SourceCaseEvidenceSighting(
            binding_id=case.binding_id,
            user_id=case.user_id,
            account_id=case.account_id,
            case_id=case.id,
            sighting_id=sighting.id,
        )
    )
    return True


def create_or_attach_source_case(
    db: Session,
    *,
    binding: ImportSourceBinding,
    conflict_observation: ExternalSourceObservation,
    trigger_sighting: StatementExecutionSighting,
    case_kind: str,
    snapshot: SourceStateSnapshot,
) -> CaseEpisodeResult:
    if (
        conflict_observation.binding_id != binding.id
        or trigger_sighting.binding_id != binding.id
        or conflict_observation.user_id != binding.user_id
        or trigger_sighting.user_id != binding.user_id
        or conflict_observation.account_id != binding.account_id
        or trigger_sighting.account_id != binding.account_id
    ):
        raise ValueError("Source case graph must remain owner-bound")
    if trigger_sighting.observation_id != conflict_observation.id:
        raise ValueError("Trigger sighting must reference the conflict observation")

    replay = (
        db.query(SourceReconciliationCase)
        .filter(
            SourceReconciliationCase.binding_id == binding.id,
            SourceReconciliationCase.trigger_sighting_id
            == trigger_sighting.id,
            SourceReconciliationCase.case_kind == case_kind,
            SourceReconciliationCase.against_source_state_hash
            == snapshot.digest,
        )
        .one_or_none()
    )
    if replay is not None:
        recompute_source_health(db, binding=binding)
        return CaseEpisodeResult(
            case=replay,
            created=False,
            evidence_attached=False,
        )

    existing = (
        db.query(SourceReconciliationCase)
        .filter(
            SourceReconciliationCase.binding_id == binding.id,
            SourceReconciliationCase.conflict_observation_id
            == conflict_observation.id,
            SourceReconciliationCase.case_kind == case_kind,
            SourceReconciliationCase.against_source_state_hash
            == snapshot.digest,
            SourceReconciliationCase.state.in_(NONTERMINAL_CASE_STATES),
        )
        .order_by(SourceReconciliationCase.id.desc())
        .first()
    )
    if existing is not None:
        attached = _attach_case_evidence(
            db,
            case=existing,
            sighting=trigger_sighting,
        )
        db.flush()
        recompute_source_health(db, binding=binding)
        return CaseEpisodeResult(
            case=existing,
            created=False,
            evidence_attached=attached,
        )

    case = SourceReconciliationCase(
        binding_id=binding.id,
        user_id=binding.user_id,
        account_id=binding.account_id,
        conflict_observation_id=conflict_observation.id,
        trigger_sighting_id=trigger_sighting.id,
        case_kind=case_kind,
        state=SourceReconciliationState.OPEN.value,
        against_source_state_schema_version=snapshot.schema_version,
        against_source_state_hash=snapshot.digest,
        against_source_state_snapshot_json=snapshot.payload,
    )
    db.add(case)
    db.flush()
    recompute_source_health(db, binding=binding)
    return CaseEpisodeResult(
        case=case,
        created=True,
        evidence_attached=False,
    )


def supersede_source_case_with_later_sighting(
    db: Session,
    *,
    binding: ImportSourceBinding,
    case: SourceReconciliationCase,
    winning_sighting: StatementExecutionSighting,
    now: datetime | None = None,
) -> bool:
    if (
        case.binding_id != binding.id
        or winning_sighting.binding_id != binding.id
        or case.user_id != binding.user_id
        or winning_sighting.user_id != binding.user_id
        or case.account_id != binding.account_id
        or winning_sighting.account_id != binding.account_id
    ):
        raise ValueError("Source authority graph must remain owner-bound")
    if case.state not in NONTERMINAL_CASE_STATES:
        recompute_source_health(db, binding=binding)
        return False
    if case.case_kind == "TARGET_UNRESOLVED":
        recompute_source_health(db, binding=binding)
        return False
    trigger = db.get(StatementExecutionSighting, case.trigger_sighting_id)
    if trigger is None or trigger.binding_id != binding.id:
        raise ValueError("Source case trigger sighting is missing")
    conflict_observation = db.get(
        ExternalSourceObservation,
        case.conflict_observation_id,
    )
    winning_observation = db.get(
        ExternalSourceObservation,
        winning_sighting.observation_id,
    )
    if (
        conflict_observation is None
        or winning_observation is None
        or conflict_observation.binding_id != binding.id
        or winning_observation.binding_id != binding.id
    ):
        raise ValueError("Source authority observation is missing")
    if _authority_scope(conflict_observation) != _authority_scope(
        winning_observation
    ):
        recompute_source_health(db, binding=binding)
        return False
    if winning_sighting.generation_order_key <= trigger.generation_order_key:
        recompute_source_health(db, binding=binding)
        return False

    case.state = (
        SourceReconciliationState.RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY.value
    )
    case.winning_sighting_id = winning_sighting.id
    case.resolved_at = now or datetime.now(timezone.utc)
    db.flush()
    recompute_source_health(db, binding=binding)
    return True
