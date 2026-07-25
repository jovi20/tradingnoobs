"""JRN-011 persistent import preview sessions

Revision ID: a7b8c9d0e1f2
Revises: f6a7b8c9d0e1
Create Date: 2026-07-25 22:10:00.000000
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision = "a7b8c9d0e1f2"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "import_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("upload_idempotency_id", sa.Integer(), nullable=False),
        sa.Column("adapter_kind", sa.String(length=40), nullable=False),
        sa.Column("file_format", sa.String(length=20), nullable=False),
        sa.Column("file_hash", sa.String(length=71), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False),
        sa.Column("original_filename", sa.String(length=255), nullable=False),
        sa.Column("media_type", sa.String(length=150), nullable=True),
        sa.Column("status", sa.String(length=30), nullable=False),
        sa.Column("total_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("valid_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("warning_rows", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "response_schema_version",
            sa.Integer(),
            nullable=False,
            server_default="1",
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "status_changed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("terminal_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rows_cleaned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "adapter_kind IN ('GENERIC_BOOTSTRAP', 'IBKR_FLEX_XML_V1')",
            name="ck_import_sessions_adapter_kind",
        ),
        sa.CheckConstraint(
            "status IN ('UPLOADING', 'PREVIEW_READY', 'CONFIRMING', "
            "'COMPLETED', 'COMPLETED_NOOP', 'CONFLICTED', 'FAILED', 'EXPIRED')",
            name="ck_import_sessions_status",
        ),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"]),
        sa.ForeignKeyConstraint(["upload_idempotency_id"], ["idempotency_keys.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "upload_idempotency_id",
            name="uq_import_sessions_upload_idempotency_id",
        ),
    )
    op.create_index(
        "ix_import_sessions_public_id",
        "import_sessions",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        "ix_import_sessions_owner_account_created",
        "import_sessions",
        ["user_id", "account_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_import_sessions_status_expiry",
        "import_sessions",
        ["status", "expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_import_sessions_terminal_cleanup",
        "import_sessions",
        ["terminal_at", "rows_cleaned_at"],
        unique=False,
    )

    op.create_table(
        "import_rows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("adapter_kind", sa.String(length=40), nullable=False),
        sa.Column("file_hash", sa.String(length=71), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("raw_values_json", sa.JSON(), nullable=False),
        sa.Column("normalized_values_json", sa.JSON(), nullable=False),
        sa.Column("validation_errors_json", sa.JSON(), nullable=False),
        sa.Column("warnings_json", sa.JSON(), nullable=False),
        sa.Column("is_valid", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["account_id"], ["trading_accounts.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["import_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "session_id",
            "row_number",
            name="uq_import_rows_session_row_number",
        ),
    )
    op.create_index(
        "ix_import_rows_public_id",
        "import_rows",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        "ix_import_rows_owner_session_row",
        "import_rows",
        ["user_id", "session_id", "row_number"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_import_rows_owner_session_row", table_name="import_rows")
    op.drop_index("ix_import_rows_public_id", table_name="import_rows")
    op.drop_table("import_rows")
    op.drop_index("ix_import_sessions_terminal_cleanup", table_name="import_sessions")
    op.drop_index("ix_import_sessions_status_expiry", table_name="import_sessions")
    op.drop_index(
        "ix_import_sessions_owner_account_created",
        table_name="import_sessions",
    )
    op.drop_index("ix_import_sessions_public_id", table_name="import_sessions")
    op.drop_table("import_sessions")
