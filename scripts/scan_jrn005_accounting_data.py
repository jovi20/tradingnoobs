#!/usr/bin/env python3
"""Emit aggregate-only JRN-005 accounting divergence counts for SQLite samples."""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path


def scalar(connection: sqlite3.Connection, sql: str) -> int:
    value = connection.execute(sql).fetchone()[0]
    return int(value or 0)


def scan(path: Path) -> dict:
    connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table'"
            )
        }
        required = {
            "trading_accounts",
            "position_events",
            "account_ledger_entries",
            "transactions",
        }
        if not required.issubset(tables):
            return {"sample": path.name, "status": "SKIPPED_MISSING_TABLES"}

        return {
            "sample": path.name,
            "status": "SCANNED",
            "accounts": scalar(connection, "SELECT count(*) FROM trading_accounts"),
            "non_usd_accounts": scalar(
                connection,
                "SELECT count(*) FROM trading_accounts "
                "WHERE currency IS NULL OR upper(currency) <> 'USD'",
            ),
            "trade_events": scalar(
                connection,
                "SELECT count(*) FROM position_events "
                "WHERE event_type IN ('OPEN','ADD','REDUCE','CLOSE')",
            ),
            "non_usd_trade_events": scalar(
                connection,
                "SELECT count(*) FROM position_events "
                "WHERE event_type IN ('OPEN','ADD','REDUCE','CLOSE') "
                "AND (currency IS NULL OR upper(currency) <> 'USD')",
            ),
            "trade_events_with_fee": scalar(
                connection,
                "SELECT count(*) FROM position_events "
                "WHERE event_type IN ('OPEN','ADD','REDUCE','CLOSE') "
                "AND fee_amount IS NOT NULL AND fee_amount <> 0",
            ),
            "negative_trade_fees": scalar(
                connection,
                "SELECT count(*) FROM position_events "
                "WHERE event_type IN ('OPEN','ADD','REDUCE','CLOSE') "
                "AND fee_amount < 0",
            ),
            "missing_dedicated_trade_fee_postings": scalar(
                connection,
                "SELECT count(*) FROM position_events e "
                "WHERE e.event_type IN ('OPEN','ADD','REDUCE','CLOSE') "
                "AND e.fee_amount IS NOT NULL AND e.fee_amount <> 0 "
                "AND NOT EXISTS (SELECT 1 FROM account_ledger_entries l "
                "WHERE l.position_event_id = e.id AND l.entry_type = 'FEE')",
            ),
            "close_events": scalar(
                connection,
                "SELECT count(*) FROM position_events "
                "WHERE event_type IN ('REDUCE','CLOSE')",
            ),
            "missing_realized_pnl_postings": scalar(
                connection,
                "SELECT count(*) FROM position_events e "
                "WHERE e.event_type IN ('REDUCE','CLOSE') "
                "AND NOT EXISTS (SELECT 1 FROM account_ledger_entries l "
                "WHERE l.position_event_id = e.id AND l.entry_type = 'REALIZED_PNL')",
            ),
            "realized_postings_not_gross": scalar(
                connection,
                "SELECT count(*) FROM position_events e "
                "JOIN account_ledger_entries l ON l.position_event_id = e.id "
                "AND l.entry_type = 'REALIZED_PNL' "
                "WHERE e.event_type IN ('REDUCE','CLOSE') "
                "AND round(coalesce(l.amount_account_ccy,l.amount),8) "
                "<> round(coalesce(e.realized_pnl_gross,0),8)",
            ),
            "non_usd_ledger_rows": scalar(
                connection,
                "SELECT count(*) FROM account_ledger_entries "
                "WHERE currency IS NULL OR upper(currency) <> 'USD'",
            ),
            "non_usd_transactions": scalar(
                connection,
                "SELECT count(*) FROM transactions "
                "WHERE currency IS NULL OR upper(currency) <> 'USD'",
            ),
        }
    finally:
        connection.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("databases", nargs="+", type=Path)
    args = parser.parse_args()
    print(json.dumps(
        {
            "schema_version": 1,
            "privacy": "AGGREGATE_COUNTS_ONLY_NO_IDS_NO_AMOUNTS",
            "samples": [scan(path) for path in args.databases],
        },
        indent=2,
        sort_keys=True,
    ))


if __name__ == "__main__":
    main()
