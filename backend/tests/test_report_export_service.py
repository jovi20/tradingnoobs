import unittest
from datetime import date, datetime, timezone

from models import WeeklyReport
from services.report_export_service import build_report_filename, build_weekly_report_pdf


class WeeklyReportPdfExportServiceTests(unittest.TestCase):
    def make_report(self, **overrides):
        values = {
            "id": 42,
            "user_id": 7,
            "week_start": date(2026, 6, 1),
            "week_end": date(2026, 6, 7),
            "trades_summary": "Closed two trades and kept risk within the plan.",
            "munger_evaluation": "Avoid the obvious stupidity of oversizing.",
            "suggestions": "Keep position sizing consistent next week.",
            "created_at": datetime(2026, 6, 8, 9, 30, tzinfo=timezone.utc),
        }
        values.update(overrides)
        return WeeklyReport(**values)

    def test_render_weekly_report_pdf_starts_with_pdf_header(self):
        pdf_bytes = build_weekly_report_pdf(self.make_report())

        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_render_weekly_report_pdf_includes_report_period_metadata(self):
        report = self.make_report()

        pdf_bytes = build_weekly_report_pdf(report)
        filename = build_report_filename(report)

        self.assertEqual(filename, "tradingnoobs-weekly-report-2026-06-01.pdf")
        self.assertIn(b"2026-06-01", pdf_bytes)
        self.assertIn(b"2026-06-07", pdf_bytes)
        self.assertIn(b"weekly_reports:42", pdf_bytes)
        self.assertIn(b"Closed two trades", pdf_bytes)

    def test_render_weekly_report_pdf_rejects_report_without_owner(self):
        report = self.make_report(user_id=None)

        with self.assertRaisesRegex(ValueError, "owner"):
            build_weekly_report_pdf(report)


if __name__ == "__main__":
    unittest.main()
