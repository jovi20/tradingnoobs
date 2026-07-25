"""JRN-006 append-only ledger and accounting health

Revision ID: c3d4e5f6a7b8
Revises: b2c3d4e5f6a7
Create Date: 2026-07-25 18:00:00.000000
"""
from __future__ import annotations

from datetime import timezone
from decimal import Decimal
import uuid

from alembic import op
import sqlalchemy as sa


revision = "c3d4e5f6a7b8"
down_revision = "b2c3d4e5f6a7"
branch_labels = None
depends_on = None

LEDGER_NAMESPACE = uuid.UUID("59f7cb40-f4a6-46c2-9943-6470a42c24c8")


def _install_append_only_guard() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION reject_account_ledger_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION 'account_ledger_entries is append-only'
                    USING ERRCODE = '55000';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_account_ledger_entries_append_only
            BEFORE UPDATE OR DELETE ON account_ledger_entries
            FOR EACH ROW EXECUTE FUNCTION reject_account_ledger_mutation()
            """
        )
    elif dialect == "sqlite":
        op.execute(
            """
            CREATE TRIGGER trg_account_ledger_entries_no_update
            BEFORE UPDATE ON account_ledger_entries
            BEGIN
                SELECT RAISE(ABORT, 'account_ledger_entries is append-only');
            END
            """
        )
        op.execute(
            """
            CREATE TRIGGER trg_account_ledger_entries_no_delete
            BEFORE DELETE ON account_ledger_entries
            BEGIN
                SELECT RAISE(ABORT, 'account_ledger_entries is append-only');
            END
            """
        )


def _drop_append_only_guard() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_account_ledger_entries_append_only "
            "ON account_ledger_entries"
        )
        op.execute(
            "DROP FUNCTION IF EXISTS reject_account_ledger_mutation()"
        )
    elif dialect == "sqlite":
        op.execute(
            "DROP TRIGGER IF EXISTS trg_account_ledger_entries_no_update"
        )
        op.execute(
            "DROP TRIGGER IF EXISTS trg_account_ledger_entries_no_delete"
        )


def _backfill_opening_balances() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT a.id, a.public_id, a.user_id, a.currency,
                   a.initial_balance, a.created_at
            FROM trading_accounts a
            WHERE a.initial_balance IS NOT NULL
              AND a.initial_balance <> 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM account_ledger_entries l
                  WHERE l.account_id = a.id
                    AND l.source = 'OPENING_BALANCE'
              )
            """
        )
    ).mappings().all()
    for row in rows:
        public_id = str(
            uuid.uuid5(
                LEDGER_NAMESPACE,
                f"{row['public_id']}:OPENING_BALANCE",
            )
        )
        occurred_at = row["created_at"]
        if occurred_at is not None and occurred_at.tzinfo is None:
            occurred_at = occurred_at.replace(tzinfo=timezone.utc)
        amount = Decimal(str(row["initial_balance"])).quantize(
            Decimal("0.00000001")
        )
        bind.execute(
            sa.text(
                """
                INSERT INTO account_ledger_entries (
                    public_id, user_id, account_id, entry_type,
                    source_fact_public_id, posting_kind, occurred_at,
                    currency, amount, amount_account_ccy,
                    fx_rate_to_account_ccy, source, source_run_id,
                    description
                ) VALUES (
                    :public_id, :user_id, :account_id, 'CASH_ADJUSTMENT',
                    :source_fact_public_id, 'OPENING_BALANCE', :occurred_at,
                    :currency, :amount, :amount, 1,
                    'OPENING_BALANCE', :source_run_id,
                    'Opening cash balance'
                )
                """
            ),
            {
                "public_id": public_id,
                "user_id": row["user_id"],
                "account_id": row["id"],
                "source_fact_public_id": row["public_id"],
                "occurred_at": occurred_at,
                "currency": (row["currency"] or "USD").upper(),
                "amount": amount,
                "source_run_id": row["public_id"],
            },
        )


