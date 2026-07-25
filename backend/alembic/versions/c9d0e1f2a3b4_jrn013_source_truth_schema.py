"""JRN-013 durable source truth and reconciliation schema.

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
"""
from alembic import op
import sqlalchemy as sa


revision = "c9d0e1f2a3b4"
down_revision = "b8c9d0e1f2a3"
branch_labels = None
depends_on = None

IMMUTABLE_SOURCE_EVIDENCE_TABLES = (
    "source_statements",
    "external_source_observations",
    "statement_execution_sightings",
    "statement_coverage_acceptances",
    "source_case_evidence_sightings",
)


def _install_append_only_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        op.execute(
            """
            CREATE OR REPLACE FUNCTION reject_source_evidence_mutation()
            RETURNS trigger AS $$
            BEGIN
                RAISE EXCEPTION '% is append-only', TG_TABLE_NAME
                    USING ERRCODE = '55000';
            END;
            $$ LANGUAGE plpgsql
            """
        )
        for table_name in IMMUTABLE_SOURCE_EVIDENCE_TABLES:
            op.execute(
                f"""
                CREATE TRIGGER trg_{table_name}_append_only
                BEFORE UPDATE OR DELETE ON {table_name}
                FOR EACH ROW EXECUTE FUNCTION reject_source_evidence_mutation()
                """
            )
    elif dialect == "sqlite":
        for table_name in IMMUTABLE_SOURCE_EVIDENCE_TABLES:
            op.execute(
                f"""
                CREATE TRIGGER trg_{table_name}_no_update
                BEFORE UPDATE ON {table_name}
                BEGIN
                    SELECT RAISE(ABORT, '{table_name} is append-only');
                END
                """
            )
            op.execute(
                f"""
                CREATE TRIGGER trg_{table_name}_no_delete
                BEFORE DELETE ON {table_name}
                BEGIN
                    SELECT RAISE(ABORT, '{table_name} is append-only');
                END
                """
            )


def _drop_append_only_guards() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        for table_name in IMMUTABLE_SOURCE_EVIDENCE_TABLES:
            op.execute(
                f"DROP TRIGGER IF EXISTS trg_{table_name}_append_only "
                f"ON {table_name}"
            )
        op.execute(
            "DROP FUNCTION IF EXISTS reject_source_evidence_mutation()"
        )
    elif dialect == "sqlite":
        for table_name in IMMUTABLE_SOURCE_EVIDENCE_TABLES:
            op.execute(
                f"DROP TRIGGER IF EXISTS trg_{table_name}_no_update"
            )
            op.execute(
                f"DROP TRIGGER IF EXISTS trg_{table_name}_no_delete"
            )


