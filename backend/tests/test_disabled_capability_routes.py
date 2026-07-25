from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import create_app
from release_profile import DeploymentCapabilityPolicy, ReleaseProfile


KNOWN_DISABLED_ROUTES = (
    ("POST", "/api/admin/test-llm", "AI_INSIGHTS"),
    ("GET", "/api/market/validate/AAPL", "MARKET"),
    ("GET", "/api/market/quote/AAPL", "MARKET"),
    ("GET", "/api/market/detect/AAPL", "MARKET"),
    ("GET", "/api/market/calendar", "MARKET"),
    ("POST", "/api/positions/position-public-id/analyze", "MARKET"),
    ("POST", "/api/broker-sync/ibkr/test", "BROKER_SYNC"),
    ("POST", "/api/broker-sync/binance/test", "BROKER_SYNC"),
    ("POST", "/api/broker-sync/ibkr/sync", "BROKER_SYNC"),
    ("POST", "/api/broker-sync/binance/sync", "BROKER_SYNC"),
    ("GET", "/api/broker-sync/runs", "BROKER_SYNC"),
    ("GET", "/api/broker-sync/executions", "BROKER_SYNC"),
    ("GET", "/api/insights", "AI_INSIGHTS"),
    ("GET", "/api/insights/123", "AI_INSIGHTS"),
    ("POST", "/api/insights/generate", "AI_INSIGHTS"),
    ("POST", "/api/insights/generate-current-week", "AI_INSIGHTS"),
    ("DELETE", "/api/insights/123", "AI_INSIGHTS"),
    ("GET", "/api/insights/summary/today", "AI_INSIGHTS"),
    ("POST", "/api/insights/summary/generate", "AI_INSIGHTS"),
    ("POST", "/api/insights/analyze", "AI_INSIGHTS"),
    ("GET", "/api/insights/analyze/history", "AI_INSIGHTS"),
    ("GET", "/api/insights/analyze/latest/emotion_pnl", "AI_INSIGHTS"),
    ("GET", "/api/v1/insights/runs", "AI_INSIGHTS"),
    ("GET", "/api/v1/insights/runs/run-public-id", "AI_INSIGHTS"),
    ("GET", "/api/v1/insights/artifacts/artifact-public-id", "AI_INSIGHTS"),
    ("GET", "/api/insights/123/export/pdf", "PDF_EXPORT"),
    ("GET", "/api/risk/summary", "RISK_CARDS"),
)


