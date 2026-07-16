# P11 Truth Hard Cutover Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:test-driven-development for code changes and superpowers:executing-plans for task execution. Do not delete legacy code before the inventory and rollback gates in this plan are green.

**Goal:** Move ordinary user trading flows from legacy `Position / TradeBatch / Transaction` semantics to `TradingPosition / PositionEvent / AccountLedgerEntry`, then make Timeline and Review Inbox truth/snapshot-backed by default.

**User-facing outcome:** users create, add, reduce, close, review, and narrate trades through the audited truth lifecycle. Legacy surfaces remain visible only as migration/support tools.

**Depends on:**
- P10 legacy cutover inventory.
- P10 observability middleware.
- P10 read-model boundary marker.
- P10 model modularization plan.

**Non-goals:**
- Do not remove legacy database tables in P11.
- Do not split `backend/models.py` in P11.
- Do not build risk alerts, PDF export, or market provider validation in this lane.
- Do not force chart renderer migration in this lane.

---

## Active Lane Contract

P11 is the active implementation lane after P10. P12-P19 stay backlog until P11 is verified or explicitly paused.

Every P11 code slice must:
- Start with a failing test.
- Keep legacy fallback behind explicit migration labels or feature flags.
- Include rollback instructions for default-path changes.
- Avoid expanding raw legacy DTO usage in `frontend/lib/api.ts`.
- Leave `docs/superpowers/demos/` untouched and uncommitted.

---

## Files Likely To Touch

Backend:
- `backend/routers/positions.py`
- `backend/routers/trading_positions.py`
- `backend/routers/timeline.py`
- `backend/routers/dashboard.py`
- `backend/services/trading_position_write_service.py`
- `backend/services/trading_position_read_service.py`
- `backend/services/legacy_truth_sync_service.py`
- `backend/services/derived_timeline_read_service.py`
- `backend/tests/test_trading_position_lifecycle_router.py`
- `backend/tests/test_position_truth_bridge_router.py`
- `backend/tests/test_timeline_home_router.py`

Frontend:
- `frontend/lib/api.ts`
- `frontend/lib/adapters/lifecycle.ts`
- `frontend/lib/adapters/trading.ts`
- `frontend/lib/read-models.ts`
- `frontend/app/positions/new/page.tsx`
- `frontend/app/positions/[id]/add-batch/page.tsx`
- `frontend/app/positions/[id]/page.tsx`
- `frontend/app/positions/page.tsx`
- `frontend/app/page.tsx`
- `frontend/app/timeline/page.tsx`

Docs:
- `docs/TODO.md`
- `docs/DEVELOPER_GUIDE.md`
- `docs/superpowers/plans/2026-06-10-dev-p11-truth-hard-cutover-plan.md`
- `docs/superpowers/plans/archive/2026-06-10-dev-p10-legacy-cutover-inventory.md`

---

## Task 1: Freeze Ordinary User Writes To Truth Routes

**Goal:** ordinary create/add/reduce/close flows prefer truth routes, with legacy writes allowed only as explicit migration fallback.

- [x] Write failing backend tests proving truth event writes cover ADD / REDUCE / CLOSE and reject closed-position writes.
- [x] Write failing frontend tests or static checks proving new ordinary action code paths call truth APIs first.
- [x] Audit `frontend/app/positions/new/page.tsx` and `frontend/app/positions/[id]/add-batch/page.tsx` for legacy fallback conditions.
- [x] Convert ambiguous legacy fallback copy into explicit migration fallback copy.
- [x] Add a rollback flag or documented rollback path for truth-first write routing.

P11 Task 1A result:
- Existing-position add/reduce/close paths now prefer `TradingPosition / PositionEvent`.
- Legacy `POST /api/positions/{position_id}/batches` is rejected with `409` once a truth lifecycle exists unless the caller sends `X-Migration-Fallback: legacy-batch-write`.
- `/positions/[id]/add-batch?migrationFallback=1` is the explicit migration fallback route for legacy batch backfill.
- `/positions/new` no longer silently falls back to legacy batch writes when adding to an existing position without a truth lifecycle.
- Brand-new position creation now uses a create-and-sync transition contract: `POST /api/positions` still creates the legacy row, immediately syncs a `TradingPosition` lifecycle, returns `truth_position_public_id`, and the frontend routes to the truth detail when available.

Verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py
../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py
cd ../frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
```

Commit:

```bash
git commit -m "feat: harden truth-first trading writes"
```

Verification log:
- RED backend: `../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py` failed because legacy batch write returned `201` instead of expected `409`.
- RED frontend: `node --experimental-strip-types --test tests/trading-adapter.test.mts tests/truth-first-writes.test.mts` failed because `getTruthFirstWriteFallbackState` was not exported and pages did not use explicit migration fallback guards.
- GREEN targeted backend: `../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py` ran 3 tests OK.
- GREEN targeted frontend: `node --experimental-strip-types --test tests/trading-adapter.test.mts tests/truth-first-writes.test.mts` ran 9 tests OK; Node emitted existing `MODULE_TYPELESS_PACKAGE_JSON` warnings.
- P11 Task 1 verification: `../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py` ran 25 tests OK.
- P11 Task 1 verification: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- P11 Task 1 verification: `npm run lint` exited 0.
- Extended frontend regression: `node --experimental-strip-types --test tests/*.test.mts` ran 82 tests OK; Node emitted existing `MODULE_TYPELESS_PACKAGE_JSON` warnings.
- RED create-and-sync backend: `../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py` failed because `POST /api/positions` did not return `truth_position_public_id`.
- RED create-and-sync frontend: `node --experimental-strip-types --test tests/truth-first-writes.test.mts` failed because `/positions/new` did not read `truth_position_public_id`.
- GREEN create-and-sync targeted backend: `../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py` ran 4 tests OK.
- GREEN create-and-sync targeted frontend: `node --experimental-strip-types --test tests/truth-first-writes.test.mts` ran 4 tests OK.
- P11 Task 1B verification: `../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py` ran 25 tests OK.
- P11 Task 1B verification: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- P11 Task 1B verification: `npm run lint` exited 0.
- Extended frontend regression after Task 1B: `node --experimental-strip-types --test tests/*.test.mts` ran 83 tests OK; Node emitted existing `MODULE_TYPELESS_PACKAGE_JSON` warnings.
- Full backend regression after Task 1B: `../.venv313/bin/python -m unittest discover -s tests` ran 153 tests OK; output included a Yahoo DNS warning from market-data-related code.

---

## Task 2: Define Review And Narrative Final Semantics

**Goal:** review and narrative edits write to `PositionEvent`/truth lifecycle, while legacy review fields become migration-only.

- [x] Write failing tests for truth event narrative update behavior.
- [x] Write failing tests or adapter checks for lifecycle page copy when truth narrative is available.
- [x] Decide and document which historical review fields remain read-only legacy support.
- [x] Update detail-page copy so users understand where the canonical review lives.
- [x] Stop ordinary review UI from patching legacy `Position.trade_review` when truth lifecycle exists.

P11 Task 2 result:
- Canonical review and narrative edits live on `PositionEvent` narrative fields through `/api/trading-positions/{position_public_id}/events/{event_public_id}/narrative`.
- Legacy historical review fields `Position.trade_review`, `Position.lessons`, and `Position.rating` are migration/support context once a matching `TradingPosition` exists.
- `PATCH /api/positions/{position_id}` rejects ordinary writes to those legacy review fields with `409` when truth lifecycle exists.
- Explicit migration correction remains possible with `X-Migration-Fallback: legacy-review-write`.
- Lifecycle detail copy now states that canonical review lives in `PositionEvent` narrative, and legacy review display is read-only migration context.

Rollback:
- Emergency migration correction can use `X-Migration-Fallback: legacy-review-write`.
- If the hard guard itself must be rolled back, revert the review-field gate in `backend/routers/positions.py::update_position`; keep the frontend truth narrative route as the preferred path.

Verification log:
- RED backend: `../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py` failed because legacy review PATCH returned `200` instead of expected `409`.
- RED frontend copy: `node --experimental-strip-types --test tests/truth-narrative-writes.test.mts` failed because lifecycle UI did not state the canonical review location.
- GREEN targeted backend: `../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py` ran 6 tests OK.
- GREEN targeted frontend: `node --experimental-strip-types --test tests/truth-narrative-writes.test.mts` ran 2 tests OK.
- P11 Task 2 verification: `../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py` ran 25 tests OK.
- P11 Task 2 verification: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- P11 Task 2 verification: `npm run lint` exited 0.
- Extended frontend regression after Task 2: `node --experimental-strip-types --test tests/*.test.mts` ran 85 tests OK; Node emitted existing `MODULE_TYPELESS_PACKAGE_JSON` warnings.
- Full backend regression after Task 2: `../.venv313/bin/python -m unittest discover -s tests` ran 155 tests OK; output included a Yahoo DNS warning from market-data-related code.

Verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py
cd ../frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
```

Commit:

```bash
git commit -m "feat: finalize truth narrative write path"
```

---

## Task 3: Product Decision Gate For Reversal, Void, Archive, And Delete

**Goal:** prevent irreversible legacy deletion semantics from leaking into the truth lifecycle.

- [x] Document final behavior for historical/non-latest reversal.
- [x] Document final behavior for `OPEN` reversal.
- [x] Document final behavior for whole-position delete versus archive/void.
- [x] Document final behavior for legacy batch edit.
- [x] Add backend tests for any chosen hard rejections before implementing new write paths.

Recommended default unless product decides otherwise:
- Latest active event reversal remains ordinary-user supported.
- Non-latest reversal is rejected or admin-only until compensating event UX exists.
- `OPEN` reversal becomes audited void/archive, not hard delete.
- Whole-position hard delete remains migration/admin-only.
- Legacy batch edit is read-only migration support when truth lifecycle exists.

P11 Task 3 result:
- Latest active `ADD` / `REDUCE` / `CLOSE` reversal remains ordinary-user supported through `/api/trading-positions/{position_public_id}/events/{event_public_id}/reverse`; it appends a `REVERSAL` event and preserves the audit trail.
- Non-latest active trade-event reversal stays rejected with `422` until a compensating-event UX exists.
- `OPEN` event reversal stays rejected with `422`; future product work should introduce audited void/archive semantics rather than deleting the opening event or legacy row.
- Whole-position hard delete through `DELETE /api/positions/{position_id}` is rejected with `409` once a truth lifecycle exists. Explicit migration-only fallback requires `X-Migration-Fallback: legacy-position-delete`.
- Legacy `PATCH /api/positions/batches/{batch_id}` and `DELETE /api/positions/batches/{batch_id}` are rejected with `409` once a truth lifecycle exists. Explicit migration-only fallback requires `X-Migration-Fallback: legacy-batch-edit`.
- Legacy batch create remains separately migration-gated by `X-Migration-Fallback: legacy-batch-write`.

Rollback:
- For migration cleanup only, use `legacy-position-delete` or `legacy-batch-edit` fallback headers.
- To roll back the hard guard, revert the destructive legacy mutation gates in `backend/routers/positions.py`; keep truth reversal behavior unchanged.

Verification log:
- RED backend: `../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py` failed because legacy position delete returned `204`, legacy batch edit returned `200`, and legacy batch delete returned `204` instead of expected `409`.
- GREEN targeted backend: `../.venv313/bin/python -m unittest discover -s tests -p test_position_truth_bridge_router.py` ran 9 tests OK.
- P11 Task 3 verification: `../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py` ran 25 tests OK.
- Full backend regression after Task 3: `../.venv313/bin/python -m unittest discover -s tests` ran 158 tests OK; output included a Yahoo DNS warning from market-data-related code.

Verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_trading_position_lifecycle_router.py
```

Commit:

```bash
git commit -m "docs: define truth lifecycle mutation semantics"
```

---

## Task 4: Make Timeline And Review Inbox Truth/Snapshot-Backed By Default

**Goal:** Timeline Home and Review Inbox stop relying on legacy `Position` as the default primary read path.

- [x] Write failing tests for snapshot/truth default behavior in `/api/timeline/home`.
- [x] Keep a rollback feature flag for legacy mixed feed.
- [x] Promote `DerivedTimelineSnapshot` and truth lifecycle data to default feed source.
- [x] Ensure empty, zero, small-data, AI insight, missing review, losing streak, stale data, and sync exception states still render.
- [x] Update trust/freshness metadata so UI can explain snapshot age and fallback state.

P11 Task 4 result:
- `/api/timeline/home` defaults to `SNAPSHOT_ONLY` through `timeline_source_policy`; `timeline_legacy_mixed_feed_enabled` remains the rollback feature flag.
- Timeline events default to `DerivedTimelineSnapshot` plus auditable insight artifacts.
- Review Inbox missing-review items now default to `DerivedTimelineSnapshot.snapshot_json.review_status == CLOSED_PENDING_REVIEW`, linking users to the truth lifecycle detail route.
- Legacy `Position` missing-review, losing streak, data stale, legacy AI, and sync-exception builders remain available only when the legacy mixed-feed rollback flag is enabled.
- Timeline top-level meta and timeline feed trust now include `note` values of `Snapshot-first truth/snapshot read model` or `Legacy mixed fallback enabled`; the frontend trust label surfaces that note.

Rollback:
- Enable `timeline_legacy_mixed_feed_enabled` for targeted users or globally to restore the mixed legacy feed and legacy Review Inbox builders.
- If the snapshot default must be reverted, change `services.timeline_source_policy.get_timeline_source_mode` back to legacy mixed default and remove the default snapshot Review Inbox branch in `backend/routers/timeline.py`.

Verification log:
- RED backend: `../.venv313/bin/python -m unittest discover -s tests -p test_timeline_home_router.py` failed because default Review Inbox still emitted legacy missing-review and snapshot `CLOSED_PENDING_REVIEW` produced no inbox item.
- RED frontend: `node --experimental-strip-types --test tests/timeline-adapter.test.mts` failed because trust labels did not surface fallback/source-mode notes.
- GREEN targeted backend: `../.venv313/bin/python -m unittest discover -s tests -p test_timeline_home_router.py` ran 19 tests OK; output included a Yahoo DNS warning from market-data-related code.
- P11 Task 4 verification: `../.venv313/bin/python -m unittest discover -s tests -p test_timeline_source_policy.py` ran 2 tests OK.
- P11 Task 4 verification: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- P11 Task 4 verification: `npm run lint` exited 0.
- Extended backend regression after Task 4: `../.venv313/bin/python -m unittest discover -s tests` ran 160 tests OK; output included a Yahoo DNS warning from market-data-related code.
- Extended frontend regression after Task 4: `node --experimental-strip-types --test tests/*.test.mts` ran 86 tests OK; Node emitted existing `MODULE_TYPELESS_PACKAGE_JSON` warnings.
- Browser smoke: `npm run dev -- --port 51559` served `/`, `/timeline`, and `/login`; unauthenticated browser state redirected to `/login`, so authenticated Timeline visual smoke was not completed in this session.

Verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests -p test_timeline_home_router.py
../.venv313/bin/python -m unittest discover -s tests -p test_timeline_source_policy.py
cd ../frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
```

Browser smoke:
- Open `/`.
- Confirm Timeline loads.
- Confirm Review Inbox cards have actions.
- Confirm empty/zero state still has useful guidance.
- Confirm fallback state is visibly labeled if rollback flag is enabled.

Commit:

```bash
git commit -m "feat: default timeline to truth snapshots"
```

---

## Task 5: Isolate Remaining Legacy UI As Migration Tools

**Goal:** legacy controls are visually and semantically migration-only, not normal product affordances.

- [x] Audit `/positions`, `/positions/[id]`, and any batch edit controls.
- [x] Rename or label legacy-only sections as migration/support.
- [x] Prevent new frontend work from importing raw legacy DTOs except in migration tools.
- [x] Add adapter-level tests where feasible.
- [x] Update `docs/TODO.md` with remaining delete candidates.

P11 Task 5 result:
- `/positions` expanded batch rows are labeled `Legacy batch timeline` with `Migration/support context`.
- `/positions` add/reduce/close links are labeled as truth event entry points and still route through the truth-first add-batch page.
- `/positions/[id]/add-batch` now visibly distinguishes the `Truth write path` from `legacy batch migration fallback`.
- Existing lifecycle detail legacy panels remain secondary migration panels through `LifecycleMigrationPanel`.
- `frontend/tests/legacy-ui-boundaries.test.mts` prevents raw legacy trading DTO imports from spreading beyond the current migration/adapter boundary list.

Remaining delete/isolation candidates:
- `frontend/app/positions/page.tsx` legacy batch expansion after a dedicated truth position list/read model exists.
- `frontend/app/positions/new/page.tsx` raw legacy create DTO once `POST /api/trading-positions` can create truth positions directly.
- `frontend/app/positions/[id]/add-batch/page.tsx` raw `Position` dependency once the truth lifecycle response carries enough quantity/currency context for event forms.
- `frontend/components/dashboard/MaeMfeScatterPlot.tsx` and `frontend/lib/adapters/chart-views.ts` legacy position chart adapter after dashboard charts are fully schema/read-model backed.
- `frontend/lib/adapters/trading.ts` legacy DTO adapter after remaining migration tools are split out.

Verification log:
- RED frontend: `node --experimental-strip-types --test tests/legacy-ui-boundaries.test.mts` failed because `/positions` and `add-batch` did not expose migration/truth boundary copy, and the raw DTO boundary list was not documented in tests.
- GREEN targeted frontend: `node --experimental-strip-types --test tests/legacy-ui-boundaries.test.mts` ran 3 tests OK.
- P11 Task 5 verification: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- P11 Task 5 verification: `npm run lint` exited 0.
- Extended frontend regression after Task 5: `node --experimental-strip-types --test tests/*.test.mts` ran 89 tests OK; Node emitted existing `MODULE_TYPELESS_PACKAGE_JSON` warnings.
- Full backend regression after Task 5: `../.venv313/bin/python -m unittest discover -s tests` ran 160 tests OK; output included a Yahoo DNS warning from market-data-related code.

Verification:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
cd ../backend
../.venv313/bin/python -m unittest discover -s tests
```

Browser smoke:
- Open `/positions`.
- Open a truth lifecycle detail page.
- Confirm legacy panels are secondary and migration-labeled.
- Confirm ordinary add/reduce/close actions route through truth paths.

Commit:

```bash
git commit -m "feat: isolate legacy trading controls"
```

---

## Task 6: P11 Completion Gate

- [x] Full backend tests pass.
- [x] Frontend typecheck passes.
- [x] Frontend lint passes.
- [ ] Authenticated browser smoke covers `/`, `/timeline`, `/positions`, `/positions/[id]`, and `/positions/[id]/add-batch`.
- [x] Legacy inventory is updated with actual post-P11 classifications.
- [x] `TODO.md` marks P11 completed or lists precise remaining blockers.
- [x] P12 platform contract hardening plan is created or selected as next active lane.

P11 Task 6 result:
- P11 code tasks are complete and committed through Task 5.
- Legacy inventory now reflects the post-P11 state: ordinary writes are truth-first, legacy writes are migration/support only behind explicit fallback headers, and Timeline/Review Inbox default to truth/snapshot read models.
- P12 Platform Contract Hardening is selected as the next active lane.
- Authenticated browser smoke remains the only completion-gate blocker: the app served `/`, `/timeline`, and `/login`, but the in-app browser was unauthenticated and redirected to `/login`, so `/positions`, `/positions/[id]`, and `/positions/[id]/add-batch` visual coverage was not completed in this session.

Verification log:
- Full backend regression: `../.venv313/bin/python -m unittest discover -s tests` ran 160 tests OK; output included an existing Yahoo/MSFT DNS warning from market-data-related code.
- Frontend typecheck: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- Frontend lint: `npm run lint` exited 0.
- Extended frontend regression: `node --experimental-strip-types --test tests/*.test.mts` ran 89 tests OK; Node emitted existing `MODULE_TYPELESS_PACKAGE_JSON` warnings.
- Diff hygiene: `git diff --check` exited 0.

Final verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
cd ../frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
cd ..
git diff --check
git status --short --branch
```

---

## Rollback And Stop Conditions

Rollback:
- Keep legacy mixed Timeline feed behind a feature flag until browser smoke is complete.
- Keep legacy routers mounted until ordinary truth write/read paths have passed tests.
- Revert one P11 commit at a time; do not revert P10 inventory, observability, or planning docs.

Stop and ask before continuing if:
- Product semantics for reversal/delete/archive are unclear.
- A test requires deleting or rewriting historical user data.
- Timeline snapshot-only mode loses review inbox coverage.
- Frontend changes require broad `frontend/lib/api.ts` expansion instead of read-model adapters.
- Full backend tests fail for a reason unrelated to known external network warnings.
