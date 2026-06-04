import time
import uuid
from typing import Any

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request


def make_error_code(namespace: str, code: str) -> str:
    return f"{namespace}.{code}"


def build_log_context(
    *,
    request_id: str,
    actor_type: str | None,
    user_public_id: str | None,
    route: str,
    method: str,
    status_code: int,
    latency_ms: float,
    error_code: str | None,
    **extra: Any,
) -> dict[str, Any]:
    context = {
        "request_id": request_id,
        "actor_type": actor_type,
        "user_public_id": user_public_id,
        "route": route,
        "method": method,
        "status_code": status_code,
        "latency_ms": latency_ms,
        "error_code": error_code,
    }
    context.update(extra)
    return context


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        started_at = time.perf_counter()
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{(time.perf_counter() - started_at) * 1000:.2f}"
        return response
