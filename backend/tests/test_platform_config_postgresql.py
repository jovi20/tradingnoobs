import os
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from sqlalchemy import create_engine, inspect, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from models import FeatureFlag, SystemSetting
from services.platform_config_service import get_feature_flag_enabled


POSTGRES_URL_ENV = "JRN001_POSTGRES_URL"


@dataclass(frozen=True)
class _PostgresContext:
    admin_engine: Engine
    engine: Engine
    schema: str


@pytest.fixture
def postgres_context() -> Iterator[_PostgresContext]:
    database_url = os.getenv(POSTGRES_URL_ENV)
    if not database_url:
        pytest.skip(f"{POSTGRES_URL_ENV} is required for PostgreSQL integration tests")

    admin_engine = create_engine(database_url)
    schema = f"jrn001_{uuid.uuid4().hex}"
    schema_created = False
    try:
        assert admin_engine.dialect.name == "postgresql", (
            f"{POSTGRES_URL_ENV} must use PostgreSQL, got {admin_engine.dialect.name}"
        )

        with admin_engine.begin() as connection:
            connection.execute(CreateSchema(schema))
        schema_created = True

        engine = admin_engine.execution_options(
            schema_translate_map={None: schema},
        )
        with engine.begin() as connection:
            FeatureFlag.__table__.create(bind=connection)
            SystemSetting.__table__.create(bind=connection)

        yield _PostgresContext(
            admin_engine=admin_engine,
            engine=engine,
            schema=schema,
        )
    finally:
        if schema_created:
            with admin_engine.begin() as connection:
                connection.execute(DropSchema(schema, cascade=True, if_exists=True))
        admin_engine.dispose()


def test_committed_flag_read_does_not_flush_pending_duplicate(
    postgres_context: _PostgresContext,
) -> None:
    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=postgres_context.engine,
    )

    with SessionLocal() as db:
        db.add(FeatureFlag(key="committed_flag", enabled=True))
        db.commit()

        pending_duplicate = FeatureFlag(key="committed_flag", enabled=False)
        db.add(pending_duplicate)

        assert get_feature_flag_enabled(db, "committed_flag") is True
        assert pending_duplicate in db.new
        assert pending_duplicate.id is None
        assert db.execute(text("SELECT 1")).scalar_one() == 1

        db.rollback()

    with postgres_context.engine.connect() as observer:
        enabled = observer.execute(
            select(FeatureFlag.enabled).where(FeatureFlag.key == "committed_flag")
        ).scalar_one()
    assert enabled is True


def test_failed_flag_read_rolls_back_savepoint_and_preserves_caller_transaction(
    postgres_context: _PostgresContext,
) -> None:
    with postgres_context.engine.begin() as connection:
        FeatureFlag.__table__.drop(bind=connection)
    assert not inspect(postgres_context.admin_engine).has_table(
        FeatureFlag.__tablename__,
        schema=postgres_context.schema,
    )

    SessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=postgres_context.engine,
    )
    pending_key = "pending_after_failed_flag_read"
    pending_setting = SystemSetting(
        key=pending_key,
        value="preserved",
    )

    with SessionLocal() as db:
        db.add(pending_setting)

        assert get_feature_flag_enabled(db, "missing_feature_flags_table") is False
        assert pending_setting in db.new
        assert db.is_active
        assert db.execute(text("SELECT 1")).scalar_one() == 1

        db.commit()

    with postgres_context.engine.connect() as observer:
        value = observer.execute(
            select(SystemSetting.value).where(
                SystemSetting.key == pending_key
            )
        ).scalar_one()
    assert value == "preserved"
