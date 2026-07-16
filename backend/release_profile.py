"""Deployment capability ceiling and legacy release-profile context."""
from __future__ import annotations

import os
from collections.abc import Mapping
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from enum import Enum
from typing import Iterator


DEPLOYMENT_CAPABILITY_ALLOWLIST_ENV = "DEPLOYMENT_CAPABILITY_ALLOWLIST"


class ReleaseProfile(str, Enum):
    JOURNAL_BASELINE = "JOURNAL_BASELINE"
    DEVELOPMENT_FULL = "DEVELOPMENT_FULL"


class RuntimeCapability(str, Enum):
    """Optional capabilities that require deployment and runtime approval."""

    MARKET = "MARKET"
    BROKER_SYNC = "BROKER_SYNC"
    AI_INSIGHTS = "AI_INSIGHTS"
    PDF_EXPORT = "PDF_EXPORT"
    RISK_CARDS = "RISK_CARDS"
    OPEN_REGISTRATION = "OPEN_REGISTRATION"


OPTIONAL_RUNTIME_CAPABILITIES = frozenset(RuntimeCapability)


class DeploymentCapabilityConfigurationError(ValueError):
    """Raised when the immutable deployment ceiling is malformed."""


def coerce_runtime_capability(
    value: RuntimeCapability | str,
) -> RuntimeCapability | None:
    if isinstance(value, RuntimeCapability):
        return value
    if not isinstance(value, str):
        return None
    normalized = value.strip().upper().replace("-", "_")
    try:
        return RuntimeCapability(normalized)
    except ValueError:
        return None


def parse_deployment_capability_allowlist(
    value: str | None,
) -> frozenset[RuntimeCapability]:
    """Parse a comma-delimited external allowlist without permissive fallbacks."""
    if value is None or not value.strip():
        return frozenset()

    allowed: set[RuntimeCapability] = set()
    unknown: set[str] = set()
    for raw_token in value.split(","):
        token = raw_token.strip()
        if not token:
            continue
        capability = coerce_runtime_capability(token)
        if capability is None:
            unknown.add(token)
        else:
            allowed.add(capability)

    if unknown:
        unknown_list = ", ".join(sorted(unknown))
        raise DeploymentCapabilityConfigurationError(
            f"Unknown deployment capability: {unknown_list}"
        )
    return frozenset(allowed)


@dataclass(frozen=True)
class DeploymentCapabilityPolicy:
    allowed_capabilities: frozenset[RuntimeCapability]

    def allows(self, capability: RuntimeCapability | str) -> bool:
        normalized = coerce_runtime_capability(capability)
        return normalized is not None and normalized in self.allowed_capabilities


def load_deployment_capability_policy(
    environ: Mapping[str, str] | None = None,
) -> DeploymentCapabilityPolicy:
    source = os.environ if environ is None else environ
    return DeploymentCapabilityPolicy(
        allowed_capabilities=parse_deployment_capability_allowlist(
            source.get(DEPLOYMENT_CAPABILITY_ALLOWLIST_ENV)
        )
    )


def parse_release_profile(value: str | ReleaseProfile | None) -> ReleaseProfile:
    if isinstance(value, ReleaseProfile):
        return value
    normalized = (value or "").strip().upper()
    try:
        return ReleaseProfile(normalized)
    except ValueError:
        return ReleaseProfile.JOURNAL_BASELINE


# Both values are read once at process import. Business tables and Admin APIs
# can narrow runtime rollout, but cannot widen this deployment-owned ceiling.
STATIC_DEPLOYMENT_CAPABILITY_POLICY = load_deployment_capability_policy()
STATIC_RELEASE_PROFILE = parse_release_profile(os.getenv("RELEASE_PROFILE"))
_active_release_profile: ContextVar[ReleaseProfile] = ContextVar(
    "active_release_profile",
    default=STATIC_RELEASE_PROFILE,
)


def get_active_release_profile() -> ReleaseProfile:
    return _active_release_profile.get()


def get_deployment_capability_allowlist() -> frozenset[RuntimeCapability]:
    return STATIC_DEPLOYMENT_CAPABILITY_POLICY.allowed_capabilities


def is_capability_enabled(
    capability: RuntimeCapability | str,
    *,
    profile: ReleaseProfile | str | None = None,
) -> bool:
    """Return whether code may load inside the immutable deployment ceiling.

    ``profile`` remains for compatibility with the JRN-000 call sites. Release
    profiles cannot widen or narrow the deployment-owned capability ceiling.
    Runtime rollout is a separate database-backed decision.
    """
    del profile
    normalized = coerce_runtime_capability(capability)
    if normalized is None:
        return False
    return STATIC_DEPLOYMENT_CAPABILITY_POLICY.allows(normalized)


@contextmanager
def bind_release_profile(profile: ReleaseProfile | str) -> Iterator[ReleaseProfile]:
    """Temporarily bind the legacy release-profile context."""
    selected = parse_release_profile(profile)
    token = _active_release_profile.set(selected)
    try:
        yield selected
    finally:
        _active_release_profile.reset(token)
