"""platform baseline schemas and identity tables

Revision ID: 20260604_0001
Revises:
Create Date: 2026-06-04
"""

from alembic import op
import sqlalchemy as sa


revision = "20260604_0001"
down_revision = None
branch_labels = None
depends_on = None

SCHEMAS = ("core", "reference", "market", "derived", "audit", "content", "ai")


def _schema(name: str) -> str | None:
    bind = op.get_bind()
    return name if bind.dialect.name == "postgresql" else None


def _create_schema(name: str) -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute(sa.text(f'CREATE SCHEMA IF NOT EXISTS "{name}"'))


def upgrade() -> None:
    for schema_name in SCHEMAS:
        _create_schema(schema_name)

    core_schema = _schema("core")
    audit_schema = _schema("audit")

    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("email_normalized", sa.String(length=255), nullable=False),
        sa.Column("hashed_password", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="user"),
        sa.Column("locale", sa.String(length=16), nullable=False, server_default="en-US"),
        sa.Column("timezone", sa.String(length=64), nullable=False, server_default="UTC"),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=core_schema,
    )
    op.create_index("uq_users_public_id", "users", ["public_id"], unique=True, schema=core_schema)
    op.create_index("uq_users_email_normalized", "users", ["email_normalized"], unique=True, schema=core_schema)

    op.create_table(
        "user_credentials",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("credential_type", sa.String(length=32), nullable=False),
        sa.Column("credential_hash", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema=core_schema,
    )

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="ACTIVE"),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        schema=core_schema,
    )
    op.create_index("uq_user_sessions_public_id", "user_sessions", ["public_id"], unique=True, schema=core_schema)

    op.create_table(
        "user_identities",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("provider_subject", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema=core_schema,
    )

    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("token_type", sa.String(length=32), nullable=False),
        sa.Column("token_hash", sa.String(length=255), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        schema=core_schema,
    )
    op.create_index("uq_auth_tokens_public_id", "auth_tokens", ["public_id"], unique=True, schema=core_schema)

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("public_id", sa.String(length=26), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_type", sa.String(length=100), nullable=False),
        sa.Column("aggregate_public_id", sa.String(length=26), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="PENDING"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        schema=audit_schema,
    )
    op.create_index("uq_outbox_events_public_id", "outbox_events", ["public_id"], unique=True, schema=audit_schema)


def downgrade() -> None:
    audit_schema = _schema("audit")
    core_schema = _schema("core")

    op.drop_index("uq_outbox_events_public_id", table_name="outbox_events", schema=audit_schema)
    op.drop_table("outbox_events", schema=audit_schema)
    op.drop_index("uq_auth_tokens_public_id", table_name="auth_tokens", schema=core_schema)
    op.drop_table("auth_tokens", schema=core_schema)
    op.drop_table("user_identities", schema=core_schema)
    op.drop_index("uq_user_sessions_public_id", table_name="user_sessions", schema=core_schema)
    op.drop_table("user_sessions", schema=core_schema)
    op.drop_table("user_credentials", schema=core_schema)
    op.drop_index("uq_users_email_normalized", table_name="users", schema=core_schema)
    op.drop_index("uq_users_public_id", table_name="users", schema=core_schema)
    op.drop_table("users", schema=core_schema)

    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        for schema_name in reversed(SCHEMAS):
            op.execute(sa.text(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE'))
