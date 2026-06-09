# P9B Dashboard Workbench Design

## Goal

Redesign `/dashboard` as the product's macro command center: a desktop-first portfolio health workbench that explains aggregate state, risk posture, allocation structure, data freshness, and portfolio movement without reclaiming the Timeline's role as the default home.

## Background

P9A made `/timeline` the primary decision workspace and kept `/` redirected to `/timeline`. That remains correct. Dashboard should not become the product's opening narrative again; it should answer a different question:

- Timeline: "What happened recently, and what needs review?"
- Dashboard: "How healthy is the whole portfolio right now, and where is risk or structure changing?"

The current Dashboard page still carries older homepage DNA. It renders quick actions, market status, summary cards, Sankey, equity curve, MAE/MFE, positions, allocation, account distribution, risk metrics, and movers in one monolithic page component. The information is useful, but the hierarchy is flat and the page does not yet feel like a deliberate macro analysis surface.

P9B intentionally brings the Dashboard macro redesign forward now. Lifecycle detail remains a separate later stage so this work can stay focused and testable.

## Selected Direction

Use **A: Macro Command Center**.

This direction turns Dashboard into a calm trading health desk:

- A top status rail summarizes portfolio health, PnL direction, drawdown, exposure, and data freshness.
- The primary hero area combines equity curve, period controls, and drawdown context.
- A right rail explains risk posture, data freshness, market status, and a weekly summary panel using current data where available.
- Lower sections preserve allocation, account distribution, movers, MAE/MFE, Sankey, and open positions as supporting evidence.
- Mobile becomes a summary-first single-column page rather than a dense desktop-equivalent chart wall.

The chosen aesthetic continues P9A's ledger desk / decision journal language: paper, ink, slate, amber, emerald, red, thin borders, deliberate numbers, and less generic SaaS card stacking.

## Scope

### In Scope

- Refactor `frontend/app/dashboard/page.tsx` into a data orchestration shell and focused workbench components.
- Reuse P9A UI primitives from `frontend/components/ui/`.
- Add Dashboard-specific pure helpers for period options, status rail metrics, risk posture, freshness display, account rows, and mobile section ordering.
- Remove local `setState` effects for viewport and period metrics from the Dashboard page where practical.
- Preserve existing backend/API contracts and keep `useDashboardData(token, historyDays)`.
- Preserve existing chart components where they still provide value: equity curve via Recharts, `PortfolioSankey`, `DashboardAllocationPanel`, `RiskMetricsCard`, `DashboardMoversPanel`, `MaeMfeScatterPlot`, and `PositionCard`.
- Improve empty/loading/error states using shared primitives.
- Run targeted React 19 strict lint for P9B-touched files.
- Verify desktop and mobile Dashboard visually after implementation.

### Out of Scope

- No backend API changes.
- No Timeline rewrite.
- No Lifecycle Detail rewrite.
- No Insights rewrite.
- No chart schema migration beyond using the current adapter surface.
- No global React 19 lint hardening.
- No changes to `docs/superpowers/demos/`.
- No PR creation unless explicitly requested.

## Information Architecture

Dashboard should render in this order.

Desktop:

```text
+----------------------------------------------------------------+
| Header: Macro command center, freshness/status, primary links  |
+----------------------------------------------------------------+
| Status rail: PnL / win quality / drawdown / exposure/freshness |
+-----------------------------------------+----------------------+
| Equity + drawdown hero + period tabs     | Risk/freshness rail  |
| Portfolio flow / MAE-MFE evidence        | Market + AI summary  |
+-----------------------------------------+----------------------+
| Allocation + account distribution        | Movers + risk card   |
+-----------------------------------------+----------------------+
| Open positions preview                                         |
+----------------------------------------------------------------+
```

Mobile:

```text
Header
Status rail as two-column metric tiles
Equity hero
Risk/freshness summary
Allocation and account distribution
Movers
Open positions preview
Secondary evidence charts
Bottom nav
```

This order keeps the page useful on phones without pretending mobile users need every desktop chart at the same density.

## Component Boundaries

Create focused components under `frontend/components/dashboard/workbench/`:

- `DashboardWorkbench.tsx`: loaded-state page composition.
- `DashboardWorkbenchHeader.tsx`: page title, macro status subtitle, quick links, market status placement.
- `DashboardStatusRail.tsx`: top metric tiles for PnL, win rate, drawdown, and open exposure.
- `DashboardEquityHero.tsx`: period tabs, period PnL summary, and equity curve chart.
- `DashboardRiskRail.tsx`: risk posture, freshness copy, market status, and weekly summary panel.
- `DashboardStructureGrid.tsx`: allocation, account distribution, movers, and risk metrics composition.
- `DashboardEvidenceStack.tsx`: Sankey, MAE/MFE, and open positions preview as supporting evidence.

Keep existing reusable Dashboard domain components in place when they already have a clear purpose:

- `frontend/components/dashboard/domain/DashboardSummaryStrip.tsx` can be retired from `/dashboard` if replaced by `DashboardStatusRail`.
- `frontend/components/dashboard/domain/DashboardAllocationPanel.tsx` remains useful.
- `frontend/components/dashboard/domain/DashboardMoversPanel.tsx` remains useful.

## Adapter And Helper Boundaries

