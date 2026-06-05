import unittest

from services.chart_schema_service import (
    build_analysis_chart_schema,
    build_dashboard_allocation_chart_payload,
)


class ChartSchemaServiceTests(unittest.TestCase):
    def test_dashboard_allocation_payload_exposes_schema_data_and_trust(self):
        payload = build_dashboard_allocation_chart_payload(
            dimension="CORE_TYPE",
            data_path="core_type_allocation",
            title="Asset type allocation",
            allocation=[
                {"name": "EQUITY", "value": 750.0, "percent": 75.0},
                {"name": "CASH", "value": 250.0, "percent": 25.0},
            ],
        )

        self.assertEqual(payload["chart_schema"]["schema_version"], "chart.v1")
        self.assertEqual(payload["chart_schema"]["chart_type"], "bar")
        self.assertEqual(payload["chart_schema"]["data_path"], "core_type_allocation")
        self.assertEqual(payload["chart_schema"]["dimensions"], [{"field": "name", "label": "Asset type allocation"}])
        self.assertEqual(payload["chart_schema"]["series"][0], {"field": "value", "label": "Value"})
        self.assertEqual(payload["data"][0]["name"], "EQUITY")
        self.assertFalse(payload["empty_state"]["is_empty"])
        self.assertEqual(payload["trust_meta"]["source"], "DASHBOARD_DERIVED_READ_MODEL")
        self.assertIn("dashboard:allocation:CORE_TYPE", payload["trust_meta"]["source_refs"])

    def test_dashboard_allocation_payload_makes_empty_state_explicit(self):
        payload = build_dashboard_allocation_chart_payload(
            dimension="MARKET",
            data_path="market_allocation",
            title="Market allocation",
            allocation=[],
        )

        self.assertEqual(payload["data"], [])
        self.assertTrue(payload["empty_state"]["is_empty"])
        self.assertEqual(payload["empty_state"]["reason"], "NO_ALLOCATION_DATA")

    def test_analysis_chart_schema_reuses_chart_v1_contract(self):
        schema = build_analysis_chart_schema(
            analysis_type="strategy_health",
            raw_data={"stats": {"Momentum": {"avg_pnl": 42.0, "count": 3}}},
        )

        self.assertEqual(schema["schema_version"], "chart.v1")
        self.assertEqual(schema["chart_type"], "bar")
        self.assertEqual(schema["data_path"], "raw_data.stats")
        self.assertEqual(schema["dimensions"], [{"field": "name", "label": "Strategy"}])
        self.assertEqual(schema["series"], [{"field": "avg_pnl", "label": "Average PnL"}])


if __name__ == "__main__":
    unittest.main()
