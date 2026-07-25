from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, HTTPException, Request, status

from models import User
from services.auth_service import get_current_user


def normalize_iana_timezone(value: str | None) -> str:
    timezone_name = (value or "").strip()
    if not timezone_name:
        raise ValueError("Timezone is required")
    try:
        ZoneInfo(timezone_name)
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError("Timezone must be a valid IANA timezone") from None
    return timezone_name


def require_write_timezone(
    current_user: User = Depends(get_current_user),
) -> User:
    try:
        normalize_iana_timezone(current_user.timezone)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_428_PRECONDITION_REQUIRED,
            detail={
                "code": "TIMEZONE_REQUIRED",
                "message": "Select a valid IANA timezone before writing journal data",
            },
        ) from None
    return current_user


def require_journal_write_timezone(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> User:
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        return require_write_timezone(current_user)
    return current_user
