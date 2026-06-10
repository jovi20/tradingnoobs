# P12 Platform Contract Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Harden the API/frontend contract layer after P11 so new product work uses generated or read-model contracts instead of expanding raw legacy DTO usage.

**Status:** selected as the next active lane after P11. P11 code tasks are complete; authenticated browser smoke remains a pre-release validation item, not a blocker for starting P12 contract hardening.

**Architecture:** Keep existing routes stable while adding contract generation, import boundaries, and release/rollback playbooks around truth writes and snapshot reads. Do not delete legacy models in P12; P12 creates the safety rails that make later deletion low-risk.

**Tech Stack:** FastAPI/Pydantic, Next.js/TypeScript, Node test runner, unittest, existing feature flags, existing read-model adapters.

---

## Files Likely To Touch

Backend:
- `backend/main.py`
- `backend/schemas.py`
- `backend/routers/trading_positions.py`
- `backend/routers/timeline.py`
- `backend/routers/positions.py`
- `backend/tests/test_openapi_contracts.py`
- `backend/tests/test_position_truth_bridge_router.py`
- `backend/tests/test_timeline_home_router.py`

Frontend:
- `frontend/lib/read-models.ts`
- `frontend/lib/api.ts`
- `frontend/lib/generated/`
- `frontend/lib/adapters/`
- `frontend/tests/legacy-ui-boundaries.test.mts`
- `frontend/tests/generated-contracts.test.mts`

Docs:
- `docs/TODO.md`
- `docs/DEVELOPER_GUIDE.md`
- `docs/superpowers/plans/2026-06-10-dev-p12-platform-contract-hardening-plan.md`
- `docs/superpowers/plans/2026-06-10-dev-p10-legacy-cutover-inventory.md`

---

## Task 1: Freeze Contract Ownership Boundaries

**Goal:** document and test which frontend modules may import raw API DTOs after P11.

- [x] Write a failing frontend boundary test that rejects new imports of legacy `Position`, `TradeBatch`, `BatchCreate`, and `Transaction` outside the current allowlist.
- [x] Extend `frontend/tests/legacy-ui-boundaries.test.mts` with a named allowlist object grouped by `migration_ui`, `create_sync_bridge`, `legacy_analytics`, and `adapter_boundary`.
- [x] Update `docs/DEVELOPER_GUIDE.md` with the same group names and the exact files in each group.
- [x] Run `cd frontend && node --experimental-strip-types --test tests/legacy-ui-boundaries.test.mts`.
- [x] Commit with `test: freeze frontend legacy dto boundaries`.

P12 Task 1 result:
- Raw legacy DTO imports from `frontend/lib/api.ts` are now tested against a named allowlist grouped by `migration_ui`, `create_sync_bridge`, `legacy_analytics`, and `adapter_boundary`.
- The allowlist now includes legacy `Transaction` imports, closing the account-transaction DTO gap.
- `docs/DEVELOPER_GUIDE.md` documents the same group names and exact files, so the code boundary and developer guide cannot drift silently.

Verification log:
- RED frontend: `node --experimental-strip-types --test tests/legacy-ui-boundaries.test.mts` failed because `docs/DEVELOPER_GUIDE.md` did not document `migration_ui`.
- GREEN targeted frontend: `node --experimental-strip-types --test tests/legacy-ui-boundaries.test.mts` ran 4 tests OK.
- P12 Task 1 verification: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- P12 Task 1 verification: `npm run lint` exited 0.
- Commit: `9af3762 test: freeze frontend legacy dto boundaries`.

Verification:

```bash
cd frontend
node --experimental-strip-types --test tests/legacy-ui-boundaries.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
```

---

## Task 2: Add OpenAPI Contract Snapshot Tests

**Goal:** make accidental API contract drift visible before generated frontend types are introduced.

- [x] Create `backend/tests/test_openapi_contracts.py`.
- [x] Add a test that calls `app.openapi()` and asserts required paths exist:
  - `/api/trading-positions/{position_public_id}/lifecycle`
  - `/api/trading-positions/{position_public_id}/events`
  - `/api/trading-positions/{position_public_id}/events/{event_public_id}/narrative`
  - `/api/timeline/home`
  - `/api/positions`
- [x] Add a test that asserts `TimelineHomeResponse` and `TradingPositionLifecycleResponse` schemas are present in the OpenAPI components.
- [x] Add a test that asserts legacy fallback headers are documented on protected legacy routes:
  - `X-Migration-Fallback` on legacy batch create
  - `X-Migration-Fallback` on legacy review update
  - `X-Migration-Fallback` on legacy position delete
- [x] Run `cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py`.
- [x] Commit with `test: snapshot core api contracts`.

P12 Task 2 result:
- Added OpenAPI snapshot coverage for truth lifecycle, truth events, canonical event narrative, Timeline Home, and legacy positions.
- Added explicit `TradingPositionLifecycleResponse` schema so lifecycle routes have a stable named OpenAPI component.
- Added `/api/trading-positions/{position_public_id}/events/{event_public_id}/narrative` as the public narrative contract while keeping the previous patch path available but hidden from schema.
- Documented protected legacy `X-Migration-Fallback` header values in OpenAPI descriptions.

Verification log:
- RED backend: `../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py` failed because the canonical narrative path, lifecycle response schema, and fallback header descriptions were missing.
- GREEN targeted backend: `../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py` ran 3 tests OK.
- P12 Task 2 lifecycle regression: `../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py` ran 25 tests OK.
- P12 Task 2 legacy bridge regression: `../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py` ran 9 tests OK.
- P12 Task 2 timeline regression: `../.venv313/bin/python -m unittest discover -s tests -p test_timeline_home_router.py` ran 19 tests OK; output included the existing Yahoo/MSFT DNS warning.
- Commit: `ac37043 test: snapshot core api contracts`.

Verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py
```

---

## Task 3: Prepare Generated Type Output Boundary

**Goal:** introduce a generated-types location without replacing hand-written read models yet.

- [x] Create `frontend/lib/generated/README.md` explaining that generated files are build artifacts and should not be edited by hand.
- [x] Create `frontend/lib/generated/contracts.ts` as a temporary checked-in stub exporting no product types yet:

```ts
// Placeholder module for future generated OpenAPI types.
// P12 keeps this file intentionally empty until generation is wired.
export {}
```

- [x] Add `frontend/tests/generated-contracts.test.mts` that imports `../lib/generated/contracts.ts` and verifies the module can be loaded.
- [x] Update `frontend/lib/read-models.ts` header to point to `frontend/lib/generated/contracts.ts` as the future replacement boundary.
- [x] Run `cd frontend && node --experimental-strip-types --test tests/generated-contracts.test.mts`.
- [x] Commit with `chore: add generated contract boundary`.

P12 Task 3 result:
- Added `frontend/lib/generated/` as the stable future OpenAPI output boundary without replacing handwritten read models yet.
- Added a checked-in placeholder `contracts.ts` module and a load test so future generator wiring has a contract-safe import location.
- Updated `frontend/lib/read-models.ts` header to point to `frontend/lib/generated/contracts.ts` as the eventual replacement boundary.

Verification log:
- RED frontend: `node --experimental-strip-types --test tests/generated-contracts.test.mts` failed with `ERR_MODULE_NOT_FOUND` before the generated boundary existed.
- GREEN targeted frontend: `node --experimental-strip-types --test tests/generated-contracts.test.mts` ran 1 test OK; Node emitted the existing `MODULE_TYPELESS_PACKAGE_JSON` warning.
- P12 Task 3 verification: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- Commit: `1c06a7a chore: add generated contract boundary`.

Verification:

```bash
cd frontend
node --experimental-strip-types --test tests/generated-contracts.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```

---

## Task 4: Release And Rollback Playbooks

**Goal:** make P11 truth/snapshot switches operable, not just coded.

- [x] Add a `docs/release-rollback-playbook.md` section for truth writes:
  - normal path: truth routes
  - migration fallback headers
  - safe rollback order by P11 commit
- [x] Add a Timeline snapshot rollback section:
  - normal mode: `SNAPSHOT_ONLY`
  - rollback flag: `timeline_legacy_mixed_feed_enabled`
  - expected UI label: `Legacy mixed fallback enabled`
- [x] Add a legacy mutation guard section:
  - `legacy-batch-write`
  - `legacy-review-write`
  - `legacy-position-delete`
  - `legacy-batch-edit`
- [x] Link the playbook from `docs/DEVELOPER_GUIDE.md` and `docs/TODO.md`.
- [x] Commit with `docs: add p11 rollback playbook`.

P12 Task 4 result:
- Added `docs/release-rollback-playbook.md` with truth write, Timeline snapshot, and legacy mutation guard release/rollback procedures.
- Linked the playbook from `docs/DEVELOPER_GUIDE.md`, `docs/TODO.md`, and `docs/README.md`.
- Captured P11 behavior rollback order using the actual commit sequence for truth-first writes, create-and-sync, narrative guards, destructive mutation guards, and snapshot Timeline.

Verification log:
- P12 Task 4 verification: `rg -n "timeline_legacy_mixed_feed_enabled|legacy-batch-write|legacy-review-write|legacy-position-delete|legacy-batch-edit" docs` found the rollback flag and all four fallback tokens in docs, including the new playbook.
- Commit: `31ab8ef docs: add p11 rollback playbook`.

Verification:

```bash
rg -n "timeline_legacy_mixed_feed_enabled|legacy-batch-write|legacy-review-write|legacy-position-delete|legacy-batch-edit" docs
```

---

## Task 5: P12 Completion Gate

- [x] Backend OpenAPI contract tests pass.
- [x] Backend full tests pass.
- [x] Frontend typecheck passes.
- [x] Frontend lint passes.
- [x] Frontend Node tests pass.
- [x] `git diff --check` passes.
- [x] `docs/TODO.md` marks P12 completed or lists precise remaining blockers.

P12 Task 5 result:
- P12 Platform Contract Hardening is complete: legacy DTO boundaries are frozen, core OpenAPI contracts are snapshotted, generated type output has a stable landing zone, and P11 release/rollback playbook is linked from the core docs.
- No P12 code blockers remain.
- P11 authenticated browser smoke remains a pre-release validation item outside P12's contract-hardening completion gate.

Verification log:
- Backend OpenAPI targeted regression: covered by full backend test run through `backend/tests/test_openapi_contracts.py`.
- Full backend regression: `../.venv313/bin/python -m unittest discover -s tests` ran 163 tests OK; output included the existing Yahoo/MSFT DNS warning from market-data-related code.
- Frontend typecheck: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- Frontend lint: `npm run lint` exited 0.
- Extended frontend regression: `node --experimental-strip-types --test tests/*.test.mts` ran 91 tests OK; Node emitted existing `MODULE_TYPELESS_PACKAGE_JSON` warnings.
- Diff hygiene: `git diff --check` exited 0.
- Status check after automated verification initially showed only the P12 plan modified; final completion documentation also updates `docs/TODO.md`, `docs/DEVELOPER_GUIDE.md`, and `docs/README.md`. The untracked `docs/superpowers/demos/` directory remains intentionally untouched.

Final verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
cd ../frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
node --experimental-strip-types --test tests/*.test.mts
cd ..
git diff --check
git status --short --branch
```
