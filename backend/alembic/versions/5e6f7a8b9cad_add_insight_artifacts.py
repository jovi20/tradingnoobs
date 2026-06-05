"""add_insight_artifacts

Revision ID: 5e6f7a8b9cad
Revises: 4d5e6f7a8b9c
Create Date: 2026-06-05 16:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "5e6f7a8b9cad"
down_revision = "4d5e6f7a8b9c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "insight_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("run_type", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=True),
        sa.Column("input_refs", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_insight_runs_id"), "insight_runs", ["id"], unique=False)
    op.create_index(op.f("ix_insight_runs_public_id"), "insight_runs", ["public_id"], unique=True)
    op.create_index(op.f("ix_insight_runs_user_id"), "insight_runs", ["user_id"], unique=False)

    op.create_table(
        "insight_artifacts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("insight_run_id", sa.Integer(), nullable=False),
        sa.Column("artifact_type", sa.String(length=64), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("summary", sa.Text(), nullable=False),
        sa.Column("content_markdown", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("evidence_refs", sa.JSON(), nullable=False),
        sa.Column("chart_schema", sa.JSON(), nullable=True),
        sa.Column("trust_meta", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["insight_run_id"], ["insight_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_insight_artifacts_id"), "insight_artifacts", ["id"], unique=False)
    op.create_index(op.f("ix_insight_artifacts_public_id"), "insight_artifacts", ["public_id"], unique=True)
    op.create_index(op.f("ix_insight_artifacts_insight_run_id"), "insight_artifacts", ["insight_run_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_insight_artifacts_insight_run_id"), table_name="insight_artifacts")
    op.drop_index(op.f("ix_insight_artifacts_public_id"), table_name="insight_artifacts")
    op.drop_index(op.f("ix_insight_artifacts_id"), table_name="insight_artifacts")
    op.drop_table("insight_artifacts")

    op.drop_index(op.f("ix_insight_runs_user_id"), table_name="insight_runs")
    op.drop_index(op.f("ix_insight_runs_public_id"), table_name="insight_runs")
    op.drop_index(op.f("ix_insight_runs_id"), table_name="insight_runs")
    op.drop_table("insight_runs")
