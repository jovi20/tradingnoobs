from datetime import datetime, timezone
from decimal import Decimal

from models import EvidenceItem, ExternalCatalyst
from services.read_model_service import ReadModelService
from services.trading_accounting_service import TradingAccountingService


def test_home_read_model_returns_trust_wrapped_timeline_and_review_inbox(db_session):
    accounting = TradingAccountingService(db_session)
    event_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    position = accounting.open_position(
        user_id=1,
        account_id=1,
        symbol="AAPL",
        side="LONG",
        quantity=Decimal("10"),
        price=Decimal("100"),
        fee=Decimal("1.00"),
        event_time=event_time,
        thesis="Breakout setup",
        edge_source="price_volume",
        invalidation_rule="Close below base low",
        sizing_rationale="One risk unit",
        checklist_snapshot={"trend": True, "risk_reward": "2R"},
    )
    accounting.add_to_position(
        position_public_id=position.public_id,
        quantity=Decimal("5"),
        price=Decimal("110"),
        fee=Decimal("0.50"),
        event_time=event_time,
    )

    home = ReadModelService(db_session).build_home_read_model(user_id=1)

    assert home["meta"]["freshness"] == "FRESH"
    assert home["meta"]["source"] == "DERIVED"
    assert [event["type"] for event in home["timeline_events"]] == ["OPEN", "ADD"]
    assert home["timeline_events"][0]["linked_object_public_id"] == position.public_id
    assert home["timeline_events"][0]["trust_meta"]["value_status"] == "FINAL"
    assert home["review_inbox"] == []
    assert home["context_rail"]["open_positions"] == 1


def test_lifecycle_detail_returns_ordered_nodes_and_evidence(db_session):
    accounting = TradingAccountingService(db_session)
    event_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    position = accounting.open_position(
        user_id=1,
        account_id=1,
        symbol="MSFT",
        side="LONG",
        quantity=Decimal("10"),
        price=Decimal("100"),
        fee=Decimal("1.00"),
        event_time=event_time,
        thesis="Cloud margin expansion",
        edge_source="earnings_revision",
        invalidation_rule="Close below 200-day moving average",
        sizing_rationale="Half size until confirmation",
        checklist_snapshot={"trend": True},
    )
    accounting.add_to_position(
        position_public_id=position.public_id,
        quantity=Decimal("5"),
        price=Decimal("110"),
        fee=Decimal("0.50"),
        event_time=event_time,
    )
    accounting.reduce_position(
        position_public_id=position.public_id,
        quantity=Decimal("12"),
        price=Decimal("120"),
        fee=Decimal("1.20"),
        event_time=event_time,
    )
    accounting.close_position(
        position_public_id=position.public_id,
        quantity=Decimal("3"),
        price=Decimal("115"),
        fee=Decimal("0.30"),
        event_time=event_time,
    )

    detail = ReadModelService(db_session).build_lifecycle_detail(
        user_id=1,
        position_public_id=position.public_id,
    )

    assert detail["meta"]["freshness"] == "FRESH"
    assert detail["position_public_id"] == position.public_id
    assert [node["type"] for node in detail["lifecycle_nodes"]] == ["OPEN", "ADD", "REDUCE", "CLOSE"]
    assert detail["lifecycle_nodes"][0]["decision_fields"]["thesis"] == "Cloud margin expansion"
    assert len(detail["lifecycle_nodes"][0]["ledger_refs"]) == 4
    assert [item["kind"] for item in detail["evidence_items"]] == ["USER_NOTE", "CHECKLIST"]
    assert detail["narrative_signals"] == []


def test_external_catalysts_only_surface_when_linked_to_position_evidence(db_session):
    accounting = TradingAccountingService(db_session)
    event_time = datetime(2026, 1, 1, tzinfo=timezone.utc)
    position = accounting.open_position(
        user_id=1,
        account_id=1,
        symbol="TSLA",
        side="LONG",
        quantity=Decimal("3"),
        price=Decimal("200"),
        fee=Decimal("1.00"),
        event_time=event_time,
        thesis="Delivery acceleration setup",
    )
    db_session.add(
        EvidenceItem(
            public_id="01JLINKEDCATALYSTEVIDENCE001",
            kind="NEWS_LINK",
            source_name="Company IR",
            source_url_or_ref="https://example.com/linked",
            captured_at=event_time,
            summary="Delivery numbers beat consensus.",
            linked_tickers=["TSLA"],
            confidence="HIGH",
            invalidates_if="Management withdraws guidance.",
            linked_object_public_id=position.public_id,
        )
    )
    db_session.add(
        ExternalCatalyst(
            public_id="01JLINKEDCATALYST000000001",
            catalyst_type="EARNINGS_EVENT",
            title="Delivery beat",
            summary="Deliveries came in above expectations.",
            evidence_public_id="01JLINKEDCATALYSTEVIDENCE001",
            linked_object_public_id=position.public_id,
            occurred_at=event_time,
        )
    )
    db_session.add(
        EvidenceItem(
            public_id="01JUNLINKEDCATALYSTEVID001",
            kind="NEWS_LINK",
            source_name="Macro wire",
            source_url_or_ref="https://example.com/unlinked",
            captured_at=event_time,
            summary="Unlinked macro headline.",
            linked_tickers=["SPY"],
            confidence="LOW",
            invalidates_if=None,
            linked_object_public_id="different-object",
        )
    )
    db_session.add(
        ExternalCatalyst(
            public_id="01JUNLINKEDCATALYST000001",
            catalyst_type="MACRO_EVENT",
            title="Unlinked macro headline",
            summary="This should not appear for the TSLA position.",
            evidence_public_id="01JUNLINKEDCATALYSTEVID001",
            linked_object_public_id="different-object",
            occurred_at=event_time,
        )
    )
    db_session.flush()

    detail = ReadModelService(db_session).build_lifecycle_detail(
        user_id=1,
        position_public_id=position.public_id,
    )

    assert len(detail["narrative_signals"]) == 1
    assert detail["narrative_signals"][0]["public_id"] == "01JLINKEDCATALYST000000001"
    assert detail["narrative_signals"][0]["linked_evidence_public_ids"] == ["01JLINKEDCATALYSTEVIDENCE001"]
