"""trading task3 completion fields and job model

Revision ID: 20260604_0003
Revises: 20260604_0002
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0003"
down_revision = "20260604_0002"
branch_labels = None
depends_on = None


def _schema(name: str) -> str | None:
    bind = op.get_bind()
    return name if bind.dialect.name == "postgresql" else None


def _table_ref(schema: str | None, table_name: str) -> str:
    return f"{schema}.{table_name}" if schema else table_name


def upgrade() -> None:
    core_schema = _schema("core")
    audit_schema = _schema("audit")

    op.add_column("position_events", sa.Column("thesis", sa.Text(), nullable=True), schema=core_schema)
    op.add_column("position_events", sa.Column("edge_source", sa.String(length=100), nullable=True), schema=core_schema)
    op.add_column("position_events", sa.Column("disconfirming_evidence", sa.Text(), nullable=True), schema=core_schema)
    op.add_column("position_events", sa.Column("invalidation_rule", sa.Text(), nullable=True), schema=core_schema)
    op.add_column("position_events", sa.Column("expected_holding_period", sa.String(length=100), nullable=True), schema=core_schema)
    op.add_column("position_events", sa.Column("planned_exit_rule", sa.Text(), nullable=True), schema=core_schema)
    op.add_column("position_events", sa.Column("sizing_rationale", sa.Text(), nullable=True), schema=core_schema)
    op.add_column("position_events", sa.Column("checklist_snapshot", sa.JSON(), nullable=True), schema=core_schema)
    op.add_column(
        "account_ledger_entries",
        sa.Column("related_position_event_id", sa.BigInteger(), nullable=True),
        schema=core_schema,
    )
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.create_foreign_key(
            "fk_account_ledger_entries_position_event",
            "account_ledger_entries",
            "position_events",
            ["related_position_event_id"],
            ["id"],
            source_schema=core_schema,
            referent_schema=core_schema,
        )

    op.create_table(
        "job_definitions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("job_key", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("queue_name", sa.String(length=100), nullable=False, server_default="default"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False, server_default="300"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=audit_schema,
    )
    op.create_index("uq_job_definitions_public_id", "job_definitions", ["public_id"], unique=True, schema=audit_schema)
    op.create_index("uq_job_definitions_job_key", "job_definitions", ["job_key"], unique=True, schema=audit_schema)

    op.create_table(
        "idempotency_keys",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("scope", sa.String(length=100), nullable=False),
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="IN_PROGRESS"),
        sa.Column("request_hash", sa.String(length=128), nullable=True),
        sa.Column("response_payload", sa.JSON(), nullable=True),
        sa.Column("locked_resource", sa.String(length=255), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("scope", "key", name="uq_idempotency_keys_scope_key"),
        schema=audit_schema,
    )
    op.create_index("uq_idempotency_keys_public_id", "idempotency_keys", ["public_id"], unique=True, schema=audit_schema)
    op.create_index("idx_idempotency_keys_locked_resource", "idempotency_keys", ["locked_resource"], schema=audit_schema)

    op.create_table(
        "job_runs",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column(
            "job_definition_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(audit_schema, "job_definitions")}.id'),
            nullable=True,
        ),
        sa.Column(
            "idempotency_key_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(audit_schema, "idempotency_keys")}.id'),
            nullable=True,
        ),
        sa.Column("job_key", sa.String(length=100), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="QUEUED"),
        sa.Column("locked_resource", sa.String(length=255), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("result_payload", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("queued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        schema=audit_schema,
    )
    op.create_index("uq_job_runs_public_id", "job_runs", ["public_id"], unique=True, schema=audit_schema)
    op.create_index("idx_job_runs_job_key", "job_runs", ["job_key"], schema=audit_schema)
    op.create_index("idx_job_runs_status", "job_runs", ["status"], schema=audit_schema)
    op.create_index("idx_job_runs_locked_resource", "job_runs", ["locked_resource"], schema=audit_schema)

    op.create_table(
        "job_run_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column(
            "job_run_id",
            sa.BigInteger(),
            sa.ForeignKey(f'{_table_ref(audit_schema, "job_runs")}.id'),
            nullable=False,
        ),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=audit_schema,
    )
    op.create_index("uq_job_run_events_public_id", "job_run_events", ["public_id"], unique=True, schema=audit_schema)


def downgrade() -> None:
    audit_schema = _schema("audit")
    core_schema = _schema("core")

    op.drop_index("uq_job_run_events_public_id", table_name="job_run_events", schema=audit_schema)
    op.drop_table("job_run_events", schema=audit_schema)
    op.drop_index("idx_job_runs_locked_resource", table_name="job_runs", schema=audit_schema)
    op.drop_index("idx_job_runs_status", table_name="job_runs", schema=audit_schema)
    op.drop_index("idx_job_runs_job_key", table_name="job_runs", schema=audit_schema)
    op.drop_index("uq_job_runs_public_id", table_name="job_runs", schema=audit_schema)
    op.drop_table("job_runs", schema=audit_schema)
    op.drop_index("idx_idempotency_keys_locked_resource", table_name="idempotency_keys", schema=audit_schema)
    op.drop_index("uq_idempotency_keys_public_id", table_name="idempotency_keys", schema=audit_schema)
    op.drop_table("idempotency_keys", schema=audit_schema)
    op.drop_index("uq_job_definitions_job_key", table_name="job_definitions", schema=audit_schema)
    op.drop_index("uq_job_definitions_public_id", table_name="job_definitions", schema=audit_schema)
    op.drop_table("job_definitions", schema=audit_schema)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.drop_constraint(
            "fk_account_ledger_entries_position_event",
            "account_ledger_entries",
            schema=core_schema,
            type_="foreignkey",
        )
    op.drop_column("account_ledger_entries", "related_position_event_id", schema=core_schema)
    op.drop_column("position_events", "checklist_snapshot", schema=core_schema)
    op.drop_column("position_events", "sizing_rationale", schema=core_schema)
    op.drop_column("position_events", "planned_exit_rule", schema=core_schema)
    op.drop_column("position_events", "expected_holding_period", schema=core_schema)
    op.drop_column("position_events", "invalidation_rule", schema=core_schema)
    op.drop_column("position_events", "disconfirming_evidence", schema=core_schema)
    op.drop_column("position_events", "edge_source", schema=core_schema)
    op.drop_column("position_events", "thesis", schema=core_schema)
