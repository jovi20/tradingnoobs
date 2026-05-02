# Dev Branch Checkpoint - 2026-05-02

## Branch

- Worktree: `/Users/a1/vibecoding/tradingnoobs/.worktrees/docs-platform-frontend-contracts`
- Current branch: `dev`
- Baseline branch kept for comparison: `main`
- Current `main...dev` committed diff: empty because the platform/frontend work is still uncommitted in the `dev` worktree.

## Current Working Tree Shape

- Tracked modified files: 30
- Untracked files/directories include:
  - Alembic setup and revisions
  - Backend bootstrap, timeline, trading position, platform config, public id, and truth sync services
  - Backend tests
  - Platform/frontend contract docs
  - Timeline/dashboard/settings/position frontend domain components
  - Frontend read models, adapters, and adapter tests

Tracked diff summary at checkpoint:

```text
30 files changed, 1444 insertions(+), 1005 deletions(-)
```

## Verification

Frontend adapter/helper tests:

```bash
node --experimental-strip-types --test frontend/tests/*.test.mts
```

Result:

```text
tests 14
pass 14
fail 0
```

Known warning:

```text
MODULE_TYPELESS_PACKAGE_JSON
```

Backend unittest discovery with system Python:

```bash
cd backend && python -m unittest discover tests
```

Result:

```text
FAILED (errors=14)
```

Reason:

- Current Python environment is missing backend dependencies, including `fastapi`, `sqlalchemy`, and `email-validator`.
- This is an environment/dependency blocker, not yet evidence of backend behavior failure.

Backend unittest discovery with project venv:

```bash
cd backend && ../.venv313/bin/python -m unittest discover -s tests
```

Result:

```text
Ran 46 tests in 3.887s
OK
```

Known warning:

```text
yfinance/Yahoo DNS warnings for guce.yahoo.com in sandboxed network conditions; tests still passed.
```

Lifecycle public-id-only regression:

```bash
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py
```

Result:

```text
Ran 2 tests in 0.130s
OK
```

Timeline cursor/limit regression:

```bash
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_timeline_home_router.py
```

Result:

```text
Ran 10 tests in 0.634s
OK
```

C3 AccountLedgerEntry regressions:

```bash
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_trading_truth_models.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_legacy_truth_sync.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p 'test_public_id_*routes.py'
cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_alembic_chain.py
```

Result:

```text
truth models: 1 OK
legacy truth sync: 4 OK
lifecycle router: 2 OK
public-id route group: 7 OK
alembic chain: 1 OK
```

## Current Plan State

- Timeline and lifecycle user-facing paths are explicitly marked as `Bridge landed / partial`.
- `/api/trading-positions/{position_public_id}/lifecycle` is now public_id-only for ordinary user paths.
- `/api/positions/{id}/truth-lifecycle` remains labeled as the legacy migration bridge.
- `/api/timeline/home` now has bridge-level `limit` / `cursor` support over stabilized timeline event cards.
- `AccountLedgerEntry` foundation is landed with migration, legacy realized PnL bridge, transaction cash bridge, and lifecycle `cash_effects` consumption.
- Account cash balance/read models are not yet fully ledger-derived; keep this as a C4/accounting-service follow-up.
- The next implementation slice should create a stage boundary commit on `dev`, then continue `C2 + C5` truth-first detail or `C4` accounting service.

## Next Checkpoint Criteria

- Backend test environment can run targeted and full unittest checks through `.venv313`.
- Public-id-only lifecycle behavior has a failing test first, then passing implementation.
- Timeline `limit` / `cursor` behavior has a failing test first, then passing implementation.
- C3 AccountLedgerEntry foundation has model, migration, sync, route, and lifecycle regressions.
- Frontend adapter tests remain green.
- Stage boundary commit created on `dev` before starting larger `C2/C4` follow-up work.
