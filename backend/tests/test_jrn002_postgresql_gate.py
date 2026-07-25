from __future__ import annotations

import asyncio
import os
import re
import subprocess
import sys
import time
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from threading import Event
from unittest.mock import patch

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import HTTPException
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.orm import sessionmaker

from models import (
    AccountLedgerEntry,
    AssetMaster,
    AuthRateLimitBucket,
    IdempotencyKey,
    ImportRow,
    ImportSession,
    LedgerPostingKind,
    PositionEvent,
    PositionEventType,
    TradeInstrument,
    TradeInstrumentType,
    Transaction,
    TransactionType,
    TradingAccount,
    TradingPosition,
    TradingPositionSide,
    TradingPositionStatus,
    User,
)
from services.account_ledger_service import (
    create_or_replay_posting,
    sync_opening_balance_to_account_ledger,
    sync_transaction_to_account_ledger,
)
from services.auth_rate_limit_service import consume_auth_attempt
from services.auth_service import authenticate_user, create_user
from services.idempotency_service import begin_idempotent_request
from services.generic_import_confirm_service import confirm_generic_bootstrap
from services.financial_command_service import (
    lock_owned_account,
    permanently_forbid_account_hard_delete,
)
from services.instrument_identity_service import InstrumentIdentity
from schemas import TradingAccountUpdate
from routers.accounts import delete_account, update_account
from services.trading_position_write_service import (
    append_truth_trade_event,
    lock_owned_truth_position,
    reverse_latest_truth_trade_event,
)
from services.truth_native_open_service import (
    OpenPositionExistsError,
    create_truth_native_open,
    lock_owned_trading_account,
)


POSTGRES_URL_ENV = "JRN002_POSTGRES_URL"
PRE_EXTENSION_FIXTURE_REVISION = "5e6f7a8b9cad"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _database_url(base_url: URL, database_name: str) -> str:
    return base_url.set(database=database_name).render_as_string(hide_password=False)


def _alembic_head() -> str:
    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    script = ScriptDirectory.from_config(config)
    head = script.get_current_head()
    assert head is not None
    return head


def _run_alembic(database_url: str, *arguments: str) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url
    env["PYTHONPATH"] = str(REPO_ROOT / "backend")
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "alembic",
            "-c",
            "backend/alembic.ini",
            *arguments,
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (
        f"alembic {' '.join(arguments)} failed\n"
        f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
    )


