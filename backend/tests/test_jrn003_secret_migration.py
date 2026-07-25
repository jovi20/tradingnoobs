from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


class JRN003SecretMigrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]

    def _run_alembic(self, database_path: Path, *arguments: str) -> None:
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{database_path}"
        env["PYTHONPATH"] = str(self.repo_root / "backend")
        result = subprocess.run(
            [
                sys.executable,
                "-m",
                "alembic",
                "-c",
                "backend/alembic.ini",
                *arguments,
            ],
            cwd=self.repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_forward_migration_drops_user_secret_columns_and_clears_alias_rows(self):
        fd, raw_path = tempfile.mkstemp(suffix=".sqlite")
        os.close(fd)
        database_path = Path(raw_path)
        self.addCleanup(lambda: database_path.unlink(missing_ok=True))
        self._run_alembic(database_path, "upgrade", "9cad10111213")

        with sqlite3.connect(database_path) as connection:
            connection.execute(
                """
                INSERT INTO users (
                    public_id, email, email_normalized, hashed_password,
                    status, is_active, role
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    "migration-user",
                    "migration@example.com",
                    "migration@example.com",
                    "hash",
                    "ACTIVE",
                    1,
                    "user",
                ),
            )
            user_id = connection.execute(
                "SELECT id FROM users WHERE public_id = ?",
                ("migration-user",),
            ).fetchone()[0]
            connection.execute(
                """
                INSERT INTO user_settings (
                    user_id, theme, ibkr_flex_query_id, ibkr_flex_token,
                    binance_api_key, binance_api_secret, finnhub_api_key,
                    llm_api_url, llm_api_key
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    "dark",
                    "query-secret",
                    "flex-secret",
                    "binance-key",
                    "binance-secret",
                    "market-secret",
                    "https://llm.invalid/v1",
                    "llm-secret",
                ),
            )
            connection.executemany(
                "INSERT INTO system_settings (key, value) VALUES (?, ?)",
                (
                    ("FINNHUB-API-TOKEN", "legacy-market-secret"),
                    ("ibkr_flex_password", "legacy-broker-secret"),
                    ("ordinary_retention_days", "30"),
                ),
            )
            connection.executemany(
                "INSERT INTO platform_settings (key, value) VALUES (?, ?)",
                (
                    ("prod-openai-api-key", "legacy-llm-secret"),
                    ("llm_model", "gpt-5"),
                ),
            )
            connection.commit()

        self._run_alembic(database_path, "upgrade", "head")

        with sqlite3.connect(database_path) as connection:
            columns = {
                row[1]
                for row in connection.execute("PRAGMA table_info(user_settings)")
            }
            for removed_column in (
                "ibkr_flex_query_id",
                "ibkr_flex_token",
                "binance_api_key",
                "binance_api_secret",
                "finnhub_api_key",
                "llm_api_url",
                "llm_api_key",
            ):
                self.assertNotIn(removed_column, columns)
            self.assertEqual(
                connection.execute(
                    "SELECT theme FROM user_settings WHERE user_id = ?",
                    (user_id,),
                ).fetchone()[0],
                "dark",
            )
            self.assertEqual(
                connection.execute(
                    "SELECT key FROM system_settings ORDER BY key"
                ).fetchall(),
                [("ordinary_retention_days",)],
            )
            self.assertEqual(
                connection.execute(
                    "SELECT key FROM platform_settings ORDER BY key"
                ).fetchall(),
                [("llm_model",)],
            )
            self.assertEqual(
                connection.execute("SELECT version_num FROM alembic_version").fetchone()[0],
                "e5f6a7b8c9d0",
            )
