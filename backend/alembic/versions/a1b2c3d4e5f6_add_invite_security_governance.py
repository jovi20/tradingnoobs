"""add invite-only auth and release secret governance

Revision ID: a1b2c3d4e5f6
Revises: 9cad10111213
Create Date: 2026-07-25 14:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "a1b2c3d4e5f6"
down_revision = "9cad10111213"
branch_labels = None
depends_on = None


_PLAINTEXT_USER_SECRET_COLUMNS = (
    "ibkr_flex_query_id",
    "ibkr_flex_token",
    "binance_api_key",
    "binance_api_secret",
    "finnhub_api_key",
    "llm_api_url",
    "llm_api_key",
)

_PLAINTEXT_SETTING_KEYS = (
    "ibkr_flex_query_id",
    "ibkr_flex_token",
    "binance_api_key",
    "binance_api_secret",
    "finnhub_api_key",
    "llm_api_key",
)

_PLAINTEXT_SETTING_PATTERNS = (
    "%api_key%",
    "%api-key%",
    "%apikey%",
    "%token%",
    "%secret%",
    "%password%",
    "%credential%",
    "%private_key%",
    "%private-key%",
    "%access_key%",
    "%access-key%",
    "%connection_string%",
    "%connection-string%",
    "%flex_query_id%",
    "%flex-query-id%",
)


def upgrade() -> None:
    op.create_table(
        "invitations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("code_hash", sa.String(length=64), nullable=False),
        sa.Column("created_by_user_id", sa.Integer(), nullable=False),
        sa.Column("redeemed_by_user_id", sa.Integer(), nullable=True),
        sa.Column("revoked_by_user_id", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("redeemed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["created_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["redeemed_by_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["revoked_by_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_invitations_id"), "invitations", ["id"], unique=False)
    op.create_index(op.f("ix_invitations_public_id"), "invitations", ["public_id"], unique=True)
    op.create_index(op.f("ix_invitations_code_hash"), "invitations", ["code_hash"], unique=True)

    op.create_table(
        "security_audit_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=80), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("subject_type", sa.String(length=50), nullable=True),
        sa.Column("subject_public_id", sa.String(length=100), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_security_audit_events_id"),
        "security_audit_events",
        ["id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_security_audit_events_public_id"),
        "security_audit_events",
        ["public_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_security_audit_events_event_type"),
        "security_audit_events",
        ["event_type"],
        unique=False,
    )

    op.create_table(
        "auth_rate_limit_buckets",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("action", sa.String(length=40), nullable=False),
        sa.Column("dimension", sa.String(length=20), nullable=False),
        sa.Column("key_hash", sa.String(length=64), nullable=False),
        sa.Column("window_started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("blocked_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "action",
            "dimension",
            "key_hash",
            name="uq_auth_rate_limit_bucket_dimension",
        ),
    )
    op.create_index(
        op.f("ix_auth_rate_limit_buckets_id"),
        "auth_rate_limit_buckets",
        ["id"],
        unique=False,
    )

    bind = op.get_bind()
    bind.execute(
        sa.text("DELETE FROM system_settings WHERE key IN :keys").bindparams(
            sa.bindparam("keys", expanding=True)
        ),
        {"keys": _PLAINTEXT_SETTING_KEYS},
    )
    bind.execute(
        sa.text("DELETE FROM platform_settings WHERE key IN :keys").bindparams(
            sa.bindparam("keys", expanding=True)
        ),
        {"keys": _PLAINTEXT_SETTING_KEYS},
    )
    for table_name in ("system_settings", "platform_settings"):
        for pattern in _PLAINTEXT_SETTING_PATTERNS:
            bind.execute(
                sa.text(
                    f"DELETE FROM {table_name} WHERE lower(key) LIKE :pattern"
                ),
                {"pattern": pattern},
            )

    existing_columns = {
        column["name"]
        for column in sa.inspect(bind).get_columns("user_settings")
    }
    with op.batch_alter_table("user_settings") as batch_op:
        for column_name in _PLAINTEXT_USER_SECRET_COLUMNS:
            if column_name in existing_columns:
                batch_op.drop_column(column_name)


def downgrade() -> None:
    with op.batch_alter_table("user_settings") as batch_op:
        batch_op.add_column(sa.Column("llm_api_key", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("llm_api_url", sa.String(length=500), nullable=True))
        batch_op.add_column(sa.Column("finnhub_api_key", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("binance_api_secret", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("binance_api_key", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("ibkr_flex_token", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("ibkr_flex_query_id", sa.String(length=100), nullable=True))

    op.drop_index(op.f("ix_auth_rate_limit_buckets_id"), table_name="auth_rate_limit_buckets")
    op.drop_table("auth_rate_limit_buckets")
    op.drop_index(op.f("ix_security_audit_events_event_type"), table_name="security_audit_events")
    op.drop_index(op.f("ix_security_audit_events_public_id"), table_name="security_audit_events")
    op.drop_index(op.f("ix_security_audit_events_id"), table_name="security_audit_events")
    op.drop_table("security_audit_events")
    op.drop_index(op.f("ix_invitations_code_hash"), table_name="invitations")
    op.drop_index(op.f("ix_invitations_public_id"), table_name="invitations")
    op.drop_index(op.f("ix_invitations_id"), table_name="invitations")
    op.drop_table("invitations")
