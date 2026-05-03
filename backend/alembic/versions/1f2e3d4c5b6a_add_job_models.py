"""add_job_models

Revision ID: 1f2e3d4c5b6a
Revises: b7e2a4c5d6f8
Create Date: 2026-05-03 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "1f2e3d4c5b6a"
down_revision = "b7e2a4c5d6f8"
branch_labels = None
depends_on = None


job_run_status = sa.Enum(
    "QUEUED",
    "RUNNING",
    "SUCCEEDED",
    "FAILED",
    "RETRYING",
    "CANCELLED",
    name="jobrunstatus",
)

job_run_event_type = sa.Enum(
    "STATUS_CHANGED",
    "ATTEMPT_STARTED",
    "ATTEMPT_FAILED",
    "RETRY_SCHEDULED",
    "LOG",
    "CANCELLED",
    name="jobruneventtype",
)


def upgrade() -> None:
    op.create_table(
        "job_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("display_name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("queue_name", sa.String(length=80), nullable=False),
        sa.Column("retry_policy", sa.JSON(), nullable=True),
        sa.Column("timeout_seconds", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_definitions_id"), "job_definitions", ["id"], unique=False)
    op.create_index(op.f("ix_job_definitions_key"), "job_definitions", ["key"], unique=True)
    op.create_index(op.f("ix_job_definitions_public_id"), "job_definitions", ["public_id"], unique=True)

    op.create_table(
        "job_runs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("job_definition_id", sa.Integer(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=255), nullable=True),
        sa.Column("status", job_run_status, nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("result", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("queue_name", sa.String(length=80), nullable=False),
        sa.Column("locked_by", sa.String(length=120), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("next_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_definition_id"], ["job_definitions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_runs_id"), "job_runs", ["id"], unique=False)
    op.create_index(op.f("ix_job_runs_idempotency_key"), "job_runs", ["idempotency_key"], unique=False)
    op.create_index(op.f("ix_job_runs_public_id"), "job_runs", ["public_id"], unique=True)
    op.create_index(op.f("ix_job_runs_status"), "job_runs", ["status"], unique=False)
    op.create_index("ix_job_runs_status_next_run", "job_runs", ["status", "next_run_at"], unique=False)
    op.create_index("ix_job_runs_user_created", "job_runs", ["user_id", "created_at"], unique=False)

    op.create_table(
        "job_run_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("job_run_id", sa.Integer(), nullable=False),
        sa.Column("event_type", job_run_event_type, nullable=False),
        sa.Column("from_status", job_run_status, nullable=True),
        sa.Column("to_status", job_run_status, nullable=True),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["job_run_id"], ["job_runs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_job_run_events_id"), "job_run_events", ["id"], unique=False)
    op.create_index(op.f("ix_job_run_events_public_id"), "job_run_events", ["public_id"], unique=True)

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("scope", sa.String(length=120), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("request_hash", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=40), nullable=False),
        sa.Column("response_json", sa.JSON(), nullable=True),
        sa.Column("job_run_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["job_run_id"], ["job_runs.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("scope", "key", name="uq_idempotency_keys_scope_key"),
    )
    op.create_index(op.f("ix_idempotency_keys_id"), "idempotency_keys", ["id"], unique=False)
    op.create_index(op.f("ix_idempotency_keys_public_id"), "idempotency_keys", ["public_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_idempotency_keys_public_id"), table_name="idempotency_keys")
    op.drop_index(op.f("ix_idempotency_keys_id"), table_name="idempotency_keys")
    op.drop_table("idempotency_keys")

    op.drop_index(op.f("ix_job_run_events_public_id"), table_name="job_run_events")
    op.drop_index(op.f("ix_job_run_events_id"), table_name="job_run_events")
    op.drop_table("job_run_events")

    op.drop_index("ix_job_runs_user_created", table_name="job_runs")
    op.drop_index("ix_job_runs_status_next_run", table_name="job_runs")
    op.drop_index(op.f("ix_job_runs_status"), table_name="job_runs")
    op.drop_index(op.f("ix_job_runs_public_id"), table_name="job_runs")
    op.drop_index(op.f("ix_job_runs_idempotency_key"), table_name="job_runs")
    op.drop_index(op.f("ix_job_runs_id"), table_name="job_runs")
    op.drop_table("job_runs")

    op.drop_index(op.f("ix_job_definitions_public_id"), table_name="job_definitions")
    op.drop_index(op.f("ix_job_definitions_key"), table_name="job_definitions")
    op.drop_index(op.f("ix_job_definitions_id"), table_name="job_definitions")
    op.drop_table("job_definitions")
