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
- [ ] Commit with `test: freeze frontend legacy dto boundaries`.

P12 Task 1 result:
- Raw legacy DTO imports from `frontend/lib/api.ts` are now tested against a named allowlist grouped by `migration_ui`, `create_sync_bridge`, `legacy_analytics`, and `adapter_boundary`.
- The allowlist now includes legacy `Transaction` imports, closing the account-transaction DTO gap.
- `docs/DEVELOPER_GUIDE.md` documents the same group names and exact files, so the code boundary and developer guide cannot drift silently.

Verification log:
- RED frontend: `node --experimental-strip-types --test tests/legacy-ui-boundaries.test.mts` failed because `docs/DEVELOPER_GUIDE.md` did not document `migration_ui`.
- GREEN targeted frontend: `node --experimental-strip-types --test tests/legacy-ui-boundaries.test.mts` ran 4 tests OK.
- P12 Task 1 verification: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- P12 Task 1 verification: `npm run lint` exited 0.

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

- [ ] Create `backend/tests/test_openapi_contracts.py`.
- [ ] Add a test that calls `app.openapi()` and asserts required paths exist:
  - `/api/trading-positions/{position_public_id}/lifecycle`
  - `/api/trading-positions/{position_public_id}/events`
  - `/api/trading-positions/{position_public_id}/events/{event_public_id}/narrative`
  - `/api/timeline/home`
  - `/api/positions`
- [ ] Add a test that asserts `TimelineHomeResponse` and `TradingPositionLifecycleResponse` schemas are present in the OpenAPI components.
- [ ] Add a test that asserts legacy fallback headers are documented on protected legacy routes:
  - `X-Migration-Fallback` on legacy batch create
  - `X-Migration-Fallback` on legacy review update
  - `X-Migration-Fallback` on legacy position delete
- [ ] Run `cd backend && ../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py`.
- [ ] Commit with `test: snapshot core api contracts`.

Verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_openapi_contracts.py
```

---

## Task 3: Prepare Generated Type Output Boundary

**Goal:** introduce a generated-types location without replacing hand-written read models yet.

- [ ] Create `frontend/lib/generated/README.md` explaining that generated files are build artifacts and should not be edited by hand.
- [ ] Create `frontend/lib/generated/contracts.ts` as a temporary checked-in stub exporting no product types yet:

```ts
// Placeholder module for future generated OpenAPI types.
// P12 keeps this file intentionally empty until generation is wired.
export {}
```

- [ ] Add `frontend/tests/generated-contracts.test.mts` that imports `../lib/generated/contracts.ts` and verifies the module can be loaded.
- [ ] Update `frontend/lib/read-models.ts` header to point to `frontend/lib/generated/contracts.ts` as the future replacement boundary.
- [ ] Run `cd frontend && node --experimental-strip-types --test tests/generated-contracts.test.mts`.
- [ ] Commit with `chore: add generated contract boundary`.

Verification:

```bash
cd frontend
node --experimental-strip-types --test tests/generated-contracts.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```

---

## Task 4: Release And Rollback Playbooks

**Goal:** make P11 truth/snapshot switches operable, not just coded.

- [ ] Add a `docs/release-rollback-playbook.md` section for truth writes:
  - normal path: truth routes
  - migration fallback headers
  - safe rollback order by P11 commit
- [ ] Add a Timeline snapshot rollback section:
  - normal mode: `SNAPSHOT_ONLY`
  - rollback flag: `timeline_legacy_mixed_feed_enabled`
  - expected UI label: `Legacy mixed fallback enabled`
- [ ] Add a legacy mutation guard section:
  - `legacy-batch-write`
  - `legacy-review-write`
  - `legacy-position-delete`
  - `legacy-batch-edit`
- [ ] Link the playbook from `docs/DEVELOPER_GUIDE.md` and `docs/TODO.md`.
- [ ] Commit with `docs: add p11 rollback playbook`.

Verification:

```bash
rg -n "timeline_legacy_mixed_feed_enabled|legacy-batch-write|legacy-review-write|legacy-position-delete|legacy-batch-edit" docs
```

---

## Task 5: P12 Completion Gate

- [ ] Backend OpenAPI contract tests pass.
- [ ] Backend full tests pass.
- [ ] Frontend typecheck passes.
- [ ] Frontend lint passes.
- [ ] Frontend Node tests pass.
- [ ] `git diff --check` passes.
- [ ] `docs/TODO.md` marks P12 completed or lists precise remaining blockers.

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
