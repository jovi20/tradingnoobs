import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class AlembicChainTests(unittest.TestCase):
    def test_alembic_upgrade_head_creates_expected_tables(self):
        repo_root = Path(__file__).resolve().parents[2]

        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            env = os.environ.copy()
            env["DATABASE_URL"] = f"sqlite:///{db_path}"
            env["PYTHONPATH"] = str(repo_root / "backend")

            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    "backend/alembic.ini",
                    "upgrade",
                    "head",
                ],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(
                result.returncode,
                0,
                msg=f"alembic upgrade head failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
            )

            conn = sqlite3.connect(db_path)
            try:
                rows = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
                user_columns = conn.execute(
                    "PRAGMA table_info(users)"
                ).fetchall()
                trading_account_columns = conn.execute(
                    "PRAGMA table_info(trading_accounts)"
                ).fetchall()
                position_columns = conn.execute(
                    "PRAGMA table_info(positions)"
                ).fetchall()
                transaction_columns = conn.execute(
                    "PRAGMA table_info(transactions)"
                ).fetchall()
                trade_batch_columns = conn.execute(
                    "PRAGMA table_info(trade_batches)"
                ).fetchall()
                asset_master_columns = conn.execute(
                    "PRAGMA table_info(asset_master)"
                ).fetchall()
                trade_instrument_columns = conn.execute(
                    "PRAGMA table_info(trade_instruments)"
                ).fetchall()
                trading_position_columns = conn.execute(
                    "PRAGMA table_info(trading_positions)"
                ).fetchall()
                position_event_columns = conn.execute(
                    "PRAGMA table_info(position_events)"
                ).fetchall()
                account_ledger_entry_columns = conn.execute(
                    "PRAGMA table_info(account_ledger_entries)"
                ).fetchall()
                job_definition_columns = conn.execute(
                    "PRAGMA table_info(job_definitions)"
                ).fetchall()
                job_run_columns = conn.execute(
                    "PRAGMA table_info(job_runs)"
                ).fetchall()
                job_run_event_columns = conn.execute(
                    "PRAGMA table_info(job_run_events)"
                ).fetchall()
                idempotency_key_columns = conn.execute(
                    "PRAGMA table_info(idempotency_keys)"
                ).fetchall()
                outbox_event_columns = conn.execute(
                    "PRAGMA table_info(outbox_events)"
                ).fetchall()
                business_lock_columns = conn.execute(
                    "PRAGMA table_info(business_locks)"
                ).fetchall()
                derived_timeline_snapshot_columns = conn.execute(
                    "PRAGMA table_info(derived_timeline_snapshots)"
                ).fetchall()
                insight_run_columns = conn.execute(
                    "PRAGMA table_info(insight_runs)"
                ).fetchall()
                insight_artifact_columns = conn.execute(
                    "PRAGMA table_info(insight_artifacts)"
                ).fetchall()
                accounting_reconciliation_columns = conn.execute(
                    "PRAGMA table_info(accounting_reconciliation_cases)"
                ).fetchall()
                broker_sync_run_columns = conn.execute(
                    "PRAGMA table_info(broker_sync_runs)"
                ).fetchall()
                broker_execution_columns = conn.execute(
                    "PRAGMA table_info(broker_executions)"
                ).fetchall()
                import_session_columns = conn.execute(
                    "PRAGMA table_info(import_sessions)"
                ).fetchall()
                import_row_columns = conn.execute(
                    "PRAGMA table_info(import_rows)"
                ).fetchall()
            finally:
                conn.close()

            table_names = {row[0] for row in rows}
            user_column_names = {row[1] for row in user_columns}
            trading_account_column_names = {row[1] for row in trading_account_columns}
            position_column_names = {row[1] for row in position_columns}
            transaction_column_names = {row[1] for row in transaction_columns}
            trade_batch_column_names = {row[1] for row in trade_batch_columns}
            asset_master_column_names = {row[1] for row in asset_master_columns}
            trade_instrument_column_names = {row[1] for row in trade_instrument_columns}
            trading_position_column_names = {row[1] for row in trading_position_columns}
            position_event_column_names = {row[1] for row in position_event_columns}
            account_ledger_entry_column_names = {row[1] for row in account_ledger_entry_columns}
            job_definition_column_names = {row[1] for row in job_definition_columns}
            job_run_column_names = {row[1] for row in job_run_columns}
            job_run_event_column_names = {row[1] for row in job_run_event_columns}
            idempotency_key_column_names = {row[1] for row in idempotency_key_columns}
            outbox_event_column_names = {row[1] for row in outbox_event_columns}
            business_lock_column_names = {row[1] for row in business_lock_columns}
            derived_timeline_snapshot_column_names = {row[1] for row in derived_timeline_snapshot_columns}
            insight_run_column_names = {row[1] for row in insight_run_columns}
            insight_artifact_column_names = {row[1] for row in insight_artifact_columns}
            accounting_reconciliation_column_names = {
                row[1] for row in accounting_reconciliation_columns
            }
            broker_sync_run_column_names = {row[1] for row in broker_sync_run_columns}
            broker_execution_column_names = {row[1] for row in broker_execution_columns}
            import_session_column_names = {row[1] for row in import_session_columns}
            import_row_column_names = {row[1] for row in import_row_columns}
            self.assertIn(
                "source_preview_schema_version",
                import_session_column_names,
            )
            self.assertIn(
                "source_preview_digest",
                import_session_column_names,
            )
            expected_tables = {
                "alembic_version",
                "users",
                "user_credentials",
                "user_sessions",
                "user_identities",
                "user_settings",
                "auth_tokens",
                "platform_settings",
                "integration_credentials",
                "feature_flags",
                "strategies",
                "trading_accounts",
                "positions",
                "trade_batches",
                "transactions",
                "daily_summaries",
                "daily_snapshots",
                "weekly_reports",
                "journal_entries",
                "asset_metadata",
                "asset_master",
                "trade_instruments",
                "ai_summaries",
                "ai_analysis_results",
                "trading_positions",
                "position_events",
                "account_ledger_entries",
                "job_definitions",
                "job_runs",
                "job_run_events",
                "idempotency_keys",
                "outbox_events",
                "business_locks",
                "derived_timeline_snapshots",
                "insight_runs",
                "insight_artifacts",
                "accounting_reconciliation_cases",
                "broker_sync_runs",
                "broker_executions",
                "import_sessions",
                "import_rows",
                "provider_symbol_mappings",
                "latest_market_quotes",
                "price_bars_daily",
                "market_data_watermarks",
                "system_settings",
            }

            self.assertTrue(
                expected_tables.issubset(table_names),
                msg=f"missing tables: {sorted(expected_tables - table_names)}",
            )
            self.assertTrue(
                {
                    "public_id",
                    "status",
                    "email_normalized",
                    "last_login_at",
                    "locale",
                    "timezone",
                }.issubset(user_column_names),
                msg=f"missing user columns: {sorted({'public_id', 'status', 'email_normalized', 'last_login_at', 'locale', 'timezone'} - user_column_names)}",
            )
            self.assertTrue(
                {"public_id", "accounting_health"}.issubset(
                    trading_account_column_names
                )
            )
            self.assertIn("public_id", position_column_names)
            self.assertIn("public_id", transaction_column_names)
            self.assertIn("public_id", trade_batch_column_names)
            self.assertTrue({"public_id", "canonical_code", "display_symbol"}.issubset(asset_master_column_names))
            self.assertTrue({"public_id", "asset_id", "instrument_type", "contract_symbol"}.issubset(trade_instrument_column_names))
            self.assertTrue({"public_id", "user_id", "account_id", "instrument_id", "cost_basis_method"}.issubset(trading_position_column_names))
            self.assertTrue(
                {
                    "public_id",
                    "position_id",
                    "instrument_id",
                    "event_type",
                    "event_time",
                    "sequence_no",
                }.issubset(position_event_column_names)
            )
            self.assertTrue(
                {
                    "public_id",
                    "user_id",
                    "account_id",
                    "position_id",
                    "position_event_id",
                    "transaction_id",
                    "reverses_ledger_entry_id",
                    "entry_type",
                    "source_fact_public_id",
                    "posting_kind",
                    "occurred_at",
                    "currency",
                    "amount",
                }.issubset(account_ledger_entry_column_names)
            )
            self.assertTrue(
                {
                    "public_id",
                    "user_id",
                    "account_id",
                    "original_ledger_entry_id",
                    "status",
                    "issue_code",
                    "details_json",
                    "resolution_note",
                    "resolved_by_user_id",
                    "resolved_at",
                }.issubset(accounting_reconciliation_column_names)
            )
            self.assertTrue({"public_id", "key", "queue_name", "retry_policy"}.issubset(job_definition_column_names))
            self.assertTrue({"public_id", "job_definition_id", "status", "payload", "idempotency_key"}.issubset(job_run_column_names))
            self.assertTrue({"public_id", "job_run_id", "event_type", "to_status", "metadata"}.issubset(job_run_event_column_names))
            self.assertTrue({"public_id", "scope", "key", "request_hash", "job_run_id"}.issubset(idempotency_key_column_names))
            self.assertTrue({"public_id", "aggregate_type", "event_type", "payload", "status", "dedupe_key"}.issubset(outbox_event_column_names))
            self.assertTrue({"public_id", "scope", "resource_key", "owner_id", "status", "expires_at"}.issubset(business_lock_column_names))
            self.assertTrue(
                {
                    "public_id",
                    "user_id",
                    "trading_position_public_id",
                    "source",
                    "snapshot_json",
                    "refreshed_by_job_run_public_id",
                    "refreshed_at",
                }.issubset(derived_timeline_snapshot_column_names)
            )
            self.assertTrue(
                {
                    "public_id",
                    "user_id",
                    "run_type",
                    "status",
                    "input_refs",
                    "started_at",
                }.issubset(insight_run_column_names)
            )
            self.assertTrue(
                {
                    "public_id",
                    "insight_run_id",
                    "artifact_type",
                    "summary",
                    "payload",
                    "evidence_refs",
                    "trust_meta",
                }.issubset(insight_artifact_column_names)
            )
            self.assertTrue(
                {
                    "public_id",
                    "user_id",
                    "provider",
                    "market_type",
                    "status",
                    "records_fetched",
                    "records_inserted",
                    "records_skipped",
                }.issubset(broker_sync_run_column_names)
            )
            self.assertTrue(
                {
                    "public_id",
                    "user_id",
                    "sync_run_id",
                    "provider",
                    "symbol",
                    "side",
                    "quantity",
                    "price",
                    "trade_time",
                    "external_trade_id",
                    "idempotency_key",
                    "raw_payload",
                }.issubset(broker_execution_column_names)
            )
            self.assertTrue(
                {
                    "public_id",
                    "user_id",
                    "account_id",
                    "upload_idempotency_id",
                    "adapter_kind",
                    "file_hash",
                    "status",
                    "expires_at",
                    "terminal_at",
                    "rows_cleaned_at",
                }.issubset(import_session_column_names)
            )
            self.assertTrue(
                {
                    "public_id",
                    "session_id",
                    "user_id",
                    "account_id",
                    "adapter_kind",
                    "file_hash",
                    "row_number",
                    "raw_values_json",
                    "normalized_values_json",
                    "validation_errors_json",
                    "warnings_json",
                    "is_valid",
                }.issubset(import_row_column_names)
            )
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)

    def test_source_preview_digest_revision_round_trip(self):
        repo_root = Path(__file__).resolve().parents[2]
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{db_path}"
        env["PYTHONPATH"] = str(repo_root / "backend")

        def run_alembic(*arguments):
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    "backend/alembic.ini",
                    *arguments,
                ],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                msg=(
                    f"alembic {' '.join(arguments)} failed\n"
                    f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
                ),
            )

        def import_session_schema():
            connection = sqlite3.connect(db_path)
            try:
                columns = {
                    row[1]
                    for row in connection.execute(
                        "PRAGMA table_info(import_sessions)"
                    ).fetchall()
                }
                table_sql = connection.execute(
                    "SELECT sql FROM sqlite_master "
                    "WHERE type = 'table' AND name = 'import_sessions'"
                ).fetchone()[0]
                return columns, table_sql
            finally:
                connection.close()

        try:
            run_alembic("upgrade", "head")
            columns, table_sql = import_session_schema()
            self.assertIn("source_preview_schema_version", columns)
            self.assertIn("source_preview_digest", columns)
            self.assertIn(
                "ck_import_sessions_source_preview_digest_pair",
                table_sql,
            )

            run_alembic("downgrade", "c9d0e1f2a3b4")
            columns, table_sql = import_session_schema()
            self.assertNotIn("source_preview_schema_version", columns)
            self.assertNotIn("source_preview_digest", columns)
            self.assertNotIn(
                "ck_import_sessions_source_preview_digest_pair",
                table_sql,
            )

            run_alembic("upgrade", "head")
            columns, table_sql = import_session_schema()
            self.assertIn("source_preview_schema_version", columns)
            self.assertIn("source_preview_digest", columns)
            self.assertIn(
                "ck_import_sessions_source_preview_digest_pair",
                table_sql,
            )
        finally:
            if os.path.exists(db_path):
                os.remove(db_path)


if __name__ == "__main__":
    unittest.main()
