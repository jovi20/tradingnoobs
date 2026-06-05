# Dev P0-P4 Execution Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the next platform/frontend hardening stages on `dev`: refresh planning truth, harden Timeline Home, finish Lifecycle Detail cutover, strengthen async operations, and prepare Dashboard/Insights for schema-first migration.

**Architecture:** Keep `dev` as the integration branch and move bridge surfaces toward durable read models in small verified slices. Backend owns truth events, derived snapshots, auditable AI artifacts, job/outbox/idempotency contracts, and schema-first payloads; frontend consumes those through typed adapters rather than expanding legacy DTO usage.

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, pytest/unittest, Next.js App Router, TypeScript, Tailwind CSS, Node test runner

---

## Current Dev Baseline

- Branch: `dev`
- Remote target: `origin/dev`
- Latest integrated commit at plan creation: `61ed189 feat: integrate auditable insight artifacts into dev`
- Known untouched local item: `docs/superpowers/demos/`
- Existing verification from the integration slice:
  - Backend: `135 passed, 20 warnings`
  - Frontend TypeScript: `tsc --noEmit --pretty false` passed
  - Frontend build: `npm run build` passed
  - Alembic current and temp DB upgrade passed
  - `git diff --check` passed

## Execution Rules

- Work on `dev` unless the user explicitly changes the branch target.
- Keep `main` as baseline; do not create a PR to `main` unless requested.
- Do not modify or remove `docs/superpowers/demos/`.
- Use TDD for behavior changes: write a failing test, observe the expected failure, implement, then rerun.
- Commit and push each coherent stage boundary, so `dev` remains reviewable.
- Before calling any stage complete, rerun the stage-specific verification listed below.

---

### Task 0: Refresh Planning State

**Files:**
- Modify: `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`
- Modify: `docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md`
- Create: `docs/superpowers/plans/2026-06-05-dev-p0-p4-execution-plan.md`

- [x] **Step 1: Update sequencing plan statuses**

Set Task 5/6/7 statuses to match `61ed189`:
- AI artifact foundation exists through `InsightRun` / `InsightArtifact`.
- Timeline still needs final truth/snapshot hard cut.
- Lifecycle still needs final edit/review/batch cutover.
- Dashboard/Insights still wait for schema-first chart and AI presentation contracts.

- [x] **Step 2: Update checkpoint**

Append a 2026-06-05 refresh section that records:
- `61ed189 feat: integrate auditable insight artifacts into dev`
- closed PR-to-main path
- `dev` pushed to `origin/dev`
- full backend/frontend/build/Alembic verification from the integration slice
- remaining local untracked `docs/superpowers/demos/`

- [x] **Step 3: Verify docs diff**

Run: `git diff -- docs/superpowers/plans`
Expected: only plan/checkpoint status updates and this execution plan.

- [x] **Step 4: Commit and push Task 0**

Run:
```bash
git add docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md docs/superpowers/plans/2026-06-05-dev-p0-p4-execution-plan.md
git commit -m "docs: refresh dev p0 p4 execution plan"
git push origin dev
```

Expected: commit succeeds and `origin/dev` advances.

---

### Task 1: Timeline Home Truth/Snapshot Hard Cut Readiness

**Files:**
- Modify: `backend/routers/timeline.py`
- Modify: `backend/services/derived_timeline_read_service.py`
- Modify: `backend/services/derived_refresh_handlers.py`
- Test: `backend/tests/test_timeline_home_router.py`
- Test: `backend/tests/test_derived_timeline_read_service.py` if the existing service coverage needs a focused extension
- Modify: `frontend/lib/timelineAdapter.ts` or the current timeline adapter file
- Modify: `frontend/app/timeline/page.tsx`
- Test: `frontend/tests/*timeline*.test.mts` or create `frontend/tests/timeline-snapshot-contract.test.mts`

- [x] **Step 1: Add backend failing test for snapshot-only default readiness**

Cover `/api/timeline/home` when the snapshot-only flag is enabled for a user:
- returns only derived timeline snapshot events
- includes AI artifact-backed events when present
- preserves cursor/limit ordering
- returns an empty but valid feed when no snapshots exist
- does not build legacy quote/LLM exception paths

- [x] **Step 2: Implement minimal backend read behavior**

Make the snapshot-only path the complete contract path behind the feature flag:
- `summary_bar`, `review_inbox`, `timeline`, and `context_rail` remain present
- each module carries trust metadata when its freshness/source differs
- AI events link to `artifact_public_id`

- [x] **Step 3: Add frontend adapter failing test**

Cover a snapshot-only response containing:
- a truth trade event
- an AI insight event with artifact link
- an empty review inbox
- module trust metadata

