"""task7 ai chart audit contracts

Revision ID: 20260604_0005
Revises: 20260604_0004
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0005"
down_revision = "20260604_0004"
branch_labels = None
depends_on = None


def _schema(name: str) -> str | None:
    bind = op.get_bind()
    return name if bind.dialect.name == "postgresql" else None


def _table_ref(schema: str | None, table_name: str) -> str:
    return f"{schema}.{table_name}" if schema else table_name


def upgrade() -> None:
    ai_schema = _schema("ai")
    core_schema = _schema("core")

    op.create_table(
        "insight_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(core_schema, "users")}.id'),
            nullable=False,
        ),
        sa.Column("run_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="RUNNING"),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column("input_refs", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=ai_schema,
    )
    op.create_index("uq_insight_runs_public_id", "insight_runs", ["public_id"], unique=True, schema=ai_schema)
    op.create_index("idx_insight_runs_user_id", "insight_runs", ["user_id"], schema=ai_schema)

    op.create_table(
        "insight_artifacts",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column(
            "insight_run_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(ai_schema, "insight_runs")}.id'),
            nullable=False,
        ),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("chart_schema", sa.JSON(), nullable=True),
        sa.Column("trust_meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=ai_schema,
    )
    op.create_index(
        "uq_insight_artifacts_public_id",
        "insight_artifacts",
        ["public_id"],
        unique=True,
        schema=ai_schema,
    )
    op.create_index(
        "idx_insight_artifacts_run_id",
        "insight_artifacts",
        ["insight_run_id"],
        schema=ai_schema,
    )


def downgrade() -> None:
    ai_schema = _schema("ai")

    op.drop_index("idx_insight_artifacts_run_id", table_name="insight_artifacts", schema=ai_schema)
    op.drop_index("uq_insight_artifacts_public_id", table_name="insight_artifacts", schema=ai_schema)
    op.drop_table("insight_artifacts", schema=ai_schema)
    op.drop_index("idx_insight_runs_user_id", table_name="insight_runs", schema=ai_schema)
    op.drop_index("uq_insight_runs_public_id", table_name="insight_runs", schema=ai_schema)
    op.drop_table("insight_runs", schema=ai_schema)
