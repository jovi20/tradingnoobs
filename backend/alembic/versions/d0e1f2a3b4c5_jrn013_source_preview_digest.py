"""JRN-013 versioned source preview digest.

Revision ID: d0e1f2a3b4c5
Revises: c9d0e1f2a3b4
"""
from alembic import op
import sqlalchemy as sa


revision = "d0e1f2a3b4c5"
down_revision = "c9d0e1f2a3b4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("import_sessions") as batch:
        batch.add_column(
            sa.Column(
                "source_preview_schema_version",
                sa.Integer(),
                nullable=True,
            )
        )
        batch.add_column(
            sa.Column(
                "source_preview_digest",
                sa.String(length=71),
                nullable=True,
            )
        )
        batch.create_check_constraint(
            "ck_import_sessions_source_preview_digest_pair",
            "(source_preview_schema_version IS NULL "
            "AND source_preview_digest IS NULL) OR "
            "(source_preview_schema_version > 0 "
            "AND source_preview_digest IS NOT NULL)",
        )


def downgrade() -> None:
    with op.batch_alter_table("import_sessions") as batch:
        batch.drop_constraint(
            "ck_import_sessions_source_preview_digest_pair",
            type_="check",
        )
        batch.drop_column("source_preview_digest")
        batch.drop_column("source_preview_schema_version")
