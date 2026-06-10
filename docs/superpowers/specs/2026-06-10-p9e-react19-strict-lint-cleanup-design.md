# P9E React 19 Strict Lint Cleanup Design

## Goal

Remove the global ESLint deferral for React 19 `react-hooks/purity` and `react-hooks/set-state-in-effect` so the whole frontend is checked under the stricter React rules by default.

## Background

P8 upgraded the frontend to Next 16 and React 19, but kept two broad React 19 lint rules disabled because enabling them globally exposed unrelated legacy cleanup work. P9A through P9D kept touched files clean with targeted strict lint. P9D finished the chart migration and left P9E as the next debt payoff step.

The current global strict lint baseline is:

- 7 errors from `react-hooks/set-state-in-effect` or `react-hooks/purity`.
- 4 existing warnings from image optimization and exhaustive-deps.
- The strict errors are concentrated in admin jobs, positions, strategies, checklist modal, and date-time picker code.

## Selected Direction

Use a conservative behavior-preserving cleanup.

The work should make React 19 strict lint pass globally without redesigning pages, changing API contracts, or replacing existing data-fetching patterns. Where current code stores derived state in effects, derive it during render instead. Where an effect is truly synchronizing with an external event such as data fetching or URL changes, schedule the state-producing work asynchronously and use `useEffectEvent` where it avoids stale closures or dependency suppression.

## Scope

### In Scope

- Remove `react-hooks/purity: off` and `react-hooks/set-state-in-effect: off` from `frontend/eslint.config.mjs`.
- Fix all current global strict lint errors:
  - `frontend/app/admin/jobs/page.tsx`
  - `frontend/app/positions/new/page.tsx`
  - `frontend/app/positions/page.tsx`
  - `frontend/app/strategies/page.tsx`
  - `frontend/components/ChecklistModal.tsx`
  - `frontend/components/DateTimePicker.tsx`
- Preserve the existing login/register image warnings unless they become blockers.
- Preserve the existing `hooks/useDashboardData.ts` exhaustive-deps warning unless it becomes a blocker.
- Record verification results in the plan.
- Commit and push to `origin/dev`.

### Out Of Scope

- No PR creation.
- No backend changes.
- No UI redesign.
- No chart migration changes beyond what P9D already completed.
- No cleanup of `docs/superpowers/demos/`.
- No broad refactor of all remaining hooks warnings unless required for strict lint.

## File-Level Design

### Admin Jobs

`AdminJobsPage` currently calls `loadJobs()` directly in an effect. That function sets loading and error state before its first await, so the strict rule reports synchronous state updates from the effect.

Change the mount/filter effect to:

- Keep `loadJobs` as the shared refresh/action function.
- Wrap the effect-triggered refresh in `useEffectEvent`.
- Schedule the call with `window.setTimeout(..., 0)`.
- Remove the `exhaustive-deps` disable because the event wrapper is the dependency-safe entry point.

Manual refresh and job actions can still call or await `loadJobs` directly because those are user/event paths, not effect bodies.

### New Position Symbol Validation

`symbolDetection` is fully derived from `form.symbol`, so it should not be stored in state. Compute it during render with `detectSymbolType(form.symbol)`.

The validation effect should:

- Compute its own local detection inside the scheduled validation callback.
- Clear `symbolValidation` asynchronously when the symbol becomes empty.
- Keep the existing 800ms validation debounce.
- Keep existing metadata autofill behavior.

### Positions URL Filters And Holding Time

The positions page has two strict issues:

- It synchronously writes URL-derived filters from an effect.
- It calls `Date.now()` during render for open-position holding time.

Use a small pure URL parser to derive initial `dimension` and `categoryFilter` from `useSearchParams()`. For subsequent search param changes, schedule state synchronization with `window.setTimeout(..., 0)`.

For holding time, keep a `currentTime` state updated from an asynchronous timer. `formatHoldingTime` receives that captured time instead of calling `Date.now()` during render. This also keeps open-position labels fresh over time without violating render purity.

Remove the debug `console.log` in the page body.

### Strategies

`StrategiesPage` has the same effect-triggered fetch pattern as admin jobs. Use `useEffectEvent` plus `window.setTimeout(..., 0)` for the initial token-driven fetch. Keep direct `fetchStrategies()` calls after create/update/delete because those run from user actions.

### Checklist Modal

The modal uses an effect to reset responses when opened. Instead, only mount `ChecklistModal` while it is open. Closing unmounts the component, and reopening starts from the state initializer `{}`. This removes the effect entirely and keeps reset semantics clear.

### Date Time Picker

`DateTimePicker` syncs internal calendar/time state from the controlled `value` prop. Keep the controlled sync behavior but schedule it asynchronously inside the effect. The visible input already reads directly from `value`, so the deferred calendar state sync should not change visible committed values.

## Testing Strategy

Use the global strict lint failure as the RED test:

```bash
cd frontend
./node_modules/.bin/eslint . --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error
```

Expected RED before implementation: 7 strict errors.

After implementation, verify:

```bash
cd frontend
./node_modules/.bin/eslint . --rule react-hooks/purity:error --rule react-hooks/set-state-in-effect:error
npm run lint
node --experimental-strip-types --test tests/*.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run build
```

`npm run build` may require escalation because Turbopack has previously hit sandbox process/port restrictions.

## Acceptance Criteria

- Global strict React 19 lint exits 0 errors.
- `frontend/eslint.config.mjs` no longer disables `react-hooks/purity` or `react-hooks/set-state-in-effect`.
- Existing functional tests and TypeScript checks pass.
- Production build passes.
- Existing warnings are documented and not expanded by this work.
- `dev` is committed and pushed to `origin/dev`.

## Risks And Controls

- Risk: deferred effect fetches can briefly delay loading state updates by one tick.
  Control: this matches the existing P9D `/insights` pattern and preserves user-visible behavior.
- Risk: URL filter initialization could flicker if only handled asynchronously.
  Control: derive initial state from `useSearchParams()` before the sync effect.
- Risk: modal response reset could regress if the modal remains mounted while closed.
  Control: render the modal only when open so React remounts it naturally.
- Risk: date picker controlled value changes could desync the calendar.
  Control: keep prop-to-state sync, only move the setState calls into an asynchronous callback.
