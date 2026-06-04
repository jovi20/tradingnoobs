from datetime import datetime, timezone

from fastapi.testclient import TestClient

from database import get_db
from main import app
from services.auth_service import create_access_token, create_user


def test_create_v1_trading_position_returns_public_contract(db_session):
    user = create_user(db_session, "truth-api@example.com", "strong-password")
    token = create_access_token({"sub": user.public_id})

    def override_db():
        yield db_session

    app.dependency_overrides[get_db] = override_db
    client = TestClient(app)
    try:
        response = client.post(
            "/api/v1/trading-positions",
            headers={"Authorization": f"Bearer {token}"},
            json={
                "account_id": 1,
                "symbol": "AAPL",
                "side": "LONG",
                "quantity": "10",
                "price": "100",
                "fee": "1.00",
                "event_time": datetime(2026, 1, 1, tzinfo=timezone.utc).isoformat(),
                "thesis": "Breakout setup",
                "edge_source": "price_volume",
                "invalidation_rule": "Close below base low",
                "sizing_rationale": "One risk unit",
                "checklist_snapshot": {"trend": True},
            },
        )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    payload = response.json()
    assert "id" not in payload
    assert len(payload["public_id"]) == 26
    assert payload["symbol"] == "AAPL"
    assert payload["status"] == "OPEN"
    assert payload["events"][0]["event_type"] == "OPEN"
    assert payload["events"][0]["thesis"] == "Breakout setup"
    assert payload["events"][0]["edge_source"] == "price_volume"
    assert payload["events"][0]["invalidation_rule"] == "Close below base low"
    assert payload["events"][0]["sizing_rationale"] == "One risk unit"
    assert payload["events"][0]["checklist_snapshot"] == {"trend": True}
    assert payload["ledger_entries"][0]["entry_type"] == "OPEN"
    assert "id" not in payload["events"][0]
    assert "id" not in payload["ledger_entries"][0]
