from __future__ import annotations

from datetime import datetime, timezone
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


class LocalDateTimeError(ValueError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def normalize_user_datetime_to_utc(
    value: datetime,
    *,
    timezone_name: str,
) -> datetime:
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc)

    zone = ZoneInfo(normalize_iana_timezone(timezone_name))
    candidates: list[datetime] = []
    for fold in (0, 1):
        candidate = value.replace(tzinfo=zone, fold=fold)
        round_trip = candidate.astimezone(timezone.utc).astimezone(zone)
        if round_trip.replace(tzinfo=None) == value:
            candidates.append(candidate)

    unique_offsets = {candidate.utcoffset() for candidate in candidates}
    if not candidates:
        raise LocalDateTimeError(
            "NONEXISTENT_LOCAL_TIME",
            "Local time does not exist in the selected timezone",
        )
    if len(unique_offsets) > 1:
        raise LocalDateTimeError(
            "AMBIGUOUS_LOCAL_TIME",
            "Local time is ambiguous in the selected timezone",
        )
    return candidates[0].astimezone(timezone.utc)
