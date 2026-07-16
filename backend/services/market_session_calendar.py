from __future__ import annotations

import calendar
from datetime import date, timedelta


def _nth_weekday(year: int, month: int, weekday: int, occurrence: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (occurrence - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last = date(year, month, calendar.monthrange(year, month)[1])
    return last - timedelta(days=(last.weekday() - weekday) % 7)


def _observed_fixed_holiday(value: date) -> date:
    if value.weekday() == 5:
        return value - timedelta(days=1)
    if value.weekday() == 6:
        return value + timedelta(days=1)
    return value


def _easter_sunday(year: int) -> date:
    # Anonymous Gregorian algorithm.
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    longitude = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * longitude) // 451
    month = (h + longitude - 7 * m + 114) // 31
    day = (h + longitude - 7 * m + 114) % 31 + 1
    return date(year, month, day)


def _us_market_holidays(year: int) -> set[date]:
    holidays = {
        _observed_fixed_holiday(date(year, 1, 1)),
        _nth_weekday(year, 1, calendar.MONDAY, 3),
        _nth_weekday(year, 2, calendar.MONDAY, 3),
        _easter_sunday(year) - timedelta(days=2),
        _last_weekday(year, 5, calendar.MONDAY),
        _observed_fixed_holiday(date(year, 7, 4)),
        _nth_weekday(year, 9, calendar.MONDAY, 1),
        _nth_weekday(year, 11, calendar.THURSDAY, 4),
        _observed_fixed_holiday(date(year, 12, 25)),
    }
    if year >= 2022:
        holidays.add(_observed_fixed_holiday(date(year, 6, 19)))
    return holidays


def expected_daily_sessions(
    market: str,
    start: date,
    end: date,
) -> set[date] | None:
    """Return sessions that can be validated locally, or None if a live calendar is required."""
    if start > end:
        return set()

    normalized_market = (market or "").upper()
    if normalized_market == "CRYPTO":
        holidays: set[date] = set()
        include_weekends = True
    elif normalized_market == "US":
        holidays = set()
        for year in range(start.year - 1, end.year + 2):
            holidays.update(_us_market_holidays(year))
        include_weekends = False
    else:
        # CN/HK holiday schedules are not derivable safely from weekdays alone.
        return None

    sessions: set[date] = set()
    current = start
    while current <= end:
        if (include_weekends or current.weekday() < 5) and current not in holidays:
            sessions.add(current)
        current += timedelta(days=1)
    return sessions
