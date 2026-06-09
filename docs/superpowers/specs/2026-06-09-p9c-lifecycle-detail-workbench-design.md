# P9C Lifecycle Detail Workbench Design

## Goal

Redesign `/positions/[id]` as the product's truth lifecycle workbench: a single-position detail page where the user reads the trade as an auditable story first, uses truth write actions directly, and sees old `Position / TradeBatch` data only as clearly labeled migration support.

P9C should finish the front-end side of the lifecycle hard cutover without changing the frozen backend lifecycle contract.

## Background

P9A made `/timeline` the default decision workspace. P9B made `/dashboard` the macro command center. The next product gap is single-trade detail.

The backend already exposes the primary user contract:

```text
GET /api/trading-positions/{position_public_id}/lifecycle
```

The frontend detail page already tries this route first and can render `TruthLifecycleDetail`, but the page is still a 1,400-line monolith. It mixes lifecycle narrative, legacy position metadata, batch editing, MAE/MFE, review, analysis, delete guards, modals, and cash adjustment logic in one component. The truth lifecycle therefore appears as an inserted module above an old detail page rather than as the page model.

P9C fixes that page-model mismatch.

## Selected Direction

Use **A: Lifecycle Command Center**.

This direction makes truth lifecycle the page itself:

- A top hero summarizes the position, status, result, review state, thesis, and execution quality.
- A right rail carries the event spine, AI sidecar, evidence, and cash effects.
- Truth write actions remain prominent: edit narrative, reverse latest active event, and record manual cash adjustment.
- Legacy `Position / TradeBatch` content moves into an explicit migration tools region.
- The old detail page sections no longer compete with lifecycle narrative for primary visual hierarchy.

The page should borrow the audit density of the "Audit Stream" option only inside the event rail, not as the whole default layout.

## Scope

### In Scope

- Refactor `frontend/app/positions/[id]/page.tsx` into an orchestration shell plus focused lifecycle workbench components.
- Make `LifecycleDetailViewModel` the primary loaded-state view model when truth lifecycle is available.
- Keep direct truth lifecycle loading through `/api/trading-positions/{position_public_id}/lifecycle`.
- Keep legacy bridge loading only as fallback or migration support.
- Preserve truth write actions:
  - edit truth narrative fields on `PositionEvent`
  - reverse latest active `ADD / REDUCE / CLOSE` event
  - create position-level manual cash adjustment
- Move legacy summary, metadata, MAE/MFE, batch list/edit, legacy review, analyze, and protected delete affordances into a clearly labeled migration panel.
- Add lifecycle-specific pure helpers for section ordering, action availability, legacy visibility, tone labels, evidence summaries, and empty states.
- Add or extend lifecycle adapter tests before implementation code.
- Verify desktop and mobile `/positions/[public_id]` after implementation.

### Out of Scope

- No backend lifecycle contract changes.
- No timeline rewrite.
- No dashboard rewrite.
- No chart schema migration.
- No non-latest historical reversal support.
- No position void/archive semantics for reversing `OPEN`.
- No replacement of all legacy write paths outside this detail page.
- No changes to `docs/superpowers/demos/`.
- No PR creation unless explicitly requested.

## Information Architecture

Desktop:

```text
+----------------------------------------------------------------+
| Header: back link, asset/title/status, account/instrument       |
+----------------------------------------------------------------+
| Lifecycle hero: result, thesis, quality, review state           |
|                                       | Event / AI / evidence   |
| Truth actions: narrative / reverse    | rail                    |
| / cash adjustment                     |                         |
+---------------------------------------+------------------------+
| Migration tools: legacy metadata, batches, MAE/MFE, review      |
+----------------------------------------------------------------+
```

Mobile:

```text
Header
Lifecycle hero
Primary truth actions
Event spine
AI sidecar and evidence
Cash effects
Legacy migration tools
Modals
```

Mobile should stay story-first. Legacy tools appear after the lifecycle evidence unless truth lifecycle is unavailable.

## Component Boundaries

Create focused components under `frontend/components/positions/lifecycle/`:

