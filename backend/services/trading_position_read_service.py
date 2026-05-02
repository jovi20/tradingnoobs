"""
Trading Noobs Backend - TradingPosition Truth Read Service
"""
from __future__ import annotations

from sqlalchemy.orm import Session, joinedload

from models import AccountLedgerEntry, AccountLedgerEntryType, PositionEventType, TradeInstrument, TradingPosition, TradingPositionStatus


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
        (entry.amount for entry in truth_position.ledger_entries if entry.entry_type == entry_type),
        0,
    )


def build_trading_position_lifecycle_payload(truth_position: TradingPosition) -> dict:
    opening_event = next((event for event in truth_position.events if event.event_type == PositionEventType.OPEN), None)
    checklist_snapshot = opening_event.checklist_snapshot or {} if opening_event else {}
    cash_effects = _ledger_cash_effects(truth_position)

    lifecycle_thread = []
    for event in truth_position.events:
        lifecycle_thread.append(
            {
                "node_public_id": event.public_id,
                "node_type": _node_type(event.event_type),
                "occurred_at": event.event_time,
                "title": f"{truth_position.instrument.contract_symbol} {event.event_type.value}",
                "summary": event.reason or event.note or event.event_type.value,
                "related_event_public_id": event.public_id,
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
                        "href": f"/positions/{truth_position.public_id}",
                    }
                ],
                "href": f"/positions/{truth_position.public_id}",
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
            "headline": f"{truth_position.instrument.contract_symbol} lifecycle",
            "summary": f"包含 {len(lifecycle_thread)} 个事件节点。",
            "key_numbers": [
                {"label": "Opened", "value": str(truth_position.quantity_opened or 0)},
                {"label": "Closed", "value": str(truth_position.quantity_closed or 0)},
                {"label": "Realized Net", "value": str(truth_position.realized_pnl_net or 0)},
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
                    "href": f"/positions/{truth_position.public_id}",
                }
                for event in truth_position.events
            ]
        },
        "ai_sidecar": {"items": []},
    }
