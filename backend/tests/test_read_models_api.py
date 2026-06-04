from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient

from database import get_db
from main import app
from services.auth_service import create_access_token, create_user
from services.trading_accounting_service import TradingAccountingService


def test_v1_read_model_endpoints_return_trust_wrapped_contracts(db_session):
    user = create_user(db_session, "readmodels@example.com", "strong-password")
    token = create_access_token({"sub": user.public_id})
    position = TradingAccountingService(db_session).open_position(
        user_id=user.id,
        account_id=1,
        symbol="AAPL",
        side="LONG",
        quantity=Decimal("10"),
        price=Decimal("100"),
        fee=Decimal("1.00"),
        event_time=datetime(2026, 1, 1, tzinfo=timezone.utc),
        thesis="Breakout setup",
        edge_source="price_volume",
        invalidation_rule="Close below base low",
        checklist_snapshot={"trend": True},
    )
    db_session.commit()

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        home_response = client.get("/api/v1/read-models/home", headers={"Authorization": f"Bearer {token}"})
        lifecycle_response = client.get(
            f"/api/v1/read-models/trading-positions/{position.public_id}/lifecycle",
            headers={"Authorization": f"Bearer {token}"},
        )
    finally:
        app.dependency_overrides.clear()

    assert home_response.status_code == 200
    home = home_response.json()
    assert "meta" in home
    assert "id" not in home["timeline_events"][0]
    assert home["timeline_events"][0]["linked_object_public_id"] == position.public_id

    assert lifecycle_response.status_code == 200
    lifecycle = lifecycle_response.json()
    assert "meta" in lifecycle
    assert lifecycle["position_public_id"] == position.public_id
    assert "id" not in lifecycle["lifecycle_nodes"][0]
    assert lifecycle["lifecycle_nodes"][0]["event_public_id"] == home["timeline_events"][0]["public_id"]
