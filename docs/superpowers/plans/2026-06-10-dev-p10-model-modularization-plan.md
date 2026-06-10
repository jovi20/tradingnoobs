# P10 Backend Model Modularization Plan

**Date:** 2026-06-10
**Branch:** `dev`
**Purpose:** define a safe split strategy for `backend/models.py` without changing runtime behavior in P10.

## Current State

- `backend/models.py` is 996 lines.
- Imports use `from models import ...` broadly across routers, services, tests, ops scripts, and Alembic.
- Legacy and truth models currently live together, which makes ownership unclear during the P11 truth hard cutover.
- P10 must not split code yet. The split should happen after the legacy cutover inventory is accepted and the first P11 cutover slice is scoped.

## Target Module Layout

```text
backend/models/
  __init__.py
  base.py
  core.py
  trading_truth.py
  platform.py
  analytics.py
  ai.py
  legacy.py
```

## Module Ownership

| Module | Owns | Notes |
|--------|------|-------|
| `base.py` | `Base`, shared SQLAlchemy naming conventions if introduced later | Keep Alembic import stable. |
| `core.py` | `User`, `UserCredential`, `UserSession`, `UserIdentity`, `AuthToken`, `Strategy`, `TradingAccount`, `UserSettings` | Auth/account/settings surface. |
| `trading_truth.py` | `AssetMaster`, `TradeInstrument`, `TradingPosition`, `PositionEvent`, `AccountLedgerEntry` and related enums | P11 primary truth ownership. |
| `platform.py` | `SystemSetting`, `PlatformSetting`, `IntegrationCredential`, `FeatureFlag`, `JobDefinition`, `JobRun`, `JobRunEvent`, `IdempotencyKey`, `BusinessLock`, `OutboxEvent`, `DerivedTimelineSnapshot` | Platform, async, config, and derived read-model foundation. |
| `analytics.py` | `DailySummary`, `JournalEntry`, `WeeklyReport`, `AIAnalysisResult`, `AISummary` if kept legacy | Should be revisited during P14/P15 reporting and AI workflow work. |
| `ai.py` | `InsightRun`, `InsightArtifact` | Artifact-first AI outputs. |
| `legacy.py` | `AssetMetadata`, `Position`, `TradeBatch`, `DailySnapshot`, `Transaction` and legacy enums | Must remain explicit migration/fallback surface until P11/P12 cleanup. |

## Compatibility Strategy

Create `backend/models/__init__.py` as a compatibility re-export layer before changing callers:

```python
from .base import Base
from .core import User, UserCredential, UserSession, UserIdentity, AuthToken, Strategy, TradingAccount, UserSettings
from .trading_truth import AssetMaster, TradeInstrument, TradingPosition, PositionEvent, AccountLedgerEntry
from .platform import SystemSetting, PlatformSetting, IntegrationCredential, FeatureFlag, JobDefinition, JobRun
from .analytics import DailySummary, JournalEntry, WeeklyReport, AIAnalysisResult, AISummary
from .ai import InsightRun, InsightArtifact
from .legacy import AssetMetadata, Position, TradeBatch, DailySnapshot, Transaction
```

The first code-split PR should keep existing `from models import ...` imports working. Direct imports such as `from models.trading_truth import TradingPosition` can be introduced only after the compatibility layer is green.

## Migration Sequence

1. Create `backend/models/` package and move `Base` plus enum definitions first, preserving exported names.
2. Move one model family at a time, starting with low-risk platform/config models before truth/legacy models.
3. Keep `backend/models.py` as either deleted or converted to a temporary shim only after import resolution is verified.
4. Update Alembic `env.py` only after `Base.metadata` is proven identical.
5. Add a model registry smoke test that imports `Base` and confirms expected tables are present.
6. Only then start replacing broad `from models import ...` imports with module-specific imports.

## Required Tests

Run these before and after each split step:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_alembic_chain.py
../.venv313/bin/python -m unittest discover -s tests -p test_trading_truth_models.py
../.venv313/bin/python -m unittest discover -s tests -p test_job_models.py
../.venv313/bin/python -m unittest discover -s tests -p test_outbox_models.py
../.venv313/bin/python -m unittest discover -s tests
```

If frontend contracts are touched during follow-up work:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
```

## Rollback Strategy

- Keep every split step as its own commit.
- If imports break, revert the latest split commit and keep the prior compatibility layer.
- Do not combine model movement with semantic changes, table renames, Alembic migrations, or legacy deletion.
- Do not remove `legacy.py` exports until P11 hard cutover and P12 contract hardening are both verified.

## Stop Conditions

- Alembic can no longer import `Base.metadata`.
- Any model table name, enum value, relationship, or foreign key changes without an explicit migration plan.
- Full backend tests fail for reasons unrelated to known external network warnings.
- The split starts changing truth/legacy semantics instead of only moving definitions.
