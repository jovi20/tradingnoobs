import os
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import AssetMetadata, BatchType, Position, PositionDirection, PositionStatus, TradeBatch, TradingAccount, User
from services.auth_service import get_current_user


class PositionTruthBridgeRouterTests(unittest.TestCase):
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
            email="bridge@example.com",
            email_normalized="bridge@example.com",
            hashed_password="hashed",
            public_id="user-public-id",
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
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _seed_legacy_position(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-public-id",
            name="IBKR Main",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)

        metadata = AssetMetadata(
            symbol="AAPL",
            name="Apple Inc.",
            core_type="STOCK",
            market="US",
            currency="USD",
            instrument="Spot",
        )
        self.db.add(metadata)
        self.db.commit()
        self.db.refresh(account)

        legacy_position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="legacy-position",
            symbol="AAPL",
            exchange="NASDAQ",
            asset_type="EQUITY",
            direction=PositionDirection.LONG,
            status=PositionStatus.CLOSED,
            total_quantity=Decimal("0"),
            average_entry_price=Decimal("185"),
            realized_pnl=Decimal("180"),
            opened_at=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
            closed_at=datetime(2026, 4, 5, 16, 0, tzinfo=timezone.utc),
            trade_review="Held plan well.",
            checklist_responses={"pre_market": True, "risk_check": False},
            asset_metadata_symbol="AAPL",
        )
        self.db.add(legacy_position)
        self.db.commit()
        self.db.refresh(legacy_position)

        self.db.add_all([
            TradeBatch(
                public_id="batch-open",
                position_id=legacy_position.id,
                type=BatchType.ENTRY,
                price=Decimal("180"),
                quantity=Decimal("5"),
                time=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
                reason="Initial breakout entry",
                emotion="Confident",
                confidence=4,
            ),
            TradeBatch(
                public_id="batch-close",
                position_id=legacy_position.id,
                type=BatchType.EXIT,
                price=Decimal("203"),
                quantity=Decimal("5"),
                time=datetime(2026, 4, 5, 16, 0, tzinfo=timezone.utc),
                reason="Take profit",
                emotion="Calm",
                confidence=5,
                pnl=Decimal("115"),
            ),
        ])
        self.db.commit()
        return legacy_position

    def test_position_truth_bridge_endpoint_syncs_and_returns_truth_lifecycle(self):
        legacy_position = self._seed_legacy_position()

        response = self.client.get(f"/api/positions/{legacy_position.public_id}/truth-lifecycle")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["data"]["position_summary"]["title"], "AAPL")
        self.assertEqual(payload["data"]["thesis_block"]["thesis"], "Initial breakout entry")
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "CLOSE"])


if __name__ == "__main__":
    unittest.main()