def upgrade() -> None:
    op.create_table(
        "import_source_bindings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("adapter_kind", sa.String(length=40), nullable=False),
        sa.Column(
            "normalized_external_account_ref",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "masked_external_account_ref",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("source_timezone", sa.String(length=100), nullable=False),
        sa.Column(
            "source_health",
            sa.String(length=40),
            nullable=False,
            server_default="HEALTHY",
        ),
        sa.Column(
            "source_completeness",
            sa.String(length=30),
            nullable=False,
            server_default="CURRENT",
        ),
        sa.Column("accepted_coverage_start", sa.Date(), nullable=True),
        sa.Column(
            "accepted_coverage_through_exclusive",
            sa.Date(),
            nullable=True,
        ),
        sa.Column(
            "source_state_revision",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"]),
        sa.UniqueConstraint(
            "public_id",
            name="uq_import_source_bindings_public_id",
        ),
        sa.UniqueConstraint(
            "account_id",
            name="uq_import_source_bindings_account_lifetime",
        ),
        sa.UniqueConstraint(
            "user_id",
            "adapter_kind",
            "normalized_external_account_ref",
            name="uq_import_source_bindings_owner_external_account",
        ),
        sa.UniqueConstraint(
            "id",
            "user_id",
            "account_id",
            name="uq_import_source_bindings_owner_graph",
        ),
        sa.CheckConstraint(
            "adapter_kind = 'IBKR_FLEX_XML_V1'",
            name="ck_import_source_bindings_adapter",
        ),
        sa.CheckConstraint(
            "source_health IN ('HEALTHY', 'RECONCILIATION_REQUIRED', "
            "'SOURCE_DIVERGED')",
            name="ck_import_source_bindings_health",
        ),
        sa.CheckConstraint(
            "source_completeness IN ('CURRENT', 'PENDING_IMPORT')",
            name="ck_import_source_bindings_completeness",
        ),
        sa.CheckConstraint(
            "source_state_revision >= 0",
            name="ck_import_source_bindings_revision",
        ),
    )
    op.create_index(
        "ix_import_source_bindings_owner_health",
        "import_source_bindings",
        ["user_id", "source_health", "source_completeness"],
    )

    op.create_table(
        "source_statements",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("binding_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("import_session_id", sa.Integer(), nullable=False),
        sa.Column("file_hash", sa.String(length=71), nullable=False),
        sa.Column("statement_generation", sa.String(length=255), nullable=False),
        sa.Column("generation_order_key", sa.String(length=512), nullable=False),
        sa.Column("raw_from_date", sa.String(length=100), nullable=False),
        sa.Column("raw_to_date", sa.String(length=100), nullable=False),
        sa.Column("coverage_start", sa.Date(), nullable=False),
        sa.Column("coverage_end_exclusive", sa.Date(), nullable=False),
        sa.Column("source_timezone", sa.String(length=100), nullable=False),
        sa.Column(
            "normalized_external_account_ref",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["binding_id", "user_id", "account_id"],
            [
                "import_source_bindings.id",
                "import_source_bindings.user_id",
                "import_source_bindings.account_id",
            ],
            name="fk_source_statements_binding_owner_graph",
        ),
        sa.ForeignKeyConstraint(
            ["import_session_id"],
            ["import_sessions.id"],
        ),
        sa.UniqueConstraint(
            "public_id",
            name="uq_source_statements_public_id",
        ),
        sa.UniqueConstraint(
            "binding_id",
            "file_hash",
            name="uq_source_statements_binding_file",
        ),
        sa.UniqueConstraint(
            "id",
            "binding_id",
            name="uq_source_statements_binding_graph",
        ),
        sa.CheckConstraint(
            "coverage_start < coverage_end_exclusive",
            name="ck_source_statements_coverage",
        ),
    )
    op.create_index(
        "ix_source_statements_binding_generation",
        "source_statements",
        ["binding_id", "generation_order_key"],
    )
    op.create_index(
        "ix_source_statements_owner_coverage",
        "source_statements",
        [
            "user_id",
            "account_id",
            "coverage_start",
            "coverage_end_exclusive",
        ],
    )

    op.create_table(
        "external_source_observations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("binding_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("event_kind", sa.String(length=30), nullable=False),
        sa.Column(
            "external_source_event_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("external_execution_id", sa.String(length=255), nullable=True),
        sa.Column(
            "affected_external_execution_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column(
            "provider_declared_target_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("fingerprint_version", sa.Integer(), nullable=False),
        sa.Column(
            "source_payload_fingerprint",
            sa.String(length=71),
            nullable=False,
        ),
        sa.Column("transaction_id", sa.String(length=255), nullable=False),
        sa.Column("source_order_key", sa.String(length=512), nullable=False),
        sa.Column("conid", sa.String(length=100), nullable=False),
        sa.Column("instrument_identity_json", sa.JSON(), nullable=False),
        sa.Column("raw_side", sa.String(length=30), nullable=False),
        sa.Column("raw_open_close", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Numeric(20, 8), nullable=True),
        sa.Column("price", sa.Numeric(20, 8), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source_timezone", sa.String(length=100), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("normalized_fee", sa.Numeric(20, 8), nullable=True),
        sa.Column("fee_currency", sa.String(length=10), nullable=True),
        sa.Column("execution_status", sa.String(length=100), nullable=False),
        sa.Column("normalized_payload_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["binding_id", "user_id", "account_id"],
            [
                "import_source_bindings.id",
                "import_source_bindings.user_id",
                "import_source_bindings.account_id",
            ],
            name="fk_external_source_observations_binding_owner_graph",
        ),
        sa.UniqueConstraint(
            "public_id",
            name="uq_external_source_observations_public_id",
        ),
        sa.UniqueConstraint(
            "binding_id",
            "external_source_event_id",
            "fingerprint_version",
            "source_payload_fingerprint",
            name="uq_external_source_observations_identity",
        ),
        sa.UniqueConstraint(
            "id",
            "binding_id",
            name="uq_external_source_observations_binding_graph",
        ),
        sa.CheckConstraint(
            "event_kind IN ('TRADE', 'CORRECTION', 'CANCEL_BUST')",
            name="ck_external_source_observations_event_kind",
        ),
        sa.CheckConstraint(
            "fingerprint_version > 0",
            name="ck_external_source_observations_fingerprint_version",
        ),
        sa.CheckConstraint(
            "quantity IS NULL OR quantity > 0",
            name="ck_external_source_observations_quantity",
        ),
        sa.CheckConstraint(
            "price IS NULL OR price > 0",
            name="ck_external_source_observations_price",
        ),
        sa.CheckConstraint(
            "normalized_fee IS NULL OR normalized_fee >= 0",
            name="ck_external_source_observations_fee",
        ),
    )
    op.create_index(
        "ix_external_source_observations_binding_execution",
        "external_source_observations",
        ["binding_id", "external_execution_id"],
    )
    op.create_index(
        "ix_external_source_observations_binding_affected",
        "external_source_observations",
        ["binding_id", "affected_external_execution_id"],
    )

    op.create_table(
        "statement_execution_sightings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("binding_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("statement_id", sa.Integer(), nullable=False),
        sa.Column("observation_id", sa.Integer(), nullable=False),
        sa.Column(
            "external_source_event_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("generation_order_key", sa.String(length=512), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["statement_id", "binding_id"],
            ["source_statements.id", "source_statements.binding_id"],
            name="fk_statement_sightings_statement_binding",
        ),
        sa.ForeignKeyConstraint(
            ["observation_id", "binding_id"],
            [
                "external_source_observations.id",
                "external_source_observations.binding_id",
            ],
            name="fk_statement_sightings_observation_binding",
        ),
        sa.ForeignKeyConstraint(
            ["binding_id", "user_id", "account_id"],
            [
                "import_source_bindings.id",
                "import_source_bindings.user_id",
                "import_source_bindings.account_id",
            ],
            name="fk_statement_sightings_binding_owner_graph",
        ),
        sa.UniqueConstraint(
            "public_id",
            name="uq_statement_execution_sightings_public_id",
        ),
        sa.UniqueConstraint(
            "statement_id",
            "external_source_event_id",
            "observation_id",
            name="uq_statement_execution_sightings_identity",
        ),
        sa.UniqueConstraint(
            "id",
            "binding_id",
            name="uq_statement_execution_sightings_binding_graph",
        ),
    )
    op.create_index(
        "ix_statement_sightings_binding_generation",
        "statement_execution_sightings",
        ["binding_id", "generation_order_key"],
    )

    op.create_table(
        "external_executions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("binding_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column(
            "external_execution_id",
            sa.String(length=255),
            nullable=False,
        ),
        sa.Column("current_trade_observation_id", sa.Integer(), nullable=False),
        sa.Column("disposition", sa.String(length=30), nullable=False),
        sa.Column("canceled_by_observation_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["binding_id", "user_id", "account_id"],
            [
                "import_source_bindings.id",
                "import_source_bindings.user_id",
                "import_source_bindings.account_id",
            ],
            name="fk_external_executions_binding_owner_graph",
        ),
        sa.ForeignKeyConstraint(
            ["current_trade_observation_id", "binding_id"],
            [
                "external_source_observations.id",
                "external_source_observations.binding_id",
            ],
            name="fk_external_executions_current_observation_binding",
        ),
        sa.ForeignKeyConstraint(
            ["canceled_by_observation_id", "binding_id"],
            [
                "external_source_observations.id",
                "external_source_observations.binding_id",
            ],
            name="fk_external_executions_canceled_observation_binding",
        ),
        sa.UniqueConstraint(
            "public_id",
            name="uq_external_executions_public_id",
        ),
        sa.UniqueConstraint(
            "binding_id",
            "external_execution_id",
            name="uq_external_executions_binding_execution",
        ),
        sa.UniqueConstraint(
            "id",
            "binding_id",
            name="uq_external_executions_binding_graph",
        ),
        sa.UniqueConstraint(
            "binding_id",
            "canceled_by_observation_id",
            name="uq_external_executions_canceled_by",
        ),
        sa.CheckConstraint(
            "disposition IN ('ACTIVE', 'ACCEPTED_TOMBSTONE')",
            name="ck_external_executions_disposition",
        ),
        sa.CheckConstraint(
            "(disposition = 'ACTIVE' AND canceled_by_observation_id IS NULL) "
            "OR (disposition = 'ACCEPTED_TOMBSTONE' "
            "AND canceled_by_observation_id IS NOT NULL)",
            name="ck_external_executions_tombstone",
        ),
    )

    op.create_table(
        "external_trade_applications",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("binding_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("external_execution_id", sa.Integer(), nullable=False),
        sa.Column("source_observation_id", sa.Integer(), nullable=False),
        sa.Column("application_version", sa.Integer(), nullable=False),
        sa.Column(
            "is_active",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column("derived_direction", sa.String(length=10), nullable=False),
        sa.Column("derived_action", sa.String(length=20), nullable=False),
        sa.Column("pre_quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column("post_quantity", sa.Numeric(20, 8), nullable=False),
        sa.Column(
            "canonical_position_public_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column(
            "canonical_event_public_id",
            sa.String(length=36),
            nullable=True,
        ),
        sa.Column("applied_import_session_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("superseded_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["external_execution_id", "binding_id"],
            ["external_executions.id", "external_executions.binding_id"],
            name="fk_external_trade_applications_execution_binding",
        ),
        sa.ForeignKeyConstraint(
            ["source_observation_id", "binding_id"],
            [
                "external_source_observations.id",
                "external_source_observations.binding_id",
            ],
            name="fk_external_trade_applications_observation_binding",
        ),
        sa.ForeignKeyConstraint(
            ["binding_id", "user_id", "account_id"],
            [
                "import_source_bindings.id",
                "import_source_bindings.user_id",
                "import_source_bindings.account_id",
            ],
            name="fk_external_trade_applications_binding_owner_graph",
        ),
        sa.ForeignKeyConstraint(
            ["applied_import_session_id"],
            ["import_sessions.id"],
        ),
        sa.UniqueConstraint(
            "public_id",
            name="uq_external_trade_applications_public_id",
        ),
        sa.UniqueConstraint(
            "external_execution_id",
            "application_version",
            name="uq_external_trade_applications_version",
        ),
        sa.UniqueConstraint(
            "id",
            "binding_id",
            name="uq_external_trade_applications_binding_graph",
        ),
        sa.CheckConstraint(
            "application_version > 0",
            name="ck_external_trade_applications_version",
        ),
        sa.CheckConstraint(
            "derived_direction IN ('LONG', 'SHORT')",
            name="ck_external_trade_applications_direction",
        ),
        sa.CheckConstraint(
            "derived_action IN ('OPEN', 'ADD', 'REDUCE', 'CLOSE')",
            name="ck_external_trade_applications_action",
        ),
        sa.CheckConstraint(
            "pre_quantity >= 0 AND post_quantity >= 0",
            name="ck_external_trade_applications_quantities",
        ),
        sa.CheckConstraint(
            "(canonical_position_public_id IS NULL "
            "AND canonical_event_public_id IS NULL) "
            "OR (canonical_position_public_id IS NOT NULL "
            "AND canonical_event_public_id IS NOT NULL)",
            name="ck_external_trade_applications_canonical_pair",
        ),
    )
    op.create_index(
        "uq_external_trade_applications_active",
        "external_trade_applications",
        ["external_execution_id"],
        unique=True,
        sqlite_where=sa.text("is_active = 1"),
        postgresql_where=sa.text("is_active"),
    )

    op.create_table(
        "statement_coverage_acceptances",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("binding_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("statement_id", sa.Integer(), nullable=False),
        sa.Column("import_session_id", sa.Integer(), nullable=False),
        sa.Column("operation_idempotency_id", sa.Integer(), nullable=False),
        sa.Column(
            "accepted_source_state_revision",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "accepted_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["statement_id", "binding_id"],
            ["source_statements.id", "source_statements.binding_id"],
            name="fk_statement_coverage_acceptances_statement_binding",
        ),
        sa.ForeignKeyConstraint(
            ["binding_id", "user_id", "account_id"],
            [
                "import_source_bindings.id",
                "import_source_bindings.user_id",
                "import_source_bindings.account_id",
            ],
            name="fk_statement_coverage_acceptances_binding_owner_graph",
        ),
        sa.ForeignKeyConstraint(
            ["import_session_id"],
            ["import_sessions.id"],
        ),
        sa.ForeignKeyConstraint(
            ["operation_idempotency_id"],
            ["idempotency_keys.id"],
        ),
        sa.UniqueConstraint(
            "public_id",
            name="uq_statement_coverage_acceptances_public_id",
        ),
        sa.UniqueConstraint(
            "binding_id",
            "statement_id",
            name="uq_statement_coverage_acceptances_binding_statement",
        ),
        sa.CheckConstraint(
            "accepted_source_state_revision > 0",
            name="ck_statement_coverage_acceptances_revision",
        ),
    )

    op.create_table(
        "source_reconciliation_cases",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("binding_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("conflict_observation_id", sa.Integer(), nullable=False),
        sa.Column("trigger_sighting_id", sa.Integer(), nullable=False),
        sa.Column("case_kind", sa.String(length=80), nullable=False),
        sa.Column(
            "state",
            sa.String(length=60),
            nullable=False,
            server_default="OPEN",
        ),
        sa.Column(
            "against_source_state_schema_version",
            sa.Integer(),
            nullable=False,
        ),
        sa.Column(
            "against_source_state_hash",
            sa.String(length=71),
            nullable=False,
        ),
        sa.Column(
            "against_source_state_snapshot_json",
            sa.JSON(),
            nullable=False,
        ),
        sa.Column(
            "selected_target_external_execution_id",
            sa.String(length=255),
            nullable=True,
        ),
        sa.Column("resolution_actor_user_id", sa.Integer(), nullable=True),
        sa.Column("resolution_reason", sa.Text(), nullable=True),
        sa.Column("resolution_request_id", sa.String(length=100), nullable=True),
        sa.Column("winning_sighting_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["binding_id", "user_id", "account_id"],
            [
                "import_source_bindings.id",
                "import_source_bindings.user_id",
                "import_source_bindings.account_id",
            ],
            name="fk_source_reconciliation_cases_binding_owner_graph",
        ),
        sa.ForeignKeyConstraint(
            ["conflict_observation_id", "binding_id"],
            [
                "external_source_observations.id",
                "external_source_observations.binding_id",
            ],
            name="fk_source_reconciliation_cases_observation_binding",
        ),
        sa.ForeignKeyConstraint(
            ["trigger_sighting_id", "binding_id"],
            [
                "statement_execution_sightings.id",
                "statement_execution_sightings.binding_id",
            ],
            name="fk_source_reconciliation_cases_trigger_binding",
        ),
        sa.ForeignKeyConstraint(
            ["winning_sighting_id", "binding_id"],
            [
                "statement_execution_sightings.id",
                "statement_execution_sightings.binding_id",
            ],
            name="fk_source_reconciliation_cases_winner_binding",
        ),
        sa.ForeignKeyConstraint(
            ["resolution_actor_user_id"],
            ["users.id"],
        ),
        sa.UniqueConstraint(
            "public_id",
            name="uq_source_reconciliation_cases_public_id",
        ),
        sa.UniqueConstraint(
            "binding_id",
            "trigger_sighting_id",
            "case_kind",
            "against_source_state_hash",
            name="uq_source_reconciliation_cases_trigger_episode",
        ),
        sa.UniqueConstraint(
            "id",
            "binding_id",
            name="uq_source_reconciliation_cases_binding_graph",
        ),
        sa.CheckConstraint(
            "state IN ('OPEN', 'RESOLVING', 'DIVERGED_REJECTED', "
            "'RESOLVED_APPLIED', "
            "'RESOLVED_SUPERSEDED_BY_LATER_AUTHORITY')",
            name="ck_source_reconciliation_cases_state",
        ),
        sa.CheckConstraint(
            "against_source_state_schema_version > 0",
            name="ck_source_reconciliation_cases_schema_version",
        ),
    )
    op.create_index(
        "uq_source_reconciliation_cases_nonterminal",
        "source_reconciliation_cases",
        [
            "binding_id",
            "conflict_observation_id",
            "case_kind",
            "against_source_state_hash",
        ],
        unique=True,
        sqlite_where=sa.text(
            "state IN ('OPEN', 'RESOLVING', 'DIVERGED_REJECTED')"
        ),
        postgresql_where=sa.text(
            "state IN ('OPEN', 'RESOLVING', 'DIVERGED_REJECTED')"
        ),
    )
    op.create_index(
        "ix_source_reconciliation_cases_binding_state",
        "source_reconciliation_cases",
        ["binding_id", "state"],
    )

    op.create_table(
        "source_case_evidence_sightings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("binding_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("case_id", sa.Integer(), nullable=False),
        sa.Column("sighting_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["case_id", "binding_id"],
            [
                "source_reconciliation_cases.id",
                "source_reconciliation_cases.binding_id",
            ],
            name="fk_source_case_evidence_sightings_case_binding",
        ),
        sa.ForeignKeyConstraint(
            ["sighting_id", "binding_id"],
            [
                "statement_execution_sightings.id",
                "statement_execution_sightings.binding_id",
            ],
            name="fk_source_case_evidence_sightings_sighting_binding",
        ),
        sa.ForeignKeyConstraint(
            ["binding_id", "user_id", "account_id"],
            [
                "import_source_bindings.id",
                "import_source_bindings.user_id",
                "import_source_bindings.account_id",
            ],
            name="fk_source_case_evidence_sightings_binding_owner_graph",
        ),
        sa.UniqueConstraint(
            "case_id",
            "sighting_id",
            name="uq_source_case_evidence_sightings_case_sighting",
        ),
    )
    _install_append_only_guards()


def downgrade() -> None:
    _drop_append_only_guards()
    op.drop_table("source_case_evidence_sightings")
    op.drop_index(
        "ix_source_reconciliation_cases_binding_state",
        table_name="source_reconciliation_cases",
    )
    op.drop_index(
        "uq_source_reconciliation_cases_nonterminal",
        table_name="source_reconciliation_cases",
    )
    op.drop_table("source_reconciliation_cases")
    op.drop_table("statement_coverage_acceptances")
    op.drop_index(
        "uq_external_trade_applications_active",
        table_name="external_trade_applications",
    )
    op.drop_table("external_trade_applications")
    op.drop_table("external_executions")
    op.drop_index(
        "ix_statement_sightings_binding_generation",
        table_name="statement_execution_sightings",
    )
    op.drop_table("statement_execution_sightings")
    op.drop_index(
        "ix_external_source_observations_binding_affected",
        table_name="external_source_observations",
    )
    op.drop_index(
        "ix_external_source_observations_binding_execution",
        table_name="external_source_observations",
    )
    op.drop_table("external_source_observations")
    op.drop_index(
        "ix_source_statements_owner_coverage",
        table_name="source_statements",
    )
    op.drop_index(
        "ix_source_statements_binding_generation",
        table_name="source_statements",
    )
    op.drop_table("source_statements")
    op.drop_index(
        "ix_import_source_bindings_owner_health",
        table_name="import_source_bindings",
    )
    op.drop_table("import_source_bindings")
