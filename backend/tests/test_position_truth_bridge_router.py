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

    def _seed_open_legacy_position(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-open-public-id",
            name="IBKR Open",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)

        metadata = AssetMetadata(
            symbol="MSFT",
            name="Microsoft",
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
            public_id="legacy-open-position",
            symbol="MSFT",
            exchange="NASDAQ",
            asset_type="EQUITY",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=Decimal("5"),
            average_entry_price=Decimal("180"),
            realized_pnl=Decimal("0"),
            opened_at=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
            asset_metadata_symbol="MSFT",
        )
        self.db.add(legacy_position)
        self.db.commit()
        self.db.refresh(legacy_position)

        self.db.add(
            TradeBatch(
                public_id="batch-open-msft",
                position_id=legacy_position.id,
                type=BatchType.ENTRY,
                price=Decimal("180"),
                quantity=Decimal("5"),
                time=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
                reason="Initial trend entry",
                emotion="Prepared",
                confidence=4,
            )
        )
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

    def test_legacy_batch_write_is_rejected_when_truth_lifecycle_exists_without_migration_header(self):
        legacy_position = self._seed_open_legacy_position()
        sync_response = self.client.get(f"/api/positions/{legacy_position.public_id}/truth-lifecycle")
        self.assertEqual(sync_response.status_code, 200)

        response = self.client.post(
            f"/api/positions/{legacy_position.public_id}/batches",
            json={
                "type": "ENTRY",
                "price": "190",
                "quantity": "1",
                "time": "2026-04-03T15:30:00+00:00",
                "reason": "Ordinary add should use truth event route",
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("Legacy batch writes are migration-only", response.json()["detail"])
        self.db.expire_all()
        self.assertEqual(
            self.db.query(TradeBatch).filter(TradeBatch.position_id == legacy_position.id).count(),
            1,
        )

    def test_legacy_batch_write_allows_explicit_migration_fallback_header(self):
        legacy_position = self._seed_open_legacy_position()
        sync_response = self.client.get(f"/api/positions/{legacy_position.public_id}/truth-lifecycle")
        self.assertEqual(sync_response.status_code, 200)

        response = self.client.post(
            f"/api/positions/{legacy_position.public_id}/batches",
            headers={"X-Migration-Fallback": "legacy-batch-write"},
            json={
                "type": "ENTRY",
                "price": "190",
                "quantity": "1",
                "time": "2026-04-03T15:30:00+00:00",
                "reason": "Explicit migration backfill",
            },
        )

        self.assertEqual(response.status_code, 201)
        self.db.expire_all()
        self.assertEqual(
            self.db.query(TradeBatch).filter(TradeBatch.position_id == legacy_position.id).count(),
            2,
        )

    def test_legacy_position_delete_is_rejected_when_truth_lifecycle_exists_without_migration_header(self):
        legacy_position = self._seed_legacy_position()
        sync_response = self.client.get(f"/api/positions/{legacy_position.public_id}/truth-lifecycle")
        self.assertEqual(sync_response.status_code, 200)

        response = self.client.delete(f"/api/positions/{legacy_position.public_id}")

        self.assertEqual(response.status_code, 409)
        self.assertIn("Legacy position hard deletes are migration-only", response.json()["detail"])
        self.db.expire_all()
        self.assertIsNotNone(self.db.query(Position).filter(Position.id == legacy_position.id).first())
        self.assertEqual(
            self.db.query(TradeBatch).filter(TradeBatch.position_id == legacy_position.id).count(),
            2,
        )

    def test_legacy_batch_edit_is_rejected_when_truth_lifecycle_exists_without_migration_header(self):
        legacy_position = self._seed_legacy_position()
        sync_response = self.client.get(f"/api/positions/{legacy_position.public_id}/truth-lifecycle")
        self.assertEqual(sync_response.status_code, 200)

        response = self.client.patch(
            "/api/positions/batches/batch-open",
            json={"price": "181"},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("Legacy batch edits are migration-only", response.json()["detail"])
        self.db.expire_all()
        batch = self.db.query(TradeBatch).filter(TradeBatch.public_id == "batch-open").one()
        self.assertEqual(batch.price, Decimal("180.00000000"))

    def test_legacy_batch_delete_is_rejected_when_truth_lifecycle_exists_without_migration_header(self):
        legacy_position = self._seed_legacy_position()
        sync_response = self.client.get(f"/api/positions/{legacy_position.public_id}/truth-lifecycle")
        self.assertEqual(sync_response.status_code, 200)

        response = self.client.delete("/api/positions/batches/batch-close")

        self.assertEqual(response.status_code, 409)
        self.assertIn("Legacy batch edits are migration-only", response.json()["detail"])
        self.db.expire_all()
        self.assertIsNotNone(self.db.query(TradeBatch).filter(TradeBatch.public_id == "batch-close").first())
        self.assertEqual(
            self.db.query(TradeBatch).filter(TradeBatch.position_id == legacy_position.id).count(),
            2,
        )

    def test_position_create_syncs_truth_lifecycle_and_returns_truth_public_id(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-create-public-id",
            name="IBKR Create",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

        response = self.client.post(
            "/api/positions",
            json={
                "account_id": account.id,
                "symbol": "NVDA",
                "asset_type": "EQUITY",
                "direction": "LONG",
                "entry_price": "900",
                "quantity": "2",
                "entry_time": "2026-04-03T15:30:00+00:00",
                "entry_reason": "New position should create truth lifecycle",
                "entry_emotion": "Focused",
                "entry_confidence": 4,
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        truth_public_id = payload.get("truth_position_public_id")
        self.assertIsNotNone(truth_public_id)

        lifecycle_response = self.client.get(f"/api/trading-positions/{truth_public_id}/lifecycle")
        self.assertEqual(lifecycle_response.status_code, 200)
        lifecycle_payload = lifecycle_response.json()
        self.assertEqual(lifecycle_payload["data"]["position_summary"]["public_id"], truth_public_id)
        node_types = [node["node_type"] for node in lifecycle_payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN"])

    def test_legacy_review_write_is_rejected_when_truth_lifecycle_exists_without_migration_header(self):
        legacy_position = self._seed_legacy_position()
        sync_response = self.client.get(f"/api/positions/{legacy_position.public_id}/truth-lifecycle")
        self.assertEqual(sync_response.status_code, 200)

        response = self.client.patch(
            f"/api/positions/{legacy_position.public_id}",
            json={"trade_review": "Ordinary review should use truth narrative."},
        )

        self.assertEqual(response.status_code, 409)
        self.assertIn("Legacy review writes are migration-only", response.json()["detail"])
        self.db.expire_all()
        updated_position = self.db.query(Position).filter(Position.id == legacy_position.id).one()
        self.assertEqual(updated_position.trade_review, "Held plan well.")

    def test_legacy_review_write_allows_explicit_migration_fallback_header(self):
        legacy_position = self._seed_legacy_position()
        sync_response = self.client.get(f"/api/positions/{legacy_position.public_id}/truth-lifecycle")
        self.assertEqual(sync_response.status_code, 200)

        response = self.client.patch(
            f"/api/positions/{legacy_position.public_id}",
            headers={"X-Migration-Fallback": "legacy-review-write"},
            json={"trade_review": "Migration-only legacy review correction."},
        )

        self.assertEqual(response.status_code, 200)
        self.db.expire_all()
        updated_position = self.db.query(Position).filter(Position.id == legacy_position.id).one()
        self.assertEqual(updated_position.trade_review, "Migration-only legacy review correction.")


if __name__ == "__main__":
    unittest.main()
