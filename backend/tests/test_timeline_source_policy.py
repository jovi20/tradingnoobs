import unittest

from services.timeline_source_policy import get_timeline_source_mode


class TimelineSourcePolicyTests(unittest.TestCase):
    def test_defaults_to_snapshot_first_when_no_legacy_escape_flag_exists(self):
        self.assertEqual(get_timeline_source_mode(legacy_mixed_feed_enabled=False), "SNAPSHOT_ONLY")

    def test_legacy_escape_flag_restores_mixed_feed(self):
        self.assertEqual(get_timeline_source_mode(legacy_mixed_feed_enabled=True), "LEGACY_MIXED")
