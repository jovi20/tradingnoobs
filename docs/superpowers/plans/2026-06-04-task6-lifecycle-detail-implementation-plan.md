# Task 6 Lifecycle Detail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make public-id position detail links render an event-sourced lifecycle thread with ledger, evidence, narrative, and trust metadata.

**Architecture:** Keep legacy numeric `/positions/{id}` detail readable while new public-id `/positions/{position_public_id}` links use the V1 lifecycle read model. Extend the Task 6 read-model client/hook boundary instead of binding the page to legacy `positionsAPI`. Render lifecycle detail through a focused component that can later replace the numeric legacy page once list routes are migrated.

**Tech Stack:** Next.js App Router, React, TypeScript, TanStack Query, Tailwind CSS, lucide-react.

---

## Files And Responsibilities

- Create `frontend/tests/task6-lifecycle-contract.tsx`: compile-only contract for lifecycle client, hook, component, and route mode selection.
- Modify `frontend/lib/readModelClient.ts`: add `readModelsAPI.lifecycle(token, positionPublicId)`.
- Create `frontend/hooks/useLifecycleReadModel.ts`: React Query hook for lifecycle detail.
- Create `frontend/components/lifecycle/LifecycleThread.tsx`: lifecycle thread, ledger refs, evidence list, narrative signals, trust metadata, and loading/error/empty states.
- Modify `frontend/app/positions/[id]/page.tsx`: route public-id params to `LifecycleThread`; keep numeric params on legacy detail.
- Modify `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`: mark lifecycle detail complete after verification.

---

### Task 6E: Compile Contract For Lifecycle Detail

**Files:**
- Create: `frontend/tests/task6-lifecycle-contract.tsx`

- [x] **Step 1: Write failing compile-only contract**

Create a TSX file that imports `readModelsAPI.lifecycle`, `useLifecycleReadModel`, `LifecycleThread`, and `lifecycleReadModelPath`, then type-checks a `LifecycleReadModel`.

- [x] **Step 2: Run TypeScript and verify RED**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false`

Expected: FAIL because lifecycle client/hook/component are incomplete.

### Task 6F: Add Lifecycle Client, Hook, And Component

**Files:**
- Modify: `frontend/lib/readModelClient.ts`
- Create: `frontend/hooks/useLifecycleReadModel.ts`
- Create: `frontend/components/lifecycle/LifecycleThread.tsx`

- [x] **Step 1: Implement lifecycle client and hook**

Add V1 lifecycle fetching through `lifecycleReadModelPath(positionPublicId)`.

- [x] **Step 2: Implement lifecycle thread component**

Render ordered lifecycle nodes, ledger refs, evidence items, narrative signals, trust metadata, loading, empty, and error states.

- [x] **Step 3: Run TypeScript and verify GREEN**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false`

Expected: PASS.

### Task 6G: Route Public IDs To Lifecycle Thread

**Files:**
- Modify: `frontend/app/positions/[id]/page.tsx`

- [x] **Step 1: Split route behavior**

If `[id]` is numeric, render the existing legacy detail page. If `[id]` is non-numeric, render the new lifecycle thread using the public id.

- [x] **Step 2: Run frontend build**

Run: `cd frontend && npm run build`

Expected: PASS.

### Task 6H: Gate Verification And Plan Update

**Files:**
- Modify: `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`
- Modify: `docs/superpowers/plans/2026-06-04-task6-lifecycle-detail-implementation-plan.md`

- [x] **Step 1: Run frontend verification**

Run: `cd frontend && npm run build`

Expected: PASS.

- [x] **Step 2: Run backend regression check**

Run: `cd backend && ../.venv/bin/python -m pytest tests -q`

Expected: PASS.

- [x] **Step 3: Review diff**

Run: `git diff --check`

Expected: no output.

- [x] **Step 4: Update plans**

Mark lifecycle detail complete only after public-id routes render the lifecycle thread and verification passes.

**Progress 2026-06-04:**
- Added `readModelsAPI.lifecycle()` and `useLifecycleReadModel()` for `/api/v1/read-models/trading-positions/{position_public_id}/lifecycle`.
- Added `LifecycleThread` with ordered lifecycle nodes, ledger refs, evidence cards, narrative signals, trust metadata, loading, empty, and error states.
- Updated `/positions/[id]` so public-id params render the lifecycle thread while numeric legacy ids keep the existing legacy detail page.
- Verification: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false` passed; `cd frontend && npm run build` passed; `cd backend && ../.venv/bin/python -m pytest tests -q` passed with 28 tests; `git diff --check` clean.
