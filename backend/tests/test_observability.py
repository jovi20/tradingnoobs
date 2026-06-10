import unittest

from fastapi import FastAPI
from fastapi.testclient import TestClient

from observability import add_observability_middleware, make_error_code


def build_test_client() -> TestClient:
    app = FastAPI()
    add_observability_middleware(app)

    @app.get("/ping")
    async def ping():
        return {"status": "ok"}

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


if __name__ == "__main__":
    unittest.main()
