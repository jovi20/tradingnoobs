import unittest
import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient
from pydantic import BaseModel

from observability import (
    add_error_handlers,
    add_observability_middleware,
    disable_unsafe_server_access_log,
    get_structured_logger,
    log_event,
    make_error_code,
)


class ValidationPayload(BaseModel):
    secret: str


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
BUSINESS_LOGGING_FILES = [
    "routers/admin.py",
    "routers/dashboard.py",
    "routers/positions.py",
    "services/import_service.py",
    "services/llm_service.py",
    "services/market_data_service.py",
]


def build_test_client() -> TestClient:
    app = FastAPI()
    add_observability_middleware(app)
    add_error_handlers(app)

    @app.get("/ping")
    async def ping():
        return {"status": "ok"}

    @app.get("/api/trading-positions/example")
    async def missing_trading_position():
        raise HTTPException(status_code=404, detail="Trading position not found")

    @app.get("/api/validation/{item_id}")
    async def validation_target(item_id: int):
        return {"item_id": item_id}

    @app.post("/api/validation")
    async def validation_body_target(payload: ValidationPayload):
        return payload

    return TestClient(app)


class ObservabilityTests(unittest.TestCase):
    def test_incoming_request_id_is_reused_on_response(self):
        client = build_test_client()

        response = client.get("/ping", headers={"X-Request-ID": "req-user-provided"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], "req-user-provided")

    def test_missing_request_id_creates_response_request_id(self):
        client = build_test_client()

        response = client.get("/ping")

        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Request-ID", response.headers)
        self.assertGreater(len(response.headers["X-Request-ID"]), 0)

    def test_response_includes_response_time_ms(self):
        client = build_test_client()

        response = client.get("/ping")

        self.assertEqual(response.status_code, 200)
        self.assertIn("X-Response-Time-Ms", response.headers)
        self.assertGreaterEqual(float(response.headers["X-Response-Time-Ms"]), 0)

    def test_make_error_code_normalizes_namespace_and_error(self):
        self.assertEqual(make_error_code("timeline", "missing_position"), "TIMELINE_MISSING_POSITION")

    def test_http_exception_response_includes_error_contract_and_request_id(self):
        client = build_test_client()

        response = client.get(
            "/api/trading-positions/example",
            headers={"X-Request-ID": "req-error-contract"},
        )

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.headers["X-Request-ID"], "req-error-contract")
        payload = response.json()
        self.assertEqual(payload["detail"], "Trading position not found")
        self.assertEqual(payload["error"]["code"], "TRADING_POSITIONS_NOT_FOUND")
        self.assertEqual(payload["error"]["message"], "Trading position not found")
        self.assertEqual(payload["error"]["request_id"], "req-error-contract")
        self.assertEqual(payload["error"]["status_code"], 404)

    def test_validation_error_response_uses_stable_error_code(self):
        client = build_test_client()

        response = client.get(
            "/api/validation/not-an-int",
            headers={"X-Request-ID": "req-validation-contract"},
        )

        self.assertEqual(response.status_code, 422)
        payload = response.json()
        self.assertEqual(payload["error"]["code"], "VALIDATION_REQUEST_INVALID")
        self.assertEqual(payload["error"]["request_id"], "req-validation-contract")
        self.assertEqual(payload["error"]["status_code"], 422)

    def test_validation_error_never_echoes_invalid_input(self):
        client = build_test_client()
        secret = "short-secret-must-not-echo"

        response = client.post(
            "/api/validation",
            json={"secret": {"nested": secret}},
        )

        self.assertEqual(response.status_code, 422)
        self.assertNotIn(secret, response.text)
        error = response.json()["detail"][0]
        self.assertNotIn("input", error)
        self.assertNotIn("ctx", error)

    def test_uvicorn_query_string_access_logger_is_disabled(self):
        logger = logging.getLogger("uvicorn.access")
        logger.disabled = False

        disable_unsafe_server_access_log()

        self.assertTrue(logger.disabled)

    def test_documented_and_packaged_uvicorn_launches_disable_access_log(self):
        launch_files = (
            "backend/Dockerfile",
            "backend/README.md",
            "README.md",
            "docs/DEVELOPER_GUIDE.md",
            "start.sh",
        )
        for relative_path in launch_files:
            with self.subTest(file=relative_path):
                uvicorn_lines = [
                    line
                    for line in (REPO_ROOT / relative_path).read_text().splitlines()
                    if "uvicorn" in line and "uvicorn[" not in line
                ]
                self.assertTrue(uvicorn_lines)
                self.assertTrue(
                    all("--no-access-log" in line for line in uvicorn_lines),
                    uvicorn_lines,
                )

    def test_structured_logger_uses_project_namespace(self):
        logger = get_structured_logger("market-data")

        self.assertEqual(logger.name, "tradingnoobs.market_data")

    def test_log_event_emits_structured_fields(self):
        logger = get_structured_logger("market_data")

        with self.assertLogs(logger.name, level="WARNING") as captured:
            log_event(logger, "warning", "quote_failed", symbol="MSFT", provider="yahoo")

        self.assertEqual(len(captured.output), 1)
        self.assertIn("event=quote_failed", captured.output[0])
        self.assertIn("provider=yahoo", captured.output[0])
        self.assertIn("symbol=MSFT", captured.output[0])

    def test_business_paths_do_not_use_print_for_logging(self):
        for relative_path in BUSINESS_LOGGING_FILES:
            with self.subTest(file=relative_path):
                source = (BACKEND_ROOT / relative_path).read_text()
                self.assertNotIn("print(", source)


if __name__ == "__main__":
    unittest.main()
