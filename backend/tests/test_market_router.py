import os
import tempfile
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import User
from services.auth_service import get_current_user


class MarketRouterTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)

        self.db = self.SessionLocal()
        self.user = User(
            email="market-router@example.com",
            email_normalized="market-router@example.com",
            hashed_password="hashed",
            public_id="market-router-user",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        def override_get_db():
            db = self.SessionLocal()
            try:
                yield db
            finally:
                db.close()

        async def override_get_current_user():
            return self.user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_get_current_user
        self.client = TestClient(app, raise_server_exceptions=False)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_quote_endpoint_awaits_market_data_service(self):
        async def fake_get_quote(self, symbol, exchange):
            return {
                "c": 100,
                "pc": 95,
                "provider": "finnhub",
                "freshness": "FRESH",
                "degraded": False,
                "source_refs": ["provider:finnhub", "symbol:MSFT"],
            }

        with (
            patch("routers.market.MarketDataService.get_quote", new=fake_get_quote),
            patch("routers.market.MarketDataService.detect_asset_type", return_value="US_STOCK"),
        ):
            response = self.client.get("/api/market/quote/MSFT?exchange=NASDAQ")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["symbol"], "MSFT")
        self.assertEqual(payload["asset_type"], "US_STOCK")
        self.assertEqual(payload["quote"]["c"], 100)
        self.assertEqual(payload["quote"]["pc"], 95)
        self.assertEqual(payload["provider"], "finnhub")
        self.assertEqual(payload["freshness"], "FRESH")
        self.assertFalse(payload["degraded"])
        self.assertEqual(payload["source_refs"], ["provider:finnhub", "symbol:MSFT"])
        self.assertEqual(payload["trust"]["freshness"], "FRESH")

    def test_quote_endpoint_returns_error_payload_on_provider_failure(self):
        async def failing_get_quote(self, symbol, exchange):
            raise RuntimeError("provider down")

        with patch("routers.market.MarketDataService.get_quote", new=failing_get_quote):
            response = self.client.get("/api/market/quote/MSFT")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["symbol"], "MSFT")
        self.assertEqual(payload["error"], "provider down")
        self.assertEqual(payload["freshness"], "UNAVAILABLE")
        self.assertTrue(payload["degraded"])
        self.assertIn("symbol:MSFT", payload["source_refs"])

    def test_validate_endpoint_preserves_existing_shape(self):
        async def fake_validate_symbol(self, symbol, exchange):
            return {
                "valid": True,
                "symbol": symbol.upper(),
                "asset_type": "US_STOCK",
                "price": 100,
                "name": "MSFT",
                "metadata": {"market": "US"},
            }

        with patch("routers.market.MarketDataService.validate_symbol", new=fake_validate_symbol):
            response = self.client.get("/api/market/validate/msft?exchange=NASDAQ")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "valid": True,
                "symbol": "MSFT",
                "asset_type": "US_STOCK",
                "price": 100,
                "name": "MSFT",
                "metadata": {"market": "US"},
            },
        )


if __name__ == "__main__":
    unittest.main()
