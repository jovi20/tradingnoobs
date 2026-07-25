from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit, urlunsplit


REDACTED = "[REDACTED]"
_SENSITIVE_KEY = re.compile(
    r"(api[_-]?key|token|secret|password|credential|authorization|cookie|query[_-]?id)",
    re.IGNORECASE,
)
_URL = re.compile(r"https?://[^\s\"'<>]+", re.IGNORECASE)
_BEARER = re.compile(r"\bBearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_KEY_VALUE = re.compile(
    r"(?i)\b(api[_-]?key|token|secret|password|credential|query[_-]?id)=([^&\s]+)"
)


def redact_url(value: str) -> str:
    try:
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            return value
        host = parsed.hostname or ""
        port = f":{parsed.port}" if parsed.port else ""
        return urlunsplit((parsed.scheme, f"{host}{port}", parsed.path, "", ""))
    except ValueError:
        return REDACTED


def redact_text(value: str) -> str:
    sanitized = _BEARER.sub(f"Bearer {REDACTED}", value)
    sanitized = _KEY_VALUE.sub(lambda match: f"{match.group(1)}={REDACTED}", sanitized)
    return _URL.sub(lambda match: redact_url(match.group(0)), sanitized)


def sanitize_for_observability(value: Any, *, field_name: str | None = None) -> Any:
    if field_name and _SENSITIVE_KEY.search(field_name):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            str(key): sanitize_for_observability(item, field_name=str(key))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple, set)):
        return [sanitize_for_observability(item) for item in value]
    if isinstance(value, BaseException):
        return redact_text(str(value))
    if isinstance(value, str):
        return redact_text(value)
    return value
