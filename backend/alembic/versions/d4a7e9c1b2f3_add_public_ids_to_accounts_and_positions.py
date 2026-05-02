"""add_public_ids_to_accounts_and_positions

Revision ID: d4a7e9c1b2f3
Revises: a9d4e6b2c1f0
Create Date: 2026-04-15 01:20:00.000000
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "d4a7e9c1b2f3"
down_revision = "a9d4e6b2c1f0"
branch_labels = None
depends_on = None


def _backfill_public_ids(bind, table_name: str) -> None:
    rows = bind.execute(sa.text(f"SELECT id FROM {table_name}")).mappings().all()
    if not rows:
        return
    bind.execute(
        sa.text(f"UPDATE {table_name} SET public_id = :public_id WHERE id = :id"),
        [{"id": row["id"], "public_id": str(uuid.uuid4())} for row in rows],
    )


def upgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("trading_accounts") as batch_op:
        batch_op.add_column(sa.Column("public_id", sa.String(length=36), nullable=True))

    with op.batch_alter_table("positions") as batch_op:
        batch_op.add_column(sa.Column("public_id", sa.String(length=36), nullable=True))

    _backfill_public_ids(bind, "trading_accounts")
    _backfill_public_ids(bind, "positions")

    with op.batch_alter_table("trading_accounts") as batch_op:
        batch_op.alter_column("public_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.create_index("ix_trading_accounts_public_id", ["public_id"], unique=True)

    with op.batch_alter_table("positions") as batch_op:
        batch_op.alter_column("public_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.create_index("ix_positions_public_id", ["public_id"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("positions") as batch_op:
        batch_op.drop_index("ix_positions_public_id")
        batch_op.drop_column("public_id")

    with op.batch_alter_table("trading_accounts") as batch_op:
        batch_op.drop_index("ix_trading_accounts_public_id")
        batch_op.drop_column("public_id")