Extend `frontend/lib/adapters/dashboard.ts` rather than putting formatting logic into JSX.

New helper responsibilities:

- `getDashboardPeriodOptions(now: Date)`: returns stable period labels and day counts for `1周`, `本月`, `1月`, `3月`, `本年`, `1年`, and `全部`.
- `getDashboardHistoryDays(option, now: Date)`: converts selected period into API history days without inline button logic.
- `buildDashboardStatusMetrics(input)`: returns PnL, win rate, drawdown, and open exposure metric tiles with tone and detail.
- `getDashboardRiskPosture(stats)`: maps max drawdown and risk ratios into `healthy`, `watch`, or `danger` posture.
- `formatDashboardAccountRows(accountAllocation, currencySymbol)`: returns safe account distribution rows with formatted values.
- `getDashboardMobileSectionOrder(hasPositions, hasEvidence)`: documents mobile priority in a testable helper.

These helpers make Dashboard behavior testable and keep React components presentational.

## Data Flow

No backend changes:

```text
GET /api/dashboard/stats
GET /api/dashboard/pnl-history?days=<historyDays>
GET /api/positions
  -> useDashboardData(token, historyDays)
  -> adaptDashboardPageData(...)
  -> DashboardWorkbench
  -> DashboardStatusRail / DashboardEquityHero / DashboardRiskRail / DashboardStructureGrid / DashboardEvidenceStack
```

Period selection remains local UI state because it controls `historyDays`. Period metrics should be derived from adapter helpers, not copied into local state.

Viewport-specific behavior should rely on responsive CSS where possible. The existing `isMobile` state is only needed by `PortfolioSankey`; P9B should either isolate that concern in a small client hook/component or pass a CSS-independent chart mode without making the whole page depend on viewport state.

## Visual Direction

Use a refined command-center layout, not a generic admin dashboard:

- Typography: keep the existing app type system, with stronger numeric hierarchy and compact uppercase labels.
- Color: slate, paper, ink, amber, emerald, red, and muted blue accents. Avoid purple gradients and novelty colors.
- Surfaces: layered panels with thin borders and subtle shadows; less glass, fewer unrelated card styles.
- Composition: desktop two-column workbench with a clear hero chart and a narrower risk rail.
- Motion: limited to hover/focus states and simple transitions already consistent with the app.
- Density: desktop can be analytical; mobile must be readable and summary-first.

## React 19 Lint Strategy

Do not enable deferred strict lint rules globally in P9B.

For P9B-touched files:

- Avoid `setState` in effects except where no practical alternative exists.
- Keep date calculations out of render by passing explicit `Date` values to pure helpers or computing in event handlers.
- Avoid browser globals in render.
- Run targeted ESLint with `react-hooks/purity:error` and `react-hooks/set-state-in-effect:error`.

## Testing Strategy

Use TDD for pure behavior:

- Add or extend `frontend/tests/dashboard-adapter.test.mts`.
- Cover period option/day calculations for normal dates, first day of month, and first day of year.
- Cover status metric tone and detail formatting for positive, negative, warning, and empty data.
- Cover risk posture mapping.
- Cover account row formatting.
- Cover mobile section ordering.

Use compile/build verification for UI:

- `node --experimental-strip-types --test tests/dashboard-adapter.test.mts`
- `./node_modules/.bin/tsc --noEmit --pretty false`
- `npm run lint`
- Targeted React 19 strict lint on P9B-touched files
- `npm run build`

Use browser verification after implementation:

- Desktop `/dashboard`: two-column macro command center with status rail, equity hero, and risk rail.
- Mobile `/dashboard` at 390px width: single-column summary-first flow without hidden primary content.
- Loading state, error state, empty PnL history, no open positions, and dark mode legibility.
- `/` still redirects to `/timeline`.

## Acceptance Criteria

- `/dashboard` no longer reads as the old default homepage or a flat chart stack.
- `/dashboard` remains independent from `/timeline`; `/` continues to redirect to `/timeline`.
- Dashboard page component is reduced to auth/data/loading/error orchestration.
- New Dashboard workbench components live under `frontend/components/dashboard/workbench/`.
- Dashboard adapter helpers own period, metric, risk, account, and mobile-order logic.
- Existing API contracts remain unchanged.
- Existing useful charts and domain components remain available unless cleanly replaced in `/dashboard`.
- P9B-touched files pass targeted React 19 strict lint.
- Full frontend tests, TypeScript, lint, and build pass.
- Browser smoke confirms desktop and mobile Dashboard layouts.
- `docs/superpowers/demos/` remains untouched.

## Risks And Controls

- Risk: Dashboard competes with Timeline again.
  Control: keep `/` redirected to `/timeline`, remove homepage-style quick action dominance, and frame Dashboard around aggregate health.

- Risk: Redesign becomes a chart-system migration.
  Control: reuse current chart components and adapters; defer chart schema migration.

- Risk: The page remains monolithic after visual improvements.
  Control: require the page shell/workbench/component split as acceptance criteria.

- Risk: Mobile becomes unusably dense.
  Control: mobile order is tested and summary-first; secondary evidence can sit below primary status and risk sections.

## Follow-Up Stages

- P9C: Lifecycle detail hard cutover and visual rewrite.
- P9D: Chart container/schema migration and freshness contract expansion.
- P9E: Global React 19 strict lint cleanup.
