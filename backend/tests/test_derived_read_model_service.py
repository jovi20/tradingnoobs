from datetime import datetime, timezone

from services.derived_read_model_service import DerivedReadModelService


def test_derived_cache_returns_payload_with_freshness_metadata(db_session):
    service = DerivedReadModelService(db_session)
    as_of = datetime(2026, 1, 1, tzinfo=timezone.utc)

    service.store_dashboard_cache(
        user_id=1,
        cache_key="home-summary",
        payload={"open_positions": 2},
        as_of=as_of,
        freshness="FRESH",
    )
    service.store_position_metric(
        position_public_id="01JPOSITIONMETRIC000000000",
        metric_key="risk-summary",
        payload={"r_multiple": 2.5},
        as_of=as_of,
        freshness="DELAYED",
    )

    dashboard = service.get_dashboard_cache(user_id=1, cache_key="home-summary")
    metric = service.get_position_metric(
        position_public_id="01JPOSITIONMETRIC000000000",
        metric_key="risk-summary",
    )

    assert dashboard["payload"] == {"open_positions": 2}
    assert dashboard["meta"]["as_of"] == as_of.isoformat()
    assert dashboard["meta"]["freshness"] == "FRESH"
    assert metric["payload"] == {"r_multiple": 2.5}
    assert metric["meta"]["freshness"] == "DELAYED"
