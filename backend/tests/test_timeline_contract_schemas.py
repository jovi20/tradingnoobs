import unittest

from schemas import (
    TrustMeta,
    TimelineHomeResponse,
)


class TimelineContractSchemaTests(unittest.TestCase):
    def test_trust_meta_accepts_frozen_enums(self):
        meta = TrustMeta(
            as_of="2026-04-13T09:30:00Z",
            generated_at="2026-04-13T09:30:04Z",
            freshness="FRESH",
            source="DERIVED",
            maturity="STABLE",
            value_status="FINAL",
        )

        self.assertEqual(meta.as_of, "2026-04-13T09:30:00Z")
        self.assertEqual(meta.freshness.value, "FRESH")
        self.assertEqual(meta.source.value, "DERIVED")
        self.assertEqual(meta.maturity.value, "STABLE")
        self.assertEqual(meta.value_status.value, "FINAL")

    def test_timeline_home_response_wraps_page_state_and_meta(self):
        response = TimelineHomeResponse.model_validate(
            {
                "data": {
                    "page_state": "ZERO",
                    "summary_bar": {
                        "period_label": "THIS_WEEK",
                        "trade_count": 0,
                        "review_completion_rate": None,
                        "net_equity_change": None,
                        "priority_alert_count": 0,
                    },
                    "review_inbox": {
                        "counts": {
                            "total": 0,
                            "high_priority": 0,
                        },
                        "items": [],
                    },
                    "timeline": {
                        "active_view": "ALL",
                        "groups": [],
                    },
                    "context_rail": {
                        "quick_filters": [],
                    },
                },
                "meta": {
                    "as_of": "2026-04-13T09:30:00Z",
                    "freshness": "FRESH",
                    "source": "DERIVED",
                    "maturity": "INSUFFICIENT_SAMPLE",
                    "value_status": "FINAL",
                },
            }
        )

        self.assertEqual(response.data.page_state.value, "ZERO")
        self.assertEqual(response.meta.maturity.value, "INSUFFICIENT_SAMPLE")
        self.assertEqual(response.data.timeline.active_view.value, "ALL")


if __name__ == "__main__":
    unittest.main()