class DisabledCapabilityRouteContractTests(unittest.TestCase):
    def setUp(self):
        self.ceiling_patch = patch(
            "release_profile.STATIC_DEPLOYMENT_CAPABILITY_POLICY",
            DeploymentCapabilityPolicy(frozenset()),
        )
        self.ceiling_patch.start()
        self.app = create_app(ReleaseProfile.JOURNAL_BASELINE)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()
        self.ceiling_patch.stop()

    def assert_not_feature_disabled(self, response) -> None:
        self.assertNotEqual(
            response.json().get("error", {}).get("code"),
            "FEATURE_DISABLED",
        )

    def test_every_known_optional_route_returns_feature_disabled(self):
        for method, path, capability in KNOWN_DISABLED_ROUTES:
            with self.subTest(method=method, path=path):
                response = self.client.request(method, path)
                self.assertEqual(response.status_code, 404)
                payload = response.json()
                self.assertEqual(payload["error"]["code"], "FEATURE_DISABLED")
                self.assertEqual(payload["detail"]["capability"], capability)

    def test_unknown_paths_under_disabled_prefixes_remain_normal_404(self):
        paths = (
            "/api/market/not-a-real-route",
            "/api/admin/test-llm/extra",
            "/api/market/quote",
            "/api/market/quote/AAPL/extra",
            "/api/positions/position-public-id/analyze/extra",
            "/api/broker-sync/not-a-real-route",
            "/api/broker-sync/runs/extra",
            "/api/insights/not-a-report",
            "/api/insights/analyze/not-a-real-route",
            "/api/v1/insights/runs/run/extra",
            "/api/v1/insights/artifacts/artifact/extra",
            "/api/risk/not-a-real-route",
        )
        for path in paths:
            with self.subTest(path=path):
                response = self.client.get(path)
                self.assertEqual(response.status_code, 404)
                self.assert_not_feature_disabled(response)

    def test_disabled_prefix_roots_remain_normal_404(self):
        for path in (
            "/api/market",
            "/api/market/",
            "/api/broker-sync",
            "/api/broker-sync/",
            "/api/risk",
            "/api/risk/",
            "/api/v1/insights/artifacts",
            "/api/v1/insights/artifacts/",
        ):
            with self.subTest(path=path):
                response = self.client.get(path, follow_redirects=False)
                self.assertEqual(response.status_code, 404)
                self.assert_not_feature_disabled(response)

    def test_wrong_methods_do_not_return_feature_disabled(self):
        requests = (
            ("POST", "/api/market/quote/AAPL"),
            ("GET", "/api/admin/test-llm"),
            ("GET", "/api/positions/position-public-id/analyze"),
            ("GET", "/api/broker-sync/ibkr/test"),
            ("POST", "/api/broker-sync/runs"),
            ("PUT", "/api/insights/analyze"),
            ("POST", "/api/insights/123/export/pdf"),
            ("POST", "/api/risk/summary"),
            ("POST", "/api/v1/insights/runs"),
        )
        for method, path in requests:
            with self.subTest(method=method, path=path):
                response = self.client.request(method, path)
                self.assertEqual(response.status_code, 405)
                self.assert_not_feature_disabled(response)

    def test_disabled_routes_are_absent_from_openapi(self):
        paths = self.app.openapi()["paths"]
        self.assertFalse(any(path.startswith("/api/market") for path in paths))
        self.assertFalse(any(path.startswith("/api/broker-sync") for path in paths))
        self.assertFalse(any(path.startswith("/api/insights") for path in paths))
        self.assertFalse(any(path.startswith("/api/v1/insights") for path in paths))
        self.assertFalse(any(path.startswith("/api/risk") for path in paths))
        self.assertNotIn("/api/admin/test-llm", paths)
        self.assertIn("/api/auth/register", paths)

    def test_clean_baseline_process_does_not_import_real_optional_routers(self):
        backend_dir = Path(__file__).resolve().parents[1]
        script = "\n".join(
            (
                "import sys",
                "import main",
                "forbidden = [",
                "    'routers.market',",
                "    'routers.admin_ai',",
                "    'routers.position_market_analysis',",
                "    'routers.broker_sync',",
                "    'routers.insights',",
                "    'routers.insight_artifacts',",
                "    'routers.pdf_export',",
                "    'routers.risk',",
                "    'services.market_data_service',",
                "    'services.broker_sync.service',",
                "    'services.insight_artifact_service',",
                "    'services.llm_service',",
                "    'services.report_export_service',",
                "]",
                "loaded = [name for name in forbidden if name in sys.modules]",
                "assert main.app.state.release_profile == 'DEVELOPMENT_FULL'",
                "assert loaded == [], loaded",
            )
        )
        env = os.environ.copy()
        env["RELEASE_PROFILE"] = "DEVELOPMENT_FULL"
        env["DEPLOYMENT_CAPABILITY_ALLOWLIST"] = ""
        env["PYTHONPATH"] = str(backend_dir)
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)

    def test_pdf_router_does_not_import_risk_service(self):
        backend_dir = Path(__file__).resolve().parents[1]
        script = "\n".join(
            (
                "import sys",
                "import routers.pdf_export",
                "assert 'services.risk_alert_service' not in sys.modules",
            )
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = str(backend_dir)
        completed = subprocess.run(
            [sys.executable, "-c", script],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr or completed.stdout)


if __name__ == "__main__":
    unittest.main()
