import unittest

from main import app


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
            "/api/risk/summary",
            "/api/insights/{report_id}/export/pdf",
            "/api/insights/analyze/history",
        ):
            with self.subTest(path=path):
                self.assertIn(path, paths)

    def test_core_read_model_response_schemas_are_present(self):
        schemas = self.openapi["components"]["schemas"]

        self.assertIn("TimelineHomeResponse", schemas)
        self.assertIn("TradingPositionLifecycleResponse", schemas)
        self.assertIn("RiskSummaryResponse", schemas)

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
