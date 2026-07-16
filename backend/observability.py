import logging
import re
import time
from http import HTTPStatus
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


REQUEST_ID_HEADER = "X-Request-ID"
RESPONSE_TIME_HEADER = "X-Response-Time-Ms"
LOGGER_PREFIX = "tradingnoobs"


def disable_unsafe_server_access_log() -> None:
    """Disable Uvicorn's query-string-bearing default access log."""
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.disabled = True


# Uvicorn configures logging before importing `main:app`, so this also covers
# CLI launches that omit the defense-in-depth `--no-access-log` option.
disable_unsafe_server_access_log()


def _normalize_error_part(value: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return normalized.upper()


def make_error_code(namespace: str, error: str) -> str:
    return f"{_normalize_error_part(namespace)}_{_normalize_error_part(error)}"


def _normalize_logger_namespace(namespace: str) -> str:
    return re.sub(r"[^A-Za-z0-9]+", "_", namespace).strip("_").lower()


def get_structured_logger(namespace: str) -> logging.Logger:
    normalized_namespace = _normalize_logger_namespace(namespace)
    return logging.getLogger(f"{LOGGER_PREFIX}.{normalized_namespace}")


def log_event(logger: logging.Logger, level: str, event: str, **fields) -> None:
    level_name = level.lower()
    log_method = getattr(logger, level_name, logger.info)
    field_parts = [f"event={event}"]
    for key in sorted(fields):
        field_parts.append(f"{key}={fields[key]}")
    log_method(" ".join(field_parts))


def get_or_create_request_id(request_id: str | None) -> str:
    if request_id and request_id.strip():
        return request_id.strip()
    return str(uuid4())


def infer_error_namespace(path: str) -> str:
    path_parts = [part for part in path.split("/") if part]
    if path_parts and path_parts[0] == "api":
        path_parts = path_parts[1:]
    if not path_parts:
        return "api"
    return path_parts[0].replace("-", "_")


def _status_error_name(status_code: int) -> str:
    try:
        phrase = HTTPStatus(status_code).phrase
    except ValueError:
        return f"HTTP_{status_code}"
    return phrase.replace(" ", "_").replace("-", "_")


def _detail_message(detail) -> str:
    if isinstance(detail, str):
        return detail
    if isinstance(detail, dict):
        message = detail.get("message") or detail.get("detail")
        if isinstance(message, str):
            return message
    return "Request failed"


def _explicit_error_code(detail) -> str | None:
    if not isinstance(detail, dict):
        return None
    code = detail.get("code")
    if isinstance(code, str) and re.fullmatch(r"[A-Z][A-Z0-9_]{0,99}", code):
        return code
    return None


def build_error_response_payload(
    *,
    code: str,
    detail,
    message: str,
    request_id: str,
    status_code: int,
) -> dict:
    return {
        "detail": detail,
        "error": {
            "code": code,
            "message": message,
            "request_id": request_id,
            "status_code": status_code,
        },
    }


def _json_safe_validation_errors(errors: list[dict]) -> list[dict]:
    safe_errors: list[dict] = []
    for error in errors:
        error_type = str(error.get("type") or "value_error")
        raw_location = error.get("loc") or ()
        safe_location = [
            part
            if isinstance(part, int)
            else part
            if isinstance(part, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,100}", part)
            else "field"
            for part in raw_location
        ]
        safe_error = {
            "type": error_type,
            "loc": safe_location,
            "msg": "Field required" if error_type == "missing" else "Invalid request value",
        }
        safe_errors.append(safe_error)
    return safe_errors


def _request_id_from_state_or_headers(request: Request) -> str:
    request_id = getattr(request.state, "request_id", None)
    return get_or_create_request_id(request_id or request.headers.get(REQUEST_ID_HEADER))


def add_error_handlers(app: FastAPI) -> None:
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        request_id = _request_id_from_state_or_headers(request)
        namespace = infer_error_namespace(request.url.path)
        detail = exc.detail
        code = _explicit_error_code(detail) or make_error_code(
            namespace,
            _status_error_name(exc.status_code),
        )
        message = _detail_message(detail)
        payload = build_error_response_payload(
            code=code,
            detail=detail,
            message=message,
            request_id=request_id,
            status_code=exc.status_code,
        )
        return JSONResponse(status_code=exc.status_code, content=payload, headers=dict(exc.headers or {}))

    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        request_id = _request_id_from_state_or_headers(request)
        payload = build_error_response_payload(
            code=make_error_code("validation", "request_invalid"),
            detail=_json_safe_validation_errors(exc.errors()),
            message="Request validation failed",
            request_id=request_id,
            status_code=422,
        )
        return JSONResponse(status_code=422, content=payload)

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)


def add_observability_middleware(app: FastAPI) -> None:
    @app.middleware("http")
    async def observability_middleware(request: Request, call_next):
        request_id = get_or_create_request_id(request.headers.get(REQUEST_ID_HEADER))
        request.state.request_id = request_id
        started_at = time.perf_counter()

        response = await call_next(request)
        elapsed_ms = (time.perf_counter() - started_at) * 1000
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[RESPONSE_TIME_HEADER] = f"{elapsed_ms:.2f}"
        return response
