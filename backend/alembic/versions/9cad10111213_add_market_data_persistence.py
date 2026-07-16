"""add_market_data_persistence

Revision ID: 9cad10111213
Revises: 8b9cad101112
Create Date: 2026-07-15 16:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "9cad10111213"
down_revision = "8b9cad101112"
branch_labels = None
depends_on = None


_MARKET_TABLE_SPECS = {
    "provider_symbol_mappings": {
        "columns": {
            "id",
            "asset_id",
            "instrument_id",
            "provider_key",
            "provider_symbol",
            "provider_market",
            "capabilities_json",
            "quality_status",
            "first_seen_at",
            "last_verified_at",
            "created_at",
            "updated_at",
        },
        "primary_key": ("id",),
        "foreign_keys": {
            (("asset_id",), "asset_master", ("id",)): "CASCADE",
            (("instrument_id",), "trade_instruments", ("id",)): "CASCADE",
        },
        "unique_constraints": {
            "uq_provider_symbol_mappings_provider_symbol": (
                "provider_key",
                "provider_market",
                "provider_symbol",
            ),
        },
        "indexes": {
            "uq_provider_symbol_mappings_asset_provider_market": {
                "columns": ("asset_id", "provider_key", "provider_market"),
                "unique": True,
                "predicate": "instrument_idisnull",
            },
            "uq_provider_symbol_mappings_instrument_provider_market": {
                "columns": ("instrument_id", "provider_key", "provider_market"),
                "unique": True,
                "predicate": "instrument_idisnotnull",
            },
            "ix_provider_symbol_mappings_quality_verified": {
                "columns": ("quality_status", "last_verified_at"),
                "unique": False,
            },
        },
    },
    "latest_market_quotes": {
        "columns": {
            "id",
            "asset_id",
            "provider",
            "price",
            "previous_close",
            "open_price",
            "high_price",
            "low_price",
            "volume",
            "change_amount",
            "change_percent",
            "currency",
            "market_time",
            "received_at",
            "quality_status",
            "raw_payload",
            "created_at",
            "updated_at",
        },
        "primary_key": ("id",),
        "foreign_keys": {
            (("asset_id",), "asset_master", ("id",)): "CASCADE",
        },
        "unique_constraints": {
            "uq_latest_market_quotes_asset_provider": ("asset_id", "provider"),
        },
        "indexes": {
            "ix_latest_market_quotes_asset_received": {
                "columns": ("asset_id", "received_at"),
                "unique": False,
            },
            "ix_latest_market_quotes_provider_received": {
                "columns": ("provider", "received_at"),
                "unique": False,
            },
        },
    },
    "price_bars_daily": {
        "columns": {
            "id",
            "asset_id",
            "trading_date",
            "provider",
            "adjustment_mode",
            "open_price",
            "high_price",
            "low_price",
            "close_price",
            "adjusted_close",
            "volume",
            "currency",
            "received_at",
            "quality_status",
            "raw_payload",
            "created_at",
            "updated_at",
        },
        "primary_key": ("id",),
        "foreign_keys": {
            (("asset_id",), "asset_master", ("id",)): "CASCADE",
        },
        "unique_constraints": {
            "uq_price_bars_daily_asset_date_provider_adjustment": (
                "asset_id",
                "trading_date",
                "provider",
                "adjustment_mode",
            ),
        },
        "indexes": {
            "ix_price_bars_daily_asset_date": {
                "columns": ("asset_id", "trading_date"),
                "unique": False,
            },
            "ix_price_bars_daily_provider_date": {
                "columns": ("provider", "trading_date"),
                "unique": False,
            },
        },
    },
    "market_data_watermarks": {
        "columns": {
            "id",
            "asset_id",
            "data_type",
            "provider",
            "covered_from",
            "covered_to",
            "last_success_at",
            "last_error",
            "created_at",
            "updated_at",
        },
        "primary_key": ("id",),
        "foreign_keys": {
            (("asset_id",), "asset_master", ("id",)): "CASCADE",
        },
        "unique_constraints": {
            "uq_market_data_watermarks_asset_type_provider": (
                "asset_id",
                "data_type",
                "provider",
            ),
        },
        "indexes": {
            "ix_market_data_watermarks_provider_type_covered": {
                "columns": ("provider", "data_type", "covered_to"),
                "unique": False,
            },
            "ix_market_data_watermarks_last_success": {
                "columns": ("last_success_at",),
                "unique": False,
            },
        },
    },
}


def _normalized_predicate(value: object, *, table_name: str) -> str:
    normalized = str("" if value is None else value).lower()
    for token in ('"', "`", "[", "]", "(", ")", " ", "\t", "\n"):
        normalized = normalized.replace(token, "")
    return normalized.replace(f"{table_name.lower()}.", "")


def _index_predicate(index: dict, *, dialect_name: str, table_name: str) -> str:
    dialect_options = index.get("dialect_options") or {}
    value = dialect_options.get(f"{dialect_name}_where")
    if value is None:
        value = dialect_options.get("sqlite_where")
    if value is None:
        value = dialect_options.get("postgresql_where")
    return _normalized_predicate(value, table_name=table_name)


def _validate_existing_market_schema(inspector: sa.Inspector) -> None:
    problems: list[str] = []
    dialect_name = inspector.bind.dialect.name

    for table_name, spec in _MARKET_TABLE_SPECS.items():
        actual_columns = {column["name"] for column in inspector.get_columns(table_name)}
        missing_columns = sorted(spec["columns"] - actual_columns)
        if missing_columns:
            problems.append(
                f"{table_name}: missing columns {', '.join(missing_columns)}"
            )

        primary_key = inspector.get_pk_constraint(table_name) or {}
        actual_pk = tuple(primary_key.get("constrained_columns") or ())
        if actual_pk != spec["primary_key"]:
            problems.append(
                f"{table_name}: primary key is {actual_pk!r}, expected {spec['primary_key']!r}"
            )

        actual_foreign_keys = {}
        for foreign_key in inspector.get_foreign_keys(table_name):
            key = (
                tuple(foreign_key.get("constrained_columns") or ()),
                foreign_key.get("referred_table"),
                tuple(foreign_key.get("referred_columns") or ()),
            )
            options = foreign_key.get("options") or {}
            actual_foreign_keys[key] = str(options.get("ondelete") or "").upper()
        for key, expected_ondelete in spec["foreign_keys"].items():
            if key not in actual_foreign_keys:
                problems.append(f"{table_name}: missing foreign key {key!r}")
            elif actual_foreign_keys[key] != expected_ondelete:
                problems.append(
                    f"{table_name}: foreign key {key!r} has ON DELETE "
                    f"{actual_foreign_keys[key] or 'NO ACTION'}, expected {expected_ondelete}"
                )

        actual_uniques = {
            constraint.get("name"): tuple(constraint.get("column_names") or ())
            for constraint in inspector.get_unique_constraints(table_name)
        }
        for constraint_name, expected_columns in spec["unique_constraints"].items():
            if constraint_name not in actual_uniques:
                problems.append(
                    f"{table_name}: missing unique constraint {constraint_name}"
                )
            elif actual_uniques[constraint_name] != expected_columns:
                problems.append(
                    f"{table_name}: unique constraint {constraint_name} has columns "
                    f"{actual_uniques[constraint_name]!r}, expected {expected_columns!r}"
                )

        actual_indexes = {
            index.get("name"): index for index in inspector.get_indexes(table_name)
        }
        for index_name, expected_index in spec["indexes"].items():
            actual_index = actual_indexes.get(index_name)
            if actual_index is None:
                problems.append(f"{table_name}: missing index {index_name}")
                continue
            actual_index_columns = tuple(actual_index.get("column_names") or ())
            if actual_index_columns != expected_index["columns"]:
                problems.append(
                    f"{table_name}: index {index_name} has columns "
                    f"{actual_index_columns!r}, expected {expected_index['columns']!r}"
                )
            if bool(actual_index.get("unique")) != expected_index["unique"]:
                problems.append(
                    f"{table_name}: index {index_name} has incorrect unique flag"
                )
            expected_predicate = expected_index.get("predicate")
            if expected_predicate is not None:
                actual_predicate = _index_predicate(
                    actual_index,
                    dialect_name=dialect_name,
                    table_name=table_name,
                )
                if actual_predicate != expected_predicate:
                    problems.append(
                        f"{table_name}: index {index_name} has predicate "
                        f"{actual_predicate!r}, expected {expected_predicate!r}"
                    )

    if problems:
        raise RuntimeError(
            "Existing market-data schema is incompatible and cannot be adopted:\n- "
            + "\n- ".join(problems)
        )


def upgrade() -> None:
    # Development can run Base.metadata.create_all before Alembic after a hot
    # reload. Adopt that complete schema instead of failing on duplicate tables.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())
    expected_tables = set(_MARKET_TABLE_SPECS)
    existing_market_tables = existing_tables.intersection(expected_tables)
    if existing_market_tables:
        if existing_market_tables != expected_tables:
            missing = sorted(expected_tables - existing_market_tables)
            raise RuntimeError(
                "Partial market-data schema already exists; missing tables: "
                + ", ".join(missing)
            )
        _validate_existing_market_schema(inspector)
        return

    op.create_table(
        "provider_symbol_mappings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("instrument_id", sa.Integer(), nullable=True),
        sa.Column("provider_key", sa.String(length=50), nullable=False),
        sa.Column("provider_symbol", sa.String(length=150), nullable=False),
        sa.Column("provider_market", sa.String(length=50), nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("quality_status", sa.String(length=30), nullable=False),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["asset_master.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["instrument_id"], ["trade_instruments.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "provider_key",
            "provider_market",
            "provider_symbol",
            name="uq_provider_symbol_mappings_provider_symbol",
        ),
    )
    op.create_index(
        "uq_provider_symbol_mappings_asset_provider_market",
        "provider_symbol_mappings",
        ["asset_id", "provider_key", "provider_market"],
        unique=True,
        sqlite_where=sa.text("instrument_id IS NULL"),
        postgresql_where=sa.text("instrument_id IS NULL"),
    )
    op.create_index(
        "uq_provider_symbol_mappings_instrument_provider_market",
        "provider_symbol_mappings",
        ["instrument_id", "provider_key", "provider_market"],
        unique=True,
        sqlite_where=sa.text("instrument_id IS NOT NULL"),
        postgresql_where=sa.text("instrument_id IS NOT NULL"),
    )
    op.create_index(
        "ix_provider_symbol_mappings_quality_verified",
        "provider_symbol_mappings",
        ["quality_status", "last_verified_at"],
        unique=False,
    )

    op.create_table(
        "latest_market_quotes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("previous_close", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("open_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("high_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("low_price", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("volume", sa.Numeric(precision=30, scale=8), nullable=True),
        sa.Column("change_amount", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("change_percent", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("market_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quality_status", sa.String(length=30), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["asset_master.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("asset_id", "provider", name="uq_latest_market_quotes_asset_provider"),
    )
    op.create_index(
        "ix_latest_market_quotes_asset_received",
        "latest_market_quotes",
        ["asset_id", "received_at"],
        unique=False,
    )
    op.create_index(
        "ix_latest_market_quotes_provider_received",
        "latest_market_quotes",
        ["provider", "received_at"],
        unique=False,
    )

    op.create_table(
        "price_bars_daily",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("trading_date", sa.Date(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("adjustment_mode", sa.String(length=20), nullable=False),
        sa.Column("open_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("high_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("low_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("close_price", sa.Numeric(precision=20, scale=8), nullable=False),
        sa.Column("adjusted_close", sa.Numeric(precision=20, scale=8), nullable=True),
        sa.Column("volume", sa.Numeric(precision=30, scale=8), nullable=True),
        sa.Column("currency", sa.String(length=10), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("quality_status", sa.String(length=30), nullable=False),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["asset_master.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_id",
            "trading_date",
            "provider",
            "adjustment_mode",
            name="uq_price_bars_daily_asset_date_provider_adjustment",
        ),
    )
    op.create_index(
        "ix_price_bars_daily_asset_date",
        "price_bars_daily",
        ["asset_id", "trading_date"],
        unique=False,
    )
    op.create_index(
        "ix_price_bars_daily_provider_date",
        "price_bars_daily",
        ["provider", "trading_date"],
        unique=False,
    )

    op.create_table(
        "market_data_watermarks",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("asset_id", sa.Integer(), nullable=False),
        sa.Column("data_type", sa.String(length=40), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("covered_from", sa.Date(), nullable=True),
        sa.Column("covered_to", sa.Date(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("(CURRENT_TIMESTAMP)"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["asset_id"], ["asset_master.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "asset_id",
            "data_type",
            "provider",
            name="uq_market_data_watermarks_asset_type_provider",
        ),
    )
    op.create_index(
        "ix_market_data_watermarks_provider_type_covered",
        "market_data_watermarks",
        ["provider", "data_type", "covered_to"],
        unique=False,
    )
    op.create_index(
        "ix_market_data_watermarks_last_success",
        "market_data_watermarks",
        ["last_success_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_market_data_watermarks_last_success", table_name="market_data_watermarks")
    op.drop_index(
        "ix_market_data_watermarks_provider_type_covered",
        table_name="market_data_watermarks",
    )
    op.drop_table("market_data_watermarks")

    op.drop_index("ix_price_bars_daily_provider_date", table_name="price_bars_daily")
    op.drop_index("ix_price_bars_daily_asset_date", table_name="price_bars_daily")
    op.drop_table("price_bars_daily")

    op.drop_index("ix_latest_market_quotes_provider_received", table_name="latest_market_quotes")
    op.drop_index("ix_latest_market_quotes_asset_received", table_name="latest_market_quotes")
    op.drop_table("latest_market_quotes")

    op.drop_index(
        "ix_provider_symbol_mappings_quality_verified",
        table_name="provider_symbol_mappings",
    )
    op.drop_index(
        "uq_provider_symbol_mappings_instrument_provider_market",
        table_name="provider_symbol_mappings",
    )
    op.drop_index(
        "uq_provider_symbol_mappings_asset_provider_market",
        table_name="provider_symbol_mappings",
    )
    op.drop_table("provider_symbol_mappings")
