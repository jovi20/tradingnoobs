"""trading truth model tables

Revision ID: 20260604_0002
Revises: 20260604_0001
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0002"
down_revision = "20260604_0001"
branch_labels = None
depends_on = None


def _schema(name: str) -> str | None:
    bind = op.get_bind()
    return name if bind.dialect.name == "postgresql" else None


def _table_ref(schema: str | None, table_name: str) -> str:
    return f"{schema}.{table_name}" if schema else table_name


def upgrade() -> None:
    reference_schema = _schema("reference")
    core_schema = _schema("core")

    op.create_table(
        "asset_master",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=True),
        sa.Column("asset_class", sa.String(length=50), nullable=False, server_default="EQUITY"),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema=reference_schema,
    )
    op.create_index("uq_asset_master_public_id", "asset_master", ["public_id"], unique=True, schema=reference_schema)
    op.create_index("uq_asset_master_symbol", "asset_master", ["symbol"], unique=True, schema=reference_schema)

    op.create_table(
        "trade_instruments",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column(
            "asset_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(reference_schema, "asset_master")}.id'),
            nullable=False,
        ),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("venue", sa.String(length=50), nullable=False, server_default="UNKNOWN"),
        sa.Column("instrument_type", sa.String(length=50), nullable=False, server_default="EQUITY"),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema=reference_schema,
    )
    op.create_index(
        "uq_trade_instruments_public_id",
        "trade_instruments",
        ["public_id"],
        unique=True,
        schema=reference_schema,
    )
    op.create_index(
        "idx_trade_instruments_symbol_venue",
        "trade_instruments",
        ["symbol", "venue"],
        schema=reference_schema,
    )

    op.create_table(
        "trading_positions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "instrument_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(reference_schema, "trade_instruments")}.id'),
            nullable=False,
        ),
        sa.Column("side", sa.String(length=10), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="OPEN"),
        sa.Column("cost_method", sa.String(length=20), nullable=False, server_default="FIFO"),
        sa.Column("quantity_opened", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("quantity_closed", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("realized_pnl_gross", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("realized_pnl_net", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("fifo_lots", sa.JSON(), nullable=False),
        sa.Column("thesis", sa.Text(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema=core_schema,
    )
    op.create_index(
        "uq_trading_positions_public_id",
        "trading_positions",
        ["public_id"],
        unique=True,
        schema=core_schema,
    )
    op.create_index(
        "idx_trading_positions_user_status",
        "trading_positions",
        ["user_id", "status"],
        schema=core_schema,
    )
    op.create_index(
        "idx_trading_positions_account_status",
        "trading_positions",
        ["account_id", "status"],
        schema=core_schema,
    )

    op.create_table(
        "position_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column(
            "position_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(core_schema, "trading_positions")}.id'),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("price", sa.Numeric(20, 8), nullable=False),
        sa.Column("fee", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("realized_pnl_gross", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("realized_pnl_net", sa.Numeric(20, 8), nullable=False, server_default="0"),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=core_schema,
    )
    op.create_index("uq_position_events_public_id", "position_events", ["public_id"], unique=True, schema=core_schema)
    op.create_index("idx_position_events_event_time", "position_events", ["event_time"], schema=core_schema)

    op.create_table(
        "account_ledger_entries",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "related_position_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(core_schema, "trading_positions")}.id'),
            nullable=True,
        ),
        sa.Column("entry_type", sa.String(length=32), nullable=False),
        sa.Column("amount", sa.Numeric(20, 8), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False, server_default="USD"),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=core_schema,
    )
    op.create_index(
        "uq_account_ledger_entries_public_id",
        "account_ledger_entries",
        ["public_id"],
        unique=True,
        schema=core_schema,
    )
    op.create_index(
        "idx_account_ledger_entries_account_time",
        "account_ledger_entries",
        ["account_id", "occurred_at"],
        schema=core_schema,
    )


def downgrade() -> None:
    core_schema = _schema("core")
    reference_schema = _schema("reference")

    op.drop_index(
        "idx_account_ledger_entries_account_time",
        table_name="account_ledger_entries",
        schema=core_schema,
    )
    op.drop_index("uq_account_ledger_entries_public_id", table_name="account_ledger_entries", schema=core_schema)
    op.drop_table("account_ledger_entries", schema=core_schema)
    op.drop_index("idx_position_events_event_time", table_name="position_events", schema=core_schema)
    op.drop_index("uq_position_events_public_id", table_name="position_events", schema=core_schema)
    op.drop_table("position_events", schema=core_schema)
    op.drop_index("idx_trading_positions_account_status", table_name="trading_positions", schema=core_schema)
    op.drop_index("idx_trading_positions_user_status", table_name="trading_positions", schema=core_schema)
    op.drop_index("uq_trading_positions_public_id", table_name="trading_positions", schema=core_schema)
    op.drop_table("trading_positions", schema=core_schema)
    op.drop_index("idx_trade_instruments_symbol_venue", table_name="trade_instruments", schema=reference_schema)
    op.drop_index("uq_trade_instruments_public_id", table_name="trade_instruments", schema=reference_schema)
    op.drop_table("trade_instruments", schema=reference_schema)
    op.drop_index("uq_asset_master_symbol", table_name="asset_master", schema=reference_schema)
    op.drop_index("uq_asset_master_public_id", table_name="asset_master", schema=reference_schema)
    op.drop_table("asset_master", schema=reference_schema)
