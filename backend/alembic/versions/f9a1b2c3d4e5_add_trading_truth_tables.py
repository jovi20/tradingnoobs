"""add_trading_truth_tables

Revision ID: f9a1b2c3d4e5
Revises: e6b7f2a4c3d1
Create Date: 2026-04-15 10:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f9a1b2c3d4e5"
down_revision = "e6b7f2a4c3d1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "asset_master",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("canonical_code", sa.String(length=100), nullable=False),
        sa.Column("display_symbol", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("asset_type", sa.String(length=50), nullable=False),
        sa.Column("quote_currency", sa.String(length=10), nullable=True),
        sa.Column("country_code", sa.String(length=10), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("sector", sa.String(length=100), nullable=True),
        sa.Column("industry", sa.String(length=100), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_asset_master_id"), "asset_master", ["id"], unique=False)
    op.create_index(op.f("ix_asset_master_public_id"), "asset_master", ["public_id"], unique=True)
    op.create_index(op.f("ix_asset_master_canonical_code"), "asset_master", ["canonical_code"], unique=True)

    op.create_table(
        "trade_instruments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("instrument_type", sa.Enum("SPOT", "EQUITY_OPTION", name="tradeinstrumenttype"), nullable=False),
        sa.Column("display_name", sa.String(length=150), nullable=False),
        sa.Column("contract_symbol", sa.String(length=100), nullable=False),
        sa.Column("option_type", sa.String(length=20), nullable=True),
        sa.Column("strike_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("expiration_date", sa.Date(), nullable=True),
        sa.Column("multiplier", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("settlement_type", sa.String(length=20), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["asset_id"], ["asset_master.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trade_instruments_id"), "trade_instruments", ["id"], unique=False)
    op.create_index(op.f("ix_trade_instruments_public_id"), "trade_instruments", ["public_id"], unique=True)

    op.create_table(
        "trading_positions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column("strategy_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.Enum("OPEN", "CLOSED", "ARCHIVED", "ERROR", name="tradingpositionstatus"), nullable=False),
        sa.Column("side", sa.Enum("LONG", "SHORT", name="tradingpositionside"), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("opening_event_id", sa.Integer(), nullable=True),
        sa.Column("closing_event_id", sa.Integer(), nullable=True),
        sa.Column("base_currency", sa.String(length=10), nullable=False),
        sa.Column("cost_basis_method", sa.String(length=20), nullable=False),
        sa.Column("quantity_opened", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("quantity_closed", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("avg_open_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("avg_close_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("realized_pnl_gross", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("realized_pnl_net", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("total_fees", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("holding_period_seconds", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"]),
        sa.ForeignKeyConstraint(["instrument_id"], ["trade_instruments.id"]),
        sa.ForeignKeyConstraint(["strategy_id"], ["strategies.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_trading_positions_id"), "trading_positions", ["id"], unique=False)
    op.create_index(op.f("ix_trading_positions_public_id"), "trading_positions", ["public_id"], unique=True)

    op.create_table(
        "position_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("position_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=False),
        sa.Column(
            "event_type",
            sa.Enum(
                "OPEN",
                "ADD",
                "REDUCE",
                "CLOSE",
                "DIVIDEND",
                "FEE",
                "CASH_ADJUSTMENT",
                "STOCK_SPLIT",
                "TRANSFER_IN",
                "TRANSFER_OUT",
                "OPTION_EXERCISE",
                "OPTION_ASSIGNMENT",
                "OPTION_EXPIRY",
                "REVERSAL",
                "MANUAL_ADJUSTMENT",
                name="positioneventtype",
            ),
            nullable=False,
        ),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("side_effect", sa.String(length=20), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("gross_amount", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("fee_amount", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("fee_currency", sa.String(length=10), nullable=True),
        sa.Column("fx_rate_to_account_ccy", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("realized_pnl_gross", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("realized_pnl_net", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("broker_exec_id", sa.String(length=255), nullable=True),
        sa.Column("external_order_id", sa.String(length=255), nullable=True),
        sa.Column("input_source", sa.String(length=50), nullable=True),
        sa.Column("source_run_id", sa.String(length=100), nullable=True),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("emotion", sa.String(length=50), nullable=True),
        sa.Column("confidence", sa.Integer(), nullable=True),
        sa.Column("thesis", sa.Text(), nullable=True),
        sa.Column("edge_source", sa.Text(), nullable=True),
        sa.Column("disconfirming_evidence", sa.Text(), nullable=True),
        sa.Column("invalidation_rule", sa.Text(), nullable=True),
        sa.Column("expected_holding_period", sa.String(length=100), nullable=True),
        sa.Column("planned_exit_rule", sa.Text(), nullable=True),
        sa.Column("sizing_rationale", sa.Text(), nullable=True),
        sa.Column("checklist_snapshot", sa.JSON(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("is_adjustment", sa.Boolean(), nullable=False),
        sa.Column("reverses_event_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"]),
        sa.ForeignKeyConstraint(["instrument_id"], ["trade_instruments.id"]),
        sa.ForeignKeyConstraint(["position_id"], ["trading_positions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_position_events_id"), "position_events", ["id"], unique=False)
    op.create_index(op.f("ix_position_events_public_id"), "position_events", ["public_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_position_events_public_id"), table_name="position_events")
    op.drop_index(op.f("ix_position_events_id"), table_name="position_events")
    op.drop_table("position_events")

    op.drop_index(op.f("ix_trading_positions_public_id"), table_name="trading_positions")
    op.drop_index(op.f("ix_trading_positions_id"), table_name="trading_positions")
    op.drop_table("trading_positions")

    op.drop_index(op.f("ix_trade_instruments_public_id"), table_name="trade_instruments")
    op.drop_index(op.f("ix_trade_instruments_id"), table_name="trade_instruments")
    op.drop_table("trade_instruments")

    op.drop_index(op.f("ix_asset_master_canonical_code"), table_name="asset_master")
    op.drop_index(op.f("ix_asset_master_public_id"), table_name="asset_master")
    op.drop_index(op.f("ix_asset_master_id"), table_name="asset_master")
    op.drop_table("asset_master")
