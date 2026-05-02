import os
import tempfile
import unittest
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import Position, PositionDirection, PositionStatus, TradingAccount, User
from services.auth_service import get_current_user


class PublicIdRouteTests(unittest.TestCase):
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
            email="publicid@example.com",
            email_normalized="publicid@example.com",
            hashed_password="hashed",
            public_id="user-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(self.user)
        self.db.commit()
        self.db.refresh(self.user)

        self.account = TradingAccount(
            user_id=self.user.id,
            public_id="acct-public-id",
            name="IBKR Main",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        self.db.add(self.account)
        self.db.commit()
        self.db.refresh(self.account)

        self.position = Position(
            user_id=self.user.id,
            account_id=self.account.id,
            public_id="pos-public-id",
            symbol="NVDA",
            exchange="NASDAQ",
            direction=PositionDirection.LONG,
            status=PositionStatus.CLOSED,
            total_quantity=1,
            opened_at=datetime.now(timezone.utc),
            closed_at=datetime.now(timezone.utc),
        )
        self.db.add(self.position)
        self.db.commit()
        self.db.refresh(self.position)

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

    def test_accounts_list_and_get_include_and_accept_public_id(self):
        list_response = self.client.get("/api/accounts")
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        self.assertEqual(payload[0]["public_id"], "acct-public-id")

        get_response = self.client.get("/api/accounts/acct-public-id")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["id"], self.account.id)
        self.assertEqual(get_response.json()["public_id"], "acct-public-id")

    def test_positions_list_and_get_include_and_accept_public_id(self):
        list_response = self.client.get("/api/positions")
        self.assertEqual(list_response.status_code, 200)
        payload = list_response.json()
        self.assertEqual(payload[0]["public_id"], "pos-public-id")

        get_response = self.client.get("/api/positions/pos-public-id")
        self.assertEqual(get_response.status_code, 200)
        self.assertEqual(get_response.json()["id"], self.position.id)
        self.assertEqual(get_response.json()["public_id"], "pos-public-id")


if __name__ == "__main__":
    unittest.main()
