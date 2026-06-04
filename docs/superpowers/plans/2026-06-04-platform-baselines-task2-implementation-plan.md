# Platform Baselines Task 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Task 2 baseline required before trading truth-model cutover: Alembic migrations, public identity/auth scaffolding, observability conventions, and a runnable backend test baseline.

**Architecture:** Keep legacy `/api/...` routes operational while adding `/api/v1`-ready foundations. Do not migrate `Position / TradeBatch` yet. Establish testable infrastructure first, then use Alembic and focused services to remove schema drift safely.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest, httpx/TestClient, structlog-compatible JSON logging conventions, ULID public identifiers.

---

## Files And Responsibilities

- Create `backend/tests/conftest.py`: isolated SQLite test database, FastAPI dependency override, per-test schema setup.
- Create `backend/tests/test_migration_config.py`: proves Alembic config exists and enables multi-schema migration metadata.
- Create `backend/tests/test_identity_public_id.py`: proves ULID generation, normalized email, user status, and public auth response behavior.
- Create `backend/tests/test_observability.py`: proves request IDs, error-code shape, and JSON log field helpers.
- Create `backend/alembic.ini`: Alembic CLI entrypoint rooted in `backend/`.
- Create `backend/alembic/env.py`: single Alembic env with `include_schemas=True`.
- Create `backend/alembic/versions/20260604_0001_platform_baseline.py`: baseline migration for core/audit/reference/market/derived/content/ai schemas and identity/session tables.
- Create `backend/services/identity_service.py`: ULID and email-normalization helpers.
- Create `backend/observability.py`: request ID middleware, error-code helper, and JSON log context helpers.
- Modify `backend/requirements.txt`: add `pytest`, `pytest-asyncio`, `ulid-py`, `structlog`, and `arq`.
- Modify `backend/models.py`: add public identity fields and auth/session support models without removing legacy fields.
- Modify `backend/schemas.py`: add `public_id`, `status`, `email_normalized`, `last_login_at`, `locale`, and `timezone` to user responses.
- Modify `backend/services/auth_service.py`: create users with normalized email, public id, status, and token subject using `public_id` while keeping legacy integer subject fallback.
- Modify `backend/routers/auth.py`: expose `/api/v1/auth/*` in addition to legacy auth routes through a shared router factory.
- Modify `backend/main.py`: remove runtime `Base.metadata.create_all()` and register observability middleware.

---

### Task 2A: Backend Test Harness

**Files:**
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_identity_public_id.py`
- Modify: `backend/requirements.txt`

- [x] **Step 1: Add pytest dependencies**

Add these lines under a new testing section in `backend/requirements.txt`:

```text
# ============== Testing ==============
pytest>=8.2.0
pytest-asyncio>=0.23.0
```

- [x] **Step 2: Create a minimal failing identity test**

Create `backend/tests/test_identity_public_id.py`:

```python
from services.identity_service import generate_public_id, normalize_email


def test_generate_public_id_returns_26_character_ulid():
    public_id = generate_public_id()

    assert len(public_id) == 26
    assert public_id == public_id.upper()


def test_normalize_email_trims_and_lowercases():
    assert normalize_email("  Trader@Example.COM ") == "trader@example.com"
```

- [x] **Step 3: Run the identity test and verify RED**

Run: `cd backend && python -m pytest tests/test_identity_public_id.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'services.identity_service'`.

- [x] **Step 4: Implement minimal identity helpers**

Create `backend/services/identity_service.py`:

```python
import ulid


def generate_public_id() -> str:
    return str(ulid.new())


def normalize_email(email: str) -> str:
    return email.strip().lower()
```

Add dependency:

```text
ulid-py>=1.1.0
```

- [x] **Step 5: Run identity test and verify GREEN**

Run: `cd backend && python -m pytest tests/test_identity_public_id.py -q`

Expected: PASS.

---

### Task 2B: Alembic Migration Baseline

**Files:**
- Create: `backend/tests/test_migration_config.py`
- Create: `backend/alembic.ini`
- Create: `backend/alembic/env.py`
- Create: `backend/alembic/versions/20260604_0001_platform_baseline.py`
- Modify: `backend/main.py`

- [x] **Step 1: Write failing migration config tests**

Create `backend/tests/test_migration_config.py`:

```python
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]


def test_alembic_config_files_exist():
    assert (BACKEND_ROOT / "alembic.ini").exists()
    assert (BACKEND_ROOT / "alembic" / "env.py").exists()
    assert (BACKEND_ROOT / "alembic" / "versions").is_dir()


def test_alembic_env_includes_schemas():
    env_text = (BACKEND_ROOT / "alembic" / "env.py").read_text()

    assert "include_schemas=True" in env_text
    assert "target_metadata = Base.metadata" in env_text


def test_runtime_create_all_removed_from_main():
    main_text = (BACKEND_ROOT / "main.py").read_text()

    assert "Base.metadata.create_all" not in main_text
```

- [x] **Step 2: Run migration tests and verify RED**

Run: `cd backend && python -m pytest tests/test_migration_config.py -q`

Expected: FAIL because Alembic files do not exist and `main.py` still contains `Base.metadata.create_all`.

- [x] **Step 3: Add Alembic configuration**

Create `backend/alembic.ini`:

```ini
[alembic]
script_location = alembic
prepend_sys_path = .
sqlalchemy.url = sqlite:///./tradingnoobs.db

