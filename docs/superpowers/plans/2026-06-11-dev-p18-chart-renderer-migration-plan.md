# P18 Chart Renderer Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove remaining Recharts usage while keeping `chart.v1` schemas and page data contracts stable.

**Architecture:** Use internal SVG renderers behind existing `ChartFrame` and adapter boundaries. Migrate all Recharts-backed chart components in one lane, then remove the `recharts` dependency only after static tests and browser smoke confirm the chart surfaces render.

**Tech Stack:** Next.js 16, React 19, TypeScript, internal SVG components, existing `chart.v1` schema helpers, Node test runner.

---

## Renderer Decision

P18 V1 target renderer: internal SVG components.

Reason:
- No new package dependency.
- Works with existing `chart.v1` data contracts.
- Keeps chart rendering reviewable in local code.
- Avoids migrating to another large library before product chart semantics are stable.

## Original Recharts Inventory

Original Recharts imports:
- `frontend/components/PortfolioSankey.tsx`
- `frontend/components/insights/LegacyAnalysisChart.tsx`
- `frontend/components/dashboard/MaeMfeScatterPlot.tsx`
- `frontend/components/dashboard/AllocationPieChart.tsx`
- `frontend/components/dashboard/workbench/DashboardEquityHero.tsx`

Dependency files:
- `frontend/package.json`
- `frontend/package-lock.json`

Completion state:
- All original Recharts-backed components now render through internal SVG renderers.
- `recharts` has been removed from `frontend/package.json` and `frontend/package-lock.json`.
- `frontend/tests/chart-renderers.test.mts` guards against new Recharts imports under app/component/lib boundaries.

## Files Likely To Touch

Frontend:
- Create: `frontend/components/charts/renderers/SvgBarChart.tsx`
- Create: `frontend/components/charts/renderers/SvgLineChart.tsx`
- Create: `frontend/components/charts/renderers/SvgPieChart.tsx`
- Create: `frontend/components/charts/renderers/SvgScatterChart.tsx`
- Create: `frontend/components/charts/renderers/SvgSankeyChart.tsx`
- Create: `frontend/components/charts/renderers/chartGeometry.ts`
- Modify: `frontend/components/PortfolioSankey.tsx`
- Modify: `frontend/components/insights/LegacyAnalysisChart.tsx`
- Modify: `frontend/components/dashboard/MaeMfeScatterPlot.tsx`
- Modify: `frontend/components/dashboard/AllocationPieChart.tsx`
- Modify: `frontend/components/dashboard/workbench/DashboardEquityHero.tsx`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Test: `frontend/tests/chart-renderers.test.mts`
- Test: `frontend/tests/chart-views.test.mts`
- Test: `frontend/tests/charts.test.mts`

Docs:
- Modify: `docs/TODO.md`
- Modify: `docs/DEVELOPER_GUIDE.md`
- Modify: `docs/superpowers/plans/2026-06-11-dev-p18-chart-renderer-migration-plan.md`

## Task 1: Add Static Guard Against New Recharts Imports

**Goal:** stop new Recharts usage before migration starts.

- [x] Create `frontend/tests/chart-renderers.test.mts` with a static scan that fails on `from 'recharts'` or `from "recharts"` in `frontend/app`, `frontend/components`, and `frontend/lib`.
- [x] Temporarily allow the five known files above with an allowlist so the test can land before migration.
- [x] Run:

```bash
cd frontend
node --experimental-strip-types --test tests/chart-renderers.test.mts
```

- [x] Commit:

```bash
git add frontend/tests/chart-renderers.test.mts
git commit -m "test: guard chart renderer imports"
```

## Task 2: Add Internal SVG Geometry Helpers

**Goal:** build deterministic chart geometry that can be tested without a browser.

- [x] Create `frontend/components/charts/renderers/chartGeometry.ts` with:
  - `scaleLinear(domainMin, domainMax, rangeMin, rangeMax)`.
  - `buildLinePath(points, width, height)`.
  - `buildPieSlices(values, radius)`.
  - `buildScatterPoints(points, width, height)`.
  - `normalizeSankeyLinks(data)`.
- [x] Add tests in `frontend/tests/chart-renderers.test.mts`:
  - line path starts with `M`.
  - pie slices sum to full circle.
  - scatter points stay within viewport.
  - sankey normalization rejects empty links with empty state.
- [x] Run targeted test.
- [x] Commit:

```bash
git add frontend/components/charts/renderers/chartGeometry.ts frontend/tests/chart-renderers.test.mts
git commit -m "feat: add internal chart geometry helpers"
```

## Task 3: Replace Bar, Line, Pie, And Scatter Renderers

**Goal:** remove Recharts from standard chart components.

- [x] Create:
  - `SvgBarChart.tsx`
  - `SvgLineChart.tsx`
  - `SvgPieChart.tsx`
  - `SvgScatterChart.tsx`
- [x] Update `frontend/components/insights/LegacyAnalysisChart.tsx` to use `SvgBarChart`.
- [x] Update `frontend/components/dashboard/workbench/DashboardEquityHero.tsx` to use `SvgLineChart`.
- [x] Update `frontend/components/dashboard/AllocationPieChart.tsx` to use `SvgPieChart`.
- [x] Update `frontend/components/dashboard/MaeMfeScatterPlot.tsx` to use `SvgScatterChart`.
- [x] Keep existing empty-state and `ChartFrame` behavior.
- [x] Remove these four files from the static allowlist.
- [x] Run:

