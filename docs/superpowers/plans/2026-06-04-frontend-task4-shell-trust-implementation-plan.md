# Frontend Task 4 Shell And Trust Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land stable frontend read-model adapters, trust/freshness primitives, and timeline-first navigation before rewriting the homepage.

**Architecture:** Keep backend V1 read-model contracts isolated from legacy `frontend/lib/api.ts` by adding a focused `frontend/lib/readModels.ts`. Add small trust/read-model display primitives that Task 6 can compose into the new homepage. Change navigation language toward the approved timeline-first IA without migrating the dashboard page body yet.

**Tech Stack:** Next.js App Router, TypeScript, React, Tailwind CSS, lucide-react, TypeScript compile-only contract tests.

---

## Files And Responsibilities

- Create `frontend/tests/task4-read-model-contract.tsx`: compile-only contract proving Task 4 exports are available without a new test runner.
- Create `frontend/lib/readModels.ts`: V1 read-model DTO types, endpoint path constants, trust tone helpers, and mock home/lifecycle adapters for Task 6.
- Create `frontend/components/trust/TrustMetaBadge.tsx`: reusable trust/freshness badge.
- Create `frontend/components/read-models/ReviewInboxPanel.tsx`: Review Inbox primitive.
- Create `frontend/components/read-models/TimelineEventCard.tsx`: timeline event primitive.
- Modify `frontend/components/Navbar.tsx`: shift labels to timeline-first IA and keep mobile quick capture explicit.
- Modify `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`: mark Task 4 complete after verification.

---

### Task 4A: Compile Contract For Read Models And Trust Components

**Files:**
- Create: `frontend/tests/task4-read-model-contract.tsx`

- [x] **Step 1: Write failing compile-only contract**

Create a TSX file that imports `buildMockHomeReadModel`, `homeReadModelPath`, `trustToneForFreshness`, `TrustMetaBadge`, `ReviewInboxPanel`, and `TimelineEventCard`. The file should type-check a home read model and render the primitives.

- [x] **Step 2: Run TypeScript and verify RED**

Run: `./node_modules/.bin/tsc --noEmit --pretty false`

Expected: FAIL because the imported read-model module and components do not exist.

### Task 4B: Add Read-Model Adapter And Trust Primitives

**Files:**
- Create: `frontend/lib/readModels.ts`
- Create: `frontend/components/trust/TrustMetaBadge.tsx`
- Create: `frontend/components/read-models/ReviewInboxPanel.tsx`
- Create: `frontend/components/read-models/TimelineEventCard.tsx`

- [x] **Step 1: Implement minimal adapter and primitives**

Add DTO types matching `/api/v1/read-models/home`, endpoint constants, `trustToneForFreshness()`, `buildMockHomeReadModel()`, and the three display primitives.

- [x] **Step 2: Run TypeScript and verify GREEN**

Run: `./node_modules/.bin/tsc --noEmit --pretty false`

Expected: PASS.

### Task 4C: Shift Navigation IA Without Rewriting Homepage

**Files:**
- Modify: `frontend/components/Navbar.tsx`

- [x] **Step 1: Update navigation labels**

Change `/` from `看板` to `时间线`, `/strategies` from `策略` to `规则与清单`, and `/insights` from `AI洞察` to `复盘/洞察`. Keep `/positions/new` visible as the mobile quick capture action.

- [x] **Step 2: Run TypeScript and verify GREEN**

Run: `./node_modules/.bin/tsc --noEmit --pretty false`

Expected: PASS.

### Task 4D: Gate Verification And Plan Update

**Files:**
- Modify: `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`
- Modify: `docs/superpowers/plans/2026-06-04-frontend-task4-shell-trust-implementation-plan.md`

- [x] **Step 1: Run frontend verification**

Run: `./node_modules/.bin/tsc --noEmit --pretty false`

Expected: PASS.

- [x] **Step 2: Run backend regression check**

Run: `cd backend && ../.venv/bin/python -m pytest tests -q`

Expected: PASS.

- [x] **Step 3: Review diff**

Run: `git diff --check`

Expected: no output.

- [x] **Step 4: Update plans**

Mark Task 4 complete only after adapter isolation, trust primitives, mock read models, navigation IA, frontend TypeScript, backend tests, and diff check are verified.

**Progress 2026-06-04:**
- Added compile-only Task 4 contract in `frontend/tests/task4-read-model-contract.tsx`.
- Added `frontend/lib/readModels.ts` with V1 read-model DTOs, endpoint constants, trust tone helpers, and mock home adapter data.
- Added `TrustMetaBadge`, `ReviewInboxPanel`, and `TimelineEventCard` primitives for Task 6 composition.
- Updated navigation labels toward timeline-first IA and added mobile quick capture as the center action.
- Verification: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false` passed; `cd backend && ../.venv/bin/python -m pytest tests -q` passed with 28 tests; `git diff --check` clean.
