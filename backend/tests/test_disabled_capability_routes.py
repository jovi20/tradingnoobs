from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys
import unittest

from fastapi.testclient import TestClient

from main import create_app
from release_profile import ReleaseProfile


KNOWN_DISABLED_ROUTES = (
    ("GET", "/api/market/validate/AAPL", "MARKET"),
    ("GET", "/api/market/quote/AAPL", "MARKET"),
    ("GET", "/api/market/detect/AAPL", "MARKET"),
    ("GET", "/api/market/calendar", "MARKET"),
    ("POST", "/api/broker-sync/ibkr/test", "BROKER_SYNC"),
    ("POST", "/api/broker-sync/binance/test", "BROKER_SYNC"),
    ("POST", "/api/broker-sync/ibkr/sync", "BROKER_SYNC"),
    ("POST", "/api/broker-sync/binance/sync", "BROKER_SYNC"),
    ("GET", "/api/broker-sync/runs", "BROKER_SYNC"),
    ("GET", "/api/broker-sync/executions", "BROKER_SYNC"),
)


class DisabledCapabilityRouteContractTests(unittest.TestCase):
    def setUp(self):
        self.app = create_app(ReleaseProfile.JOURNAL_BASELINE)
        self.client = TestClient(self.app, raise_server_exceptions=False)

    def tearDown(self):
        self.client.close()

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
            "/api/market/quote",
            "/api/market/quote/AAPL/extra",
            "/api/broker-sync/not-a-real-route",
            "/api/broker-sync/runs/extra",
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
        ):
            with self.subTest(path=path):
                response = self.client.get(path, follow_redirects=False)
                self.assertEqual(response.status_code, 404)
                self.assert_not_feature_disabled(response)

    def test_wrong_methods_do_not_return_feature_disabled(self):
        requests = (
            ("POST", "/api/market/quote/AAPL"),
            ("GET", "/api/broker-sync/ibkr/test"),
            ("POST", "/api/broker-sync/runs"),
        )
        for method, path in requests:
            with self.subTest(method=method, path=path):
                response = self.client.request(method, path)
                self.assertIn(response.status_code, {404, 405})
                self.assert_not_feature_disabled(response)

    def test_disabled_routes_are_absent_from_openapi(self):
        paths = self.app.openapi()["paths"]
        self.assertFalse(any(path.startswith("/api/market") for path in paths))
        self.assertFalse(any(path.startswith("/api/broker-sync") for path in paths))

    def test_clean_baseline_process_does_not_import_real_optional_routers(self):
        backend_dir = Path(__file__).resolve().parents[1]
        script = "\n".join(
            (
                "import sys",
                "import main",
                "forbidden = [",
                "    'routers.market',",
                "    'routers.broker_sync',",
                "    'services.market_data_service',",
                "    'services.broker_sync.service',",
                "]",
                "loaded = [name for name in forbidden if name in sys.modules]",
                "assert main.app.state.release_profile == 'JOURNAL_BASELINE'",
                "assert loaded == [], loaded",
            )
        )
        env = os.environ.copy()
        env["RELEASE_PROFILE"] = "JOURNAL_BASELINE"
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