[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
```

Create `backend/alembic/env.py`:

```python
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from config import get_settings
from database import Base
import models  # noqa: F401


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def get_url() -> str:
    return get_settings().database_url


def run_migrations_offline() -> None:
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

- [x] **Step 4: Add baseline migration**

Create `backend/alembic/versions/20260604_0001_platform_baseline.py` with schema creation guarded for PostgreSQL and identity/session tables for both PostgreSQL and SQLite.

- [x] **Step 5: Remove runtime schema creation**

Modify `backend/main.py` so `lifespan()` no longer calls `Base.metadata.create_all(bind=engine)`.

- [x] **Step 6: Run migration tests and verify GREEN**

Run: `cd backend && python -m pytest tests/test_migration_config.py -q`

Expected: PASS.

---

### Task 2C: Identity And Auth Baseline

**Files:**
- Create: `backend/tests/test_auth_identity.py`
- Modify: `backend/models.py`
- Modify: `backend/schemas.py`
- Modify: `backend/services/auth_service.py`
- Modify: `backend/routers/auth.py`

- [x] **Step 1: Write failing auth identity tests**

Create `backend/tests/test_auth_identity.py` with tests proving:

```python
from datetime import timedelta

import pytest
from jose import jwt

from config import get_settings
from models import User
from schemas import UserResponse
from services.auth_service import create_access_token, create_user, get_current_user


def test_create_user_sets_public_identity_fields(db_session):
    user = create_user(db_session, " Trader@Example.COM ", "strong-password")

    assert len(user.public_id) == 26
    assert user.public_id == user.public_id.upper()
    assert user.email == "trader@example.com"
    assert user.email_normalized == "trader@example.com"
    assert user.status == "ACTIVE"
    assert user.locale == "en-US"
    assert user.timezone == "UTC"


def test_user_response_exposes_public_id(db_session):
    user = create_user(db_session, "public@example.com", "strong-password")

    response = UserResponse.model_validate(user)

    assert response.public_id == user.public_id
    assert response.email_normalized == "public@example.com"
    assert response.status == "ACTIVE"


@pytest.mark.asyncio
async def test_current_user_accepts_public_id_subject(db_session):
    user = create_user(db_session, "token@example.com", "strong-password")
    token = create_access_token({"sub": user.public_id}, expires_delta=timedelta(minutes=5))

    current_user = await get_current_user(token=token, db=db_session)

    assert current_user.public_id == user.public_id


@pytest.mark.asyncio
async def test_current_user_accepts_legacy_integer_subject(db_session):
    user = create_user(db_session, "legacy-token@example.com", "strong-password")
    settings = get_settings()
    token = jwt.encode({"sub": str(user.id)}, settings.secret_key, algorithm=settings.algorithm)

    current_user = await get_current_user(token=token, db=db_session)

    assert current_user.id == user.id
```

- [x] **Step 2: Run auth identity tests and verify RED**

Run: `cd backend && python -m pytest tests/test_auth_identity.py -q`

Expected: FAIL because model fields and response fields are missing.

- [x] **Step 3: Add identity fields and auth support models**

Add `public_id`, `status`, `email_normalized`, `last_login_at`, `locale`, and `timezone` to `User`. Add `UserCredential`, `UserSession`, `UserIdentity`, and `AuthToken` models.

- [x] **Step 4: Update auth service and schemas**

Create users with normalized email and public id. Use `public_id` for new JWT subjects, but keep integer fallback in `get_current_user()`.

- [x] **Step 5: Expose `/api/v1/auth` alongside legacy auth**

Refactor auth router creation so `auth.router` remains `/api/auth` and a new `auth.v1_router` serves `/api/v1/auth`.

- [x] **Step 6: Run auth identity tests and verify GREEN**

Run: `cd backend && python -m pytest tests/test_auth_identity.py -q`

Expected: PASS.

---

### Task 2D: Observability Baseline

**Files:**
- Create: `backend/tests/test_observability.py`
- Create: `backend/observability.py`
- Modify: `backend/main.py`
- Modify: `backend/requirements.txt`

- [x] **Step 1: Write failing observability tests**

Create `backend/tests/test_observability.py`:

```python
from observability import make_error_code, build_log_context


def test_make_error_code_namespaces_errors():
    assert make_error_code("auth", "invalid_credentials") == "auth.invalid_credentials"


def test_build_log_context_includes_required_fields():
    context = build_log_context(
        request_id="req-1",
        actor_type="user",
        user_public_id="01HX0000000000000000000000",
        route="/api/v1/auth/me",
        method="GET",
        status_code=200,
        latency_ms=12.5,
        error_code=None,
    )

    assert context["request_id"] == "req-1"
    assert context["route"] == "/api/v1/auth/me"
    assert context["latency_ms"] == 12.5
```

- [x] **Step 2: Run observability tests and verify RED**

Run: `cd backend && python -m pytest tests/test_observability.py -q`

Expected: FAIL because `observability.py` does not exist.

- [x] **Step 3: Add observability helpers and dependency**

Create `backend/observability.py` with `make_error_code()`, `build_log_context()`, and request ID middleware. Add `structlog>=24.1.0`.

- [x] **Step 4: Register middleware**

Modify `backend/main.py` to register request ID middleware before routers.

- [x] **Step 5: Run observability tests and verify GREEN**

Run: `cd backend && python -m pytest tests/test_observability.py -q`

Expected: PASS.

---

### Task 2E: Baseline Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`

- [x] **Step 1: Run full backend baseline tests**

Run: `cd backend && python -m pytest tests -q`

Expected: PASS.

- [x] **Step 2: Run Alembic smoke check**

Run: `cd backend && alembic -c alembic.ini current`

Expected: command exits 0 against the configured local database.

- [x] **Step 3: Update top-level sequencing plan**

Mark Task 2 checklist items complete only after the tests above pass.

- [x] **Step 4: Review diff**

Run: `git diff --check`

Expected: no output.
