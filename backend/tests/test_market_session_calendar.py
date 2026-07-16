import unittest
from datetime import date

from services.market_session_calendar import expected_daily_sessions


class MarketSessionCalendarTests(unittest.TestCase):
    def test_us_sessions_exclude_weekends_and_observed_holiday(self):
        sessions = expected_daily_sessions(
            "US",
            date(2026, 7, 2),
            date(2026, 7, 6),
        )

        self.assertEqual(sessions, {date(2026, 7, 2), date(2026, 7, 6)})

    def test_crypto_sessions_include_every_calendar_day(self):
        sessions = expected_daily_sessions(
            "CRYPTO",
            date(2026, 7, 3),
            date(2026, 7, 5),
        )

        self.assertEqual(
            sessions,
            {date(2026, 7, 3), date(2026, 7, 4), date(2026, 7, 5)},
        )

    def test_markets_without_safe_local_calendar_are_live_first(self):
        self.assertIsNone(
            expected_daily_sessions("A_SHARE", date(2026, 1, 1), date(2026, 1, 5))
        )


if __name__ == "__main__":
    unittest.main()
