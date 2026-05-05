import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import BusinessLock, BusinessLockStatus
from services.business_lock_service import acquire_business_lock, release_business_lock


class BusinessLockServiceTests(unittest.TestCase):
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

    def test_acquire_business_lock_blocks_active_lock_for_same_resource(self):
        now = datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc)

        acquired = acquire_business_lock(
            self.db,
            scope="asset_timeframe",
            resource_key="AAPL:1d",
            owner_id="job-a",
            ttl_seconds=300,
            now=now,
        )
        blocked = acquire_business_lock(
            self.db,
            scope="asset_timeframe",
            resource_key="AAPL:1d",
            owner_id="job-b",
            ttl_seconds=300,
            now=now,
        )
        self.db.commit()

        self.assertIsNotNone(acquired)
        self.assertIsNone(blocked)
        lock = self.db.query(BusinessLock).one()
        self.assertEqual(lock.status, BusinessLockStatus.ACTIVE)
        self.assertEqual(lock.owner_id, "job-a")
        self.assertEqual(lock.resource_key, "AAPL:1d")

    def test_acquire_business_lock_reuses_expired_lock_for_new_owner(self):
        stale_now = datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc)
        acquire_business_lock(
            self.db,
            scope="broker_connection",
            resource_key="ibkr:acct-1",
            owner_id="job-a",
            ttl_seconds=60,
            now=stale_now,
        )
        self.db.commit()

        acquired = acquire_business_lock(
            self.db,
            scope="broker_connection",
            resource_key="ibkr:acct-1",
            owner_id="job-b",
            ttl_seconds=120,
            now=datetime(2026, 5, 3, 10, 2, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertIsNotNone(acquired)
        self.assertEqual(acquired.status, BusinessLockStatus.ACTIVE)
        self.assertEqual(acquired.owner_id, "job-b")
        self.assertEqual(
            acquired.expires_at.replace(tzinfo=timezone.utc),
            datetime(2026, 5, 3, 10, 4, tzinfo=timezone.utc),
        )

    def test_release_business_lock_requires_owner(self):
        acquired = acquire_business_lock(
            self.db,
            scope="ai_scope",
            resource_key="user-1:position-1",
            owner_id="job-a",
            ttl_seconds=300,
            now=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        self.db.commit()

        with self.assertRaises(ValueError):
            release_business_lock(
                self.db,
                business_lock=acquired,
                owner_id="job-b",
                now=datetime(2026, 5, 3, 10, 1, tzinfo=timezone.utc),
            )

        released = release_business_lock(
            self.db,
            business_lock=acquired,
            owner_id="job-a",
            now=datetime(2026, 5, 3, 10, 1, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(released.status, BusinessLockStatus.RELEASED)
        self.assertIsNotNone(released.released_at)
