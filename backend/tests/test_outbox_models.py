import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import OutboxEvent, OutboxEventStatus, User


class OutboxModelTests(unittest.TestCase):
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

    def tearDown(self):
        self.db.close()
        self.engine.dispose()
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_outbox_event_persists_dispatch_metadata_and_payload(self):
        user = User(
            email="outbox@example.com",
            email_normalized="outbox@example.com",
            hashed_password="hashed",
            public_id="user-outbox-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)

        event = OutboxEvent(
            user_id=user.id,
            aggregate_type="TradingPosition",
            aggregate_public_id="tp-1",
            event_type="truth.position_event.created",
            queue_name="derived",
            dedupe_key="truth.position_event.created:evt-1",
            payload={"position_event_public_id": "evt-1"},
            available_at=datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc),
        )
        self.db.add(event)
        self.db.commit()
        self.db.refresh(event)

        self.assertEqual(event.status, OutboxEventStatus.PENDING)
        self.assertEqual(event.attempt_count, 0)
        self.assertEqual(event.queue_name, "derived")
        self.assertEqual(event.payload["position_event_public_id"], "evt-1")
        self.assertEqual(event.user.email, "outbox@example.com")


if __name__ == "__main__":
    unittest.main()
