import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import DerivedTimelineSnapshot, User
from services.derived_timeline_read_service import list_recent_timeline_snapshots


class DerivedTimelineReadServiceTests(unittest.TestCase):
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

    def test_list_recent_timeline_snapshots_filters_user_and_orders_by_refresh_time(self):
        user = User(
            email="snapshot-reader@example.com",
            email_normalized="snapshot-reader@example.com",
            hashed_password="hashed",
            public_id="user-snapshot-reader-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        other_user = User(
            email="snapshot-reader-other@example.com",
            email_normalized="snapshot-reader-other@example.com",
            hashed_password="hashed",
            public_id="user-snapshot-reader-other-public-id",
            status="ACTIVE",
            is_active=True,
            role="user",
        )
        self.db.add_all([user, other_user])
        self.db.flush()
        self.db.add_all(
            [
                DerivedTimelineSnapshot(
                    user_id=user.id,
                    trading_position_public_id="tp-old",
                    source="truth.lifecycle.bridge",
                    snapshot_json={"position_title": "Old"},
                    refreshed_at=datetime(2026, 5, 3, 9, 0, tzinfo=timezone.utc),
                ),
                DerivedTimelineSnapshot(
                    user_id=user.id,
                    trading_position_public_id="tp-new",
                    source="truth.lifecycle.bridge",
                    snapshot_json={"position_title": "New"},
                    refreshed_at=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
                ),
                DerivedTimelineSnapshot(
                    user_id=other_user.id,
                    trading_position_public_id="tp-other",
                    source="truth.lifecycle.bridge",
                    snapshot_json={"position_title": "Other"},
                    refreshed_at=datetime(2026, 5, 3, 11, 0, tzinfo=timezone.utc),
                ),
            ]
        )
        self.db.commit()

        snapshots = list_recent_timeline_snapshots(self.db, user_id=user.id, limit=2)

        self.assertEqual([snapshot.trading_position_public_id for snapshot in snapshots], ["tp-new", "tp-old"])
