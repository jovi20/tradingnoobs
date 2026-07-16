"""Static release-profile boundary for launch-safe capability loading."""
from __future__ import annotations

import os
from contextlib import contextmanager
from contextvars import ContextVar
from enum import Enum
from typing import Iterator


class ReleaseProfile(str, Enum):
    JOURNAL_BASELINE = "JOURNAL_BASELINE"
    DEVELOPMENT_FULL = "DEVELOPMENT_FULL"


class RuntimeCapability(str, Enum):
    MARKET = "MARKET"
    BROKER_SYNC = "BROKER_SYNC"


def parse_release_profile(value: str | ReleaseProfile | None) -> ReleaseProfile:
    if isinstance(value, ReleaseProfile):
        return value
    normalized = (value or "").strip().upper()
    try:
        return ReleaseProfile(normalized)
    except ValueError:
        return ReleaseProfile.JOURNAL_BASELINE


# Read once at process import. Business tables and Admin APIs cannot mutate it.
STATIC_RELEASE_PROFILE = parse_release_profile(os.getenv("RELEASE_PROFILE"))
_active_release_profile: ContextVar[ReleaseProfile] = ContextVar(
    "active_release_profile",
    default=STATIC_RELEASE_PROFILE,
)


def get_active_release_profile() -> ReleaseProfile:
    return _active_release_profile.get()


def is_capability_enabled(
    capability: RuntimeCapability,
    *,
    profile: ReleaseProfile | str | None = None,
) -> bool:
    selected = parse_release_profile(profile) if profile is not None else get_active_release_profile()
    return selected is ReleaseProfile.DEVELOPMENT_FULL and capability in {
        RuntimeCapability.MARKET,
        RuntimeCapability.BROKER_SYNC,
    }


@contextmanager
def bind_release_profile(profile: ReleaseProfile | str) -> Iterator[ReleaseProfile]:
    selected = parse_release_profile(profile)
    token = _active_release_profile.set(selected)
    try:
        yield selected
    finally:
        _active_release_profile.reset(token)
