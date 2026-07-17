"""
Trading Noobs Backend - TradingPosition Truth Read Service
"""
from __future__ import annotations

from decimal import Decimal

from sqlalchemy.orm import Session, joinedload

from models import AccountLedgerEntry, AccountLedgerEntryType, PositionEventType, TradeInstrument, TradingPosition, TradingPositionStatus
from services.truth_legacy_projection_service import resolve_legacy_position_for_truth


def resolve_truth_position_by_public_id(db: Session, user_id: int, public_id: str) -> TradingPosition | None:
    query = db.query(TradingPosition).options(
        joinedload(TradingPosition.account),
        joinedload(TradingPosition.instrument).joinedload(TradeInstrument.asset),
        joinedload(TradingPosition.events),
        joinedload(TradingPosition.ledger_entries).joinedload(AccountLedgerEntry.position_event),
    )

    return query.filter(
        TradingPosition.public_id == public_id,
        TradingPosition.user_id == user_id,
    ).first()


def _node_type(event_type: PositionEventType) -> str:
    if event_type == PositionEventType.OPEN:
        return "OPEN"
    if event_type == PositionEventType.ADD:
        return "ADD"
    if event_type == PositionEventType.REDUCE:
        return "REDUCE"
    if event_type == PositionEventType.CLOSE:
        return "CLOSE"
    return event_type.value


def _node_label(event_type: PositionEventType) -> str:
    return {
        PositionEventType.OPEN: "开仓",
        PositionEventType.ADD: "加仓",
        PositionEventType.REDUCE: "减仓",
        PositionEventType.CLOSE: "平仓",
        PositionEventType.REVERSAL: "撤销",
        PositionEventType.MANUAL_ADJUSTMENT: "手工调整",
        PositionEventType.DIVIDEND: "股息",
    }.get(event_type, event_type.value)


def _ledger_cash_effects(truth_position: TradingPosition) -> list[dict]:
    return [
        {
            "ledger_entry_public_id": entry.public_id,
            "entry_type": entry.entry_type.value,
            "occurred_at": entry.occurred_at,
            "amount": entry.amount,
            "amount_account_ccy": entry.amount_account_ccy,
            "currency": entry.currency,
            "fx_rate_to_account_ccy": entry.fx_rate_to_account_ccy,
            "source_event_public_id": entry.position_event.public_id if entry.position_event else None,
            "description": entry.description,
        }
        for entry in sorted(
            truth_position.ledger_entries,
            key=lambda item: (item.occurred_at, item.id),
        )
    ]


def _ledger_total(truth_position: TradingPosition, entry_type: AccountLedgerEntryType):
    return sum(
        (
            entry.amount_account_ccy if entry.amount_account_ccy is not None else entry.amount
            for entry in truth_position.ledger_entries
            if entry.entry_type == entry_type
        ),
        Decimal("0"),
    )


def _build_ai_sidecar_items(db: Session, truth_position: TradingPosition) -> list[dict]:
    from services.insight_artifact_service import InsightArtifactService

    artifacts = InsightArtifactService(db).list_artifacts_for_object(
        user_id=truth_position.user_id,
        linked_object_public_id=truth_position.public_id,
        limit=5,
    )
    items = []
    for artifact in artifacts:
        artifact_href = f"/insights/{artifact['public_id']}"
        items.append({
            "insight_artifact_public_id": artifact["public_id"],
            "title": artifact["title"],
            "conclusion": artifact["summary"],
            "coverage_summary": artifact.get("artifact_type"),
            "confidence_label": artifact.get("trust_meta", {}).get("freshness"),
            "recommended_action": artifact.get("payload", {}).get("recommended_action"),
            "evidence_refs": [
                {
                    "ref_type": "EVIDENCE_REF",
                    "public_id": ref,
                    "label": ref,
                    "href": artifact_href,
                }
                for ref in artifact.get("evidence_refs", [])
            ],
            "href": artifact_href,
        })
    return items


