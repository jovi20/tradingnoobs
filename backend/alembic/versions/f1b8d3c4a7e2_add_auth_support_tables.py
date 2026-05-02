"""add_auth_support_tables

Revision ID: f1b8d3c4a7e2
Revises: c2f4f9fbb9e1
Create Date: 2026-04-14 01:05:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "f1b8d3c4a7e2"
down_revision = "c2f4f9fbb9e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("password_updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_credentials_id"), "user_credentials", ["id"], unique=False)

    op.create_table(
        "user_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("public_id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=512), nullable=True),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_sessions_id"), "user_sessions", ["id"], unique=False)
    op.create_index(op.f("ix_user_sessions_public_id"), "user_sessions", ["public_id"], unique=True)

    op.create_table(
        "user_identities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("provider_user_id", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider", "provider_user_id", name="uq_user_identities_provider_user"),
    )
    op.create_index(op.f("ix_user_identities_id"), "user_identities", ["id"], unique=False)

    op.create_table(
        "auth_tokens",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("token_jti", sa.String(length=64), nullable=False),
        sa.Column("token_type", sa.String(length=20), nullable=False),
        sa.Column("issued_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["user_sessions.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_auth_tokens_id"), "auth_tokens", ["id"], unique=False)
    op.create_index(op.f("ix_auth_tokens_token_jti"), "auth_tokens", ["token_jti"], unique=True)

    bind = op.get_bind()
    users = bind.execute(
        sa.text("SELECT id, hashed_password FROM users")
    ).mappings().all()
    if users:
        bind.execute(
            sa.text(
                """
                INSERT INTO user_credentials (user_id, password_hash, password_updated_at, created_at)
                VALUES (:user_id, :password_hash, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                """
            ),
            [
                {
                    "user_id": row["id"],
                    "password_hash": row["hashed_password"],
                }
                for row in users
            ],
        )


def downgrade() -> None:
    op.drop_index(op.f("ix_auth_tokens_token_jti"), table_name="auth_tokens")
    op.drop_index(op.f("ix_auth_tokens_id"), table_name="auth_tokens")
    op.drop_table("auth_tokens")
    op.drop_index(op.f("ix_user_identities_id"), table_name="user_identities")
    op.drop_table("user_identities")
    op.drop_index(op.f("ix_user_sessions_public_id"), table_name="user_sessions")
    op.drop_index(op.f("ix_user_sessions_id"), table_name="user_sessions")
    op.drop_table("user_sessions")
    op.drop_index(op.f("ix_user_credentials_id"), table_name="user_credentials")
    op.drop_table("user_credentials")
