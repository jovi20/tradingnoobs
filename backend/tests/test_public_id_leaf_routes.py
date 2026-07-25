import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base, get_db
from main import app
from models import Position, PositionDirection, PositionStatus, TradeBatch, TradingAccount, Transaction, TransactionType, User
from services.auth_service import get_current_user


class PublicIdLeafRouteTests(unittest.TestCase):
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
            email="leaf@example.com",
            email_normalized="leaf@example.com",
            hashed_password="hashed",
            public_id="user-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
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
            cash_balance=1000,
            is_active=True,
        )
        self.db.add(self.account)
        self.db.commit()
        self.db.refresh(self.account)

        opened_at = datetime.now(timezone.utc)
        self.position = Position(
            user_id=self.user.id,
            account_id=self.account.id,
            public_id="pos-public-id",
            symbol="NVDA",
            exchange="NASDAQ",
            direction=PositionDirection.LONG,
            status=PositionStatus.OPEN,
            total_quantity=1,
            average_entry_price=100,
            opened_at=opened_at,
        )
        self.db.add(self.position)
        self.db.commit()
        self.db.refresh(self.position)

        self.batch = TradeBatch(
            public_id="batch-public-id",
            position_id=self.position.id,
            type="EXIT",
            price=110,
            quantity=1,
            time=opened_at + timedelta(minutes=1),
            reason="Partial exit",
            pnl=10,
        )
        self.db.add(self.batch)

        self.second_batch = TradeBatch(
            public_id="batch-public-id-2",
            position_id=self.position.id,
            type="ENTRY",
            price=101,
            quantity=1,
            time=opened_at,
            reason="Second entry",
        )
        self.db.add(self.second_batch)

        self.transaction = Transaction(
            public_id="txn-public-id",
            account_id=self.account.id,
            type=TransactionType.DEPOSIT,
            amount=100,
            currency="USD",
            date=datetime.now(timezone.utc),
            description="Seed cash",
        )
        self.db.add(self.transaction)
        self.db.commit()
        self.db.refresh(self.batch)
        self.db.refresh(self.second_batch)
        self.db.refresh(self.transaction)

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

    def test_transaction_create_and_delete_support_public_id(self):
        create_response = self.client.post(
            f"/api/accounts/{self.account.public_id}/transactions",
            json={
                "type": "DEPOSIT",
                "amount": 50,
                "currency": "USD",
                "date": datetime.now(timezone.utc).isoformat(),
                "description": "Top up",
            },
        )
        self.assertEqual(create_response.status_code, 200)
        payload = create_response.json()
        self.assertIn("public_id", payload)

        delete_response = self.client.delete(f"/api/transactions/{self.transaction.public_id}")
        self.assertEqual(delete_response.status_code, 409)
        self.assertEqual(
            delete_response.json()["detail"]["code"],
            "POSTING_FACT_CONFLICT",
        )

    def test_public_trade_batch_mutations_fail_closed_for_public_id(self):
        update_response = self.client.patch(
            f"/api/positions/batches/{self.batch.public_id}",
            json={
                "reason": "Updated reason",
            },
        )
        self.assertEqual(update_response.status_code, 409)
        self.assertIn("disabled on public product routes", update_response.json()["detail"])

        delete_response = self.client.delete(f"/api/positions/batches/{self.batch.public_id}")
        self.assertEqual(delete_response.status_code, 409)
        self.assertIn("disabled on public product routes", delete_response.json()["detail"])

        self.db.expire_all()
        unchanged = self.db.query(TradeBatch).filter(
            TradeBatch.public_id == self.batch.public_id
        ).one()
        self.assertEqual(unchanged.reason, "Partial exit")


if __name__ == "__main__":
    unittest.main()
