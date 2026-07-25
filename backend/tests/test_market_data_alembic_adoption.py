from __future__ import annotations

import importlib.util
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine, inspect

from database import Base
import models  # noqa: F401 - register every model table on Base.metadata


MARKET_TABLES = (
    "provider_symbol_mappings",
    "latest_market_quotes",
    "price_bars_daily",
    "market_data_watermarks",
)
PREVIOUS_REVISION = "8b9cad101112"
HEAD_REVISION = "e5f6a7b8c9d0"


class MarketDataAlembicAdoptionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.repo_root = Path(__file__).resolve().parents[2]

    def _new_database(self) -> Path:
        fd, raw_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        path = Path(raw_path)
        self.addCleanup(lambda: path.unlink(missing_ok=True))
        return path

    def _run_alembic(self, database_path: Path, *arguments: str) -> subprocess.CompletedProcess:
        env = os.environ.copy()
        env["DATABASE_URL"] = f"sqlite:///{database_path}"
        env["PYTHONPATH"] = str(self.repo_root / "backend")
        return subprocess.run(
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
        )

    def _upgrade_to_previous_revision(self, database_path: Path) -> None:
        result = self._run_alembic(
            database_path,
            "upgrade",
            PREVIOUS_REVISION,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=f"upgrade failed\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}",
        )

    def _create_model_market_tables(self, database_path: Path) -> None:
        engine = create_engine(f"sqlite:///{database_path}")
        try:
            for table_name in MARKET_TABLES:
                Base.metadata.tables[table_name].create(bind=engine)
        finally:
            engine.dispose()

    def _revision(self, database_path: Path) -> str:
        with sqlite3.connect(database_path) as connection:
            row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        self.assertIsNotNone(row)
        return row[0]

    def _load_migration(self):
        migration_path = (
            self.repo_root
            / "backend"
            / "alembic"
            / "versions"
            / "9cad10111213_add_market_data_persistence.py"
        )
        spec = importlib.util.spec_from_file_location(
            "market_data_migration_9cad10111213",
            migration_path,
        )
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        migration = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(migration)
        return migration

    def _assert_adoption_rejected(
        self,
        database_path: Path,
        *expected_messages: str,
    ) -> None:
        result = self._run_alembic(database_path, "upgrade", "head")
        output = result.stdout + result.stderr
        self.assertNotEqual(result.returncode, 0, msg=output)
        for expected_message in expected_messages:
            self.assertIn(expected_message, output)
        self.assertEqual(self._revision(database_path), PREVIOUS_REVISION)

    def test_complete_model_schema_is_adopted_and_remains_reversible(self):
        database_path = self._new_database()
        self._upgrade_to_previous_revision(database_path)
        self._create_model_market_tables(database_path)

        adoption = self._run_alembic(database_path, "upgrade", "head")
        self.assertEqual(
            adoption.returncode,
            0,
            msg=f"adoption failed\nSTDOUT:\n{adoption.stdout}\nSTDERR:\n{adoption.stderr}",
        )
        self.assertEqual(self._revision(database_path), HEAD_REVISION)

        downgrade = self._run_alembic(
            database_path,
            "downgrade",
            PREVIOUS_REVISION,
        )
        self.assertEqual(
            downgrade.returncode,
            0,
            msg=f"downgrade failed\nSTDOUT:\n{downgrade.stdout}\nSTDERR:\n{downgrade.stderr}",
        )
        with sqlite3.connect(database_path) as connection:
            remaining_tables = {
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'"
                ).fetchall()
            }
        self.assertTrue(set(MARKET_TABLES).isdisjoint(remaining_tables))

        clean_upgrade = self._run_alembic(database_path, "upgrade", "head")
        self.assertEqual(
            clean_upgrade.returncode,
            0,
            msg=(
                "clean re-upgrade failed\n"
                f"STDOUT:\n{clean_upgrade.stdout}\nSTDERR:\n{clean_upgrade.stderr}"
            ),
        )
        self.assertEqual(self._revision(database_path), HEAD_REVISION)

    def test_clean_migration_schema_satisfies_full_adoption_contract(self):
        database_path = self._new_database()
        upgrade = self._run_alembic(database_path, "upgrade", "head")
        self.assertEqual(
            upgrade.returncode,
            0,
            msg=f"upgrade failed\nSTDOUT:\n{upgrade.stdout}\nSTDERR:\n{upgrade.stderr}",
        )
        engine = create_engine(f"sqlite:///{database_path}")
        try:
            self._load_migration()._validate_existing_market_schema(inspect(engine))
        finally:
            engine.dispose()

    def test_adoption_rejects_missing_normal_index(self):
        database_path = self._new_database()
        self._upgrade_to_previous_revision(database_path)
        self._create_model_market_tables(database_path)
        with sqlite3.connect(database_path) as connection:
            connection.execute("DROP INDEX ix_latest_market_quotes_asset_received")

        self._assert_adoption_rejected(
            database_path,
            "missing index ix_latest_market_quotes_asset_received",
        )

    def test_adoption_rejects_wrong_partial_unique_index_predicate(self):
        database_path = self._new_database()
        self._upgrade_to_previous_revision(database_path)
        self._create_model_market_tables(database_path)
        with sqlite3.connect(database_path) as connection:
            connection.execute(
                "DROP INDEX uq_provider_symbol_mappings_asset_provider_market"
            )
            connection.execute(
                "CREATE UNIQUE INDEX "
                "uq_provider_symbol_mappings_asset_provider_market "
                "ON provider_symbol_mappings "
                "(asset_id, provider_key, provider_market) "
                "WHERE instrument_id IS NOT NULL"
            )

        self._assert_adoption_rejected(
            database_path,
            "index uq_provider_symbol_mappings_asset_provider_market has predicate",
            "expected 'instrument_idisnull'",
        )

    def test_adoption_rejects_missing_foreign_key_and_unique_constraint(self):
        database_path = self._new_database()
        self._upgrade_to_previous_revision(database_path)
        engine = create_engine(f"sqlite:///{database_path}")
        try:
            for table_name in (
                "provider_symbol_mappings",
                "price_bars_daily",
                "market_data_watermarks",
            ):
                Base.metadata.tables[table_name].create(bind=engine)
        finally:
            engine.dispose()

        with sqlite3.connect(database_path) as connection:
            connection.executescript(
                """
                CREATE TABLE latest_market_quotes (
                    id INTEGER NOT NULL PRIMARY KEY,
                    asset_id INTEGER NOT NULL,
                    provider VARCHAR(50) NOT NULL,
                    price NUMERIC(20, 8) NOT NULL,
                    previous_close NUMERIC(20, 8),
                    open_price NUMERIC(20, 8),
                    high_price NUMERIC(20, 8),
                    low_price NUMERIC(20, 8),
                    volume NUMERIC(30, 8),
                    change_amount NUMERIC(20, 8),
                    change_percent NUMERIC(20, 8),
                    currency VARCHAR(10),
                    market_time DATETIME,
                    received_at DATETIME NOT NULL,
                    quality_status VARCHAR(30) NOT NULL,
                    raw_payload JSON,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                );
                CREATE INDEX ix_latest_market_quotes_asset_received
                    ON latest_market_quotes (asset_id, received_at);
                CREATE INDEX ix_latest_market_quotes_provider_received
                    ON latest_market_quotes (provider, received_at);
                """
            )

        self._assert_adoption_rejected(
            database_path,
            "latest_market_quotes: missing foreign key",
            "latest_market_quotes: missing unique constraint "
            "uq_latest_market_quotes_asset_provider",
        )

    def test_adoption_rejects_partial_table_set(self):
        database_path = self._new_database()
        self._upgrade_to_previous_revision(database_path)
        engine = create_engine(f"sqlite:///{database_path}")
        try:
            Base.metadata.tables["latest_market_quotes"].create(bind=engine)
        finally:
            engine.dispose()

        self._assert_adoption_rejected(
            database_path,
            "Partial market-data schema already exists; missing tables:",
        )

    def test_partial_predicate_normalization_accepts_postgresql_shape(self):
        migration = self._load_migration()

        predicate = migration._index_predicate(
            {
                "dialect_options": {
                    "postgresql_where": (
                        '("provider_symbol_mappings"."instrument_id" IS NULL)'
                    )
                }
            },
            dialect_name="postgresql",
            table_name="provider_symbol_mappings",
        )

        self.assertEqual(predicate, "instrument_idisnull")


if __name__ == "__main__":
    unittest.main()
