"""add_outbox_events

Revision ID: 2a3b4c5d6e7f
Revises: 1f2e3d4c5b6a
Create Date: 2026-05-03 00:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "2a3b4c5d6e7f"
down_revision = "1f2e3d4c5b6a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("aggregate_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_public_id", sa.String(length=100), nullable=True),
        sa.Column("event_type", sa.String(length=150), nullable=False),
        sa.Column("queue_name", sa.String(length=80), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("PENDING", "PUBLISHED", "FAILED", "DISCARDED", name="outboxeventstatus"),
            nullable=False,
        ),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("available_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outbox_events_id"), "outbox_events", ["id"], unique=False)
    op.create_index(op.f("ix_outbox_events_public_id"), "outbox_events", ["public_id"], unique=True)
    op.create_index(op.f("ix_outbox_events_status"), "outbox_events", ["status"], unique=False)
    op.create_index(op.f("ix_outbox_events_dedupe_key"), "outbox_events", ["dedupe_key"], unique=True)
    op.create_index("ix_outbox_events_status_available", "outbox_events", ["status", "available_at"], unique=False)
    op.create_index("ix_outbox_events_aggregate", "outbox_events", ["aggregate_type", "aggregate_public_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_outbox_events_aggregate", table_name="outbox_events")
    op.drop_index("ix_outbox_events_status_available", table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_dedupe_key"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_status"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_public_id"), table_name="outbox_events")
    op.drop_index(op.f("ix_outbox_events_id"), table_name="outbox_events")
    op.drop_table("outbox_events")
