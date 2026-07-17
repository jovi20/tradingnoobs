import os
import tempfile
import unittest
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import DailySnapshot, User
from services.auth_service import get_current_user


class RiskRouterTests(unittest.TestCase):
    def setUp(self):
        fd, self.db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
        )
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        Base.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()
        self.user = User(
            email="risk-router@example.com",
            email_normalized="risk-router@example.com",
            hashed_password="hashed",
            public_id="risk-router-user",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.session.add(self.user)
        self.session.commit()
        self.session.refresh(self.user)

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
        self.capability_patch = patch(
            "services.capability_service.get_feature_flag_enabled",
            return_value=True,
        )
        self.capability_patch.start()
        self.client = TestClient(app)

    def tearDown(self):
        self.capability_patch.stop()
        app.dependency_overrides.clear()
        self.session.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def _add_snapshot(self, snapshot_date: date, total_equity: str) -> None:
        self.session.add(
            DailySnapshot(
                user_id=self.user.id,
                date=snapshot_date,
                total_equity=Decimal(total_equity),
                total_assets=Decimal(total_equity),
                total_liabilities=Decimal("0"),
                net_transfers=Decimal("0"),
            )
        )
        self.session.commit()

    def test_authenticated_user_can_fetch_risk_summary(self):
        self._add_snapshot(date(2026, 6, 10), "100000")
        self._add_snapshot(date(2026, 6, 11), "94000")

        response = self.client.get("/api/risk/summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("portfolio", payload)
        self.assertIn("alerts", payload)
        self.assertEqual(payload["portfolio"]["daily_pnl"], -6000.0)
        self.assertEqual(payload["alerts"][0]["kind"], "DAILY_LOSS_LIMIT")
        self.assertEqual(payload["alerts"][0]["severity"], "CRITICAL")

    def test_unauthenticated_request_returns_401(self):
        app.dependency_overrides.pop(get_current_user, None)

        response = self.client.get("/api/risk/summary")

        self.assertEqual(response.status_code, 401)

    def test_risk_summary_includes_stable_trust_source_refs(self):
        response = self.client.get("/api/risk/summary")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["trust"]["source"], "DERIVED")
        self.assertEqual(
            payload["trust"]["source_refs"],
            ["TradingPosition", "AccountLedgerEntry", "DailySnapshot"],
        )

    def test_core_dashboard_does_not_embed_optional_risk_summary(self):
        self._add_snapshot(date(2026, 6, 10), "100000")
        self._add_snapshot(date(2026, 6, 11), "94000")

        response = self.client.get("/api/dashboard/stats")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(
            set(payload),
            {
                "journal_balance",
                "realized_pnl",
                "win_rate",
                "avg_pnl_ratio",
                "total_trades",
                "open_positions",
                "closed_trades",
                "account_balances",
            },
        )


if __name__ == "__main__":
    unittest.main()
