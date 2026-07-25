from __future__ import annotations

import os
import re
import subprocess
import sys
import uuid
from collections.abc import Iterator
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import Engine, URL, make_url
from sqlalchemy.orm import sessionmaker

from models import (
    AccountLedgerEntry,
    AssetMaster,
    PositionEvent,
    PositionEventType,
    TradeInstrument,
    TradeInstrumentType,
    TradingAccount,
    TradingPosition,
    TradingPositionSide,
    TradingPositionStatus,
    User,
)
from services.account_ledger_service import sync_opening_balance_to_account_ledger
from services.auth_service import authenticate_user, create_user
from services.trading_position_write_service import append_truth_trade_event


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
    } <= set(inspector.get_table_names())
    with engine.connect() as connection:
        assert connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one() == _alembic_head()


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
        "ibkr_flex_query_id",
        "ibkr_flex_token",
        "ibkr_flex_start_date",
        "binance_market_type",
        "binance_symbols",
    } <= user_settings_columns
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
