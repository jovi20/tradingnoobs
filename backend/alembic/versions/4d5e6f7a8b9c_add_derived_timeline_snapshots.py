"""add_derived_timeline_snapshots

Revision ID: 4d5e6f7a8b9c
Revises: 3c4d5e6f7a8b
Create Date: 2026-05-05 00:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "4d5e6f7a8b9c"
down_revision = "3c4d5e6f7a8b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "derived_timeline_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("trading_position_public_id", sa.String(length=100), nullable=False),
        sa.Column("source", sa.String(length=120), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("refreshed_by_job_run_public_id", sa.String(length=36), nullable=True),
        sa.Column("refreshed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "trading_position_public_id", name="uq_derived_timeline_snapshots_user_position"),
    )
    op.create_index(op.f("ix_derived_timeline_snapshots_id"), "derived_timeline_snapshots", ["id"], unique=False)
    op.create_index(op.f("ix_derived_timeline_snapshots_public_id"), "derived_timeline_snapshots", ["public_id"], unique=True)
    op.create_index(
        op.f("ix_derived_timeline_snapshots_trading_position_public_id"),
        "derived_timeline_snapshots",
        ["trading_position_public_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_derived_timeline_snapshots_refreshed_by_job_run_public_id"),
        "derived_timeline_snapshots",
        ["refreshed_by_job_run_public_id"],
        unique=False,
    )
    op.create_index(
        "ix_derived_timeline_snapshots_user_refreshed",
        "derived_timeline_snapshots",
        ["user_id", "refreshed_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_derived_timeline_snapshots_user_refreshed", table_name="derived_timeline_snapshots")
    op.drop_index(op.f("ix_derived_timeline_snapshots_refreshed_by_job_run_public_id"), table_name="derived_timeline_snapshots")
    op.drop_index(op.f("ix_derived_timeline_snapshots_trading_position_public_id"), table_name="derived_timeline_snapshots")
    op.drop_index(op.f("ix_derived_timeline_snapshots_public_id"), table_name="derived_timeline_snapshots")
    op.drop_index(op.f("ix_derived_timeline_snapshots_id"), table_name="derived_timeline_snapshots")
    op.drop_table("derived_timeline_snapshots")
