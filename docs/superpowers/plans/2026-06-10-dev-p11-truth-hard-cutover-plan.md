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
- `docs/superpowers/plans/2026-06-10-dev-p10-legacy-cutover-inventory.md`

---

## Task 1: Freeze Ordinary User Writes To Truth Routes

**Goal:** ordinary create/add/reduce/close flows prefer truth routes, with legacy writes allowed only as explicit migration fallback.

- [ ] Write failing backend tests proving truth event writes cover ADD / REDUCE / CLOSE and reject closed-position writes.
- [ ] Write failing frontend tests or static checks proving new ordinary action code paths call truth APIs first.
- [ ] Audit `frontend/app/positions/new/page.tsx` and `frontend/app/positions/[id]/add-batch/page.tsx` for legacy fallback conditions.
- [ ] Convert ambiguous legacy fallback copy into explicit migration fallback copy.
- [ ] Add a rollback flag or documented rollback path for truth-first write routing.

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

---

## Task 2: Define Review And Narrative Final Semantics

**Goal:** review and narrative edits write to `PositionEvent`/truth lifecycle, while legacy review fields become migration-only.

- [ ] Write failing tests for truth event narrative update behavior.
- [ ] Write failing tests or adapter checks for lifecycle page copy when truth narrative is available.
- [ ] Decide and document which historical review fields remain read-only legacy support.
- [ ] Update detail-page copy so users understand where the canonical review lives.
- [ ] Stop ordinary review UI from patching legacy `Position.trade_review` when truth lifecycle exists.

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

- [ ] Document final behavior for historical/non-latest reversal.
- [ ] Document final behavior for `OPEN` reversal.
- [ ] Document final behavior for whole-position delete versus archive/void.
- [ ] Document final behavior for legacy batch edit.
- [ ] Add backend tests for any chosen hard rejections before implementing new write paths.

Recommended default unless product decides otherwise:
- Latest active event reversal remains ordinary-user supported.
- Non-latest reversal is rejected or admin-only until compensating event UX exists.
- `OPEN` reversal becomes audited void/archive, not hard delete.
- Whole-position hard delete remains migration/admin-only.
- Legacy batch edit is read-only migration support when truth lifecycle exists.

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

- [ ] Write failing tests for snapshot/truth default behavior in `/api/timeline/home`.
- [ ] Keep a rollback feature flag for legacy mixed feed.
- [ ] Promote `DerivedTimelineSnapshot` and truth lifecycle data to default feed source.
- [ ] Ensure empty, zero, small-data, AI insight, missing review, losing streak, stale data, and sync exception states still render.
- [ ] Update trust/freshness metadata so UI can explain snapshot age and fallback state.

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

- [ ] Audit `/positions`, `/positions/[id]`, and any batch edit controls.
- [ ] Rename or label legacy-only sections as migration/support.
- [ ] Prevent new frontend work from importing raw legacy DTOs except in migration tools.
- [ ] Add adapter-level tests where feasible.
- [ ] Update `docs/TODO.md` with remaining delete candidates.

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

- [ ] Full backend tests pass.
- [ ] Frontend typecheck passes.
- [ ] Frontend lint passes.
- [ ] Browser smoke covers `/`, `/timeline`, `/positions`, `/positions/[id]`, and `/positions/[id]/add-batch`.
- [ ] Legacy inventory is updated with actual post-P11 classifications.
- [ ] `TODO.md` marks P11 completed or lists precise remaining blockers.
- [ ] P12 platform contract hardening plan is created or selected as next active lane.

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
