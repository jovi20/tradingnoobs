import unittest

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from observability import add_error_handlers, add_observability_middleware, make_error_code


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


if __name__ == "__main__":
    unittest.main()
