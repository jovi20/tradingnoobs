"""JRN-009 immutable cash facts and financial audit metadata

Revision ID: e5f6a7b8c9d0
Revises: d4e5f6a7b8c9
Create Date: 2026-07-25 20:20:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "e5f6a7b8c9d0"
down_revision = "d4e5f6a7b8c9"
branch_labels = None
depends_on = None


def _install_financial_fact_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION reject_transaction_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'transactions are immutable'
                    USING ERRCODE = '55000';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_transactions_immutable
            BEFORE UPDATE OR DELETE ON transactions
            FOR EACH ROW EXECUTE FUNCTION reject_transaction_mutation()
            """
        )
        op.execute(
            """
            CREATE OR REPLACE FUNCTION reject_position_event_financial_mutation()
            RETURNS trigger AS $$
            BEGIN
                IF TG_OP = 'DELETE' THEN
                    RAISE EXCEPTION 'position events are immutable'
                        USING ERRCODE = '55000';
                END IF;
                IF OLD.position_id IS DISTINCT FROM NEW.position_id
                   OR OLD.account_id IS DISTINCT FROM NEW.account_id
                   OR OLD.instrument_id IS DISTINCT FROM NEW.instrument_id
                   OR OLD.event_type IS DISTINCT FROM NEW.event_type
                   OR OLD.event_time IS DISTINCT FROM NEW.event_time
                   OR OLD.sequence_no IS DISTINCT FROM NEW.sequence_no
                   OR OLD.side_effect IS DISTINCT FROM NEW.side_effect
                   OR OLD.quantity IS DISTINCT FROM NEW.quantity
                   OR OLD.price IS DISTINCT FROM NEW.price
                   OR OLD.currency IS DISTINCT FROM NEW.currency
                   OR OLD.gross_amount IS DISTINCT FROM NEW.gross_amount
                   OR OLD.fee_amount IS DISTINCT FROM NEW.fee_amount
                   OR OLD.fee_currency IS DISTINCT FROM NEW.fee_currency
                   OR OLD.fx_rate_to_account_ccy IS DISTINCT FROM NEW.fx_rate_to_account_ccy
                   OR OLD.reverses_event_id IS DISTINCT FROM NEW.reverses_event_id THEN
                    RAISE EXCEPTION 'position-event financial fields are immutable'
                        USING ERRCODE = '55000';
                END IF;
                RETURN NEW;
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_position_events_financial_immutable
            BEFORE UPDATE OR DELETE ON position_events
            FOR EACH ROW EXECUTE FUNCTION reject_position_event_financial_mutation()
            """
        )
    elif dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER trg_transactions_no_update
            BEFORE UPDATE ON transactions
            BEGIN
                SELECT RAISE(ABORT, 'transactions are immutable');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_transactions_no_delete
            BEFORE DELETE ON transactions
            BEGIN
                SELECT RAISE(ABORT, 'transactions are immutable');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_position_events_no_delete
            BEFORE DELETE ON position_events
            BEGIN
                SELECT RAISE(ABORT, 'position events are immutable');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_position_events_financial_no_update
            BEFORE UPDATE ON position_events
            WHEN OLD.position_id IS NOT NEW.position_id
              OR OLD.account_id IS NOT NEW.account_id
              OR OLD.instrument_id IS NOT NEW.instrument_id
              OR OLD.event_type IS NOT NEW.event_type
              OR OLD.event_time IS NOT NEW.event_time
              OR OLD.sequence_no IS NOT NEW.sequence_no
              OR OLD.side_effect IS NOT NEW.side_effect
              OR OLD.quantity IS NOT NEW.quantity
              OR OLD.price IS NOT NEW.price
              OR OLD.currency IS NOT NEW.currency
              OR OLD.gross_amount IS NOT NEW.gross_amount
              OR OLD.fee_amount IS NOT NEW.fee_amount
              OR OLD.fee_currency IS NOT NEW.fee_currency
              OR OLD.fx_rate_to_account_ccy IS NOT NEW.fx_rate_to_account_ccy
              OR OLD.reverses_event_id IS NOT NEW.reverses_event_id
            BEGIN
                SELECT RAISE(ABORT, 'position-event financial fields are immutable');
            END
            """
        )


def _drop_financial_fact_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_position_events_financial_immutable "
            "ON position_events"
        )
        op.execute(
            "DROP FUNCTION IF EXISTS reject_position_event_financial_mutation()"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS trg_transactions_immutable ON transactions"
        )
        op.execute("DROP FUNCTION IF EXISTS reject_transaction_mutation()")
    elif dialect == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS trg_position_events_financial_no_update")
        op.execute("DROP TRIGGER IF EXISTS trg_position_events_no_delete")
        op.execute("DROP TRIGGER IF EXISTS trg_transactions_no_update")
        op.execute("DROP TRIGGER IF EXISTS trg_transactions_no_delete")


def upgrade() -> None:
    op.add_column(
        "trading_accounts",
        sa.Column(
            "hard_delete_eligible",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.execute(
        """
        UPDATE trading_accounts
        SET hard_delete_eligible = FALSE
        WHERE EXISTS (
            SELECT 1 FROM account_ledger_entries
            WHERE account_ledger_entries.account_id = trading_accounts.id
        )
        OR EXISTS (
            SELECT 1 FROM transactions
            WHERE transactions.account_id = trading_accounts.id
        )
        OR EXISTS (
            SELECT 1 FROM trading_positions
            WHERE trading_positions.account_id = trading_accounts.id
        )
        OR EXISTS (
            SELECT 1 FROM position_events
            WHERE position_events.account_id = trading_accounts.id
        )
        """
    )
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.add_column(
            sa.Column("reverses_transaction_id", sa.Integer(), nullable=True)
        )
        batch_op.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("request_id", sa.String(length=100), nullable=True))
        batch_op.add_column(sa.Column("reversal_reason", sa.Text(), nullable=True))
        batch_op.create_foreign_key(
            "fk_transactions_reverses_transaction",
            "transactions",
            ["reverses_transaction_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_transactions_actor_user",
            "users",
            ["actor_user_id"],
            ["id"],
        )
        batch_op.create_unique_constraint(
            "uq_transaction_reverses_transaction",
            ["reverses_transaction_id"],
        )

    with op.batch_alter_table("position_events") as batch_op:
        batch_op.add_column(sa.Column("actor_user_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("request_id", sa.String(length=100), nullable=True))
        batch_op.create_foreign_key(
            "fk_position_events_actor_user",
            "users",
            ["actor_user_id"],
            ["id"],
        )

    _install_financial_fact_guards()


def downgrade() -> None:
    _drop_financial_fact_guards()
    with op.batch_alter_table("position_events") as batch_op:
        batch_op.drop_constraint(
            "fk_position_events_actor_user",
            type_="foreignkey",
        )
        batch_op.drop_column("request_id")
        batch_op.drop_column("actor_user_id")
    with op.batch_alter_table("transactions") as batch_op:
        batch_op.drop_constraint(
            "uq_transaction_reverses_transaction",
            type_="unique",
        )
        batch_op.drop_constraint(
            "fk_transactions_actor_user",
            type_="foreignkey",
        )
        batch_op.drop_constraint(
            "fk_transactions_reverses_transaction",
            type_="foreignkey",
        )
        batch_op.drop_column("reversal_reason")
        batch_op.drop_column("request_id")
        batch_op.drop_column("actor_user_id")
        batch_op.drop_column("reverses_transaction_id")
    op.drop_column("trading_accounts", "hard_delete_eligible")
