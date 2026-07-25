"""JRN-010 canonical position void status

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-07-25 23:30:00.000000
"""
from __future__ import annotations

from alembic import op


revision = "f6a7b8c9d0e1"
down_revision = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("ALTER TYPE tradingpositionstatus ADD VALUE IF NOT EXISTS 'VOID'")


def downgrade() -> None:
    # PostgreSQL enum values cannot be removed safely while rows may reference
    # them. Application rollback remains compatible with the stored value.
    pass
