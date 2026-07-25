"""JRN-013 bind source accounts to their owning user.

Revision ID: e1f2a3b4c5d6
Revises: d0e1f2a3b4c5
"""
from alembic import op
import sqlalchemy as sa


revision = "e1f2a3b4c5d6"
down_revision = "d0e1f2a3b4c5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    mismatched_binding = connection.execute(
        sa.text(
            "SELECT b.id "
            "FROM import_source_bindings AS b "
            "JOIN trading_accounts AS a ON a.id = b.account_id "
            "WHERE b.user_id <> a.user_id "
            "LIMIT 1"
        )
    ).first()
    if mismatched_binding is not None:
        raise RuntimeError(
            "Cannot enforce source binding ownership: "
            "an import source binding references another user's account"
        )

    with op.batch_alter_table("trading_accounts") as batch_op:
        batch_op.create_unique_constraint(
            "uq_trading_accounts_owner_graph",
            ["id", "user_id"],
        )

    with op.batch_alter_table("import_source_bindings") as batch_op:
        batch_op.create_foreign_key(
            "fk_import_source_bindings_account_owner",
            "trading_accounts",
            ["account_id", "user_id"],
            ["id", "user_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("import_source_bindings") as batch_op:
        batch_op.drop_constraint(
            "fk_import_source_bindings_account_owner",
            type_="foreignkey",
        )

    with op.batch_alter_table("trading_accounts") as batch_op:
        batch_op.drop_constraint(
            "uq_trading_accounts_owner_graph",
            type_="unique",
        )