def build_trading_position_lifecycle_payload(
    db: Session,
    truth_position: TradingPosition,
    *,
    include_ai_sidecar: bool = False,
) -> dict:
    opening_event = next((event for event in truth_position.events if event.event_type == PositionEventType.OPEN), None)
    checklist_snapshot = opening_event.checklist_snapshot or {} if opening_event else {}
    cash_effects = _ledger_cash_effects(truth_position)
    event_public_ids_by_id = {event.id: event.public_id for event in truth_position.events}
    legacy_position = resolve_legacy_position_for_truth(db, truth_position=truth_position)
    route_public_id = legacy_position.public_id if legacy_position else truth_position.public_id
    quantity_opened = truth_position.quantity_opened or Decimal("0")
    quantity_closed = truth_position.quantity_closed or Decimal("0")

    lifecycle_thread = []
    for event in truth_position.events:
        lifecycle_thread.append(
            {
                "node_public_id": event.public_id,
                "node_type": _node_type(event.event_type),
                "occurred_at": event.event_time,
                "title": f"{truth_position.instrument.contract_symbol} {_node_label(event.event_type)}",
                "summary": event.reason or event.note or _node_label(event.event_type),
                "related_event_public_id": event.public_id,
                "reverses_event_public_id": (
                    event_public_ids_by_id.get(event.reverses_event_id)
                    if event.reverses_event_id
                    else None
                ),
                "quantities": {
                    "quantity": event.quantity,
                    "price": event.price,
                    "currency": event.currency,
                },
                "pnl_delta": {
                    "realized_gross": event.realized_pnl_gross,
                    "realized_net": event.realized_pnl_net,
                },
                "emotion": event.emotion,
                "confidence": event.confidence,
                "note": event.note,
                "evidence_refs": [
                    {
                        "ref_type": "POSITION_EVENT",
                        "public_id": event.public_id,
                        "label": event.event_type.value,
                        "href": f"/positions/{route_public_id}",
                    }
                ],
                "href": f"/positions/{route_public_id}",
            }
        )

    return {
        "review_status": (
            "CLOSED_PENDING_REVIEW"
            if truth_position.status == TradingPositionStatus.CLOSED
            else "OPEN"
        ),
        "position_summary": {
            "public_id": truth_position.public_id,
            "route_public_id": route_public_id,
            "title": truth_position.instrument.contract_symbol,
            "status": truth_position.status.value,
            "side": truth_position.side.value,
            "account": {
                "public_id": truth_position.account.public_id if truth_position.account else "",
                "label": truth_position.account.name if truth_position.account else "",
            },
            "asset": {
                "symbol": truth_position.instrument.contract_symbol,
                "asset_label": truth_position.instrument.asset.name if truth_position.instrument and truth_position.instrument.asset else truth_position.instrument.contract_symbol,
                "instrument_label": truth_position.instrument.display_name if truth_position.instrument else truth_position.instrument_id,
            },
            "opened_at": truth_position.opened_at,
            "closed_at": truth_position.closed_at,
            "realized_pnl_gross": truth_position.realized_pnl_gross,
            "realized_pnl_net": truth_position.realized_pnl_net,
            "total_fees": truth_position.total_fees,
            "quantity_opened": quantity_opened,
            "quantity_closed": quantity_closed,
            "open_quantity": max(Decimal("0"), quantity_opened - quantity_closed),
            "average_open_price": truth_position.avg_open_price,
            "average_close_price": truth_position.avg_close_price,
            "base_currency": truth_position.base_currency,
            "holding_period_seconds": truth_position.holding_period_seconds,
            "pnl_basis": {
                "cost_basis_method": truth_position.cost_basis_method,
                "realized_definition": "EVENT_REALIZED",
                "unrealized_definition": "MARK_TO_MARKET",
                "fee_treatment": "NET_INCLUDED",
                "fx_treatment": "EVENT_TIME_ACCOUNT_CCY",
            },
        },
        "thesis_block": {
            "source_event_public_id": opening_event.public_id if opening_event else None,
            "thesis": opening_event.thesis if opening_event else None,
            "invalidation_rule": opening_event.invalidation_rule if opening_event else None,
            "planned_exit_rule": opening_event.planned_exit_rule if opening_event else None,
            "sizing_rationale": opening_event.sizing_rationale if opening_event else None,
            "expected_holding_period": opening_event.expected_holding_period if opening_event else None,
            "checklist_snapshot": [
                {"label": key, "checked": bool(value)}
                for key, value in checklist_snapshot.items()
            ],
        },
        "lifecycle_thread": {
            "nodes": lifecycle_thread,
        },
        "result_summary": {
            "headline": f"{truth_position.instrument.contract_symbol} 交易生命周期",
            "summary": f"包含 {len(lifecycle_thread)} 个事件节点。",
            "key_numbers": [
                {"label": "累计开仓", "value": str(truth_position.quantity_opened or 0)},
                {"label": "累计平仓", "value": str(truth_position.quantity_closed or 0)},
                {"label": "已实现净盈亏", "value": str(truth_position.realized_pnl_net or 0)},
            ],
        },
        "execution_quality": {
            "execution_quality": "GOOD" if opening_event and opening_event.confidence and opening_event.confidence >= 4 else None,
            "drift_summary": None,
            "checklist_miss_count": sum(1 for checked in checklist_snapshot.values() if not checked),
        },
        "discipline_profile": None,
        "emotion_path": {
            "points": [
                {
                    "occurred_at": event.event_time,
                    "emotion": event.emotion,
                    "confidence": event.confidence,
                }
                for event in truth_position.events
                if event.emotion
            ]
        },
        "ledger_summary": {
            "account_currency": truth_position.base_currency,
            "cash_effects": cash_effects,
            "total_fees": truth_position.total_fees,
            "total_dividends": _ledger_total(truth_position, AccountLedgerEntryType.DIVIDEND),
            "total_adjustments": _ledger_total(truth_position, AccountLedgerEntryType.CASH_ADJUSTMENT),
        },
        "evidence_list": {
            "items": [
                {
                    "ref_type": "POSITION_EVENT",
                    "public_id": event.public_id,
                    "label": event.event_type.value,
                    "href": f"/positions/{route_public_id}",
                }
                for event in truth_position.events
            ]
        },
        "ai_sidecar": {
            "items": (
                _build_ai_sidecar_items(db, truth_position)
                if include_ai_sidecar
                else []
            )
        },
    }
