"""JRN-007 truth-native OPEN foundations

Revision ID: d4e5f6a7b8c9
Revises: c3d4e5f6a7b8
Create Date: 2026-07-25 18:35:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "d4e5f6a7b8c9"
down_revision = "c3d4e5f6a7b8"
branch_labels = None
depends_on = None


def _quarantine_duplicate_instruments() -> None:
    bind = op.get_bind()
    duplicate_rows = bind.execute(
        sa.text(
            """
            SELECT id, asset_id, instrument_type, contract_symbol
            FROM trade_instruments
            WHERE (asset_id, instrument_type, contract_symbol) IN (
                SELECT asset_id, instrument_type, contract_symbol
                FROM trade_instruments
                GROUP BY asset_id, instrument_type, contract_symbol
                HAVING COUNT(*) > 1
            )
            ORDER BY asset_id, instrument_type, contract_symbol, id
            """
        )
    ).mappings().all()
    groups: dict[tuple[object, object, object], list[object]] = {}
    for row in duplicate_rows:
        groups.setdefault(
            (row["asset_id"], row["instrument_type"], row["contract_symbol"]),
            [],
        ).append(row)

    for rows in groups.values():
        duplicate_ids = [row["id"] for row in rows[1:]]
        if not duplicate_ids:
            continue
        for instrument_id in duplicate_ids:
            bind.execute(
                sa.text(
                    """
                    UPDATE trading_accounts
                    SET accounting_health = 'ACCOUNTING_RECONCILIATION_REQUIRED'
                    WHERE id IN (
                        SELECT account_id
                        FROM trading_positions
                        WHERE instrument_id = :instrument_id
                    )
                    """
                ),
                {"instrument_id": instrument_id},
            )
            bind.execute(
                sa.text(
                    """
                    UPDATE trade_instruments
                    SET contract_symbol =
                        SUBSTR(contract_symbol, 1, 60)
                        || '#QUARANTINED-' || CAST(id AS VARCHAR(20))
                    WHERE id = :instrument_id
                    """
                ),
                {"instrument_id": instrument_id},
            )


def _repair_duplicate_event_sequences() -> None:
    bind = op.get_bind()
    affected_position_ids = [
        row[0]
        for row in bind.execute(
            sa.text(
                """
                SELECT position_id
                FROM position_events
                GROUP BY position_id, sequence_no
                HAVING COUNT(*) > 1
                """
            )
        ).all()
    ]
    for position_id in sorted(set(affected_position_ids)):
        bind.execute(
            sa.text(
                """
                UPDATE trading_accounts
                SET accounting_health = 'ACCOUNTING_RECONCILIATION_REQUIRED'
                WHERE id = (
                    SELECT account_id
                    FROM trading_positions
                    WHERE id = :position_id
                )
                """
            ),
            {"position_id": position_id},
        )
        event_ids = [
            row[0]
            for row in bind.execute(
                sa.text(
                    """
                    SELECT id
                    FROM position_events
                    WHERE position_id = :position_id
                    ORDER BY event_time, sequence_no, id
                    """
                ),
                {"position_id": position_id},
            ).all()
        ]
        for sequence_no, event_id in enumerate(event_ids, start=1):
            bind.execute(
                sa.text(
                    """
                    UPDATE position_events
                    SET sequence_no = :sequence_no
                    WHERE id = :event_id
                    """
                ),
                {"sequence_no": sequence_no, "event_id": event_id},
            )


def _quarantine_duplicate_open_slots() -> None:
    bind = op.get_bind()
    duplicate_rows = bind.execute(
        sa.text(
            """
            SELECT account_id, instrument_id, side
            FROM trading_positions
            WHERE financially_open = TRUE
            GROUP BY account_id, instrument_id, side
            HAVING COUNT(*) > 1
            """
        )
    ).all()
    for account_id, instrument_id, side in duplicate_rows:
        bind.execute(
            sa.text(
                """
                UPDATE trading_accounts
                SET accounting_health = 'ACCOUNTING_RECONCILIATION_REQUIRED'
                WHERE id = :account_id
                """
            ),
            {"account_id": account_id},
        )
        position_ids = [
            row[0]
            for row in bind.execute(
                sa.text(
                    """
                    SELECT id
                    FROM trading_positions
                    WHERE account_id = :account_id
                      AND instrument_id = :instrument_id
                      AND side = :side
                      AND financially_open = TRUE
                    ORDER BY opened_at, id
                    """
                ),
                {
                    "account_id": account_id,
                    "instrument_id": instrument_id,
                    "side": side,
                },
            ).all()
        ]
        for position_id in position_ids[1:]:
            bind.execute(
                sa.text(
                    """
                    UPDATE trading_positions
                    SET financially_open = FALSE
                    WHERE id = :position_id
                    """
                ),
                {"position_id": position_id},
            )


def upgrade() -> None:
    op.add_column(
        "trading_accounts",
        sa.Column(
            "trade_source_state",
            sa.String(length=20),
            nullable=False,
            server_default="CLEAN",
        ),
    )
    op.execute(
        """
        UPDATE trading_accounts
        SET trade_source_state = 'MANUAL'
        WHERE EXISTS (
            SELECT 1 FROM positions
            WHERE positions.account_id = trading_accounts.id
        )
        OR EXISTS (
            SELECT 1 FROM trading_positions
            WHERE trading_positions.account_id = trading_accounts.id
        )
        """
    )

    op.add_column(
        "trading_positions",
        sa.Column(
            "financially_open",
            sa.Boolean(),
            nullable=False,
            server_default=sa.true(),
        ),
    )
    op.execute(
        """
        UPDATE trading_positions
        SET financially_open = CASE
            WHEN quantity_opened IS NULL OR quantity_closed IS NULL THEN TRUE
            WHEN quantity_opened - quantity_closed > 0 THEN TRUE
            ELSE FALSE
        END
        """
    )

    _quarantine_duplicate_instruments()
    _repair_duplicate_event_sequences()
    _quarantine_duplicate_open_slots()

    op.add_column(
        "idempotency_keys",
        sa.Column("source_fact_public_id", sa.String(length=36), nullable=True),
    )

    with op.batch_alter_table("trade_instruments") as batch_op:
        batch_op.create_unique_constraint(
            "uq_trade_instrument_journal_identity",
            ["asset_id", "instrument_type", "contract_symbol"],
        )
    with op.batch_alter_table("position_events") as batch_op:
        batch_op.create_unique_constraint(
            "uq_position_event_sequence",
            ["position_id", "sequence_no"],
        )

    op.create_index(
        "uq_trading_position_financially_open_side",
        "trading_positions",
        ["account_id", "instrument_id", "side"],
        unique=True,
        postgresql_where=sa.text("financially_open"),
        sqlite_where=sa.text("financially_open = 1"),
    )
    op.create_index(
        "ix_idempotency_source_fact_public_id",
        "idempotency_keys",
        ["source_fact_public_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_idempotency_source_fact_public_id",
        table_name="idempotency_keys",
    )
    op.drop_index(
        "uq_trading_position_financially_open_side",
        table_name="trading_positions",
    )
    with op.batch_alter_table("position_events") as batch_op:
        batch_op.drop_constraint(
            "uq_position_event_sequence",
            type_="unique",
        )
    with op.batch_alter_table("trade_instruments") as batch_op:
        batch_op.drop_constraint(
            "uq_trade_instrument_journal_identity",
            type_="unique",
        )
    op.drop_column("idempotency_keys", "source_fact_public_id")
    op.drop_column("trading_positions", "financially_open")
    op.drop_column("trading_accounts", "trade_source_state")