def _backfill_reconciliation_cases() -> None:
    bind = op.get_bind()
    rows = bind.execute(
        sa.text(
            """
            SELECT a.id AS account_id, a.user_id,
                   l.id AS ledger_entry_id, l.public_id AS ledger_public_id
            FROM trading_accounts a
            JOIN account_ledger_entries l ON l.account_id = a.id
            WHERE l.posting_kind = 'LEGACY_UNRESOLVED'
            """
        )
    ).mappings().all()
    case_table = sa.table(
        "accounting_reconciliation_cases",
        sa.column("public_id", sa.String()),
        sa.column("user_id", sa.Integer()),
        sa.column("account_id", sa.Integer()),
        sa.column("original_ledger_entry_id", sa.Integer()),
        sa.column("status", sa.String()),
        sa.column("issue_code", sa.String()),
        sa.column("details_json", sa.JSON()),
    )
    if rows:
        op.bulk_insert(
            case_table,
            [
                {
                    "public_id": str(uuid.uuid4()),
                    "user_id": row["user_id"],
                    "account_id": row["account_id"],
                    "original_ledger_entry_id": row["ledger_entry_id"],
                    "status": "OPEN",
                    "issue_code": "LEGACY_UNRESOLVED_POSTINGS",
                    "details_json": {
                        "ledger_entry_public_id": row["ledger_public_id"],
                        "migration_revision": revision,
                    },
                }
                for row in rows
            ],
        )


def _quarantine_legacy_divergences() -> None:
    """Make every unsafe legacy row uniquely addressable before adding the key."""
    op.execute(
        """
        UPDATE account_ledger_entries
        SET source_fact_public_id = public_id,
            posting_kind = 'LEGACY_UNRESOLVED'
        WHERE id IN (
            SELECT id
            FROM (
                SELECT id,
                       COUNT(*) OVER (
                           PARTITION BY source_fact_public_id, posting_kind
                       ) AS duplicate_count
                FROM account_ledger_entries
            ) ranked
            WHERE ranked.duplicate_count > 1
        )
        """
    )
    op.execute(
        """
        UPDATE account_ledger_entries
        SET source_fact_public_id = public_id,
            posting_kind = 'LEGACY_UNRESOLVED'
        WHERE EXISTS (
            SELECT 1
            FROM trading_accounts a
            WHERE a.id = account_ledger_entries.account_id
              AND (
                  account_ledger_entries.user_id <> a.user_id
                  OR UPPER(TRIM(account_ledger_entries.currency))
                     <> UPPER(TRIM(a.currency))
                  OR ABS(
                      COALESCE(
                          account_ledger_entries.amount_account_ccy,
                          account_ledger_entries.amount
                      )
                      - ROUND(
                          account_ledger_entries.amount
                          * COALESCE(
                              account_ledger_entries.fx_rate_to_account_ccy,
                              1
                          ),
                          8
                      )
                  ) > 0.000000005
                  OR (
                      account_ledger_entries.position_id IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM trading_positions p
                          WHERE p.id = account_ledger_entries.position_id
                            AND p.user_id = a.user_id
                            AND p.account_id = a.id
                      )
                  )
                  OR (
                      account_ledger_entries.position_event_id IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM position_events e
                          WHERE e.id = account_ledger_entries.position_event_id
                            AND e.user_id = a.user_id
                            AND e.account_id = a.id
                            AND (
                                account_ledger_entries.position_id IS NULL
                                OR e.position_id
                                   = account_ledger_entries.position_id
                            )
                      )
                  )
                  OR (
                      account_ledger_entries.transaction_id IS NOT NULL
                      AND NOT EXISTS (
                          SELECT 1
                          FROM transactions t
                          WHERE t.id = account_ledger_entries.transaction_id
                            AND t.account_id = a.id
                      )
                  )
              )
        )
        """
    )