def test_jrn006_postgresql_backfill_guard_and_reupgrade(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "b2c3d4e5f6a7")
    with engine.begin() as connection:
        user_id = connection.execute(
            text(
                """
                INSERT INTO users (
                    public_id, email, email_normalized, hashed_password,
                    status, is_active, role, timezone
                ) VALUES (
                    'jrn006-pg-user', 'jrn006-pg@example.com',
                    'jrn006-pg@example.com', 'hash',
                    'ACTIVE', true, 'user', 'UTC'
                ) RETURNING id
                """
            )
        ).scalar_one()
        account_id = connection.execute(
            text(
                """
                INSERT INTO trading_accounts (
                    public_id, user_id, name, broker, currency,
                    initial_balance, cash_balance, is_active
                ) VALUES (
                    'jrn006-pg-account', :user_id, 'JRN006', 'MANUAL',
                    'USD', 100, 9999, true
                ) RETURNING id
                """
            ),
            {"user_id": user_id},
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO account_ledger_entries (
                    public_id, user_id, account_id, entry_type,
                    occurred_at, currency, amount, amount_account_ccy,
                    fx_rate_to_account_ccy, source
                ) VALUES (
                    'jrn006-pg-legacy', :user_id, :account_id,
                    'REALIZED_PNL', '2026-07-24T10:00:00Z',
                    'USD', 12, 12, 1, 'LEGACY_BACKFILL'
                )
                """
            ),
            {"user_id": user_id, "account_id": account_id},
        )
        transaction_id = connection.execute(
            text(
                """
                INSERT INTO transactions (
                    public_id, account_id, type, amount, currency, date
                ) VALUES (
                    'jrn006-pg-transaction', :account_id, 'DEPOSIT',
                    5, 'USD', '2026-07-24T11:00:00Z'
                ) RETURNING id
                """
            ),
            {"account_id": account_id},
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO account_ledger_entries (
                    public_id, user_id, account_id, transaction_id,
                    entry_type, occurred_at, currency, amount,
                    amount_account_ccy, fx_rate_to_account_ccy, source
                ) VALUES
                    (
                        'jrn006-pg-duplicate-1', :user_id, :account_id,
                        :transaction_id, 'DEPOSIT',
                        '2026-07-24T11:00:00Z', 'USD', 5, 5, 1,
                        'TRANSACTION'
                    ),
                    (
                        'jrn006-pg-duplicate-2', :user_id, :account_id,
                        :transaction_id, 'DEPOSIT',
                        '2026-07-24T11:00:00Z', 'USD', 5, 5, 1,
                        'TRANSACTION'
                    ),
                    (
                        'jrn006-pg-amount-mismatch', :user_id, :account_id,
                        NULL, 'CASH_ADJUSTMENT',
                        '2026-07-24T12:00:00Z', 'USD', 3, 4, 1,
                        'LEGACY_BACKFILL'
                    )
                """
            ),
            {
                "user_id": user_id,
                "account_id": account_id,
                "transaction_id": transaction_id,
            },
        )

    _run_alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT accounting_health
                FROM trading_accounts
                WHERE public_id = 'jrn006-pg-account'
                """
            )
        ).one()
        assert row.accounting_health == "ACCOUNTING_RECONCILIATION_REQUIRED"
        assert connection.execute(
            text(
                """
                SELECT count(*)
                FROM accounting_reconciliation_cases
                WHERE account_id = :account_id
                  AND status = 'OPEN'
                """
            ),
            {"account_id": account_id},
        ).scalar_one() == 4
        assert connection.execute(
            text(
                """
                SELECT count(DISTINCT source_fact_public_id)
                FROM account_ledger_entries
                WHERE account_id = :account_id
                  AND posting_kind = 'LEGACY_UNRESOLVED'
                """
            ),
            {"account_id": account_id},
        ).scalar_one() == 4
        assert connection.execute(
            text(
                """
                SELECT count(*)
                FROM account_ledger_entries
                WHERE account_id = :account_id
                  AND posting_kind = 'OPENING_BALANCE'
                """
            ),
            {"account_id": account_id},
        ).scalar_one() == 1

    with engine.connect() as connection:
        transaction = connection.begin()
        with pytest.raises(DBAPIError, match="append-only"):
            connection.execute(
                text(
                    """
                    UPDATE account_ledger_entries
                    SET amount = amount + 1
                    WHERE public_id = 'jrn006-pg-legacy'
                    """
                )
            )
        transaction.rollback()

    _run_alembic(database_url, "downgrade", "b2c3d4e5f6a7")
    _run_alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.execute(
            text(
                """
                SELECT count(*)
                FROM accounting_reconciliation_cases
                WHERE account_id = :account_id
                  AND status = 'OPEN'
                """
            ),
            {"account_id": account_id},
        ).scalar_one() == 4

    SessionLocal = sessionmaker(bind=engine)
    occurred_at = datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc)

    def create_same_posting() -> str:
        with SessionLocal() as db:
            entry = create_or_replay_posting(
                db,
                user_id=user_id,
                account_id=account_id,
                source_fact_public_id="jrn006-concurrent-fact",
                posting_kind=LedgerPostingKind.DEPOSIT,
                occurred_at=occurred_at,
                currency="USD",
                amount=Decimal("5"),
                source="JRN006_TEST",
            )
            db.commit()
            return entry.public_id

    with ThreadPoolExecutor(max_workers=2) as executor:
        public_ids = list(executor.map(lambda _: create_same_posting(), range(2)))
    assert public_ids[0] == public_ids[1]
    with engine.connect() as connection:
        assert connection.execute(
            text(
                """
                SELECT count(*)
                FROM account_ledger_entries
                WHERE source_fact_public_id = 'jrn006-concurrent-fact'
                  AND posting_kind = 'DEPOSIT'
                """
            )
        ).scalar_one() == 1


@pytest.fixture
def postgres_database() -> Iterator[tuple[Engine, str]]:
    raw_url = os.getenv(POSTGRES_URL_ENV)
    if not raw_url:
        pytest.skip(f"{POSTGRES_URL_ENV} is required for PostgreSQL gate tests")

    base_url = make_url(raw_url)
    assert base_url.get_backend_name() == "postgresql", (
        f"{POSTGRES_URL_ENV} must use PostgreSQL, got {base_url.get_backend_name()}"
    )
    database_name = f"jrn002_{uuid.uuid4().hex}"
    assert re.fullmatch(r"jrn002_[0-9a-f]{32}", database_name)

    admin_engine = create_engine(
        base_url.render_as_string(hide_password=False),
        isolation_level="AUTOCOMMIT",
    )
    database_url = _database_url(base_url, database_name)
    database_engine: Engine | None = None
    try:
        with admin_engine.connect() as connection:
            server_version_num = int(
                connection.execute(text("SHOW server_version_num")).scalar_one()
            )
            assert 160000 <= server_version_num < 170000, (
                f"PostgreSQL 16 is required, got server_version_num={server_version_num}"
            )
            connection.execute(text(f'CREATE DATABASE "{database_name}"'))

        database_engine = create_engine(database_url)
        yield database_engine, database_url
    finally:
        if database_engine is not None:
            database_engine.dispose()
        with admin_engine.connect() as connection:
            connection.execute(
                text(
                    """
                    SELECT pg_terminate_backend(pid)
                    FROM pg_stat_activity
                    WHERE datname = :database_name
                      AND pid <> pg_backend_pid()
                    """
                ),
                {"database_name": database_name},
            )
            connection.execute(text(f'DROP DATABASE IF EXISTS "{database_name}"'))
        admin_engine.dispose()


def test_empty_postgresql_database_upgrades_to_current_head(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "head")

    inspector = inspect(engine)
    assert {
        "users",
        "trading_accounts",
        "trading_positions",
        "position_events",
        "account_ledger_entries",
        "broker_sync_runs",
        "broker_executions",
        "provider_symbol_mappings",
        "latest_market_quotes",
        "price_bars_daily",
        "market_data_watermarks",
        "import_source_bindings",
        "source_statements",
        "external_source_observations",
        "statement_execution_sightings",
        "external_executions",
        "external_trade_applications",
        "statement_coverage_acceptances",
        "source_reconciliation_cases",
        "source_case_evidence_sightings",
    } <= set(inspector.get_table_names())
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == _alembic_head()
        assert connection.execute(
            text(
                """
                SELECT count(*)
                FROM pg_trigger
                WHERE NOT tgisinternal
                  AND tgname LIKE 'trg_%_append_only'
                  AND tgrelid IN (
                      'source_statements'::regclass,
                      'external_source_observations'::regclass,
                      'statement_execution_sightings'::regclass,
                      'statement_coverage_acceptances'::regclass,
                      'source_case_evidence_sightings'::regclass
                  )
                """
            )
        ).scalar_one() == 5
    assert {
        "reverses_transaction_id",
        "actor_user_id",
        "request_id",
        "reversal_reason",
    } <= {
        column["name"] for column in inspector.get_columns("transactions")
    }
    assert {"actor_user_id", "request_id"} <= {
        column["name"] for column in inspector.get_columns("position_events")
    }
    assert "hard_delete_eligible" in {
        column["name"] for column in inspector.get_columns("trading_accounts")
    }


def test_jrn009_populated_upgrade_downgrade_reupgrade_preserves_cash_facts(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "d4e5f6a7b8c9")
    with engine.begin() as connection:
        user_id = connection.execute(
            text(
                """
                INSERT INTO users (
                    public_id, email, email_normalized, hashed_password,
                    status, is_active, role, timezone
                ) VALUES (
                    'jrn009-upgrade-user', 'jrn009-upgrade@example.com',
                    'jrn009-upgrade@example.com', 'hash',
                    'ACTIVE', true, 'user', 'UTC'
                ) RETURNING id
                """
            )
        ).scalar_one()
        account_id = connection.execute(
            text(
                """
                INSERT INTO trading_accounts (
                    public_id, user_id, name, broker, currency, is_active,
                    accounting_health, trade_source_state
                ) VALUES (
                    'jrn009-upgrade-account', :user_id, 'Upgrade', 'MANUAL',
                    'USD', true, 'ACCOUNTING_HEALTHY', 'MANUAL'
                ) RETURNING id
                """
            ),
            {"user_id": user_id},
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO transactions (
                    public_id, account_id, type, amount, currency, date,
                    description
                ) VALUES (
                    'jrn009-existing-cash', :account_id, 'DEPOSIT', 25,
                    'USD', '2026-07-25T12:00:00+00:00', 'Existing cash'
                )
                """
            ),
            {"account_id": account_id},
        )

    _run_alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT amount FROM transactions "
                "WHERE public_id = 'jrn009-existing-cash'"
            )
        ).scalar_one() == Decimal("25.00")
        assert connection.execute(
            text(
                "SELECT hard_delete_eligible FROM trading_accounts "
                "WHERE public_id = 'jrn009-upgrade-account'"
            )
        ).scalar_one() is False

    _run_alembic(database_url, "downgrade", "d4e5f6a7b8c9")
    assert "reverses_transaction_id" not in {
        column["name"] for column in inspect(engine).get_columns("transactions")
    }
    assert "hard_delete_eligible" not in {
        column["name"] for column in inspect(engine).get_columns("trading_accounts")
    }
    _run_alembic(database_url, "upgrade", "head")
    with engine.connect() as connection:
        assert connection.execute(
            text(
                "SELECT amount FROM transactions "
                "WHERE public_id = 'jrn009-existing-cash'"
            )
        ).scalar_one() == Decimal("25.00")


