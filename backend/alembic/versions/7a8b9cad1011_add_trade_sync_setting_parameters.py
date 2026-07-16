"""add_trade_sync_setting_parameters

Revision ID: 7a8b9cad1011
Revises: 6f7a8b9cad10
Create Date: 2026-07-08 00:20:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "7a8b9cad1011"
down_revision = "6f7a8b9cad10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user_settings", sa.Column("ibkr_flex_start_date", sa.Date(), nullable=True))
    op.add_column("user_settings", sa.Column("binance_market_type", sa.String(length=20), nullable=True))
    op.add_column("user_settings", sa.Column("binance_symbols", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_settings", "binance_symbols")
    op.drop_column("user_settings", "binance_market_type")
    op.drop_column("user_settings", "ibkr_flex_start_date")
