# Task 6 Timeline Homepage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship the default homepage as a timeline-first surface with Review Inbox, context rail, and evidence/trust cues.

**Architecture:** Keep `/` as a thin page wrapper and move the user-facing homepage composition into `frontend/components/home/TimelineHome.tsx`. Fetch V1 read models through a focused `frontend/lib/readModelClient.ts` and `frontend/hooks/useHomeReadModel.ts`, not through the legacy dashboard DTO layer. Reuse Task 4 primitives so the new page can swap mock/real data without reshaping UI code.

**Tech Stack:** Next.js App Router, React, TypeScript, TanStack Query, Tailwind CSS, lucide-react.

---

## Files And Responsibilities

- Create `frontend/tests/task6-homepage-contract.tsx`: compile-only contract for the new homepage route dependencies.
- Create `frontend/lib/readModelClient.ts`: authenticated fetch client for `/api/v1/read-models/home`.
- Create `frontend/hooks/useHomeReadModel.ts`: React Query hook for the homepage read model.
- Create `frontend/components/home/TimelineHome.tsx`: timeline-first homepage composition.
- Modify `frontend/app/page.tsx`: replace dashboard body with the Task 6 homepage wrapper.
- Modify `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`: mark homepage migration complete after verification.

---

### Task 6A: Compile Contract For Timeline Homepage

**Files:**
- Create: `frontend/tests/task6-homepage-contract.tsx`

- [x] **Step 1: Write failing compile-only contract**

Create a TSX file that imports `readModelsAPI`, `useHomeReadModel`, `TimelineHome`, and `buildMockHomeReadModel`. The file should type-check a `HomeReadModel`, call the API surface, and render `TimelineHome`.

- [x] **Step 2: Run TypeScript and verify RED**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false`

Expected: FAIL because `readModelClient`, `useHomeReadModel`, and `TimelineHome` do not exist.

### Task 6B: Add V1 Read-Model Client And Hook

**Files:**
- Create: `frontend/lib/readModelClient.ts`
- Create: `frontend/hooks/useHomeReadModel.ts`

- [x] **Step 1: Implement minimal client and hook**

Add `readModelsAPI.home(token)` using `API_BASE` and `homeReadModelPath`, plus `useHomeReadModel(token)` using React Query.

- [x] **Step 2: Run TypeScript and verify client/hook GREEN**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false`

Expected: remaining failures only mention `TimelineHome`, or PASS if the component already exists.

### Task 6C: Replace Homepage Body With Timeline-First Surface

**Files:**
- Create: `frontend/components/home/TimelineHome.tsx`
- Modify: `frontend/app/page.tsx`

- [x] **Step 1: Implement timeline homepage composition**

Render a top summary strip, Review Inbox, main timeline events, and context rail. Include loading, empty, and error states. Reuse `ReviewInboxPanel`, `TimelineEventCard`, and `TrustMetaBadge`.

- [x] **Step 2: Replace `frontend/app/page.tsx` with thin wrapper**

Use `useAuth()` and `useHomeReadModel(token)` in the page, then pass query state into `TimelineHome`.

- [x] **Step 3: Run TypeScript and verify GREEN**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false`

Expected: PASS.

### Task 6D: Gate Verification And Plan Update

**Files:**
- Modify: `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`
- Modify: `docs/superpowers/plans/2026-06-04-task6-timeline-homepage-implementation-plan.md`

- [x] **Step 1: Run frontend verification**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false`

Expected: PASS.

- [x] **Step 2: Run backend regression check**

Run: `cd backend && ../.venv/bin/python -m pytest tests -q`

Expected: PASS.

- [x] **Step 3: Review diff**

Run: `git diff --check`

Expected: no output.

- [x] **Step 4: Update plans**

Mark Task 6 homepage complete only after `/` uses the new timeline-first surface, frontend TypeScript passes, backend tests pass, and diff check is clean.

**Progress 2026-06-04:**
- Added `frontend/lib/readModelClient.ts` and `frontend/hooks/useHomeReadModel.ts` for `/api/v1/read-models/home`.
- Replaced `frontend/app/page.tsx` with a thin TimelineHome wrapper.
- Added `frontend/components/home/TimelineHome.tsx` with summary strip, Review Inbox, timeline, context rail, loading, empty, and error states.
- Removed `next/font/google` Inter dependency from `frontend/app/layout.tsx` and added local `.tn-app-shell` font stack so production builds do not require Google Fonts network access.
- Verification: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false` passed; `cd frontend && npm run build` passed; `cd backend && ../.venv/bin/python -m pytest tests -q` passed with 28 tests; `git diff --check` clean.
