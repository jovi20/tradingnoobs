import re
import time
from uuid import uuid4

from fastapi import FastAPI, Request


REQUEST_ID_HEADER = "X-Request-ID"
RESPONSE_TIME_HEADER = "X-Response-Time-Ms"


def _normalize_error_part(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return normalized.upper()


def make_error_code(namespace: str, error: str) -> str:
    return f"{_normalize_error_part(namespace)}_{_normalize_error_part(error)}"


def get_or_create_request_id(request_id: str | None) -> str:
    if request_id and request_id.strip():
        return request_id.strip()
    return str(uuid4())


def add_observability_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        request_id = get_or_create_request_id(request.headers.get(REQUEST_ID_HEADER))
        started_at = time.perf_counter()

        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[RESPONSE_TIME_HEADER] = f"{elapsed_ms:.2f}"
        return response
