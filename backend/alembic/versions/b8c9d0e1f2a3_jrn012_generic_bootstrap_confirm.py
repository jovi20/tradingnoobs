"""JRN-012 generic bootstrap confirm audit linkage.

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
"""
from alembic import op
import sqlalchemy as sa


revision = "b8c9d0e1f2a3"
down_revision = "a7b8c9d0e1f2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("import_sessions") as batch_op:
        batch_op.add_column(
            sa.Column("confirm_idempotency_id", sa.Integer(), nullable=True),
        )
        batch_op.create_foreign_key(
            "fk_import_sessions_confirm_idempotency",
            "idempotency_keys",
            ["confirm_idempotency_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_import_sessions_confirm_idempotency",
            ["confirm_idempotency_id"],
        )

    with op.batch_alter_table("import_rows") as batch_op:
        batch_op.add_column(
            sa.Column(
                "applied_position_public_id",
                sa.String(length=36),
                nullable=True,
            ),
        )
        batch_op.add_column(
            sa.Column(
                "applied_event_public_id",
                sa.String(length=36),
                nullable=True,
            ),
        )
        batch_op.create_unique_constraint(
            "uq_import_rows_applied_event",
            ["applied_event_public_id"],
        )
        batch_op.create_check_constraint(
            "ck_import_rows_applied_link_pair",
            "(applied_position_public_id IS NULL "
            "AND applied_event_public_id IS NULL) "
            "OR (applied_position_public_id IS NOT NULL "
            "AND applied_event_public_id IS NOT NULL)",
        )


def downgrade() -> None:
    with op.batch_alter_table("import_rows") as batch_op:
        batch_op.drop_constraint(
            "ck_import_rows_applied_link_pair",
            type_="check",
        )
        batch_op.drop_constraint(
            "uq_import_rows_applied_event",
            type_="unique",
        )
        batch_op.drop_column("applied_event_public_id")
        batch_op.drop_column("applied_position_public_id")

    with op.batch_alter_table("import_sessions") as batch_op:
        batch_op.drop_constraint(
            "uq_import_sessions_confirm_idempotency",
            type_="unique",
        )
        batch_op.drop_constraint(
            "fk_import_sessions_confirm_idempotency",
            type_="foreignkey",
        )
        batch_op.drop_column("confirm_idempotency_id")
