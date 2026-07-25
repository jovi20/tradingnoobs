"""scope idempotency keys by owner

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-25 15:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "b2c3d4e5f6a7"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("idempotency_keys") as batch_op:
        batch_op.drop_constraint("uq_idempotency_keys_scope_key", type_="unique")
        batch_op.create_unique_constraint(
            "uq_idempotency_keys_user_scope_key",
            ["user_id", "scope", "key"],
        )

    op.create_index(
        "uq_idempotency_keys_system_scope_key",
        "idempotency_keys",
        ["scope", "key"],
        unique=True,
        postgresql_where=sa.text("user_id IS NULL"),
        sqlite_where=sa.text("user_id IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_idempotency_keys_system_scope_key",
        table_name="idempotency_keys",
    )
    with op.batch_alter_table("idempotency_keys") as batch_op:
        batch_op.drop_constraint(
            "uq_idempotency_keys_user_scope_key",
            type_="unique",
        )
        batch_op.create_unique_constraint(
            "uq_idempotency_keys_scope_key",
            ["scope", "key"],
        )
