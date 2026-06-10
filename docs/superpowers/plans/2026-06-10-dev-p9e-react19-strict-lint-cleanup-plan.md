# P9E React 19 Strict Lint Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Enable React 19 strict hooks lint globally by removing the deferred rule overrides and fixing the current strict lint errors.

**Architecture:** Keep behavior stable and make targeted fixes at the lint root causes. Derived values move out of effect state, effect-triggered fetches use `useEffectEvent` plus async scheduling, URL state gets initial render derivation plus async synchronization, and modal reset is handled by remounting.

**Tech Stack:** Next.js 16, React 19, TypeScript, ESLint CLI, Node test runner.

---

### Task 1: Baseline And Design Docs

**Files:**
- Create: `docs/superpowers/specs/2026-06-10-p9e-react19-strict-lint-cleanup-design.md`
- Create: `docs/superpowers/plans/2026-06-10-dev-p9e-react19-strict-lint-cleanup-plan.md`

- [x] **Step 1: Run strict lint RED baseline**

Run:

```bash
cd frontend
./node_modules/.bin/eslint . --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error
```

Expected: fails with 7 strict errors and 4 existing warnings.

- [x] **Step 2: Write the P9E design document**

Create `docs/superpowers/specs/2026-06-10-p9e-react19-strict-lint-cleanup-design.md` describing scope, selected direction, file-level fixes, verification, and risks.

- [x] **Step 3: Write this implementation plan**

Create `docs/superpowers/plans/2026-06-10-dev-p9e-react19-strict-lint-cleanup-plan.md` with task-by-task execution steps.

- [x] **Step 4: Commit P9E planning docs**

Run:

```bash
git add docs/superpowers/specs/2026-06-10-p9e-react19-strict-lint-cleanup-design.md docs/superpowers/plans/2026-06-10-dev-p9e-react19-strict-lint-cleanup-plan.md
git commit -m "docs: plan p9e react strict lint cleanup"
```

Expected: planning docs are committed on `dev`. Do not stage `docs/superpowers/demos/`.

### Task 2: Effect Fetch Cleanup

**Files:**
- Modify: `frontend/app/admin/jobs/page.tsx`
- Modify: `frontend/app/strategies/page.tsx`

- [x] **Step 1: Update admin jobs effect fetch**

In `frontend/app/admin/jobs/page.tsx`:

- Import `useEffectEvent` from React.
- Add an effect event that calls `void loadJobs()`.
- In the token/filter effect, schedule that event with `window.setTimeout(..., 0)`.
- Remove the `react-hooks/exhaustive-deps` disable.

- [x] **Step 2: Update strategies effect fetch**

In `frontend/app/strategies/page.tsx`:

- Import `useEffectEvent` from React.
- Add an effect event that calls `void fetchStrategies()`.
- In the token effect, schedule that event with `window.setTimeout(..., 0)`.
- Keep direct refresh calls after create/update/delete.

- [x] **Step 3: Run targeted strict lint for fetch pages**

Run:

```bash
cd frontend
./node_modules/.bin/eslint app/admin/jobs/page.tsx app/strategies/page.tsx --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error
```

Expected: exits 0 errors. Existing warnings should not include these two effect fetch errors.

- [x] **Step 4: Commit fetch cleanup**

Run:

```bash
git add frontend/app/admin/jobs/page.tsx frontend/app/strategies/page.tsx
git commit -m "fix: defer effect triggered fetch state"
```

### Task 3: Positions Strict Cleanup

**Files:**
- Modify: `frontend/app/positions/new/page.tsx`
- Modify: `frontend/app/positions/page.tsx`

- [x] **Step 1: Replace stored symbol detection with derived detection**

In `frontend/app/positions/new/page.tsx`:

- Remove `symbolDetection` state.
- Add `const symbolDetection = detectSymbolType(form.symbol)` near form state usage.
- Keep validation-specific detection local inside the debounced callback.
- Schedule `setSymbolValidation(null)` asynchronously when `form.symbol` is empty.

- [x] **Step 2: Fix positions URL filter sync**

In `frontend/app/positions/page.tsx`:

- Move `useSearchParams()` before filter state initialization.
- Add a small `readPositionUrlFilters(searchParams)` helper.
- Initialize `dimension` and `categoryFilter` from that helper.
- Update the existing URL sync effect to schedule state changes with `window.setTimeout(..., 0)`.
- Remove the unused `asset_type` local and debug `console.log`.

- [x] **Step 3: Fix holding time render purity**

In `frontend/app/positions/page.tsx`:

- Add `currentTime` state.
- Populate it from a deferred effect and refresh it every minute.
- Change `formatHoldingTime(position)` to `formatHoldingTime(position, currentTime)` and avoid `Date.now()` during render.

- [x] **Step 4: Run targeted strict lint for positions**

Run:

```bash
cd frontend
./node_modules/.bin/eslint app/positions/new/page.tsx app/positions/page.tsx --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error
```

Expected: exits 0 errors.

- [x] **Step 5: Commit positions cleanup**

Run:

```bash
git add frontend/app/positions/new/page.tsx frontend/app/positions/page.tsx
git commit -m "fix: make positions filters and timing react strict safe"
```

### Task 4: Modal And Date Picker Cleanup

**Files:**
- Modify: `frontend/components/ChecklistModal.tsx`
- Modify: `frontend/components/DateTimePicker.tsx`
- Modify: `frontend/app/positions/new/page.tsx`

- [x] **Step 1: Remove checklist modal reset effect**

In `frontend/components/ChecklistModal.tsx`:

- Remove the `useEffect` import.
- Remove the reset effect.
- Keep `responses` initialized to `{}`.

In `frontend/app/positions/new/page.tsx`:

- Render `ChecklistModal` only when `showChecklistModal` is true.
- Keep `isOpen={showChecklistModal}` as a defensive prop.

- [x] **Step 2: Defer date picker controlled sync**

In `frontend/components/DateTimePicker.tsx`:

- Keep the existing controlled value sync effect.
- Move `setSelectedDate` and `setTimeValue` into a `window.setTimeout(..., 0)` callback.
- Clear the timeout on cleanup.

- [x] **Step 3: Run targeted strict lint for modal and date picker**

Run:

```bash
cd frontend
./node_modules/.bin/eslint components/ChecklistModal.tsx components/DateTimePicker.tsx app/positions/new/page.tsx --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error
```

Expected: exits 0 errors.

- [x] **Step 4: Commit modal/date cleanup**

Run:

```bash
git add frontend/components/ChecklistModal.tsx frontend/components/DateTimePicker.tsx frontend/app/positions/new/page.tsx
git commit -m "fix: remove modal and picker sync state effects"
```

### Task 5: Enable Global Strict Rules

**Files:**
- Modify: `frontend/eslint.config.mjs`

- [x] **Step 1: Remove deferred React 19 rule overrides**

In `frontend/eslint.config.mjs`, remove the config object that disables:

```js
'react-hooks/purity': 'off',
'react-hooks/set-state-in-effect': 'off',
```

The exported config should rely on `eslint-config-next/core-web-vitals` defaults.

- [x] **Step 2: Run global strict lint**

Run:

```bash
cd frontend
./node_modules/.bin/eslint . --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error
```

Expected: exits 0 errors. Existing warnings may remain.

- [x] **Step 3: Run normal lint**

Run:

```bash
cd frontend
npm run lint
```

Expected: exits 0. Existing warnings may remain but no strict errors should be hidden by config.

- [x] **Step 4: Commit lint config enablement**

Run:

```bash
git add frontend/eslint.config.mjs
git commit -m "chore: enable react strict hook lint globally"
```

### Task 6: Full Verification And Push

**Files:**
- Modify: `docs/superpowers/plans/2026-06-10-dev-p9e-react19-strict-lint-cleanup-plan.md`

- [x] **Step 1: Run frontend tests**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/*.test.mts
```

Expected: exits 0.

- [x] **Step 2: Run TypeScript**

Run:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected: exits 0.

- [x] **Step 3: Run production build**

Run:

```bash
cd frontend
npm run build
```

Expected: exits 0. If sandbox restrictions block Turbopack, rerun with approval and record the reason.

- [x] **Step 4: Restore generated files if needed**

Run:

```bash
git status --short
```

Expected: no generated file changes. If `frontend/next-env.d.ts` or `frontend/tsconfig.tsbuildinfo` changed, restore only those generated files.

- [x] **Step 5: Record verification results in this plan**

Add exact command results, remaining warnings, and any build escalation note under `Verification Results`.

- [x] **Step 6: Commit verification record**

Run:

```bash
git add docs/superpowers/plans/2026-06-10-dev-p9e-react19-strict-lint-cleanup-plan.md
git commit -m "docs: close p9e react strict lint cleanup"
```

- [x] **Step 7: Push `dev`**

Run:

```bash
git push origin dev
```

Expected: push succeeds. Do not create a PR.

## Verification Results

- RED baseline strict lint: `./node_modules/.bin/eslint . --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error` exited 1 with 7 strict errors and 4 warnings before implementation.
- Fetch-page targeted strict lint: `./node_modules/.bin/eslint app/admin/jobs/page.tsx app/strategies/page.tsx --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error` exited 0.
- Positions targeted strict lint: `./node_modules/.bin/eslint app/positions/new/page.tsx app/positions/page.tsx --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error` exited 0.
- Modal/date targeted strict lint: `./node_modules/.bin/eslint components/ChecklistModal.tsx components/DateTimePicker.tsx app/positions/new/page.tsx --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error` exited 0.
- Global strict lint after enabling rules: `./node_modules/.bin/eslint . --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error` exited 0 with 0 errors and 3 warnings.
- Normal lint: `npm run lint` exited 0 with 0 errors and 3 warnings.
- Remaining warnings: `app/login/page.tsx` and `app/register/page.tsx` still use `<img>`; `hooks/useDashboardData.ts` still has an existing `allPositionsQuery.error` exhaustive-deps warning.
- Frontend tests: `node --experimental-strip-types --test tests/*.test.mts` exited 0; 78 tests passed.
- TypeScript: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- Sandboxed build: `npm run build` exited 1 because Turbopack could not create a process / bind a port while processing `app/globals.css`.
- Escalated build: `npm run build` exited 0 on Next 16.2.7; routes included `/admin/jobs`, `/positions`, `/positions/new`, `/strategies`, `/timeline`, `/dashboard`, and `/`.
- Generated files `frontend/next-env.d.ts` and `frontend/tsconfig.tsbuildinfo` were restored after build.

## Final Acceptance Checklist

- [x] Planning docs committed.
- [x] Admin jobs and strategies effect fetches are strict-lint safe.
- [x] Positions symbol detection, URL filters, and holding time are strict-lint safe.
- [x] Checklist modal and date picker sync paths are strict-lint safe.
- [x] `frontend/eslint.config.mjs` no longer disables React 19 strict hooks rules.
- [x] Global strict React 19 lint exits 0 errors.
- [x] Normal lint, tests, TypeScript, and build pass.
- [x] Work is committed and pushed to `origin/dev`.