def test_jrn009_postgresql_guards_and_account_lock_prevent_duplicate_reversal(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "head")
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    with SessionLocal() as db:
        user = create_user(db, "jrn009-lock@example.com", "StrongPassword-123")
        user.timezone = "UTC"
        account = TradingAccount(
            public_id="jrn009-lock-account",
            user_id=user.id,
            name="JRN009 Lock",
            broker="MANUAL",
            currency="USD",
            is_active=True,
        )
        db.add(account)
        db.flush()
        original = Transaction(
            public_id="jrn009-original-transaction",
            account_id=account.id,
            type=TransactionType.WITHDRAWAL,
            amount=Decimal("-25"),
            currency="USD",
            date=datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
            actor_user_id=user.id,
            request_id="original-request",
        )
        db.add(original)
        db.flush()
        sync_transaction_to_account_ledger(db, transaction=original, account=account)
        db.commit()
        user_id = user.id
        original_id = original.id

    with engine.connect() as connection:
        transaction_id = connection.execute(
            text(
                "SELECT id FROM transactions "
                "WHERE public_id = 'jrn009-original-transaction'"
            )
        ).scalar_one()
        with pytest.raises(DBAPIError):
            connection.execute(
                text("UPDATE transactions SET amount = -30 WHERE id = :id"),
                {"id": transaction_id},
            )
        connection.rollback()
        with pytest.raises(DBAPIError):
            connection.execute(
                text("DELETE FROM transactions WHERE id = :id"),
                {"id": transaction_id},
            )
        connection.rollback()

    def reverse_once(index: int) -> str:
        with SessionLocal() as db:
            account = lock_owned_account(
                db,
                user_id=user_id,
                account_public_id="jrn009-lock-account",
            )
            assert account is not None
            if db.query(Transaction.id).filter(
                Transaction.reverses_transaction_id == original_id
            ).first() is not None:
                db.rollback()
                return "CONFLICT"
            reversal = Transaction(
                public_id=f"jrn009-reversal-{index}",
                account_id=account.id,
                type=TransactionType.WITHDRAWAL,
                amount=Decimal("25"),
                currency="USD",
                date=datetime(2026, 7, 25, 13, index, tzinfo=timezone.utc),
                reverses_transaction_id=original_id,
                actor_user_id=user_id,
                request_id=f"reversal-request-{index}",
                reversal_reason="Concurrent correction",
            )
            db.add(reversal)
            db.commit()
            return "CREATED"

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(reverse_once, range(2)))
    assert sorted(results) == ["CONFLICT", "CREATED"]
    with SessionLocal() as db:
        assert db.query(Transaction).filter(
            Transaction.reverses_transaction_id == original_id
        ).count() == 1

        account = TradingAccount(
            public_id="jrn009-currency-lock-account",
            user_id=user_id,
            name="JRN009 Currency Lock",
            broker="MANUAL",
            currency="USD",
            is_active=True,
        )
        db.add(account)
        db.commit()

    writer_locked = Event()
    updater_started = Event()

    def create_first_history_marker() -> None:
        with SessionLocal() as db:
            account = lock_owned_account(
                db,
                user_id=user_id,
                account_public_id="jrn009-currency-lock-account",
            )
            assert account is not None
            account.hard_delete_eligible = False
            writer_locked.set()
            assert updater_started.wait(timeout=5)
            time.sleep(0.2)
            db.commit()

    def race_currency_update() -> str:
        assert writer_locked.wait(timeout=5)
        updater_started.set()
        with SessionLocal() as db:
            user = db.get(User, user_id)
            assert user is not None
            try:
                with patch(
                    "routers.accounts._require_release_currency",
                    return_value="EUR",
                ):
                    asyncio.run(
                        update_account(
                            "jrn009-currency-lock-account",
                            TradingAccountUpdate(currency="EUR"),
                            current_user=user,
                            db=db,
                        )
                    )
            except HTTPException as exc:
                assert exc.status_code == 409
                assert exc.detail["code"] == "ACCOUNT_BASE_CURRENCY_FROZEN"
                return "FROZEN"
            return "UPDATED"

    with ThreadPoolExecutor(max_workers=2) as executor:
        writer_future = executor.submit(create_first_history_marker)
        updater_future = executor.submit(race_currency_update)
        writer_future.result()
        assert updater_future.result() == "FROZEN"

    with SessionLocal() as db:
        account = db.query(TradingAccount).filter(
            TradingAccount.public_id == "jrn009-currency-lock-account"
        ).one()
        assert account.currency == "USD"
        assert account.hard_delete_eligible is False


