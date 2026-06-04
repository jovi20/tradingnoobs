# Task 6 Dashboard Macro Route Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Keep Dashboard as a macro analysis view while preserving Timeline + Review Inbox as the default homepage.

**Architecture:** Add a dedicated `/dashboard` route that consumes the existing dashboard data hook and chart/card primitives. Keep the mobile bottom navigation focused on capture/review loops, but restore Dashboard in desktop navigation so it remains discoverable as a secondary macro surface.

**Tech Stack:** Next.js App Router, React, TypeScript, TanStack Query, Tailwind CSS, Recharts, existing dashboard components.

---

## Files And Responsibilities

- Create `frontend/tests/task6-dashboard-contract.tsx`: compile-only contract for the new Dashboard macro component.
- Create `frontend/components/dashboard/DashboardMacroView.tsx`: macro dashboard composition using existing dashboard hook/components.
- Create `frontend/app/dashboard/page.tsx`: thin route wrapper for Dashboard macro view.
- Modify `frontend/components/Navbar.tsx`: add desktop `Dashboard` route, keep mobile bottom nav unchanged.
- Modify `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`: mark Dashboard macro route complete after verification.

---

### Task 6I: Compile Contract For Dashboard Macro View

**Files:**
- Create: `frontend/tests/task6-dashboard-contract.tsx`

- [x] **Step 1: Write failing compile-only contract**

Import `DashboardMacroView` and render it in a TSX contract.

- [x] **Step 2: Run TypeScript and verify RED**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false`

Expected: FAIL because `DashboardMacroView` does not exist.

### Task 6J: Add Dashboard Macro View And Route

**Files:**
- Create: `frontend/components/dashboard/DashboardMacroView.tsx`
- Create: `frontend/app/dashboard/page.tsx`
- Modify: `frontend/components/Navbar.tsx`

- [x] **Step 1: Implement Dashboard macro view**

Use `useAuth()`, `useDashboardData()`, `StatCard`, `AllocationPieChart`, `PerformanceMovers`, `RiskMetricsCard`, `MaeMfeScatterPlot`, `PortfolioSankey`, `MarketStatus`, and existing trend/currency helpers.

- [x] **Step 2: Add `/dashboard` route**

Create a thin App Router page that renders `DashboardMacroView`.

- [x] **Step 3: Restore desktop Dashboard nav**

Add `/dashboard` with label `Dashboard` to the desktop nav only; mobile keeps the 4+1 capture/review bottom nav.

- [x] **Step 4: Run TypeScript and verify GREEN**

Run: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false`

Expected: PASS.

### Task 6K: Gate Verification And Plan Update

**Files:**
- Modify: `docs/superpowers/plans/2026-04-13-platform-frontend-sequencing-plan.md`
- Modify: `docs/superpowers/plans/2026-06-04-task6-dashboard-macro-route-implementation-plan.md`

- [x] **Step 1: Run frontend build**

Run: `cd frontend && npm run build`

Expected: PASS.

- [x] **Step 2: Run backend regression**

Run: `cd backend && ../.venv/bin/python -m pytest tests -q`

Expected: PASS.

- [x] **Step 3: Review diff**

Run: `git diff --check`

Expected: no output.

- [x] **Step 4: Update plans**

Mark Dashboard macro route complete only after `/dashboard` builds, `/` remains Timeline-first, and verification passes.

**Progress 2026-06-04:**
- Added `DashboardMacroView` as a secondary macro analysis surface using existing dashboard hooks and chart/card primitives.
- Added `/dashboard` route while keeping `/` as the Timeline + Review Inbox homepage.
- Restored desktop `Dashboard` navigation and kept mobile bottom navigation focused on capture/review.
- Verification: `cd frontend && ./node_modules/.bin/tsc --noEmit --pretty false` passed; `cd frontend && npm run build` passed with `/dashboard`; `cd backend && ../.venv/bin/python -m pytest tests -q` passed with 28 tests; `git diff --check` clean.
