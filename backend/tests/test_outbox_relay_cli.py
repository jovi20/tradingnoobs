import unittest
from unittest.mock import Mock, patch

from outbox_relay_cli import relay_once


class OutboxRelayCliTests(unittest.TestCase):
    def test_relay_once_commits_and_closes_session(self):
        db = Mock()
        session_factory = Mock(return_value=db)

        with patch("outbox_relay_cli.relay_pending_outbox_events", return_value=3) as relay:
            relayed = relay_once(session_factory=session_factory, limit=25)

        self.assertEqual(relayed, 3)
        relay.assert_called_once_with(db, limit=25)
        db.commit.assert_called_once()
        db.rollback.assert_not_called()
        db.close.assert_called_once()

    def test_relay_once_rolls_back_and_closes_session_on_failure(self):
        db = Mock()
        session_factory = Mock(return_value=db)

        with patch("outbox_relay_cli.relay_pending_outbox_events", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                relay_once(session_factory=session_factory, limit=10)

        db.commit.assert_not_called()
        db.rollback.assert_called_once()
        db.close.assert_called_once()


if __name__ == "__main__":
    unittest.main()