- `LifecycleWorkbench.tsx`: loaded-state page composition for truth lifecycle.
- `LifecycleWorkbenchHeader.tsx`: back navigation, symbol/title/status, account, instrument, and high-level status labels.
- `LifecycleHero.tsx`: result summary, key numbers, thesis block, execution quality, and review state.
- `LifecycleActionPanel.tsx`: edit narrative, reverse latest event, and manual cash adjustment entry points.
- `LifecycleEventRail.tsx`: compact event spine using lifecycle nodes.
- `LifecycleEvidencePanel.tsx`: evidence list, cash effects, and trust metadata.
- `LifecycleAiSidecarPanel.tsx`: artifact-backed AI sidecar.
- `LifecycleMigrationPanel.tsx`: explicit legacy-only area for `Position / TradeBatch` sections.
- `LifecycleModals.tsx`: narrative edit and cash adjustment modals, kept out of the page shell.

Retire or shrink `frontend/components/positions/domain/TruthLifecycleDetail.tsx` after its display responsibilities move into the workbench components. It can remain as a small compatibility wrapper only if that reduces implementation risk.

Keep legacy UI pieces only when they are still needed inside `LifecycleMigrationPanel`.

## Page Shell Responsibilities

`frontend/app/positions/[id]/page.tsx` should become responsible for:

- auth token and route param access
- primary truth lifecycle fetch
- legacy fallback/support fetch
- loading, error, and not-found states
- passing stable handler functions into the workbench
- refreshing lifecycle/legacy data after mutations

It should not contain large JSX sections for lifecycle panels, legacy batch tables, or modal internals after P9C.

## Adapter And Helper Boundaries

Extend `frontend/lib/adapters/lifecycle.ts` rather than putting page rules into JSX.

New helper responsibilities:

- `getLifecyclePageSections(input)`: returns desktop/mobile section order.
- `getLifecyclePrimaryActions(input)`: returns narrative, reversal, and cash adjustment action states.
- `getLifecycleLegacyPanelState(input)`: decides whether legacy content is hidden, collapsed, migration-only, or fallback-primary.
- `getLifecycleReviewTone(reviewStatus)`: maps review status to labels and tones.
- `getLifecycleEventRailItems(lifecycle)`: formats node sequence for the right rail.
- `getLifecycleEvidencePanelSummary(lifecycle)`: formats evidence and cash effect summaries.
- `getLifecycleEmptyState(input)`: documents empty lifecycle and legacy fallback copy.

Existing helpers should remain where they already encode correct truth behavior:

- `adaptLifecycleDetail`
- `getLifecycleNarrativeDraft`
- `getLifecycleReversalAction`
- evidence, cash effect, AI sidecar, and trust summary helpers

## Data Flow

Primary path:

```text
/positions/[position_public_id]
  -> positionsAPI.getTradingPositionLifecycle(token, position_public_id)
  -> adaptLifecycleDetail(...)
  -> LifecycleWorkbench
```

Support path when truth lifecycle exists:

```text
positionsAPI.get(token, routeId).catch(() => null)
  -> adaptPosition(...)
  -> LifecycleMigrationPanel
```

Fallback path when the route id is legacy-only:

```text
positionsAPI.get(token, routeId)
positionsAPI.getTruthLifecycle(token, routeId).catch(() => null)
  -> truth lifecycle if bridge resolves
  -> otherwise legacy fallback state
```

Mutation refresh rules:

- Truth narrative save refreshes truth lifecycle.
- Latest event reversal refreshes truth lifecycle and clears page-level error.
- Manual cash adjustment refreshes truth lifecycle and clears page-level error.
- Legacy mutation paths, when available, refresh legacy data and attempt bridge lifecycle refresh.

## Legacy Boundary

When truth lifecycle is available:

- Legacy batch edit is read-only or disabled according to existing adapter rules.
- Legacy position delete is disabled according to existing adapter rules.
- Legacy review is labeled as migration data if shown.
- Legacy metadata, MAE/MFE, and analysis tools appear below lifecycle evidence.
- Legacy copy must explain that new trade quantity/price truth writes live in `TradingPosition / PositionEvent`.

When truth lifecycle is not available:

- The page may render a fallback legacy detail experience.
- The fallback must be labeled as legacy/fallback, not as the new lifecycle workbench.
- Fallback behavior should preserve current user ability to inspect older data while avoiding new visual investment in obsolete DTOs.

