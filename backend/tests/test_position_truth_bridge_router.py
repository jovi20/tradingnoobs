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
from models import (
    AssetMaster,
    AssetMetadata,
    BatchType,
    Position,
    PositionDirection,
    PositionStatus,
    TradeBatch,
    TradingAccount,
    TradingPosition,
    User,
)
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

    def _seed_proven_asset_identity(self, *, symbol: str, exchange_code: str) -> None:
        self.db.add(
            AssetMaster(
                public_id=f"proven-{symbol.lower()}-asset",
                canonical_code=symbol,
                display_symbol=symbol,
                name=symbol,
                asset_type="STOCK",
                quote_currency="USD",
                status="ACTIVE",
                metadata_json={
                    "journal_identity_v1": {
                        "asset_type": "STOCK",
                        "market": "US",
                        "exchange_code": exchange_code,
                        "normalized_symbol": symbol,
                        "instrument_type": "SPOT",
                        "quote_currency": "USD",
                    }
                },
            )
        )

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
        self._seed_proven_asset_identity(symbol="AAPL", exchange_code="NASDAQ")
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
        self._seed_proven_asset_identity(symbol="MSFT", exchange_code="NASDAQ")
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

    def test_truth_public_id_resolves_to_the_canonical_legacy_position_route(self):
        legacy_position = self._seed_open_legacy_position()
        lifecycle_response = self.client.get(
            f"/api/positions/{legacy_position.public_id}/truth-lifecycle"
        )
        self.assertEqual(lifecycle_response.status_code, 200)
        truth_public_id = lifecycle_response.json()["data"]["position_summary"]["public_id"]

        response = self.client.get(f"/api/positions/{truth_public_id}")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["public_id"], legacy_position.public_id)
        self.assertEqual(payload["truth_position_public_id"], truth_public_id)

    def test_bridge_read_preserves_manual_truth_events_and_canonical_accounting(self):
        legacy_position = self._seed_open_legacy_position()
        initial_response = self.client.get(
            f"/api/positions/{legacy_position.public_id}/truth-lifecycle"
        )
        self.assertEqual(initial_response.status_code, 200)
        truth_public_id = initial_response.json()["data"]["position_summary"]["public_id"]

        add_response = self.client.post(
            f"/api/trading-positions/{truth_public_id}/events",
            json={
                "event_type": "ADD",
                "quantity": "1",
                "price": "190",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
            },
        )
        self.assertEqual(add_response.status_code, 201)

        response = self.client.get(
            f"/api/positions/{legacy_position.public_id}/truth-lifecycle"
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        summary = payload["data"]["position_summary"]
        self.assertEqual(Decimal(str(summary["quantity_opened"])), Decimal("6"))
        self.assertEqual(Decimal(str(summary["open_quantity"])), Decimal("6"))
        self.assertEqual(summary["route_public_id"], legacy_position.public_id)
        node_types = [node["node_type"] for node in payload["data"]["lifecycle_thread"]["nodes"]]
        self.assertEqual(node_types, ["OPEN", "ADD"])

    def test_positions_list_uses_truth_accounting_projection_after_manual_event(self):
        legacy_position = self._seed_open_legacy_position()
        initial_response = self.client.get(
            f"/api/positions/{legacy_position.public_id}/truth-lifecycle"
        )
        truth_public_id = initial_response.json()["data"]["position_summary"]["public_id"]
        add_response = self.client.post(
            f"/api/trading-positions/{truth_public_id}/events",
            json={
                "event_type": "ADD",
                "quantity": "1",
                "price": "190",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
            },
        )
        self.assertEqual(add_response.status_code, 201)

        response = self.client.get("/api/positions")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        projected = next(item for item in payload if item["public_id"] == legacy_position.public_id)
        self.assertEqual(projected["truth_position_public_id"], truth_public_id)
        self.assertEqual(Decimal(str(projected["total_quantity"])), Decimal("6"))
        self.assertEqual(
            Decimal(str(projected["average_entry_price"])).quantize(Decimal("0.0001")),
            Decimal("181.6667"),
        )

    def test_dashboard_win_rate_uses_truth_exit_events_instead_of_stale_legacy_batches(self):
        legacy_position = self._seed_open_legacy_position()
        initial_response = self.client.get(
            f"/api/positions/{legacy_position.public_id}/truth-lifecycle"
        )
        truth_public_id = initial_response.json()["data"]["position_summary"]["public_id"]
        reduce_response = self.client.post(
            f"/api/trading-positions/{truth_public_id}/events",
            json={
                "event_type": "REDUCE",
                "quantity": "2",
                "price": "210",
                "currency": "USD",
                "occurred_at": "2026-04-03T15:30:00+00:00",
            },
        )
        self.assertEqual(reduce_response.status_code, 201)

        response = self.client.get("/api/dashboard/stats")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["win_rate"], 100.0)

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
                "exchange_code": "NASDAQ",
                "asset_type": "EQUITY",
                "direction": "LONG",
                "entry_price": "900",
                "quantity": "2",
                "entry_time": "2026-04-03T15:30:00+00:00",
                "entry_reason": "New position should create truth lifecycle",
                "entry_emotion": "Focused",
                "entry_confidence": 4,
                "asset_metadata": {
                    "core_type": "STOCK",
                    "market": "US",
                    "currency": "USD",
                    "instrument": "SPOT",
                },
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

    def test_position_identity_projection_is_consistent_across_create_list_detail_and_check(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-identity-projection",
            name="Identity Projection",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

        expected_metadata = {
            "symbol": "QQQ",
            "name": "QQQ",
            "core_type": "FUND",
            "market": "US",
            "currency": "USD",
            "sector": None,
            "instrument": "SPOT",
        }
        create_response = self.client.post(
            "/api/positions",
            json={
                "account_id": account.id,
                "symbol": " qqq ",
                "exchange_code": " nasdaq ",
                "asset_type": "ETF",
                "direction": "LONG",
                "entry_price": "500",
                "quantity": "2",
                "entry_time": "2026-04-03T15:30:00+00:00",
                "asset_metadata": {
                    "core_type": "FUND",
                    "market": "US",
                    "currency": "USD",
                    "instrument": "SPOT",
                },
            },
        )

        self.assertEqual(create_response.status_code, 201, create_response.text)
        created_payload = create_response.json()
        self.assertEqual(created_payload["asset_metadata"], expected_metadata)
        self.assertEqual(created_payload["asset_type"], "FUND")
        self.assertEqual(created_payload["exchange"], "NASDAQ")

        self.db.expire_all()
        stored_position = self.db.query(Position).filter(Position.symbol == "QQQ").one()
        self.assertIsNone(stored_position.asset_metadata_symbol)
        self.assertEqual(
            self.db.query(AssetMetadata).filter(AssetMetadata.symbol == "QQQ").count(),
            0,
        )

        # Canonical truth remains the response/filter authority if a legacy
        # compatibility column later drifts.
        stored_position.asset_type = "STOCK"
        stored_position.exchange = "NYSE"
        self.db.commit()

        detail_response = self.client.get(
            f"/api/positions/{created_payload['public_id']}"
        )
        list_response = self.client.get(
            "/api/positions",
            params={
                "account_id": account.id,
                "asset_type": "ETF",
                "core_type": "FUND",
                "market": "us",
            },
        )
        check_response = self.client.get(
            "/api/positions/check/open",
            params={
                "account_id": account.public_id,
                "symbol": "QQQ",
                "exchange_code": "NASDAQ",
                "direction": "LONG",
                "asset_type": "FUND",
                "market": "US",
                "instrument_type": "SPOT",
                "quote_currency": "USD",
            },
        )

        self.assertEqual(detail_response.status_code, 200, detail_response.text)
        self.assertEqual(list_response.status_code, 200, list_response.text)
        self.assertEqual(check_response.status_code, 200, check_response.text)
        self.assertEqual(len(list_response.json()), 1)
        for payload in (
            detail_response.json(),
            list_response.json()[0],
            check_response.json(),
        ):
            self.assertEqual(payload["asset_metadata"], expected_metadata)
            self.assertEqual(payload["asset_type"], "FUND")
            self.assertEqual(payload["exchange"], "NASDAQ")

        excluded = self.client.get(
            "/api/positions",
            params={
                "account_id": account.id,
                "asset_type": "STOCK",
            },
        )
        self.assertEqual(excluded.status_code, 200, excluded.text)
        self.assertEqual(excluded.json(), [])

        for non_ascii_market in ("\u00a0US", "US\u2003"):
            rejected_filter = self.client.get(
                "/api/positions",
                params={"account_id": account.id, "market": non_ascii_market},
            )
            self.assertEqual(rejected_filter.status_code, 422, rejected_filter.text)
            self.assertEqual(
                rejected_filter.json()["detail"]["code"],
                "UNSUPPORTED_MARKET",
            )

    def test_position_create_requires_release_asset_type_and_usd_account(self):
        usd_account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-release-guard-usd",
            name="Release Guard USD",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        non_usd_account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-release-guard-hkd",
            name="Release Guard HKD",
            broker="IBKR",
            currency="HKD",
            is_active=True,
        )
        self.db.add_all([usd_account, non_usd_account])
        self.db.commit()

        def request(account_id, asset_type_marker):
            payload = {
                "account_id": account_id,
                "symbol": "NVDA",
                "exchange_code": "NASDAQ",
                "direction": "LONG",
                "entry_price": "900",
                "quantity": "2",
                "entry_time": "2026-04-03T15:30:00+00:00",
                "asset_metadata": {
                    "core_type": "STOCK",
                    "market": "US",
                    "currency": "USD",
                    "instrument": "SPOT",
                },
            }
            if asset_type_marker is not None:
                payload["asset_type"] = asset_type_marker
            return self.client.post("/api/positions", json=payload)

        missing_response = request(usd_account.id, None)
        unsupported_response = request(usd_account.id, "BOND")
        currency_response = request(non_usd_account.id, "STOCK")

        self.assertEqual(missing_response.status_code, 422)
        self.assertEqual(missing_response.json()["detail"][0]["loc"][-1], "asset_type")
        self.assertEqual(unsupported_response.status_code, 422)
        self.assertEqual(
            unsupported_response.json()["detail"]["code"],
            "UNSUPPORTED_ASSET_TYPE",
        )
        self.assertEqual(currency_response.status_code, 422)
        self.assertEqual(
            currency_response.json()["detail"]["code"],
            "UNSUPPORTED_RELEASE_CURRENCY",
        )
        self.assertEqual(
            self.db.query(Position).filter(
                Position.account_id.in_([usd_account.id, non_usd_account.id])
            ).count(),
            0,
        )

    def test_position_create_normalizes_and_persists_full_release_identity(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-full-identity",
            name="Full Identity",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(account)
        self.db.commit()
        self.db.refresh(account)

        base_payload = {
            "account_id": account.id,
            "asset_type": "EQUITY",
            "direction": "LONG",
            "entry_price": "100",
            "quantity": "1",
            "entry_time": "2026-04-03T15:30:00+00:00",
            "asset_metadata": {
                "core_type": "equity",
                "market": "us",
                "currency": "usd",
                "instrument": "spot",
            },
        }

        def request(**overrides):
            return self.client.post(
                "/api/positions",
                json={**base_payload, **overrides},
            )

        for overrides, expected_code in (
            ({"symbol": "   ", "exchange_code": "NASDAQ"}, "INVALID_NORMALIZED_SYMBOL"),
            ({"symbol": " 苹果 ", "exchange_code": "NASDAQ"}, "INVALID_NORMALIZED_SYMBOL"),
            ({"symbol": "ſpy", "exchange_code": "NASDAQ"}, "INVALID_NORMALIZED_SYMBOL"),
            ({"symbol": "NVDA", "exchange_code": "naſdaq"}, "INVALID_EXCHANGE_CODE"),
            ({"symbol": "NVDA", "exchange_code": "ß"}, "INVALID_EXCHANGE_CODE"),
            ({"symbol": "NVDA", "exchange_code": "   "}, "INVALID_EXCHANGE_CODE"),
            ({"symbol": "NVDA", "exchange_code": "纳斯达克"}, "INVALID_EXCHANGE_CODE"),
        ):
            with self.subTest(overrides=overrides):
                response = request(**overrides)
                self.assertEqual(response.status_code, 422)
                self.assertEqual(response.json()["detail"]["code"], expected_code)

        shared_label_response = request(
            symbol="NVDA",
            exchange_code="NASDAQ",
            asset_metadata={
                **base_payload["asset_metadata"],
                "name": "User-owned label",
                "sector": "Technology",
            },
        )
        self.assertEqual(shared_label_response.status_code, 422)
        self.assertEqual(
            {item["loc"][-1] for item in shared_label_response.json()["detail"]},
            {"name", "sector"},
        )

        valid_response = request(symbol=" nvda ", exchange_code=" nasdaq ")
        self.assertEqual(valid_response.status_code, 201, valid_response.text)
        self.db.expire_all()
        position = self.db.query(Position).filter(Position.symbol == "NVDA").one()
        self.assertEqual(position.exchange, "NASDAQ")
        asset = self.db.query(AssetMaster).filter(AssetMaster.canonical_code == "NVDA").one()
        self.assertEqual(asset.asset_type, "STOCK")
        self.assertEqual(asset.quote_currency, "USD")
        self.assertEqual(
            asset.metadata_json["journal_identity_v1"],
            {
                "asset_type": "STOCK",
                "market": "US",
                "exchange_code": "NASDAQ",
                "normalized_symbol": "NVDA",
                "instrument_type": "SPOT",
                "quote_currency": "USD",
            },
        )

        duplicate_same_side = request(symbol="NVDA", exchange_code="NASDAQ")
        self.assertEqual(duplicate_same_side.status_code, 409, duplicate_same_side.text)
        self.assertEqual(
            duplicate_same_side.json()["detail"]["code"],
            "OPEN_POSITION_EXISTS",
        )

        opposite_side = request(
            symbol="NVDA",
            exchange_code="NASDAQ",
            direction="SHORT",
        )
        self.assertEqual(opposite_side.status_code, 201, opposite_side.text)

        # JRN-007 replaces the legacy symbol-only AssetMaster key. Until then,
        # a same-symbol cross-exchange create must fail closed rather than alias.
        conflicting_exchange = request(symbol="NVDA", exchange_code="NYSE")
        self.assertEqual(conflicting_exchange.status_code, 422)
        self.assertEqual(
            conflicting_exchange.json()["detail"]["code"],
            "INSTRUMENT_IDENTITY_MISMATCH",
        )
        self.assertEqual(
            self.db.query(Position).filter(Position.symbol == "NVDA").count(),
            2,
        )

        self.db.add(AssetMetadata(symbol="NULLMETA", name=None))
        self.db.commit()
        shared_metadata_response = request(
            symbol="NULLMETA",
            exchange_code="NASDAQ",
        )
        self.assertEqual(
            shared_metadata_response.status_code,
            201,
            shared_metadata_response.text,
        )
        self.db.expire_all()
        untouched = self.db.query(AssetMetadata).filter(
            AssetMetadata.symbol == "NULLMETA"
        ).one()
        self.assertIsNone(untouched.name)
        self.assertIsNone(untouched.core_type)
        self.assertIsNone(untouched.market)
        self.assertIsNone(untouched.currency)
        self.assertIsNone(untouched.instrument)
        created = self.db.query(Position).filter(Position.symbol == "NULLMETA").one()
        self.assertIsNone(created.asset_metadata_symbol)

    def test_truth_sync_rejects_any_unproven_legacy_exchange_without_partial_writes(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-unproven-exchange",
            name="Legacy broker-derived exchange",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        metadata = AssetMetadata(
            symbol="MSFT",
            name="Microsoft",
            core_type="STOCK",
            market="US",
            currency="USD",
            instrument="SPOT",
        )
        self.db.add_all([account, metadata])
        self.db.commit()
        position = Position(
            user_id=self.user.id,
            account_id=account.id,
            public_id="legacy-broker-derived-position",
            symbol="MSFT",
            exchange="Imported",
            asset_type="EQUITY",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=Decimal("1"),
            average_entry_price=Decimal("300"),
            opened_at=datetime(2026, 4, 1, 9, 30, tzinfo=timezone.utc),
            asset_metadata_symbol="MSFT",
        )
        self.db.add(position)
        self.db.commit()

        response = self.client.get(
            f"/api/positions/{position.public_id}/truth-lifecycle"
        )

        self.assertEqual(response.status_code, 422, response.text)
        self.assertEqual(
            response.json()["detail"]["code"],
            "LEGACY_INSTRUMENT_IDENTITY_UNPROVEN",
        )
        self.assertEqual(
            self.db.query(AssetMaster).filter(AssetMaster.canonical_code == "MSFT").count(),
            0,
        )
        self.assertEqual(
            self.db.query(TradingPosition).filter(
                TradingPosition.account_id == account.id
            ).count(),
            0,
        )

        detail = self.client.get(f"/api/positions/{position.public_id}")
        filtered_list = self.client.get(
            "/api/positions",
            params={"asset_type": "STOCK", "market": "US"},
        )
        check = self.client.get(
            "/api/positions/check/open",
            params={
                "account_id": account.public_id,
                "symbol": "MSFT",
                "exchange_code": "IMPORTED",
                "direction": "LONG",
                "asset_type": "STOCK",
                "market": "US",
                "instrument_type": "SPOT",
                "quote_currency": "USD",
            },
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertIsNone(detail.json()["asset_metadata"])
        self.assertEqual(filtered_list.status_code, 200, filtered_list.text)
        self.assertEqual(filtered_list.json(), [])
        self.assertEqual(check.status_code, 422, check.text)
        self.assertEqual(
            check.json()["detail"]["code"],
            "LEGACY_INSTRUMENT_IDENTITY_UNPROVEN",
        )
        self.assertEqual(
            self.db.query(TradingPosition).filter(
                TradingPosition.account_id == account.id
            ).count(),
            0,
        )

        def create(symbol: str):
            return self.client.post(
                "/api/positions",
                json={
                    "account_id": account.id,
                    "symbol": symbol,
                    "exchange_code": "NASDAQ",
                    "asset_type": "STOCK",
                    "direction": "LONG",
                    "entry_price": "100",
                    "quantity": "1",
                    "entry_time": "2026-04-03T15:30:00+00:00",
                    "asset_metadata": {
                        "core_type": "STOCK",
                        "market": "US",
                        "currency": "USD",
                        "instrument": "SPOT",
                    },
                },
            )

        same_symbol = create("MSFT")
        self.assertEqual(same_symbol.status_code, 422, same_symbol.text)
        self.assertEqual(
            same_symbol.json()["detail"]["code"],
            "LEGACY_INSTRUMENT_IDENTITY_UNPROVEN",
        )
        self.assertEqual(self.db.query(Position).filter(Position.account_id == account.id).count(), 1)
        self.assertEqual(self.db.query(AssetMaster).count(), 0)
        self.assertEqual(self.db.query(TradingPosition).count(), 0)

        different_symbol = create("AAPL")
        self.assertEqual(different_symbol.status_code, 201, different_symbol.text)
        self.assertEqual(different_symbol.json()["symbol"], "AAPL")
        self.assertEqual(self.db.query(Position).filter(Position.account_id == account.id).count(), 2)
        self.assertEqual(
            self.db.query(TradingPosition).filter(
                TradingPosition.account_id == account.id
            ).count(),
            1,
        )

    def test_exact_identity_proof_projects_without_creating_truth(self):
        position = self._seed_open_legacy_position()
        account = position.trading_account
        self.assertEqual(self.db.query(TradingPosition).count(), 0)

        detail = self.client.get(f"/api/positions/{position.public_id}")
        filtered_list = self.client.get(
            "/api/positions",
            params={"asset_type": "STOCK", "core_type": "EQUITY", "market": "US"},
        )
        check = self.client.get(
            "/api/positions/check/open",
            params={
                "account_id": account.public_id,
                "symbol": "MSFT",
                "exchange_code": "NASDAQ",
                "direction": "LONG",
                "asset_type": "STOCK",
                "market": "US",
                "instrument_type": "SPOT",
                "quote_currency": "USD",
            },
        )

        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(filtered_list.status_code, 200, filtered_list.text)
        self.assertEqual(check.status_code, 200, check.text)
        self.assertEqual(len(filtered_list.json()), 1)
        for payload in (detail.json(), filtered_list.json()[0], check.json()):
            self.assertEqual(payload["public_id"], position.public_id)
            self.assertEqual(payload["exchange"], "NASDAQ")
            self.assertEqual(payload["asset_metadata"]["core_type"], "STOCK")
            self.assertEqual(payload["asset_metadata"]["market"], "US")

        self.assertEqual(self.db.query(TradingPosition).count(), 0)
        self.assertEqual(
            self.db.query(AssetMaster).filter(
                AssetMaster.canonical_code == "MSFT"
            ).one().metadata_json["journal_identity_v1"]["exchange_code"],
            "NASDAQ",
        )

    def test_existing_legacy_truth_remains_readable_when_preupgrade_asset_lacks_identity_metadata(self):
        legacy_position = self._seed_legacy_position()
        first = self.client.get(
            f"/api/positions/{legacy_position.public_id}/truth-lifecycle"
        )
        self.assertEqual(first.status_code, 200, first.text)

        asset = self.db.query(AssetMaster).filter(AssetMaster.canonical_code == "AAPL").one()
        asset.metadata_json = {}
        self.db.commit()

        second = self.client.get(
            f"/api/positions/{legacy_position.public_id}/truth-lifecycle"
        )

        self.assertEqual(second.status_code, 200, second.text)
        self.assertEqual(
            second.json()["data"]["position_summary"]["public_id"],
            first.json()["data"]["position_summary"]["public_id"],
        )

        detail = self.client.get(f"/api/positions/{legacy_position.public_id}")
        filtered_list = self.client.get(
            "/api/positions",
            params={"asset_type": "EQUITY", "core_type": "STOCK", "market": "US"},
        )
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(filtered_list.status_code, 200, filtered_list.text)
        self.assertEqual(len(filtered_list.json()), 1)
        for payload in (detail.json(), filtered_list.json()[0]):
            self.assertEqual(
                payload["asset_metadata"],
                {
                    "symbol": "AAPL",
                    "name": "Apple Inc.",
                    "core_type": "STOCK",
                    "market": "US",
                    "currency": "USD",
                    "sector": None,
                    "instrument": "SPOT",
                },
            )

        self.db.expire_all()
        unchanged_asset = self.db.query(AssetMaster).filter(
            AssetMaster.canonical_code == "AAPL"
        ).one()
        self.assertEqual(unchanged_asset.metadata_json, {})

    def test_position_create_ignores_shared_legacy_metadata_and_never_mutates_it(self):
        account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-metadata-reuse",
            name="Metadata Reuse",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add_all([
            account,
            AssetMetadata(
                symbol="BADBOND",
                core_type="BOND",
                market="US",
                currency="USD",
            ),
            AssetMetadata(
                symbol="BADCCY",
                core_type="STOCK",
                market="US",
                currency="HKD",
            ),
            AssetMetadata(
                symbol="BADINSTR",
                core_type="STOCK",
                market="US",
                currency="USD",
                instrument="Future",
            ),
            AssetMetadata(
                symbol="BADMISMATCH",
                core_type="FUND",
                market="US",
                currency="USD",
                instrument="Spot",
            ),
            AssetMetadata(
                symbol="GOODMETA",
                core_type="STOCK",
                market="US",
                currency="USD",
                instrument="Spot",
            ),
            AssetMetadata(
                symbol="BADMASTER",
                core_type="STOCK",
                market="US",
                currency="USD",
                instrument="Spot",
            ),
            AssetMetadata(
                symbol="ALIASMASTER",
                core_type="STOCK",
                market="US",
                currency="USD",
                instrument="Spot",
            ),
            AssetMaster(
                public_id="bad-master-public-id",
                canonical_code="BADMASTER",
                display_symbol="BADMASTER",
                name="Conflicting master",
                asset_type="CRYPTO",
                quote_currency="USD",
                status="ACTIVE",
                metadata_json={},
            ),
            AssetMaster(
                public_id="alias-master-public-id",
                canonical_code="ALIASMASTER",
                display_symbol="ALIASMASTER",
                name="Noncanonical stored master",
                asset_type="EQUITY",
                quote_currency="usd",
                status="ACTIVE",
                metadata_json={
                    "journal_identity_v1": {
                        "asset_type": "STOCK",
                        "market": "US",
                        "exchange_code": "NASDAQ",
                        "normalized_symbol": "ALIASMASTER",
                        "instrument_type": "SPOT",
                        "quote_currency": "USD",
                    },
                },
            ),
        ])
        self.db.commit()
        self.db.refresh(account)

        def request(symbol):
            return self.client.post(
                "/api/positions",
                json={
                    "account_id": account.id,
                    "symbol": symbol,
                    "exchange_code": "NASDAQ",
                    "asset_type": "EQUITY",
                    "direction": "LONG",
                    "entry_price": "100",
                    "quantity": "1",
                    "entry_time": "2026-04-03T15:30:00+00:00",
                    "asset_metadata": {
                        "core_type": "STOCK",
                        "market": "US",
                        "currency": "USD",
                        "instrument": "SPOT",
                    },
                },
            )

        bad_type_response = request("BADBOND")
        bad_currency_response = request("BADCCY")
        bad_instrument_response = request("BADINSTR")
        mismatch_response = request("BADMISMATCH")
        bad_master_response = request("BADMASTER")
        alias_master_response = request("ALIASMASTER")
        valid_response = request("GOODMETA")

        for response in (
            bad_type_response,
            bad_currency_response,
            bad_instrument_response,
            mismatch_response,
            valid_response,
        ):
            self.assertEqual(response.status_code, 201, response.text)
        self.assertEqual(bad_master_response.status_code, 422)
        self.assertEqual(
            bad_master_response.json()["detail"]["code"],
            "INSTRUMENT_IDENTITY_MISMATCH",
        )
        self.assertEqual(alias_master_response.status_code, 422)
        self.assertEqual(
            alias_master_response.json()["detail"]["code"],
            "INSTRUMENT_IDENTITY_MISMATCH",
        )
        self.assertEqual(
            self.db.query(Position).filter(
                Position.symbol.in_([
                    "BADMASTER",
                    "ALIASMASTER",
                ])
            ).count(),
            0,
        )
        self.assertEqual(
            self.db.query(Position).filter(
                Position.symbol.in_([
                    "BADBOND",
                    "BADCCY",
                    "BADINSTR",
                    "BADMISMATCH",
                    "GOODMETA",
                ])
            ).count(),
            5,
        )
        self.db.expire_all()
        self.assertEqual(
            self.db.query(AssetMetadata).filter(AssetMetadata.symbol == "BADBOND").one().core_type.value,
            "BOND",
        )
        self.assertEqual(
            self.db.query(AssetMetadata).filter(AssetMetadata.symbol == "BADCCY").one().currency.value,
            "HKD",
        )
        asset = self.db.query(AssetMaster).filter(AssetMaster.canonical_code == "GOODMETA").one()
        self.assertEqual(asset.asset_type, "STOCK")
        self.assertEqual(asset.quote_currency, "USD")

    def test_shared_asset_metadata_patch_is_forbidden_without_owner_scoped_storage(self):
        legacy_position = self._seed_legacy_position()

        original = self.db.query(AssetMetadata).filter(AssetMetadata.symbol == "AAPL").one()
        original_values = (
            original.core_type,
            original.market,
            original.currency,
            original.instrument,
            original.sector,
        )
        for metadata_update in (
            {"core_type": "BOND"},
            {"market": "CRYPTO"},
            {"currency": "HKD"},
            {"instrument": "Future"},
            {"sector": "Technology"},
            {},
        ):
            with self.subTest(metadata_update=metadata_update):
                response = self.client.patch(
                    f"/api/positions/{legacy_position.public_id}",
                    json={"asset_metadata": metadata_update},
                )
                self.assertEqual(response.status_code, 422, response.text)
                self.assertTrue(
                    all(
                        item["type"] == "extra_forbidden"
                        for item in response.json()["detail"]
                    )
                )

        self.db.expire_all()
        metadata = self.db.query(AssetMetadata).filter(AssetMetadata.symbol == "AAPL").one()
        self.assertEqual(
            (
                metadata.core_type,
                metadata.market,
                metadata.currency,
                metadata.instrument,
                metadata.sector,
            ),
            original_values,
        )

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
