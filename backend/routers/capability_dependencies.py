"""FastAPI dependencies for deployment-ceiling and runtime rollout checks."""
from __future__ import annotations

from functools import lru_cache

from fastapi import Depends
from sqlalchemy.orm import Session

from database import get_db
from models import User
from release_profile import RuntimeCapability
from routers.disabled_capabilities import raise_feature_disabled
from services.auth_service import get_current_user
from services.capability_service import is_effective_capability_enabled


@lru_cache(maxsize=None)
def require_runtime_capability(capability: RuntimeCapability):
    """Return a stable dependency that fails closed before route handlers run."""

    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db),
    ) -> None:
        if not is_effective_capability_enabled(
            db,
            capability,
            actor_key=current_user.public_id,
        ):
            raise_feature_disabled(capability.value)

    dependency.__name__ = f"require_{capability.value.lower()}_capability"
    return dependency


@lru_cache(maxsize=None)
def require_public_runtime_capability(capability: RuntimeCapability):
    """Fail closed for an unauthenticated optional route such as registration."""

    def dependency(db: Session = Depends(get_db)) -> None:
        if not is_effective_capability_enabled(db, capability):
            raise_feature_disabled(capability.value)

    dependency.__name__ = f"require_public_{capability.value.lower()}_capability"
    return dependency
