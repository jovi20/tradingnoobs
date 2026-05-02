"""add_account_ledger_entries

Revision ID: b7e2a4c5d6f8
Revises: f9a1b2c3d4e5
Create Date: 2026-05-02 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "b7e2a4c5d6f8"
down_revision = "f9a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "account_ledger_entries",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=True),
        sa.Column("position_event_id", sa.Integer(), nullable=True),
        sa.Column("transaction_id", sa.Integer(), nullable=True),
        sa.Column(
            "entry_type",
            sa.Enum(
                "DEPOSIT",
                "WITHDRAWAL",
                "DIVIDEND",
                "FEE",
                "CASH_ADJUSTMENT",
                "REALIZED_PNL",
                name="accountledgerentrytype",
            ),
            nullable=False,
        ),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("amount_account_ccy", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("fx_rate_to_account_ccy", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("source", sa.String(length=50), nullable=True),
        sa.Column("source_run_id", sa.String(length=100), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"]),
        sa.ForeignKeyConstraint(["position_event_id"], ["position_events.id"]),
        sa.ForeignKeyConstraint(["position_id"], ["trading_positions.id"]),
        sa.ForeignKeyConstraint(["transaction_id"], ["transactions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_account_ledger_entries_id"), "account_ledger_entries", ["id"], unique=False)
    op.create_index(op.f("ix_account_ledger_entries_public_id"), "account_ledger_entries", ["public_id"], unique=True)
    op.create_index(
        "ix_account_ledger_entries_user_account_occurred",
        "account_ledger_entries",
        ["user_id", "account_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_account_ledger_entries_position_event",
        "account_ledger_entries",
        ["position_id", "position_event_id"],
        unique=False,
    )
    op.create_index(
        "ix_account_ledger_entries_transaction",
        "account_ledger_entries",
        ["transaction_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_account_ledger_entries_transaction", table_name="account_ledger_entries")
    op.drop_index("ix_account_ledger_entries_position_event", table_name="account_ledger_entries")
    op.drop_index("ix_account_ledger_entries_user_account_occurred", table_name="account_ledger_entries")
    op.drop_index(op.f("ix_account_ledger_entries_public_id"), table_name="account_ledger_entries")
    op.drop_index(op.f("ix_account_ledger_entries_id"), table_name="account_ledger_entries")
    op.drop_table("account_ledger_entries")