def upgrade() -> None:
    op.add_column(
        "trading_accounts",
        sa.Column(
            "accounting_health",
            sa.String(length=50),
            nullable=False,
            server_default="ACCOUNTING_HEALTHY",
        ),
    )
    op.add_column(
        "position_events",
        sa.Column(
            "sequence_no",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT id,
                   ROW_NUMBER() OVER (
                       PARTITION BY position_id
                       ORDER BY event_time, id
                   ) AS sequence_no
            FROM position_events
        )
        UPDATE position_events
        SET sequence_no = (
            SELECT ranked.sequence_no
            FROM ranked
            WHERE ranked.id = position_events.id
        )
        """
    )
    op.add_column(
        "account_ledger_entries",
        sa.Column("source_fact_public_id", sa.String(length=36), nullable=True),
    )
    op.add_column(
        "account_ledger_entries",
        sa.Column("posting_kind", sa.String(length=50), nullable=True),
    )
    with op.batch_alter_table("account_ledger_entries") as batch_op:
        batch_op.add_column(
            sa.Column("reverses_ledger_entry_id", sa.Integer(), nullable=True)
        )
        batch_op.create_foreign_key(
            "fk_account_ledger_reverses_entry",
            "account_ledger_entries",
            ["reverses_ledger_entry_id"],
            ["id"],
        )

    op.execute(
        """
        UPDATE account_ledger_entries
        SET source_fact_public_id = CASE
            WHEN source = 'OPENING_BALANCE' THEN (
                SELECT public_id FROM trading_accounts
                WHERE trading_accounts.id = account_ledger_entries.account_id
            )
            WHEN transaction_id IS NOT NULL THEN (
                SELECT public_id FROM transactions
                WHERE transactions.id = account_ledger_entries.transaction_id
            )
            WHEN position_event_id IS NOT NULL
                 AND entry_type <> 'REALIZED_PNL' THEN (
                SELECT public_id FROM position_events
                WHERE position_events.id = account_ledger_entries.position_event_id
            )
            ELSE public_id
        END
        """
    )
    op.execute(
        """
        UPDATE account_ledger_entries
        SET posting_kind = CASE
            WHEN source = 'OPENING_BALANCE' THEN 'OPENING_BALANCE'
            WHEN transaction_id IS NOT NULL AND entry_type = 'DEPOSIT' THEN 'DEPOSIT'
            WHEN transaction_id IS NOT NULL AND entry_type = 'WITHDRAWAL' THEN 'WITHDRAWAL'
            WHEN transaction_id IS NOT NULL AND entry_type = 'FEE' THEN 'ACCOUNT_FEE'
            WHEN transaction_id IS NOT NULL AND entry_type = 'CASH_ADJUSTMENT'
                THEN 'INTEREST'
            WHEN entry_type = 'DIVIDEND' AND amount >= 0
                THEN 'CASH_DIVIDEND_RECEIVED'
            WHEN entry_type = 'DIVIDEND' AND amount < 0
                THEN 'CASH_DIVIDEND_PAID_IN_LIEU'
            ELSE 'LEGACY_UNRESOLVED'
        END
        """
    )
    _quarantine_legacy_divergences()

    _backfill_opening_balances()

    op.create_table(
        "accounting_reconciliation_cases",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("original_ledger_entry_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("issue_code", sa.String(length=100), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=False),
        sa.Column("resolution_note", sa.Text(), nullable=True),
        sa.Column("resolved_by_user_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"]),
        sa.ForeignKeyConstraint(
            ["original_ledger_entry_id"],
            ["account_ledger_entries.id"],
        ),
        sa.ForeignKeyConstraint(["resolved_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_accounting_reconciliation_cases_public_id",
        "accounting_reconciliation_cases",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        "ix_accounting_reconciliation_account_status",
        "accounting_reconciliation_cases",
        ["account_id", "status"],
        unique=False,
    )

    op.execute(
        """
        UPDATE trading_accounts
        SET accounting_health = 'ACCOUNTING_RECONCILIATION_REQUIRED'
        WHERE EXISTS (
            SELECT 1
            FROM account_ledger_entries
            WHERE account_ledger_entries.account_id = trading_accounts.id
              AND account_ledger_entries.posting_kind = 'LEGACY_UNRESOLVED'
        )
        """
    )
    _backfill_reconciliation_cases()

    with op.batch_alter_table("account_ledger_entries") as batch_op:
        batch_op.alter_column(
            "source_fact_public_id",
            existing_type=sa.String(length=36),
            nullable=False,
        )
        batch_op.alter_column(
            "posting_kind",
            existing_type=sa.String(length=50),
            nullable=False,
        )
        batch_op.create_unique_constraint(
            "uq_account_ledger_source_fact_posting_kind",
            ["source_fact_public_id", "posting_kind"],
        )
    op.create_index(
        "ix_account_ledger_account_occurred_id",
        "account_ledger_entries",
        ["account_id", "occurred_at", "id"],
        unique=False,
    )
    _install_append_only_guard()


def downgrade() -> None:
    _drop_append_only_guard()
    op.drop_index(
        "ix_accounting_reconciliation_account_status",
        table_name="accounting_reconciliation_cases",
    )
    op.drop_index(
        "ix_accounting_reconciliation_cases_public_id",
        table_name="accounting_reconciliation_cases",
    )
    op.drop_table("accounting_reconciliation_cases")
    op.drop_index(
        "ix_account_ledger_account_occurred_id",
        table_name="account_ledger_entries",
    )
    with op.batch_alter_table("account_ledger_entries") as batch_op:
        batch_op.drop_constraint(
            "uq_account_ledger_source_fact_posting_kind",
            type_="unique",
        )
        batch_op.drop_constraint(
            "fk_account_ledger_reverses_entry",
            type_="foreignkey",
        )
        batch_op.drop_column("reverses_ledger_entry_id")
        batch_op.drop_column("posting_kind")
        batch_op.drop_column("source_fact_public_id")
    op.drop_column("position_events", "sequence_no")
    op.drop_column("trading_accounts", "accounting_health")
