import json
import unittest
from unittest.mock import patch

from main import app, create_app
from release_profile import (
    DeploymentCapabilityPolicy,
    RuntimeCapability,
)


class OpenAPIContractTests(unittest.TestCase):
    def setUp(self):
        app.openapi_schema = None
        self.openapi = app.openapi()

    def test_core_product_paths_are_present(self):
        paths = self.openapi["paths"]

        for path in (
            "/api/trading-positions/{position_public_id}/lifecycle",
            "/api/trading-positions/{position_public_id}/events",
            "/api/trading-positions/{position_public_id}/events/{event_public_id}/narrative",
            "/api/timeline/home",
            "/api/positions",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)

    def test_core_read_model_response_schemas_are_present(self):
        schemas = self.openapi["components"]["schemas"]

        self.assertIn("JournalTimelineHomeResponse", schemas)
        self.assertIn("TradingPositionLifecycleResponse", schemas)

    def test_empty_ceiling_publishes_only_core_user_settings_fields(self):
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            DeploymentCapabilityPolicy(frozenset()),
        ):
            openapi = create_app().openapi()
            schemas = openapi["components"]["schemas"]

        self.assertEqual(
            set(schemas["UserSettingsUpdate"]["properties"]),
            {"theme", "up_color", "display_currency"},
        )
        self.assertEqual(
            set(schemas["UserSettingsResponse"]["properties"]),
            {"id", "user_id", "theme", "up_color", "display_currency"},
        )
        serialized = json.dumps(openapi, sort_keys=True)
        for field in (
            "ibkr_flex_query_id",
            "ibkr_flex_token",
            "binance_api_key",
            "binance_api_secret",
            "finnhub_api_key",
            "llm_api_url",
            "llm_api_key",
            "llm_model",
        ):
            self.assertNotIn(field, serialized)

    def test_empty_ceiling_publishes_journal_only_product_dtos(self):
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            DeploymentCapabilityPolicy(frozenset()),
        ):
            openapi = create_app().openapi()

        schemas = openapi["components"]["schemas"]
        self.assertEqual(
            set(schemas["DashboardStats"]["properties"]),
            {
                "journal_balance",
                "realized_pnl",
                "win_rate",
                "avg_pnl_ratio",
                "total_trades",
                "open_positions",
                "closed_trades",
                "account_balances",
            },
        )
        self.assertEqual(
            set(schemas["DashboardAccountBalance"]["properties"]),
            {"name", "broker", "journal_balance"},
        )
        self.assertIn(
            "journal_balance",
            schemas["TradingAccountResponse"]["properties"],
        )

        timeline_operation = openapi["paths"]["/api/timeline/home"]["get"]
        view_parameter = next(
            parameter
            for parameter in timeline_operation["parameters"]
            if parameter["name"] == "view"
        )
        self.assertEqual(
            view_parameter["schema"]["enum"],
            ["ALL", "TRADING", "REVIEW", "EXCEPTION"],
        )
        self.assertEqual(
            timeline_operation["responses"]["200"]["content"]["application/json"]["schema"],
            {"$ref": "#/components/schemas/JournalTimelineHomeResponse"},
        )
        self.assertNotIn("TimelineAiAnnotation", schemas)
        self.assertNotIn("TimelineViewEnum", schemas)
        self.assertNotIn("TimelineEventTypeEnum", schemas)
        self.assertNotIn("TradingPositionManualAdjustmentCreate", schemas)
        self.assertNotIn(
            "/api/trading-positions/{position_public_id}/adjustments",
            openapi["paths"],
        )

        serialized = json.dumps(openapi, sort_keys=True)
        for disabled_or_legacy_field in (
            "ai_annotation",
            "AI_INSIGHT",
            "current_price",
            "unrealized_pnl",
            "risk_level",
            "risk_summary",
            "sharpe_ratio",
            "max_drawdown",
            "top_movers",
            "bottom_movers",
            "asset_allocation",
            "market_allocation",
            "total_assets",
            "cash_balance",
            "current_balance",
            "market_value",
            "total_equity",
            "net_equity_change",
        ):
            self.assertNotIn(disabled_or_legacy_field, serialized)

    def test_allowlist_alone_does_not_publish_optional_routes_or_dtos(self):
        allowed = frozenset(
            {
                RuntimeCapability.AI_INSIGHTS,
                RuntimeCapability.MARKET,
                RuntimeCapability.RISK_CARDS,
            }
        )
        with patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            DeploymentCapabilityPolicy(allowed),
        ):
            openapi = create_app().openapi()

        schemas = openapi["components"]["schemas"]
        for schema_name in (
            "TimelineAiAnnotation",
            "PositionMarketAnalysisResponse",
            "RiskSummaryResponse",
            "MarketQuoteResponse",
        ):
            self.assertNotIn(schema_name, schemas)
        for path in (
            "/api/risk/summary",
            "/api/market/quote/{symbol}",
            "/api/positions/{position_id}/analyze",
            "/api/insights/{report_id}/export/pdf",
            "/api/insights/analyze/history",
        ):
            self.assertNotIn(path, openapi["paths"])
        timeline_schema = openapi["paths"]["/api/timeline/home"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertEqual(
            timeline_schema,
            {"$ref": "#/components/schemas/JournalTimelineHomeResponse"},
        )

    def test_allowlisted_optional_settings_remain_hidden_from_beta_openapi(self):
        core_update = {"theme", "up_color", "display_currency"}
        core_response = {
            "id",
            "user_id",
            "theme",
            "up_color",
            "display_currency",
        }
        for capability in (
            RuntimeCapability.BROKER_SYNC,
            RuntimeCapability.MARKET,
            RuntimeCapability.AI_INSIGHTS,
        ):
            with self.subTest(capability=capability.value):
                with patch(
                    "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
                    DeploymentCapabilityPolicy(frozenset({capability})),
                ):
                    schemas = create_app().openapi()["components"]["schemas"]

                self.assertEqual(
                    set(schemas["UserSettingsUpdate"]["properties"]),
                    core_update,
                )
                self.assertEqual(
                    set(schemas["UserSettingsResponse"]["properties"]),
                    core_response,
                )

    def test_legacy_fallback_headers_are_documented_on_protected_routes(self):
        protected_routes = (
            ("/api/positions/{position_id}/batches", "post", "legacy-batch-write"),
            ("/api/positions/{position_id}", "patch", "legacy-review-write"),
            ("/api/positions/{position_id}", "delete", "legacy-position-delete"),
        )

        for path, method, allowed_value in protected_routes:
            with self.subTest(path=path, method=method):
                operation = self.openapi["paths"][path][method]
                migration_header = next(
                    (
                        parameter
                        for parameter in operation.get("parameters", [])
                        if parameter.get("name") == "X-Migration-Fallback"
                        and parameter.get("in") == "header"
                    ),
                    None,
                )

                self.assertIsNotNone(migration_header)
                self.assertIn(allowed_value, migration_header.get("description", ""))


if __name__ == "__main__":
    unittest.main()
