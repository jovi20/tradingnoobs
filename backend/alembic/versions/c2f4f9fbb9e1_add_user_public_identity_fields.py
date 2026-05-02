"""add_user_public_identity_fields

Revision ID: c2f4f9fbb9e1
Revises: 6b082785e3a3
Create Date: 2026-04-14 00:40:00.000000
"""
from __future__ import annotations

import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c2f4f9fbb9e1"
down_revision = "6b082785e3a3"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_users = bind.execute(
        sa.text("SELECT id, email FROM users")
    ).mappings().all()

    normalized_seen: dict[str, int] = {}
    updates: list[dict[str, object]] = []
    for row in existing_users:
        normalized = row["email"].strip().lower()
        if normalized in normalized_seen and normalized_seen[normalized] != row["id"]:
            raise RuntimeError(
                f"Cannot backfill users.email_normalized because duplicate normalized email exists: {normalized}"
            )
        normalized_seen[normalized] = row["id"]
        updates.append(
            {
                "id": row["id"],
                "public_id": str(uuid.uuid4()),
                "email_normalized": normalized,
            }
        )

    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("public_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("status", sa.String(length=20), nullable=True, server_default="ACTIVE"))
        batch_op.add_column(sa.Column("email_normalized", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("locale", sa.String(length=20), nullable=True))
        batch_op.add_column(sa.Column("timezone", sa.String(length=50), nullable=True))

    if updates:
        bind.execute(
            sa.text(
                """
                UPDATE users
                SET public_id = :public_id,
                    status = 'ACTIVE',
                    email_normalized = :email_normalized
                WHERE id = :id
                """
            ),
            updates,
        )
    else:
        bind.execute(sa.text("UPDATE users SET status = 'ACTIVE' WHERE status IS NULL"))

    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("public_id", existing_type=sa.String(length=36), nullable=False)
        batch_op.alter_column("status", existing_type=sa.String(length=20), nullable=False, server_default="ACTIVE")
        batch_op.alter_column("email_normalized", existing_type=sa.String(length=255), nullable=False)
        batch_op.create_index("ix_users_public_id", ["public_id"], unique=True)
        batch_op.create_index("ix_users_email_normalized", ["email_normalized"], unique=True)


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_email_normalized")
        batch_op.drop_index("ix_users_public_id")
        batch_op.drop_column("timezone")
        batch_op.drop_column("locale")
        batch_op.drop_column("last_login_at")
        batch_op.drop_column("email_normalized")
        batch_op.drop_column("status")
        batch_op.drop_column("public_id")