def test_populated_pre_extension_fixture_upgrades_without_data_loss(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", PRE_EXTENSION_FIXTURE_REVISION)

    with engine.begin() as connection:
        user_id = connection.execute(
            text(
                """
                INSERT INTO users (
                    public_id,
                    email,
                    email_normalized,
                    hashed_password,
                    status,
                    is_active,
                    role,
                    timezone
                )
                VALUES (
                    'fixture-user-public-id',
                    'fixture@example.com',
                    'fixture@example.com',
                    'fixture-password-hash',
                    'ACTIVE',
                    true,
                    'user',
                    'Asia/Shanghai'
                )
                RETURNING id
                """
            )
        ).scalar_one()
        connection.execute(
            text(
                """
                INSERT INTO user_settings (
                    user_id,
                    theme,
                    up_color,
                    display_currency
                )
                VALUES (:user_id, 'dark', 'red', 'USD')
                """
            ),
            {"user_id": user_id},
        )

    _run_alembic(database_url, "upgrade", "head")

    inspector = inspect(engine)
    user_settings_columns = {
        column["name"] for column in inspector.get_columns("user_settings")
    }
    assert {
        "ibkr_flex_start_date",
        "binance_market_type",
        "binance_symbols",
    } <= user_settings_columns
    assert {
        "ibkr_flex_query_id",
        "ibkr_flex_token",
        "binance_api_key",
        "binance_api_secret",
        "finnhub_api_key",
        "llm_api_url",
        "llm_api_key",
    }.isdisjoint(user_settings_columns)
    assert {"broker_sync_runs", "broker_executions"} <= set(
        inspector.get_table_names()
    )

    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    users.public_id,
                    users.timezone,
                    user_settings.theme,
                    user_settings.display_currency
                FROM users
                JOIN user_settings ON user_settings.user_id = users.id
                WHERE users.email_normalized = 'fixture@example.com'
                """
            )
        ).one()
        assert tuple(row) == (
            "fixture-user-public-id",
            "Asia/Shanghai",
            "dark",
            "USD",
        )
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == _alembic_head()


def test_postgresql_secret_governance_migration_downgrades_and_reupgrades(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "head")
    _run_alembic(database_url, "downgrade", "9cad10111213")

    downgraded_columns = {
        column["name"] for column in inspect(engine).get_columns("user_settings")
    }
    assert {
        "ibkr_flex_query_id",
        "ibkr_flex_token",
        "binance_api_key",
        "binance_api_secret",
        "finnhub_api_key",
        "llm_api_url",
        "llm_api_key",
    } <= downgraded_columns

    _run_alembic(database_url, "upgrade", "head")

    upgraded_columns = {
        column["name"] for column in inspect(engine).get_columns("user_settings")
    }
    assert {
        "ibkr_flex_query_id",
        "ibkr_flex_token",
        "binance_api_key",
        "binance_api_secret",
        "finnhub_api_key",
        "llm_api_url",
        "llm_api_key",
    }.isdisjoint(upgraded_columns)
    assert {
        "invitations",
        "security_audit_events",
        "auth_rate_limit_buckets",
    } <= set(inspect(engine).get_table_names())
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == _alembic_head()


def test_postgresql_auth_account_timezone_and_canonical_write_integration(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "head")
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    with SessionLocal() as db:
        user = create_user(db, "pg-gate@example.com", "StrongPassword-123")
        user.timezone = "Asia/Shanghai"
        db.add(user)
        db.commit()

        authenticated = authenticate_user(
            db,
            "PG-GATE@example.com",
            "StrongPassword-123",
        )
        assert authenticated is not None
        assert authenticated.timezone == "Asia/Shanghai"
        assert authenticated.last_login_at is not None

        account = TradingAccount(
            user_id=authenticated.id,
            name="PostgreSQL Gate",
            broker="MANUAL",
            currency="USD",
            initial_balance=Decimal("10000.00"),
            is_active=True,
        )
        db.add(account)
        db.flush()
        opening_entry = sync_opening_balance_to_account_ledger(db, account=account)
        assert opening_entry is not None

        asset = AssetMaster(
            canonical_code="US:AAPL",
            display_symbol="AAPL",
            name="Apple Inc.",
            asset_type="STOCK",
            quote_currency="USD",
            status="ACTIVE",
            metadata_json={},
        )
        db.add(asset)
        db.flush()
        instrument = TradeInstrument(
            asset_id=asset.id,
            instrument_type=TradeInstrumentType.SPOT,
            display_name="AAPL",
            contract_symbol="AAPL",
            status="ACTIVE",
        )
        db.add(instrument)
        db.flush()

        occurred_at = datetime(2026, 7, 25, 1, 30, tzinfo=timezone.utc)
        position = TradingPosition(
            user_id=authenticated.id,
            account_id=account.id,
            instrument_id=instrument.id,
            status=TradingPositionStatus.OPEN,
            side=TradingPositionSide.LONG,
            opened_at=occurred_at,
            base_currency="USD",
            cost_basis_method="FIFO",
            quantity_opened=Decimal("0"),
            quantity_closed=Decimal("0"),
        )
        db.add(position)
        db.flush()
        event = append_truth_trade_event(
            db,
            position=position,
            event_type=PositionEventType.OPEN,
            quantity=Decimal("10"),
            price=Decimal("200"),
            currency="USD",
            occurred_at=occurred_at,
            fee_amount=Decimal("1"),
            fee_currency="USD",
        )
        db.commit()

        persisted_event = db.execute(
            select(PositionEvent).where(PositionEvent.id == event.id)
        ).scalar_one()
        persisted_user = db.execute(
            select(User).where(User.id == authenticated.id)
        ).scalar_one()
        persisted_ledger = db.execute(
            select(AccountLedgerEntry).where(
                AccountLedgerEntry.account_id == account.id,
                AccountLedgerEntry.source == "OPENING_BALANCE",
            )
        ).scalar_one()

        assert persisted_user.timezone == "Asia/Shanghai"
        assert persisted_event.event_time == occurred_at
        assert persisted_event.event_time.tzinfo is not None
        assert persisted_event.event_time.astimezone(timezone.utc) == occurred_at
        assert persisted_event.quantity == Decimal("10.00000000")
        assert position.quantity_opened == Decimal("10.00000000")
        assert persisted_ledger.amount == Decimal("10000.00000000")


def test_postgresql_auth_rate_limit_first_attempt_is_concurrency_safe(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "head")
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )

    def consume_and_commit() -> None:
        with SessionLocal() as db:
            consume_auth_attempt(
                db,
                action="LOGIN",
                dimension="IP",
                value="203.0.113.10",
                limit=20,
            )
            db.commit()

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(lambda _: consume_and_commit(), range(8)))

    with SessionLocal() as db:
        bucket = db.execute(select(AuthRateLimitBucket)).scalar_one()
        assert bucket.attempt_count == 8


def test_postgresql_idempotency_keys_are_owner_scoped_and_concurrency_safe(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "head")
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    with SessionLocal() as db:
        first_user = create_user(
            db,
            "idempotency-one@example.com",
            "StrongPassword-123",
        )
        second_user = create_user(
            db,
            "idempotency-two@example.com",
            "StrongPassword-123",
        )
        first_user_id = first_user.id
        second_user_id = second_user.id

        begin_idempotent_request(
            db,
            scope="owner-boundary",
            key="same-client-key",
            request_payload={"owner": "one"},
            user_id=first_user_id,
        )
        begin_idempotent_request(
            db,
            scope="owner-boundary",
            key="same-client-key",
            request_payload={"owner": "two"},
            user_id=second_user_id,
        )
        db.commit()

    def begin_and_commit() -> bool:
        with SessionLocal() as db:
            result = begin_idempotent_request(
                db,
                scope="concurrent-owner-boundary",
                key="same-owner-key",
                request_payload={"position": "one"},
                user_id=first_user_id,
            )
            db.commit()
            return result.created

    with ThreadPoolExecutor(max_workers=8) as executor:
        created_results = list(executor.map(lambda _: begin_and_commit(), range(8)))

    with SessionLocal() as db:
        owner_scoped_rows = db.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.scope == "owner-boundary",
                IdempotencyKey.key == "same-client-key",
            )
        ).scalars().all()
        concurrent_rows = db.execute(
            select(IdempotencyKey).where(
                IdempotencyKey.scope == "concurrent-owner-boundary",
                IdempotencyKey.key == "same-owner-key",
            )
        ).scalars().all()

        assert {row.user_id for row in owner_scoped_rows} == {
            first_user_id,
            second_user_id,
        }
        assert len(concurrent_rows) == 1
        assert created_results.count(True) == 1


def test_jrn007_postgresql_open_slot_and_instrument_races(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "head")
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    with SessionLocal() as db:
        user = User(
            public_id="jrn007-pg-user",
            email="jrn007-pg@example.com",
            email_normalized="jrn007-pg@example.com",
            hashed_password="hash",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        db.add(user)
        db.flush()
        accounts = [
            TradingAccount(
                public_id=f"jrn007-pg-account-{index}",
                user_id=user.id,
                name=f"JRN007 {index}",
                broker="IBKR",
                currency="USD",
                is_active=True,
            )
            for index in range(4)
        ]
        db.add_all(accounts)
        db.commit()
        user_id = user.id
        account_ids = [account.id for account in accounts]

    identity = InstrumentIdentity(
        asset_type="STOCK",
        market="US",
        exchange_code="NASDAQ",
        normalized_symbol="AAPL",
        instrument_type="SPOT",
        quote_currency="USD",
    )

    def open_and_commit(account_id: int, side: TradingPositionSide) -> str:
        with SessionLocal() as db:
            account = lock_owned_trading_account(
                db,
                user_id=user_id,
                account_id=account_id,
            )
            assert account is not None
            try:
                create_truth_native_open(
                    db,
                    user_id=user_id,
                    account=account,
                    strategy=None,
                    identity=identity,
                    side=side,
                    quantity=Decimal("1"),
                    price=Decimal("200"),
                    occurred_at=datetime(
                        2026,
                        7,
                        25,
                        10,
                        0,
                        tzinfo=timezone.utc,
                    ),
                )
                db.commit()
                return "CREATED"
            except OpenPositionExistsError:
                db.rollback()
                return "CONFLICT"

    with ThreadPoolExecutor(max_workers=2) as executor:
        instrument_results = list(
            executor.map(
                lambda account_id: open_and_commit(
                    account_id,
                    TradingPositionSide.LONG,
                ),
                account_ids[:2],
            )
        )
    assert instrument_results == ["CREATED", "CREATED"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        same_side_results = list(
            executor.map(
                lambda _: open_and_commit(
                    account_ids[2],
                    TradingPositionSide.LONG,
                ),
                range(2),
            )
        )
    assert sorted(same_side_results) == ["CONFLICT", "CREATED"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        opposite_side_results = list(
            executor.map(
                lambda side: open_and_commit(account_ids[3], side),
                (TradingPositionSide.LONG, TradingPositionSide.SHORT),
            )
        )
    assert opposite_side_results == ["CREATED", "CREATED"]

    with SessionLocal() as db:
        assert len(db.execute(select(AssetMaster)).scalars().all()) == 1
        assert len(db.execute(select(TradeInstrument)).scalars().all()) == 1
        assert len(db.execute(select(TradingPosition)).scalars().all()) == 5


def test_jrn008_postgresql_lifecycle_lock_serializes_sequence_and_close_races(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "head")
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    with SessionLocal() as db:
        user = User(
            public_id="jrn008-pg-user",
            email="jrn008-pg@example.com",
            email_normalized="jrn008-pg@example.com",
            hashed_password="hash",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        account = TradingAccount(
            public_id="jrn008-pg-account",
            user=user,
            name="JRN008",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        db.add_all([user, account])
        db.commit()
        user_id = user.id
        account_id = account.id

    identity = InstrumentIdentity(
        asset_type="STOCK",
        market="US",
        exchange_code="NASDAQ",
        normalized_symbol="MSFT",
        instrument_type="SPOT",
        quote_currency="USD",
    )
    with SessionLocal() as db:
        account = lock_owned_trading_account(
            db,
            user_id=user_id,
            account_id=account_id,
        )
        assert account is not None
        _, position, _ = create_truth_native_open(
            db,
            user_id=user_id,
            account=account,
            strategy=None,
            identity=identity,
            side=TradingPositionSide.LONG,
            quantity=Decimal("10"),
            price=Decimal("100"),
            occurred_at=datetime(2026, 7, 25, 10, 0, tzinfo=timezone.utc),
        )
        db.commit()
        position_public_id = position.public_id

    def append_and_commit(
        event_type: PositionEventType,
        quantity: Decimal,
        price: Decimal,
    ) -> str:
        with SessionLocal() as db:
            locked = lock_owned_truth_position(
                db,
                user_id=user_id,
                position_public_id=position_public_id,
            )
            assert locked is not None
            account, position = locked
            try:
                append_truth_trade_event(
                    db,
                    position=position,
                    account=account,
                    event_type=event_type,
                    quantity=quantity,
                    price=price,
                    currency="USD",
                    occurred_at=datetime(
                        2026,
                        7,
                        25,
                        11,
                        0,
                        tzinfo=timezone.utc,
                    ),
                )
                db.commit()
                return "CREATED"
            except ValueError:
                db.rollback()
                return "REJECTED"

    with ThreadPoolExecutor(max_workers=2) as executor:
        add_results = list(
            executor.map(
                lambda price: append_and_commit(
                    PositionEventType.ADD,
                    Decimal("1"),
                    price,
                ),
                (Decimal("101"), Decimal("102")),
            )
        )
    assert add_results == ["CREATED", "CREATED"]

    with ThreadPoolExecutor(max_workers=2) as executor:
        close_results = list(
            executor.map(
                lambda command: append_and_commit(*command),
                (
                    (
                        PositionEventType.REDUCE,
                        Decimal("8"),
                        Decimal("110"),
                    ),
                    (
                        PositionEventType.CLOSE,
                        Decimal("12"),
                        Decimal("111"),
                    ),
                ),
            )
        )
    assert sorted(close_results) == ["CREATED", "REJECTED"]

    with SessionLocal() as db:
        position = db.execute(
            select(TradingPosition).where(
                TradingPosition.public_id == position_public_id,
            )
        ).scalar_one()
        events = db.execute(
            select(PositionEvent)
            .where(PositionEvent.position_id == position.id)
            .order_by(PositionEvent.sequence_no.asc())
        ).scalars().all()
        assert [event.sequence_no for event in events] == list(
            range(1, len(events) + 1)
        )
        assert len(events) == 4
        assert position.quantity_closed in {Decimal("8.00000000"), Decimal("12.00000000")}


def test_jrn010_postgresql_reverse_close_vs_new_open_allows_at_most_one(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "head")
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    identity = InstrumentIdentity(
        asset_type="STOCK",
        market="US",
        exchange_code="NASDAQ",
        normalized_symbol="NVDA",
        instrument_type="SPOT",
        quote_currency="USD",
    )
    with SessionLocal() as db:
        user = User(
            public_id="jrn010-pg-user",
            email="jrn010-pg@example.com",
            email_normalized="jrn010-pg@example.com",
            hashed_password="hash",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        account = TradingAccount(
            public_id="jrn010-pg-account",
            user=user,
            name="JRN010",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        db.add_all([user, account])
        db.commit()
        user_id = user.id
        account_id = account.id

        locked_account = lock_owned_trading_account(
            db,
            user_id=user_id,
            account_id=account_id,
        )
        assert locked_account is not None
        _, position, _ = create_truth_native_open(
            db,
            user_id=user_id,
            account=locked_account,
            strategy=None,
            identity=identity,
            side=TradingPositionSide.LONG,
            quantity=Decimal("2"),
            price=Decimal("100"),
            occurred_at=datetime(2026, 7, 25, 10, 0, tzinfo=timezone.utc),
        )
        close = append_truth_trade_event(
            db,
            position=position,
            account=locked_account,
            event_type=PositionEventType.CLOSE,
            quantity=Decimal("2"),
            price=Decimal("110"),
            currency="USD",
            occurred_at=datetime(2026, 7, 25, 11, 0, tzinfo=timezone.utc),
        )
        db.commit()
        position_public_id = position.public_id
        close_public_id = close.public_id

    def reverse_and_commit() -> str:
        with SessionLocal() as db:
            locked = lock_owned_truth_position(
                db,
                user_id=user_id,
                position_public_id=position_public_id,
            )
            assert locked is not None
            _, position = locked
            close = db.execute(
                select(PositionEvent).where(
                    PositionEvent.public_id == close_public_id
                )
            ).scalar_one()
            try:
                reverse_latest_truth_trade_event(
                    db,
                    position=position,
                    event=close,
                    occurred_at=datetime(
                        2026, 7, 25, 12, 0, tzinfo=timezone.utc
                    ),
                    actor_user_id=user_id,
                    request_id="jrn010-race-reverse",
                    reason="Race correction",
                )
                db.commit()
                return "REVERSED"
            except ValueError:
                db.rollback()
                return "CONFLICT"

    def reopen_and_commit() -> str:
        with SessionLocal() as db:
            account = lock_owned_trading_account(
                db,
                user_id=user_id,
                account_id=account_id,
            )
            assert account is not None
            try:
                create_truth_native_open(
                    db,
                    user_id=user_id,
                    account=account,
                    strategy=None,
                    identity=identity,
                    side=TradingPositionSide.LONG,
                    quantity=Decimal("1"),
                    price=Decimal("111"),
                    occurred_at=datetime(
                        2026, 7, 25, 11, 30, tzinfo=timezone.utc
                    ),
                )
                db.commit()
                return "OPENED"
            except ValueError:
                db.rollback()
                return "CONFLICT"

    with ThreadPoolExecutor(max_workers=2) as executor:
        reverse_future = executor.submit(reverse_and_commit)
        open_future = executor.submit(reopen_and_commit)
        results = [reverse_future.result(), open_future.result()]

    assert results.count("CONFLICT") == 1
    assert sorted(results) in (
        ["CONFLICT", "OPENED"],
        ["CONFLICT", "REVERSED"],
    )


def test_jrn011_postgresql_session_create_serializes_account_delete(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "head")
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    with SessionLocal() as db:
        user = User(
            public_id="jrn011-pg-user",
            email="jrn011-pg@example.com",
            email_normalized="jrn011-pg@example.com",
            hashed_password="hash",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        account = TradingAccount(
            public_id="jrn011-pg-account",
            user=user,
            name="JRN011",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        db.add_all([user, account])
        db.commit()
        user_id = user.id
        account_id = account.id
        account_public_id = account.public_id

    account_locked = Event()
    allow_commit = Event()

    def create_session() -> None:
        with SessionLocal() as db:
            account = lock_owned_account(
                db,
                user_id=user_id,
                account_public_id=account_public_id,
            )
            assert account is not None
            command = begin_idempotent_request(
                db,
                scope="GENERIC_IMPORT_UPLOAD_V1",
                key="sha256:jrn011-postgresql-race",
                request_payload={
                    "account_public_id": account_public_id,
                    "adapter_kind": "GENERIC_BOOTSTRAP",
                    "file_hash": "sha256:fixture",
                },
                user_id=user_id,
                ttl_seconds=None,
            )
            db.add(
                ImportSession(
                    public_id="jrn011-pg-session",
                    user_id=user_id,
                    account_id=account.id,
                    upload_idempotency_id=command.record.id,
                    adapter_kind="GENERIC_BOOTSTRAP",
                    file_format="CSV_UTF8",
                    file_hash="sha256:fixture",
                    file_size_bytes=0,
                    original_filename="fixture.csv",
                    status="UPLOADING",
                    expires_at=datetime(
                        2026,
                        7,
                        26,
                        10,
                        0,
                        tzinfo=timezone.utc,
                    ),
                )
            )
            permanently_forbid_account_hard_delete(account)
            db.flush()
            account_locked.set()
            assert allow_commit.wait(timeout=10)
            db.commit()

    def delete_after_session() -> None:
        assert account_locked.wait(timeout=10)
        with SessionLocal() as db:
            user = db.get(User, user_id)
            assert user is not None
            asyncio.run(delete_account(account_public_id, user, db))

    with ThreadPoolExecutor(max_workers=2) as executor:
        create_future = executor.submit(create_session)
        delete_future = executor.submit(delete_after_session)
        assert account_locked.wait(timeout=10)
        time.sleep(0.2)
        assert not delete_future.done()
        allow_commit.set()
        create_future.result(timeout=10)
        delete_future.result(timeout=10)

    with SessionLocal() as db:
        account = db.get(TradingAccount, account_id)
        assert account is not None
        assert account.is_active is False
        assert account.hard_delete_eligible is False
        session = db.execute(select(ImportSession)).scalar_one()
        assert session.account_id == account_id


def test_jrn012_postgresql_concurrent_confirm_replays_one_canonical_write(
    postgres_database: tuple[Engine, str],
) -> None:
    engine, database_url = postgres_database
    _run_alembic(database_url, "upgrade", "head")
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )
    raw_values = {
        "asset_type": "STOCK",
        "market": "US",
        "exchange_code": "NASDAQ",
        "symbol": "AAPL",
        "instrument_type": "SPOT",
        "direction": "LONG",
        "action": "OPEN",
        "timestamp": "2026-07-25T10:00:00+00:00",
        "price": "200",
        "quantity": "2",
        "currency": "USD",
        "commission": "1.25",
        "fee_currency": "USD",
        "reason": "bootstrap",
        "note": "postgres concurrency",
    }
    normalized_values = {
        "direction": "LONG",
        "action": "OPEN",
        "occurred_at": "2026-07-25T10:00:00Z",
        "price": "200",
        "quantity": "2",
        "commission": "1.25",
        "asset_type": "STOCK",
        "market": "US",
        "exchange_code": "NASDAQ",
        "symbol": "AAPL",
        "instrument_type": "SPOT",
        "currency": "USD",
        "instrument_resolution": "CREATE_ON_CONFIRM",
        "fee_currency": "USD",
        "reason": "bootstrap",
        "note": "postgres concurrency",
    }
    with SessionLocal() as db:
        user = User(
            public_id="jrn012-pg-user",
            email="jrn012-pg@example.com",
            email_normalized="jrn012-pg@example.com",
            hashed_password="hash",
            status="ACTIVE",
            is_active=True,
            role="user",
            timezone="UTC",
        )
        account = TradingAccount(
            public_id="jrn012-pg-account",
            user=user,
            name="JRN012",
            broker="IBKR",
            currency="USD",
            is_active=True,
        )
        db.add_all([user, account])
        db.flush()
        upload = begin_idempotent_request(
            db,
            scope="GENERIC_IMPORT_UPLOAD_V1",
            key="sha256:jrn012-postgresql-upload",
            request_payload={
                "account_public_id": account.public_id,
                "adapter_kind": "GENERIC_BOOTSTRAP",
                "file_hash": "sha256:jrn012-fixture",
            },
            user_id=user.id,
            ttl_seconds=None,
        )
        session = ImportSession(
            public_id="jrn012-pg-session",
            user_id=user.id,
            account_id=account.id,
            upload_idempotency_id=upload.record.id,
            adapter_kind="GENERIC_BOOTSTRAP",
            file_format="CSV_UTF8",
            file_hash="sha256:jrn012-fixture",
            file_size_bytes=1,
            original_filename="fixture.csv",
            status="PREVIEW_READY",
            total_rows=1,
            valid_rows=1,
            error_rows=0,
            warning_rows=0,
            expires_at=datetime(2026, 7, 26, 10, 0, tzinfo=timezone.utc),
        )
        db.add(session)
        db.flush()
        import_row = ImportRow(
            public_id="jrn012-pg-row",
            session_id=session.id,
            user_id=user.id,
            account_id=account.id,
            adapter_kind="GENERIC_BOOTSTRAP",
            file_hash=session.file_hash,
            row_number=2,
            raw_values_json=raw_values,
            normalized_values_json=normalized_values,
            validation_errors_json=[],
            warnings_json=[],
            is_valid=True,
        )
        db.add(import_row)
        permanently_forbid_account_hard_delete(account)
        db.commit()
        user_id = user.id

    def confirm() -> tuple[dict, bool]:
        with SessionLocal() as db:
            result = confirm_generic_bootstrap(
                db,
                user_id=user_id,
                timezone_name="UTC",
                session_public_id="jrn012-pg-session",
                selected_row_public_ids=["jrn012-pg-row"],
                idempotency_key="jrn012-pg-confirm",
                now=datetime(2026, 7, 25, 12, 0, tzinfo=timezone.utc),
            )
            return result.body, result.replayed

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(lambda _index: confirm(), range(2)))

    assert results[0][0] == results[1][0]
    assert sorted(replayed for _body, replayed in results) == [False, True]
    with SessionLocal() as db:
        session = db.execute(select(ImportSession)).scalar_one()
        assert session.status == "COMPLETED"
        assert session.confirm_idempotency_id is not None
        assert len(db.execute(select(TradingPosition)).scalars().all()) == 1
        assert len(db.execute(select(PositionEvent)).scalars().all()) == 1
        row_record = db.execute(select(ImportRow)).scalar_one()
        assert row_record.applied_position_public_id is not None
        assert row_record.applied_event_public_id is not None
