from datetime import datetime, timezone

from models import AccountLedgerEntry, EvidenceItem, ExternalCatalyst, PositionEvent, TradeInstrument, TradingPosition


class ReadModelService:
    def __init__(self, db_session):
        self.db = db_session

    def build_home_read_model(self, *, user_id: int) -> dict:
        positions = self.db.query(TradingPosition).filter_by(user_id=user_id).all()
        position_ids = [position.id for position in positions]
        events = []
        if position_ids:
            events = (
                self.db.query(PositionEvent)
                .filter(PositionEvent.position_id.in_(position_ids))
                .order_by(PositionEvent.event_time)
                .all()
            )

        timeline_events = [self._timeline_event(event) for event in events]
        review_inbox = []
        for position in positions:
            review_inbox.extend(self._review_items_for_position(position))

        return {
            "meta": self._trust_meta(source="DERIVED"),
            "timeline_events": timeline_events,
            "review_inbox": review_inbox,
            "context_rail": {
                "open_positions": sum(1 for position in positions if position.status == "OPEN"),
                "closed_positions": sum(1 for position in positions if position.status == "CLOSED"),
            },
        }

    def build_lifecycle_detail(self, *, user_id: int, position_public_id: str) -> dict:
        position = self.db.query(TradingPosition).filter_by(
            user_id=user_id,
            public_id=position_public_id,
        ).one()
        events = (
            self.db.query(PositionEvent)
            .filter_by(position_id=position.id)
            .order_by(PositionEvent.event_time)
            .all()
        )
        ledger_entries = self.db.query(AccountLedgerEntry).filter_by(related_position_id=position.id).all()
        ledger_refs = [entry.public_id for entry in ledger_entries]

        return {
            "meta": self._trust_meta(source="DERIVED"),
            "position_public_id": position.public_id,
            "lifecycle_nodes": [self._lifecycle_node(event=event, ledger_refs=ledger_refs) for event in events],
            "evidence_items": self._evidence_items_for_events(events=events, position_public_id=position.public_id),
            "narrative_signals": self._linked_narrative_signals(position_public_id=position.public_id),
        }

    def _timeline_event(self, event: PositionEvent) -> dict:
        position = self.db.query(TradingPosition).filter_by(id=event.position_id).one()
        instrument = self.db.query(TradeInstrument).filter_by(id=position.instrument_id).one()
        return {
            "public_id": event.public_id,
            "type": event.event_type,
            "occurred_at": event.event_time,
            "subject": instrument.symbol,
            "summary": self._event_summary(event=event, symbol=instrument.symbol),
            "impact": {
                "quantity": event.quantity,
                "price": event.price,
                "realized_pnl_net": event.realized_pnl_net,
            },
            "trust_meta": self._trust_meta(source="DERIVED"),
            "linked_object_public_id": position.public_id,
            "evidence_refs": [],
        }

    def _review_items_for_position(self, position: TradingPosition) -> list[dict]:
        open_event = (
            self.db.query(PositionEvent)
            .filter_by(position_id=position.id, event_type="OPEN")
            .order_by(PositionEvent.event_time)
            .first()
        )
        if not open_event:
            return []

        items = []
        if not open_event.thesis:
            items.append(self._review_item(position=position, kind="MISSING_THESIS", summary="Add the opening thesis."))
        if not open_event.invalidation_rule:
            items.append(self._review_item(position=position, kind="PLAN_DRIFT", summary="Add an invalidation rule."))
        if not open_event.checklist_snapshot:
            items.append(self._review_item(position=position, kind="CHECKLIST_MISS", summary="Attach the entry checklist."))
        return items

    def _review_item(self, *, position: TradingPosition, kind: str, summary: str) -> dict:
        return {
            "kind": kind,
            "severity": "MEDIUM",
            "summary": summary,
            "reason": "Decision-quality evidence is incomplete.",
            "recommended_action": "Complete the missing trade narrative before review.",
            "linked_object_public_id": position.public_id,
            "due_state": "OPEN",
            "trust_meta": self._trust_meta(source="DERIVED"),
        }

    def _lifecycle_node(self, *, event: PositionEvent, ledger_refs: list[str]) -> dict:
        return {
            "type": event.event_type,
            "occurred_at": event.event_time,
            "position_public_id": self.db.query(TradingPosition).filter_by(id=event.position_id).one().public_id,
            "event_public_id": event.public_id,
            "decision_fields": {
                "thesis": event.thesis,
                "edge_source": event.edge_source,
                "disconfirming_evidence": event.disconfirming_evidence,
                "invalidation_rule": event.invalidation_rule,
                "expected_holding_period": event.expected_holding_period,
                "planned_exit_rule": event.planned_exit_rule,
                "sizing_rationale": event.sizing_rationale,
                "checklist_snapshot": event.checklist_snapshot,
            },
            "execution_fields": {
                "quantity": event.quantity,
                "price": event.price,
                "fee": event.fee,
                "realized_pnl_gross": event.realized_pnl_gross,
                "realized_pnl_net": event.realized_pnl_net,
            },
            "ledger_refs": ledger_refs,
            "evidence_refs": self._evidence_refs_for_event(event),
        }

    def _evidence_items_for_events(self, *, events: list[PositionEvent], position_public_id: str) -> list[dict]:
        items = []
        stored_items = self.db.query(EvidenceItem).filter_by(linked_object_public_id=position_public_id).all()
        for item in stored_items:
            items.append(
                {
                    "public_id": item.public_id,
                    "kind": item.kind,
                    "source_name": item.source_name,
                    "source_url_or_ref": item.source_url_or_ref,
                    "captured_at": item.captured_at,
                    "summary": item.summary,
                    "linked_tickers": item.linked_tickers,
                    "confidence": item.confidence,
                    "invalidates_if": item.invalidates_if,
                    "linked_object_public_id": item.linked_object_public_id,
                }
            )
        for event in events:
            if event.thesis:
                items.append(
                    {
                        "public_id": f"{event.public_id}-THESIS",
                        "kind": "USER_NOTE",
                        "source_name": "TradingPosition thesis",
                        "source_url_or_ref": event.public_id,
                        "captured_at": event.event_time,
                        "summary": event.thesis,
                        "linked_tickers": [],
                        "confidence": "USER_PROVIDED",
                        "invalidates_if": event.invalidation_rule,
                        "linked_object_public_id": position_public_id,
                    }
                )
            if event.checklist_snapshot:
                items.append(
                    {
                        "public_id": f"{event.public_id}-CHECKLIST",
                        "kind": "CHECKLIST",
                        "source_name": "Entry checklist",
                        "source_url_or_ref": event.public_id,
                        "captured_at": event.event_time,
                        "summary": "Entry checklist captured",
                        "linked_tickers": [],
                        "confidence": "USER_PROVIDED",
                        "invalidates_if": None,
                        "linked_object_public_id": position_public_id,
                    }
                )
        return items

    def _linked_narrative_signals(self, *, position_public_id: str) -> list[dict]:
        catalysts = self.db.query(ExternalCatalyst).filter_by(linked_object_public_id=position_public_id).all()
        return [
            {
                "public_id": catalyst.public_id,
                "signal_type": catalyst.catalyst_type,
                "direction": "CONTEXT",
                "strength": "MEDIUM",
                "sample_size": 1,
                "time_window": None,
                "summary": catalyst.summary,
                "linked_evidence_public_ids": [catalyst.evidence_public_id],
                "trust_meta": self._trust_meta(source="EXTERNAL"),
            }
            for catalyst in catalysts
        ]

    @staticmethod
    def _evidence_refs_for_event(event: PositionEvent) -> list[str]:
        refs = []
        if event.thesis:
            refs.append(f"{event.public_id}-THESIS")
        if event.checklist_snapshot:
            refs.append(f"{event.public_id}-CHECKLIST")
        return refs

    @staticmethod
    def _event_summary(*, event: PositionEvent, symbol: str) -> str:
        return f"{event.event_type} {event.quantity} {symbol} @ {event.price}"

    @staticmethod
    def _trust_meta(*, source: str) -> dict:
        return {
            "as_of": datetime.now(timezone.utc).isoformat(),
            "freshness": "FRESH",
            "source": source,
            "maturity": "EARLY_SIGNAL",
            "value_status": "FINAL",
            "generated_by": "read_model_service",
            "source_refs": [],
        }