- [x] **Step 4: Implement minimal frontend adapter/page behavior**

Ensure Timeline Home renders snapshot-only payloads without legacy assumptions and without treating AI markdown as the primary audited surface.

- [x] **Step 5: Verify Task 1**

Run:
```bash
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests/test_timeline_home_router.py backend/tests/test_derived_timeline_read_service.py -q
node --experimental-strip-types --test frontend/tests/*.test.mts
```

Expected: all selected backend and frontend tests pass.

- [x] **Step 6: Commit and push Task 1**

Run:
```bash
git add backend frontend
git commit -m "feat: harden timeline snapshot home contract"
git push origin dev
```

---

### Task 2: Lifecycle Detail Hard Cutover

**Files:**
- Modify: `backend/routers/trading_positions.py`
- Modify: `backend/services/trading_position_read_service.py`
- Modify: `backend/services/trading_position_write_service.py`
- Test: `backend/tests/test_trading_position_lifecycle_router.py`
- Modify: `frontend/app/positions/[id]/page.tsx`
- Modify: `frontend/lib/tradingPositionClient.ts` or current trading position API client
- Modify: lifecycle adapter files under `frontend/lib` / `frontend/components`
- Test: existing lifecycle/frontend adapter tests

- [x] **Step 1: Add backend failing tests for final lifecycle semantics**

Cover:
- truth lifecycle returns ledger cash effects, evidence refs, and AI artifacts in one envelope
- legacy batch edit/delete endpoints are not used when a truth lifecycle exists
- unsupported historical reversal and `OPEN` reversal remain rejected with explicit messages
- review/narrative updates target `PositionEvent` fields rather than legacy `Position` fields

- [x] **Step 2: Implement minimal backend hard cutover behavior**

Keep migration bridge routes available only as explicitly labeled bridge paths, and make ordinary lifecycle/detail behavior truth-first.

- [x] **Step 3: Add frontend failing tests for migration-tool labeling**

Cover:
- truth lifecycle page renders edit/review/batch legacy controls as migration tools or disables them
- latest allowed reversal and manual adjustment remain available
- AI sidecar reads artifact-backed content

- [x] **Step 4: Implement minimal frontend hard cutover behavior**

Move user-facing detail actions onto truth routes or label old flows as migration tools.

- [x] **Step 5: Verify Task 2**

Run:
```bash
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests/test_trading_position_lifecycle_router.py backend/tests/test_insight_artifact_service.py backend/tests/test_insight_artifacts_api.py -q
node --experimental-strip-types --test frontend/tests/*.test.mts
```

- [x] **Step 6: Commit and push Task 2**

Run:
```bash
git add backend frontend
git commit -m "feat: complete truth lifecycle detail cutover"
git push origin dev
```

---

### Task 3: Async Operations Hardening

**Files:**
- Modify: `backend/services/job_service.py`
- Modify: `backend/services/outbox_service.py`
- Modify: `backend/services/business_lock_service.py`
- Modify: `backend/routers/admin.py`
- Modify: `frontend/app/admin/jobs/page.tsx`
- Test: `backend/tests/test_job_service.py`
- Test: `backend/tests/test_outbox_models.py` or current outbox service tests
- Test: admin jobs API/frontend adapter tests

- [x] **Step 1: Add failing tests for running job control semantics**

Cover:
- queued/retrying jobs can be canceled
- running jobs cannot be silently canceled
- force-cancel requires explicit supported status transition
- business locks are released or marked according to final status
- idempotency keys retain enough result/error state for replay/debugging

- [x] **Step 2: Implement minimal safe job control**

Define and implement the smallest safe status model for interrupt/force-cancel semantics without adding Redis dependency yet.

- [x] **Step 3: Add admin UI/adapter tests**

Cover:
- unsafe actions are hidden or disabled for running jobs
- failed/retrying jobs expose requeue
- canceled jobs display final event history

- [x] **Step 4: Implement admin UI hardening**

Expose clear job state and action availability using the existing admin jobs page patterns.

- [x] **Step 5: Verify Task 3**

Run:
```bash
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests/test_job_service.py backend/tests/test_business_lock_service.py backend/tests/test_admin_jobs_api.py -q
node --experimental-strip-types --test frontend/tests/*.test.mts
```

- [x] **Step 6: Commit and push Task 3**

Run:
```bash
git add backend frontend
git commit -m "feat: harden async job operations"
git push origin dev
```

---

### Task 4: Dashboard and Insights Schema-First Preparation

**Files:**
- Create or modify: `backend/services/chart_schema_service.py`
- Modify: `backend/routers/dashboard.py`
- Modify: `backend/routers/insights.py`
- Modify: `backend/routers/insight_artifacts.py`
- Test: dashboard/insights backend tests
- Create or modify: `frontend/lib/chartSchemas.ts`
- Modify: `frontend/app/dashboard/page.tsx`
- Modify: `frontend/app/insights/page.tsx`
- Test: frontend chart/insight adapter tests

