"""user-facing read models and derived caches

Revision ID: 20260604_0004
Revises: 20260604_0003
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0004"
down_revision = "20260604_0003"
branch_labels = None
depends_on = None


def _schema(name: str) -> str | None:
    bind = op.get_bind()
    return name if bind.dialect.name == "postgresql" else None


def _table_ref(schema: str | None, table_name: str) -> str:
    return f"{schema}.{table_name}" if schema else table_name


def upgrade() -> None:
    content_schema = _schema("content")
    core_schema = _schema("core")
    derived_schema = _schema("derived")
    market_schema = _schema("market")
    reference_schema = _schema("reference")

    op.create_table(
        "evidence_items",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("kind", sa.String(length=64), nullable=False),
        sa.Column("source_name", sa.String(length=255), nullable=False),
        sa.Column("source_url_or_ref", sa.String(length=500), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("linked_tickers", sa.JSON(), nullable=False),
        sa.Column("confidence", sa.String(length=32), nullable=False, server_default="MEDIUM"),
        sa.Column("invalidates_if", sa.Text(), nullable=True),
        sa.Column("linked_object_public_id", sa.String(length=26), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=content_schema,
    )
    op.create_index("uq_evidence_items_public_id", "evidence_items", ["public_id"], unique=True, schema=content_schema)
    op.create_index(
        "idx_evidence_items_linked_object",
        "evidence_items",
        ["linked_object_public_id"],
        schema=content_schema,
    )

    op.create_table(
        "external_catalysts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("catalyst_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("evidence_public_id", sa.String(length=26), nullable=False),
        sa.Column("linked_object_public_id", sa.String(length=26), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=content_schema,
    )
    op.create_index(
        "uq_external_catalysts_public_id",
        "external_catalysts",
        ["public_id"],
        unique=True,
        schema=content_schema,
    )
    op.create_index(
        "idx_external_catalysts_evidence",
        "external_catalysts",
        ["evidence_public_id"],
        schema=content_schema,
    )
    op.create_index(
        "idx_external_catalysts_linked_object",
        "external_catalysts",
        ["linked_object_public_id"],
        schema=content_schema,
    )

    op.create_table(
        "narrative_signals",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("signal_type", sa.String(length=64), nullable=False),
        sa.Column("direction", sa.String(length=32), nullable=False),
        sa.Column("strength", sa.String(length=32), nullable=False),
        sa.Column("sample_size", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("time_window", sa.String(length=64), nullable=True),
        sa.Column("linked_evidence_public_ids", sa.JSON(), nullable=False),
        sa.Column("linked_object_public_id", sa.String(length=26), nullable=False),
        sa.Column("trust_meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=content_schema,
    )
    op.create_index(
        "uq_narrative_signals_public_id",
        "narrative_signals",
        ["public_id"],
        unique=True,
        schema=content_schema,
    )
    op.create_index(
        "idx_narrative_signals_linked_object",
        "narrative_signals",
        ["linked_object_public_id"],
        schema=content_schema,
    )

    op.create_table(
        "provider_symbol_mappings",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column(
            "asset_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(reference_schema, "asset_master")}.id'),
            nullable=True,
        ),
        sa.Column(
            "instrument_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(reference_schema, "trade_instruments")}.id'),
            nullable=True,
        ),
        sa.Column("provider_key", sa.String(length=100), nullable=False),
        sa.Column("provider_symbol", sa.String(length=100), nullable=False),
        sa.Column("provider_market", sa.String(length=50), nullable=True),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        schema=market_schema,
    )
    op.create_index(
        "uq_provider_symbol_mappings_public_id",
        "provider_symbol_mappings",
        ["public_id"],
        unique=True,
        schema=market_schema,
    )
    op.create_index(
        "idx_provider_symbol_mappings_provider_symbol",
        "provider_symbol_mappings",
        ["provider_key", "provider_symbol"],
        schema=market_schema,
    )

    op.create_table(
        "market_data_coverage",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column(
            "provider_symbol_mapping_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(market_schema, "provider_symbol_mappings")}.id'),
            nullable=False,
        ),
        sa.Column("capability", sa.String(length=64), nullable=False),
        sa.Column("quality_status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("first_seen_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_verified_at", sa.DateTime(timezone=True), nullable=True),
        schema=market_schema,
    )
    op.create_index(
        "uq_market_data_coverage_public_id",
        "market_data_coverage",
        ["public_id"],
        unique=True,
        schema=market_schema,
    )

    op.create_table(
        "dashboard_cache",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(core_schema, "users")}.id'),
            nullable=False,
        ),
        sa.Column("cache_key", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("freshness", sa.String(length=32), nullable=False, server_default="FRESH"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="DERIVED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "cache_key", name="uq_dashboard_cache_user_key"),
        schema=derived_schema,
    )
    op.create_index(
        "uq_dashboard_cache_public_id",
        "dashboard_cache",
        ["public_id"],
        unique=True,
        schema=derived_schema,
    )

    op.create_table(
        "position_metrics",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("position_public_id", sa.String(length=26), nullable=False),
        sa.Column("metric_key", sa.String(length=100), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("as_of", sa.DateTime(timezone=True), nullable=False),
        sa.Column("freshness", sa.String(length=32), nullable=False, server_default="FRESH"),
        sa.Column("source", sa.String(length=32), nullable=False, server_default="DERIVED"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("position_public_id", "metric_key", name="uq_position_metrics_position_key"),
        schema=derived_schema,
    )
    op.create_index(
        "uq_position_metrics_public_id",
        "position_metrics",
        ["public_id"],
        unique=True,
        schema=derived_schema,
    )
    op.create_index(
        "idx_position_metrics_position_public_id",
        "position_metrics",
        ["position_public_id"],
        schema=derived_schema,
    )


def downgrade() -> None:
    derived_schema = _schema("derived")
    market_schema = _schema("market")
    content_schema = _schema("content")

    op.drop_index(
        "idx_position_metrics_position_public_id",
        table_name="position_metrics",
        schema=derived_schema,
    )
    op.drop_index("uq_position_metrics_public_id", table_name="position_metrics", schema=derived_schema)
    op.drop_table("position_metrics", schema=derived_schema)
    op.drop_index("uq_dashboard_cache_public_id", table_name="dashboard_cache", schema=derived_schema)
    op.drop_table("dashboard_cache", schema=derived_schema)
    op.drop_index("uq_market_data_coverage_public_id", table_name="market_data_coverage", schema=market_schema)
    op.drop_table("market_data_coverage", schema=market_schema)
    op.drop_index(
        "idx_provider_symbol_mappings_provider_symbol",
        table_name="provider_symbol_mappings",
        schema=market_schema,
    )
    op.drop_index("uq_provider_symbol_mappings_public_id", table_name="provider_symbol_mappings", schema=market_schema)
    op.drop_table("provider_symbol_mappings", schema=market_schema)
    op.drop_index("idx_narrative_signals_linked_object", table_name="narrative_signals", schema=content_schema)
    op.drop_index("uq_narrative_signals_public_id", table_name="narrative_signals", schema=content_schema)
    op.drop_table("narrative_signals", schema=content_schema)
    op.drop_index("idx_external_catalysts_linked_object", table_name="external_catalysts", schema=content_schema)
    op.drop_index("idx_external_catalysts_evidence", table_name="external_catalysts", schema=content_schema)
    op.drop_index("uq_external_catalysts_public_id", table_name="external_catalysts", schema=content_schema)
    op.drop_table("external_catalysts", schema=content_schema)
    op.drop_index("idx_evidence_items_linked_object", table_name="evidence_items", schema=content_schema)
    op.drop_index("uq_evidence_items_public_id", table_name="evidence_items", schema=content_schema)
    op.drop_table("evidence_items", schema=content_schema)
