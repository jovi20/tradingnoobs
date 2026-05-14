import os
import tempfile
import unittest
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base
from models import IdempotencyKey
from services.idempotency_service import begin_idempotent_request, complete_idempotent_request


class IdempotencyServiceTests(unittest.TestCase):
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

    def test_begin_idempotent_request_creates_record_and_reuses_same_request(self):
        first = begin_idempotent_request(
            self.db,
            scope="manual_sync",
            key="user-1:broker:ibkr",
            request_payload={"broker": "ibkr", "account": "acct-1"},
            now=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
        )
        second = begin_idempotent_request(
            self.db,
            scope="manual_sync",
            key="user-1:broker:ibkr",
            request_payload={"account": "acct-1", "broker": "ibkr"},
            now=datetime(2026, 5, 3, 10, 1, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertTrue(first.created)
        self.assertFalse(second.created)
        self.assertEqual(first.record.id, second.record.id)
        self.assertEqual(self.db.query(IdempotencyKey).count(), 1)

    def test_begin_idempotent_request_rejects_same_key_with_different_payload(self):
        begin_idempotent_request(
            self.db,
            scope="ai_trigger",
            key="user-1:position-1:summary",
            request_payload={"prompt_version": "v1"},
        )
        self.db.commit()

        with self.assertRaises(ValueError):
            begin_idempotent_request(
                self.db,
                scope="ai_trigger",
                key="user-1:position-1:summary",
                request_payload={"prompt_version": "v2"},
            )

    def test_begin_idempotent_request_restarts_expired_key(self):
        first = begin_idempotent_request(
            self.db,
            scope="manual_sync",
            key="user-1:broker:expired",
            request_payload={"broker": "ibkr", "account": "old"},
            now=datetime(2026, 5, 3, 10, 0, tzinfo=timezone.utc),
            ttl_seconds=60,
        )
        complete_idempotent_request(
            self.db,
            record=first.record,
            response_json={"status": "old"},
            now=datetime(2026, 5, 3, 10, 1, tzinfo=timezone.utc),
        )
        self.db.commit()

        restarted = begin_idempotent_request(
            self.db,
            scope="manual_sync",
            key="user-1:broker:expired",
            request_payload={"broker": "ibkr", "account": "new"},
            now=datetime(2026, 5, 3, 10, 2, tzinfo=timezone.utc),
            ttl_seconds=120,
        )
        self.db.commit()

        self.assertTrue(restarted.created)
        self.assertEqual(restarted.record.id, first.record.id)
        self.assertEqual(restarted.record.status, "IN_PROGRESS")
        self.assertIsNone(restarted.record.response_json)
        self.assertEqual(self.db.query(IdempotencyKey).count(), 1)

    def test_complete_idempotent_request_stores_replayable_response(self):
        started = begin_idempotent_request(
            self.db,
            scope="import",
            key="user-1:csv:sha256-file",
            request_payload={"filename": "fills.csv"},
        )
        self.db.commit()

        completed = complete_idempotent_request(
            self.db,
            record=started.record,
            response_json={"imported_rows": 12},
            now=datetime(2026, 5, 3, 10, 2, tzinfo=timezone.utc),
        )
        self.db.commit()

        self.assertEqual(completed.status, "COMPLETED")
        self.assertEqual(completed.response_json, {"imported_rows": 12})
