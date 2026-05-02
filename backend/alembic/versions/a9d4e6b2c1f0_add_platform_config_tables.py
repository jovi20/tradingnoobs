"""add_platform_config_tables

Revision ID: a9d4e6b2c1f0
Revises: f1b8d3c4a7e2
Create Date: 2026-04-15 00:30:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a9d4e6b2c1f0"
down_revision = "f1b8d3c4a7e2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "platform_settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_platform_settings_id"), "platform_settings", ["id"], unique=False)
    op.create_index(op.f("ix_platform_settings_key"), "platform_settings", ["key"], unique=True)

    op.create_table(
        "integration_credentials",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("provider_key", sa.String(length=50), nullable=False),
        sa.Column("credential_key", sa.String(length=100), nullable=False),
        sa.Column("secret_ciphertext", sa.Text(), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("provider_key", "credential_key", name="uq_integration_credentials_provider_key"),
    )
    op.create_index(op.f("ix_integration_credentials_id"), "integration_credentials", ["id"], unique=False)

    op.create_table(
        "feature_flags",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=100), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("actor_targets", sa.JSON(), nullable=True),
        sa.Column("rollout_percentage", sa.Integer(), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.String(length=255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_feature_flags_id"), "feature_flags", ["id"], unique=False)
    op.create_index(op.f("ix_feature_flags_key"), "feature_flags", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_feature_flags_key"), table_name="feature_flags")
    op.drop_index(op.f("ix_feature_flags_id"), table_name="feature_flags")
    op.drop_table("feature_flags")
    op.drop_index(op.f("ix_integration_credentials_id"), table_name="integration_credentials")
    op.drop_table("integration_credentials")
    op.drop_index(op.f("ix_platform_settings_key"), table_name="platform_settings")
    op.drop_index(op.f("ix_platform_settings_id"), table_name="platform_settings")
    op.drop_table("platform_settings")