## Visual Direction

The workbench should feel like a focused trade case file, not a generic admin detail page:

- Strong hero with dark ink/slate, cyan/amber highlights, and disciplined numeric hierarchy.
- Event rail with compact audit nodes and clear `OPEN / ADD / REDUCE / CLOSE / REVIEW / AI_CONCLUSION / REVERSAL` semantics.
- Evidence and AI sidecar should feel attached to the lifecycle, not decorative.
- Legacy migration tools should use amber/warning treatment and lower hierarchy.
- Mobile should keep one-column storytelling and avoid dense legacy-first stacking.
- Reuse the established P9A/P9B visual language rather than introducing a new theme.

## React 19 Lint Strategy

Do not enable new strict rules globally in P9C.

For P9C-touched files:

- Keep derived view state in adapter helpers where practical.
- Avoid `setState` in effects except fetch lifecycle and mutation state.
- Avoid browser globals during render.
- Keep modal state local but small.
- Avoid adding `useMemo` / `useCallback` by default unless needed by existing project patterns.

## Testing Strategy

Use TDD for pure behavior:

- Add or extend `frontend/tests/lifecycle-adapter.test.mts`.
- Cover primary action states for editable lifecycle, missing event public id, reversible latest event, no reversible event, and already reversed events.
- Cover legacy panel state for truth-available, truth-missing, legacy-only, and no legacy data states.
- Cover section order for desktop and mobile.
- Cover review tone labels.
- Cover evidence/cash/AI summary formatting.
- Cover empty and fallback copy.

Use compile/build verification for UI:

- `node --experimental-strip-types --test tests/lifecycle-adapter.test.mts`
- `node --experimental-strip-types --test tests/*.test.mts`
- `./node_modules/.bin/tsc --noEmit --pretty false`
- `npm run lint`
- `npm run build`

Use browser verification after implementation:

- Desktop `/positions/[public_id]`: Lifecycle Command Center hero, actions, rail, and migration panel are visible in the correct hierarchy.
- Mobile `/positions/[public_id]` at 390px width: one-column story-first order.
- Truth narrative modal opens and can be closed.
- Manual cash adjustment modal opens and validates zero amount before submit.
- Reversal button state matches adapter helper.
- Legacy-only or missing truth lifecycle state remains understandable.

## Acceptance Criteria

- `/positions/[id]` reads as a truth lifecycle workbench when lifecycle data exists.
- `frontend/app/positions/[id]/page.tsx` is reduced to orchestration, state, fetch, mutation handlers, and top-level branching.
- Lifecycle workbench components live under `frontend/components/positions/lifecycle/`.
- Truth lifecycle is the primary loaded-state view model.
- Legacy `Position / TradeBatch` UI is isolated in a clearly labeled migration panel.
- Truth write actions remain available and preserve current API behavior.
- Existing backend lifecycle and legacy bridge contracts remain unchanged.
- Lifecycle adapter/helper tests cover page ordering and action/legacy states.
- Frontend tests, TypeScript, lint, and build pass.
- Browser smoke confirms desktop and mobile detail layouts.
- `docs/superpowers/demos/` remains untouched.

## Risks And Controls

- Risk: The page remains visually improved but structurally monolithic.
  Control: make the page shell reduction and component split acceptance criteria.

- Risk: Legacy controls continue to look like first-class product surfaces.
  Control: require `LifecycleMigrationPanel` labeling, lower hierarchy, and disabled/protected states when truth exists.

- Risk: P9C drifts into backend truth-model work.
  Control: keep backend contract unchanged unless implementation proves a hard frontend blocker.

- Risk: Detail page becomes too dense on mobile.
  Control: test mobile section order and keep legacy tools below lifecycle evidence.

- Risk: AI sidecar becomes a markdown blob again.
  Control: keep AI sidecar artifact/evidence linked and subordinate to lifecycle narrative.

## Follow-Up Stages

- P9D: Chart container/schema migration and freshness contract expansion.
- P9E: Global React 19 strict lint cleanup.
- Later backend stages: final truth/snapshot read models, broader reversal semantics, and legacy endpoint retirement.
