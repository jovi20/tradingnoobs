"""add_broker_trade_sync_tables

Revision ID: 8b9cad101112
Revises: 7a8b9cad1011
Create Date: 2026-07-08 00:40:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "8b9cad101112"
down_revision = "7a8b9cad1011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broker_sync_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("market_type", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("requested_start_date", sa.Date(), nullable=True),
        sa.Column("requested_end_date", sa.Date(), nullable=True),
        sa.Column("records_fetched", sa.Integer(), nullable=False),
        sa.Column("records_inserted", sa.Integer(), nullable=False),
        sa.Column("records_skipped", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_broker_sync_runs_id"), "broker_sync_runs", ["id"], unique=False)
    op.create_index(op.f("ix_broker_sync_runs_public_id"), "broker_sync_runs", ["public_id"], unique=True)
    op.create_index(
        "ix_broker_sync_runs_user_provider_created",
        "broker_sync_runs",
        ["user_id", "provider", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_broker_sync_runs_status_created",
        "broker_sync_runs",
        ["status", "created_at"],
        unique=False,
    )

    op.create_table(
        "broker_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("sync_run_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("market_type", sa.String(length=50), nullable=True),
        sa.Column("account_ref", sa.String(length=100), nullable=True),
        sa.Column("symbol", sa.String(length=100), nullable=False),
        sa.Column("side", sa.String(length=20), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("trade_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("commission", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("commission_currency", sa.String(length=10), nullable=True),
        sa.Column("external_trade_id", sa.String(length=255), nullable=False),
        sa.Column("external_order_id", sa.String(length=255), nullable=True),
        sa.Column("idempotency_key", sa.String(length=500), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("import_status", sa.String(length=30), nullable=False),
        sa.Column("position_event_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["position_event_id"], ["position_events.id"]),
        sa.ForeignKeyConstraint(["sync_run_id"], ["broker_sync_runs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("idempotency_key", name="uq_broker_executions_idempotency_key"),
    )
    op.create_index(op.f("ix_broker_executions_id"), "broker_executions", ["id"], unique=False)
    op.create_index(op.f("ix_broker_executions_public_id"), "broker_executions", ["public_id"], unique=True)
    op.create_index(
        "ix_broker_executions_user_provider_time",
        "broker_executions",
        ["user_id", "provider", "trade_time"],
        unique=False,
    )
    op.create_index(
        "ix_broker_executions_symbol_time",
        "broker_executions",
        ["symbol", "trade_time"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_broker_executions_symbol_time", table_name="broker_executions")
    op.drop_index("ix_broker_executions_user_provider_time", table_name="broker_executions")
    op.drop_index(op.f("ix_broker_executions_public_id"), table_name="broker_executions")
    op.drop_index(op.f("ix_broker_executions_id"), table_name="broker_executions")
    op.drop_table("broker_executions")
    op.drop_index("ix_broker_sync_runs_status_created", table_name="broker_sync_runs")
    op.drop_index("ix_broker_sync_runs_user_provider_created", table_name="broker_sync_runs")
    op.drop_index(op.f("ix_broker_sync_runs_public_id"), table_name="broker_sync_runs")
    op.drop_index(op.f("ix_broker_sync_runs_id"), table_name="broker_sync_runs")
    op.drop_table("broker_sync_runs")
