"""
Trading Noobs Backend - Application Bootstrap Helpers
"""

from typing import Optional


def resolve_auto_create_schema_enabled(env_name: str, explicit: Optional[bool]) -> bool:
    """Default to disabled in production unless explicitly overridden."""
    if explicit is not None:
        return explicit
    return env_name.lower() != "production"


def bootstrap_schema_if_enabled(metadata, engine, enabled: bool) -> None:
    """Create database tables only when schema auto-bootstrap is enabled."""
    if enabled:
        metadata.create_all(bind=engine)
