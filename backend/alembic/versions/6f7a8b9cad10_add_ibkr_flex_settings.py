"""add_ibkr_flex_settings

Revision ID: 6f7a8b9cad10
Revises: 5e6f7a8b9cad
Create Date: 2026-07-08 00:00:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "6f7a8b9cad10"
down_revision = "5e6f7a8b9cad"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("ibkr_flex_query_id", sa.String(length=100), nullable=True))
    op.add_column("user_settings", sa.Column("ibkr_flex_token", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("user_settings", "ibkr_flex_token")
    op.drop_column("user_settings", "ibkr_flex_query_id")