- [x] **Step 1: Add failing backend tests for schema-first chart payloads**

Cover:
- dashboard chart payloads expose stable chart type, dimensions, series, and trust metadata
- legacy chart-specific payloads remain available only where needed for bridge compatibility

- [x] **Step 2: Implement minimal chart schema service**

Create a small internal schema layer used by dashboard routes before touching frontend visual design.

- [x] **Step 3: Add failing frontend tests for chart schema adapters**

Cover:
- schema-first chart payload adapts into existing chart components
- missing/partial data renders an explicit empty state

- [x] **Step 4: Implement frontend chart adapters**

Keep current UI layout, but consume the schema-first adapter where available.

- [x] **Step 5: Add failing insight presentation tests**

Cover:
- `InsightArtifact` summaries are the primary AI card source
- legacy markdown is displayed only as legacy read-only content
- artifact evidence links are visible to Timeline, Lifecycle, and Insights consumers

- [x] **Step 6: Implement insight presentation hardening**

Unify AI cards around auditable artifacts and keep old markdown as fallback/migration content.

- [x] **Step 7: Verify Task 4**

Run:
```bash
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests -q
./node_modules/.bin/tsc --noEmit --pretty false
npm run build
```

- [x] **Step 8: Commit and push Task 4**

Run:
```bash
git add backend frontend
git commit -m "feat: prepare dashboard insights schema contracts"
git push origin dev
```

---

### Task 5: Final Verification and Goal Closeout

**Files:**
- Modify: `docs/superpowers/plans/2026-06-05-dev-p0-p4-execution-plan.md`
- Modify: `docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md`

- [x] **Step 1: Mark completed plan items**

Update this plan and the checkpoint with:
- completed task list
- commit SHAs
- exact verification commands and results
- any remaining migration-only paths

Completion record:

- P0 `5c60523 docs: refresh dev p0 p4 execution plan`
- P1 `0c103f5 feat: harden timeline snapshot home contract`
- P2 `d1cbb44 feat: complete truth lifecycle detail cutover`
- P3 `344de3e feat: harden async job operations`
- P4 `c626e2c feat: prepare dashboard insights schema contracts`

Stage verification recorded during execution:

- P1: `17 passed` backend timeline/derived tests; `30 passed` frontend tests.
- P2: `27 passed` backend lifecycle/artifact tests; `31 passed` frontend tests.
- P3: `25 passed` backend job/admin/business-lock tests; `31 passed` frontend tests.
- P4: `141 passed, 20 warnings` backend full tests; `36 passed` frontend Node tests; frontend `tsc --noEmit --pretty false` passed; frontend `npm run build` passed.

Remaining migration-only paths:

- Legacy lifecycle routes and legacy position review/batch/delete controls remain bridge/migration surfaces when truth lifecycle is missing.
- Legacy AI markdown remains read-only fallback; auditable `InsightArtifact` summary/evidence/trust metadata is the primary AI presentation contract.
- Historical/non-latest reversal and `OPEN` reversal remain intentionally blocked until audit/accounting semantics are explicitly designed.
- `docs/superpowers/demos/` remains untouched user content.

- [x] **Step 2: Run final verification**

Run:
```bash
git diff --check
PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests -q
./node_modules/.bin/tsc --noEmit --pretty false
npm run build
PYTHONPATH=backend DATABASE_URL=sqlite:////private/tmp/tradingnoobs_dev_p0_p4_final.db /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/alembic -c backend/alembic.ini upgrade head
```

Final verification result:

- `git diff --check`: clean.
- `PYTHONPATH=backend /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/python -m pytest backend/tests -q`: `141 passed, 20 warnings`.
- `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false`: passed.
- `cd frontend && npm run build`: passed.
- `PYTHONPATH=backend DATABASE_URL=sqlite:////private/tmp/tradingnoobs_dev_p0_p4_final.db /Users/a1/vibecoding/tradingnoobs/.worktrees/execute-plan-task0/.venv/bin/alembic -c backend/alembic.ini upgrade head`: upgraded through `5e6f7a8b9cad`.

- [x] **Step 3: Commit and push final docs**

Run:
```bash
git add docs/superpowers/plans/2026-06-05-dev-p0-p4-execution-plan.md docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md
git commit -m "docs: record dev p0 p4 completion"
git push origin dev
```

- [x] **Step 4: Mark goal complete**

Only mark the long-running goal complete after all P0-P4 tasks pass verification and `origin/dev` includes the final commits.