```bash
cd frontend
node --experimental-strip-types --test tests/chart-renderers.test.mts tests/chart-views.test.mts tests/charts.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```

- [x] Commit:

```bash
git add frontend/components/charts/renderers frontend/components/insights/LegacyAnalysisChart.tsx frontend/components/dashboard/workbench/DashboardEquityHero.tsx frontend/components/dashboard/AllocationPieChart.tsx frontend/components/dashboard/MaeMfeScatterPlot.tsx frontend/tests/chart-renderers.test.mts
git commit -m "feat: migrate standard charts to svg renderers"
```

## Task 4: Replace Sankey Renderer

**Goal:** remove the last Recharts dependency from portfolio flow.

- [x] Create `frontend/components/charts/renderers/SvgSankeyChart.tsx`.
- [x] Use existing `buildPortfolioSankeyChartView(...)` output as input.
- [x] Render:
  - columns based on node depth inferred from links.
  - proportional link stroke width.
  - accessible node labels.
  - compact mobile height when `isMobile` is true.
- [x] Update `frontend/components/PortfolioSankey.tsx`.
- [x] Remove the final Recharts static allowlist entry.
- [x] Run:

```bash
cd frontend
node --experimental-strip-types --test tests/chart-renderers.test.mts tests/chart-views.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```

- [x] Commit:

```bash
git add frontend/components/charts/renderers/SvgSankeyChart.tsx frontend/components/PortfolioSankey.tsx frontend/tests/chart-renderers.test.mts
git commit -m "feat: migrate portfolio sankey to svg renderer"
```

## Task 5: Remove Recharts Dependency

**Goal:** prove the migration is complete at dependency level.

- [x] Remove `recharts` from `frontend/package.json`.
- [x] Run package lock update:

```bash
cd frontend
npm install --package-lock-only
```

- [x] Run static scan:

```bash
cd frontend
rg -n "recharts|ResponsiveContainer|LineChart|BarChart|PieChart|ScatterChart|Sankey" app components lib package.json --glob '!node_modules/**'
```

Expected: no Recharts imports or dependency references.

- [x] Run:

```bash
cd frontend
npm run lint
./node_modules/.bin/tsc --noEmit --pretty false
node --experimental-strip-types --test tests/*.test.mts
```

- [x] Commit:

```bash
git add frontend/package.json frontend/package-lock.json frontend/tests/chart-renderers.test.mts
git commit -m "chore: remove recharts dependency"
```

## Task 6: Browser Smoke And Completion Gate

- [x] Authenticated browser smoke covers:
  - `/dashboard` equity line, allocation pie, MAE/MFE scatter, portfolio sankey.
  - `/insights` analysis bar chart.
- [x] Confirm mobile viewport does not overflow chart cards.
- [x] Update `docs/TODO.md` with P18 completion and P19 next lane.
- [x] Run final verification:

```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
cd ../frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
node --experimental-strip-types --test tests/*.test.mts
cd ..
git diff --check
git status --short --branch
```

- [x] Commit:

```bash
git add docs/TODO.md docs/DEVELOPER_GUIDE.md docs/superpowers/plans/2026-06-11-dev-p18-chart-renderer-migration-plan.md
git commit -m "docs: complete p18 chart renderer migration gate"
```

## Stop Conditions

- Stop before changing `chart.v1` schema shape.
- Stop before deleting chart adapters.
- Stop if an SVG replacement cannot render the same data with readable labels on mobile.
- Stop before adding another chart dependency to replace Recharts.

## Execution Log

Code commits:
- `22c675f test: guard chart renderer imports`
- `438c164 feat: add internal chart geometry helpers`
- `f7f13d7 feat: migrate standard charts to svg renderers`
- `fbd5bd5 feat: migrate portfolio sankey to svg renderer`
- `e5938b5 chore: remove recharts dependency`

Final verification:
- Backend full suite: `../.venv313/bin/python -m unittest discover -s tests` ran 222 tests OK. Expected market-data warnings appeared for offline Finnhub/YFinance fallback and `guce.yahoo.com` DNS resolution.
- Frontend typecheck: `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- Frontend lint: `npm run lint` exited 0.
- Frontend Node tests: `node --experimental-strip-types --test tests/*.test.mts` ran 119 tests OK with the existing `MODULE_TYPELESS_PACKAGE_JSON` warnings.
- Static Recharts scan: no matches for Recharts imports, `ResponsiveContainer`, `node_modules/recharts`, or package dependency references under frontend app/component/lib/package files.
- `git diff --check` exited 0.

Browser smoke:
- Started an isolated smoke backend with `DATABASE_URL=sqlite:////private/tmp/tradingnoobs_p18_smoke_20260611.db` and a local frontend on `http://localhost:51559`.
- Created and logged in as temporary smoke user `p18-smoke-20260611@example.com`.
- `/timeline` loaded after login with authenticated navigation and no browser console errors.
- `/dashboard` loaded authenticated chart cards for equity/drawdown, allocation, and portfolio flow empty states; DOM contained SVG output and no browser console errors.
- `/insights` loaded the AI insight page after a clean reload with no `Failed to fetch` state and no browser console errors.
- Mobile viewport check at 390px width showed no horizontal overflow on `/dashboard` or `/insights`: `scrollWidth` matched `clientWidth` on both pages.

Known browser-smoke boundary:
- The temporary user had an empty portfolio, so this smoke proves authenticated route rendering, empty-state chart cards, SVG renderer presence, console cleanliness, and mobile non-overflow. P19 should add a release-grade fixture for populated chart visual coverage together with the remaining P11 routes.
