"""add_business_locks

Revision ID: 3c4d5e6f7a8b
Revises: 2a3b4c5d6e7f
Create Date: 2026-05-05 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "3c4d5e6f7a8b"
down_revision = "2a3b4c5d6e7f"
branch_labels = None
depends_on = None


business_lock_status = sa.Enum(
    "ACTIVE",
    "RELEASED",
    "EXPIRED",
    name="businesslockstatus",
)


def upgrade() -> None:
    op.create_table(
        "business_locks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("scope", sa.String(length=120), nullable=False),
        sa.Column("resource_key", sa.String(length=255), nullable=False),
        sa.Column("owner_id", sa.String(length=120), nullable=False),
        sa.Column("owner_type", sa.String(length=80), nullable=False),
        sa.Column("status", business_lock_status, nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("acquired_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("released_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "resource_key", name="uq_business_locks_scope_resource"),
    )
    op.create_index(op.f("ix_business_locks_id"), "business_locks", ["id"], unique=False)
    op.create_index(op.f("ix_business_locks_public_id"), "business_locks", ["public_id"], unique=True)
    op.create_index(op.f("ix_business_locks_resource_key"), "business_locks", ["resource_key"], unique=False)
    op.create_index(op.f("ix_business_locks_scope"), "business_locks", ["scope"], unique=False)
    op.create_index(op.f("ix_business_locks_status"), "business_locks", ["status"], unique=False)
    op.create_index("ix_business_locks_status_expires", "business_locks", ["status", "expires_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_business_locks_status_expires", table_name="business_locks")
    op.drop_index(op.f("ix_business_locks_status"), table_name="business_locks")
    op.drop_index(op.f("ix_business_locks_scope"), table_name="business_locks")
    op.drop_index(op.f("ix_business_locks_resource_key"), table_name="business_locks")
    op.drop_index(op.f("ix_business_locks_public_id"), table_name="business_locks")
    op.drop_index(op.f("ix_business_locks_id"), table_name="business_locks")
    op.drop_table("business_locks")
