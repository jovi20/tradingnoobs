"""Fail-closed runtime rollout resolution for optional capabilities."""
from __future__ import annotations

from types import MappingProxyType

from sqlalchemy.orm import Session

from release_profile import (
    ReleaseProfile,
    RuntimeCapability,
    coerce_runtime_capability,
    is_capability_enabled,
)
from services.platform_config_service import get_feature_flag_enabled


CAPABILITY_ROLLOUT_FLAG_KEYS = MappingProxyType(
    {
        capability: f"capability.{capability.value.lower()}.v1"
        for capability in RuntimeCapability
    }
)


def capability_rollout_flag_key(
    capability: RuntimeCapability | str,
) -> str | None:
    normalized = coerce_runtime_capability(capability)
    if normalized is None:
        return None
    return CAPABILITY_ROLLOUT_FLAG_KEYS[normalized]


def is_effective_capability_enabled(
    db: Session,
    capability: RuntimeCapability | str,
    *,
    actor_key: str | None = None,
    profile: ReleaseProfile | str | None = None,
) -> bool:
    """Resolve deployment ceiling AND database rollout, failing closed."""
    normalized = coerce_runtime_capability(capability)
    if normalized is None or not is_capability_enabled(normalized, profile=profile):
        return False

    flag_key = CAPABILITY_ROLLOUT_FLAG_KEYS[normalized]
    try:
        return get_feature_flag_enabled(db, flag_key, actor_key=actor_key)
    except Exception:
        return False


# Keep the name explicit for callers that think in terms of runtime rollout.
is_runtime_capability_enabled = is_effective_capability_enabled
