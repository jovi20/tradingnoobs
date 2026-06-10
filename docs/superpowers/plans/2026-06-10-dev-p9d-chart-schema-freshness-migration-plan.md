# P9D Chart Schema And Freshness Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate all existing Recharts surfaces to a shared chart schema, freshness, trust, and empty-state shell without changing backend API contracts or replacing Recharts.

**Architecture:** `frontend/lib/charts.ts` becomes the canonical chart contract and helper layer. `ChartFrame` becomes the shared trust-aware visual shell, while existing Recharts components remain renderer-specific children. Dashboard and Insights get pure adapters so chart data derivation is tested outside JSX.

**Tech Stack:** Next.js 16, React 19, TypeScript, Tailwind CSS, Recharts, Node test runner, ESLint CLI.

---

### Task 1: Baseline And Contract Tests

**Files:**
- Create: `frontend/tests/charts.test.mts`
- Create: `frontend/lib/charts.ts`
- Modify: `frontend/lib/insightArtifacts.ts`
- Modify: `frontend/lib/chartSchemas.ts`
- Modify: `frontend/tests/chart-schemas.test.mts`

- [x] **Step 1: Run baseline chart-related tests**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/chart-schemas.test.mts tests/insight-artifact-presentation.test.mts
```

Expected: current tests pass before P9D edits.

- [x] **Step 2: Write failing shared chart contract tests**

Create `frontend/tests/charts.test.mts` with:

```ts
import test from 'node:test'
import assert from 'node:assert/strict'

import {
  assertSupportedChartSchema,
  buildChartEmptyState,
  formatChartTrustLabel,
  getChartFreshnessTone,
  getChartSchemaBadge,
  hasChartData,
} from '../lib/charts.ts'

test('chart schema validation supports every current Recharts surface', () => {
  const types = ['bar', 'line', 'pie', 'scatter', 'sankey'] as const

  for (const chartType of types) {
    assert.equal(assertSupportedChartSchema({
      schema_version: 'chart.v1',
      chart_type: chartType,
      dimensions: [{ field: 'name', label: 'Name' }],
      series: [{ field: 'value', label: 'Value' }],
    }), true)
  }
})

test('chart schema validation rejects unversioned or fieldless charts', () => {
  assert.equal(assertSupportedChartSchema(null), false)
  assert.equal(assertSupportedChartSchema({
    schema_version: 'chart.v1',
    chart_type: 'bar',
    series: [],
  }), false)
  assert.equal(assertSupportedChartSchema({
    schema_version: 'chart.v1',
    chart_type: 'bar',
    dimensions: [{ field: '', label: 'Missing field' }],
    series: [{ field: 'value', label: 'Value' }],
  }), false)
})

test('chart schema badge is shared by dashboard and insight artifacts', () => {
  assert.equal(getChartSchemaBadge({
    schema_version: 'chart.v1',
    chart_type: 'scatter',
    series: [{ field: 'mfe', label: 'MFE' }],
  }), 'chart.v1 · scatter')

  assert.equal(getChartSchemaBadge(null), null)
})

test('chart freshness maps to stable UI tones', () => {
  assert.equal(getChartFreshnessTone({ freshness: 'FRESH' }), 'positive')
  assert.equal(getChartFreshnessTone({ freshness: 'DELAYED' }), 'warning')
  assert.equal(getChartFreshnessTone({ freshness: 'STALE' }), 'warning')
  assert.equal(getChartFreshnessTone({ freshness: 'DEGRADED' }), 'danger')
  assert.equal(getChartFreshnessTone({ freshness: 'UNKNOWN_VENDOR_STATE' }), 'neutral')
  assert.equal(getChartFreshnessTone({}), 'neutral')
})

test('chart trust label keeps missing trust visible instead of hiding it', () => {
  assert.equal(formatChartTrustLabel({}), 'local view')
  assert.equal(formatChartTrustLabel({
    freshness: 'FRESH',
    source: 'DASHBOARD_DERIVED_READ_MODEL',
    as_of: '2026-06-10T08:00:00Z',
  }), 'fresh · DASHBOARD_DERIVED_READ_MODEL · as of 2026/6/10 16:00:00')
})

test('chart empty state and data presence use payload flags plus actual data', () => {
  const emptyState = buildChartEmptyState(undefined, 'MISSING_CHART_PAYLOAD')
  assert.deepEqual(emptyState, {
    is_empty: true,
    reason: 'MISSING_CHART_PAYLOAD',
    message: 'MISSING_CHART_PAYLOAD',
  })

  assert.equal(hasChartData([{ name: 'A', value: 1 }], { is_empty: false, reason: null }), true)
  assert.equal(hasChartData([], { is_empty: false, reason: null }), false)
  assert.equal(hasChartData([{ name: 'A', value: 1 }], { is_empty: true, reason: 'NO_DATA' }), false)
})
```

- [x] **Step 3: Run shared chart contract tests and verify RED**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/charts.test.mts
```

Expected: fails because `../lib/charts.ts` does not exist or exported helpers are missing.

- [x] **Step 4: Implement shared chart contract layer**

Create `frontend/lib/charts.ts` with canonical chart types and helpers:

```ts
import type { WorkbenchTone } from './adapters/timeline-workbench.ts'

export type SupportedChartType = 'bar' | 'line' | 'pie' | 'scatter' | 'sankey'
export type DashboardAllocationDimension = 'CORE_TYPE' | 'MARKET' | 'RISK'

export interface ChartSeriesRef {
  field: string
  label: string
  color?: string
}

export interface ChartDimensionRef {
  field: string
  label: string
}

export interface ChartSchema {
  schema_version: 'chart.v1'
  chart_type: SupportedChartType
  series: ChartSeriesRef[]
  dimensions?: ChartDimensionRef[]
  data_path?: string
  options?: Record<string, string | number | boolean | null>
}

export interface ChartTrustMeta {
  as_of?: string
  generated_at?: string
  freshness?: 'FRESH' | 'DELAYED' | 'STALE' | 'DEGRADED' | string
  source?: string
  source_refs?: string[]
  maturity?: string
  value_status?: string
  note?: string
}

export interface ChartEmptyState {
  is_empty: boolean
  reason: string | null
  message?: string
}

export interface ChartPayload<TData = Record<string, unknown>> {
  chart_schema: ChartSchema
  data: TData[]
  empty_state: ChartEmptyState
  trust_meta: ChartTrustMeta
}

export interface AllocationChartDataPoint {
  name: string
  value: number
  percent: number
}

export interface DashboardAllocationChartView {
  data: AllocationChartDataPoint[]
  emptyState: ChartEmptyState
  isEmpty: boolean
  schema: ChartSchema | null
  trustMeta: ChartTrustMeta
}
```

Then move these helper behaviors into the file:

```ts
const supportedChartTypes: ReadonlySet<string> = new Set(['bar', 'line', 'pie', 'scatter', 'sankey'])

export function assertSupportedChartSchema(schema: ChartSchema | null | undefined): boolean
export function getChartSchemaBadge(schema: ChartSchema | null | undefined): string | null
export function getChartFreshnessTone(trust: ChartTrustMeta | null | undefined): WorkbenchTone
export function formatChartTrustLabel(trust: ChartTrustMeta | null | undefined): string
export function buildChartEmptyState(payload: { empty_state?: ChartEmptyState } | undefined, fallbackReason: string): ChartEmptyState
export function hasChartData<TData>(data: TData[] | undefined, emptyState?: ChartEmptyState | null): boolean
export function getDashboardChartPayloadKey(dimension: DashboardAllocationDimension): 'core_type' | 'market' | 'risk_level'
export function adaptDashboardAllocationChartPayload(payload: ChartPayload<AllocationPayloadInput> | undefined): DashboardAllocationChartView
export function buildDashboardAllocationFallbackChart(data: AllocationChartDataPoint[], dimension: DashboardAllocationDimension): DashboardAllocationChartView
```

Implementation details:

- `formatChartTrustLabel({})` returns `local view`.
- Date formatting uses `new Date(value).toLocaleString('zh-CN')`.
- `buildChartEmptyState(undefined, reason)` returns `{ is_empty: true, reason, message: reason }`.
- `buildDashboardAllocationFallbackChart` returns a `pie` schema with `source: 'LOCAL_FALLBACK_VIEW'` and `freshness: 'DELAYED'` when fallback data exists.

- [x] **Step 5: Convert split schema imports to shared chart types**

Modify `frontend/lib/insightArtifacts.ts`:

```ts
import {
  assertSupportedChartSchema,
  getChartSchemaBadge,
  type ChartSchema,
  type ChartTrustMeta,
} from './charts.ts'

export type { ChartSchema }
export type InsightArtifactTrustMeta = ChartTrustMeta
```

Remove its local `SupportedChartType`, `ChartSeriesRef`, `ChartSchema`, `InsightArtifactTrustMeta`, `supportedChartTypes`, and `assertSupportedChartSchema` definitions.

Modify `buildInsightArtifactDetailView` to use:

```ts
chartBadge: getChartSchemaBadge(artifact.chart_schema),
```

Modify `frontend/lib/chartSchemas.ts` into a compatibility wrapper:

```ts
export type {
  AllocationChartDataPoint,
  ChartEmptyState as DashboardChartEmptyState,
  ChartPayload as DashboardChartPayload,
  DashboardAllocationChartView,
  DashboardAllocationDimension,
} from './charts.ts'

export {
  adaptDashboardAllocationChartPayload,
  getDashboardChartPayloadKey,
} from './charts.ts'
```

- [x] **Step 6: Run shared chart contract tests and related tests**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/charts.test.mts tests/chart-schemas.test.mts tests/insight-artifact-presentation.test.mts
```

Expected: all selected tests pass.

- [x] **Step 7: Commit shared contract layer**

Run:

```bash
git add frontend/lib/charts.ts frontend/lib/insightArtifacts.ts frontend/lib/chartSchemas.ts frontend/tests/charts.test.mts frontend/tests/chart-schemas.test.mts docs/superpowers/plans/2026-06-10-dev-p9d-chart-schema-freshness-migration-plan.md
git commit -m "feat: unify frontend chart contracts"
```

### Task 2: Dashboard Allocation Fallback And Tests

**Files:**
- Modify: `frontend/lib/adapters/dashboard.ts`
- Modify: `frontend/tests/dashboard-adapter.test.mts`

- [x] **Step 1: Write failing Dashboard fallback chart test**

Add to `frontend/tests/dashboard-adapter.test.mts`:

```ts
test('dashboard allocation chart synthesizes local trust for legacy fallback data', () => {
  const stats = {
    core_type_allocation: [{ name: 'STOCK', value: 700, percent: 70 }],
    market_allocation: [],
    risk_level_allocation: [],
  }

  const chart = getDashboardAllocationChart(stats, 'CORE_TYPE')
  assert.equal(chart.isEmpty, false)
  assert.equal(chart.schema?.chart_type, 'pie')
  assert.equal(chart.trustMeta.source, 'LOCAL_FALLBACK_VIEW')
  assert.deepEqual(chart.data, [{ name: 'STOCK', value: 700, percent: 70 }])
})
```

- [x] **Step 2: Run Dashboard adapter test and verify RED**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/dashboard-adapter.test.mts
```

Expected: the new fallback test fails because missing schema payload currently returns `MISSING_CHART_PAYLOAD`.

- [x] **Step 3: Implement fallback chart view**

Modify `frontend/lib/adapters/dashboard.ts`:

```ts
import {
  adaptDashboardAllocationChartPayload,
  buildDashboardAllocationFallbackChart,
  getDashboardChartPayloadKey,
  type DashboardAllocationDimension,
} from '../charts.ts'
```

Update `getDashboardAllocationData` to derive from `getDashboardAllocationChart`:

```ts
export function getDashboardAllocationData(
  stats: Pick<DashboardStats, 'core_type_allocation' | 'market_allocation' | 'risk_level_allocation' | 'chart_payloads'>,
  dimension: DashboardAllocationDimension
) {
  return getDashboardAllocationChart(stats, dimension).data
}
```

Update `getDashboardAllocationChart`:

```ts
export function getDashboardAllocationChart(
  stats: Pick<DashboardStats, 'core_type_allocation' | 'market_allocation' | 'risk_level_allocation' | 'chart_payloads'>,
  dimension: DashboardAllocationDimension
) {
  const schemaPayload = stats.chart_payloads?.[getDashboardChartPayloadKey(dimension)]
  if (schemaPayload) return adaptDashboardAllocationChartPayload(schemaPayload)

  if (dimension === 'MARKET') return buildDashboardAllocationFallbackChart(stats.market_allocation ?? [], dimension)
  if (dimension === 'RISK') return buildDashboardAllocationFallbackChart(stats.risk_level_allocation ?? [], dimension)
  return buildDashboardAllocationFallbackChart(stats.core_type_allocation ?? [], dimension)
}
```

- [x] **Step 4: Run Dashboard adapter tests**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/dashboard-adapter.test.mts tests/chart-schemas.test.mts tests/charts.test.mts
```

Expected: all selected tests pass.

- [ ] **Step 5: Commit Dashboard adapter fallback**

Run:

```bash
git add frontend/lib/adapters/dashboard.ts frontend/tests/dashboard-adapter.test.mts docs/superpowers/plans/2026-06-10-dev-p9d-chart-schema-freshness-migration-plan.md
git commit -m "feat: synthesize dashboard chart fallback trust"
```

### Task 3: Shared ChartFrame And Dashboard Renderer Migration

**Files:**
- Create: `frontend/components/charts/ChartFrame.tsx`
- Modify: `frontend/components/dashboard/domain/DashboardAllocationPanel.tsx`
- Modify: `frontend/components/dashboard/AllocationPieChart.tsx`
- Modify: `frontend/components/dashboard/workbench/DashboardEquityHero.tsx`

- [ ] **Step 1: Create ChartFrame component**

Create `frontend/components/charts/ChartFrame.tsx`:

```tsx
import type { ReactNode } from 'react'

import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { StatusPill } from '@/components/ui/StatusPill'
import { Surface } from '@/components/ui/Surface'
import {
  assertSupportedChartSchema,
  formatChartTrustLabel,
  getChartFreshnessTone,
  getChartSchemaBadge,
  hasChartData,
  type ChartEmptyState,
  type ChartSchema,
  type ChartTrustMeta,
} from '@/lib/charts'

interface ChartFrameProps {
  title: string
  eyebrow?: string
  description?: string
  schema?: ChartSchema | null
  trustMeta?: ChartTrustMeta | null
  emptyState?: ChartEmptyState | null
  dataCount?: number
  compact?: boolean
  className?: string
  children: ReactNode
  footer?: ReactNode
}

export function ChartFrame({
  title,
  eyebrow = 'Chart',
  description,
  schema,
  trustMeta,
  emptyState,
  dataCount,
  compact = false,
  className = '',
  children,
  footer,
}: ChartFrameProps) {
  const schemaBadge = getChartSchemaBadge(schema)
  const trustLabel = formatChartTrustLabel(trustMeta)
  const hasData = dataCount === undefined
    ? !emptyState?.is_empty
    : hasChartData(new Array(dataCount).fill(true), emptyState)

  return (
    <Surface className={`${compact ? 'p-4' : 'p-4 md:p-5'} ${className}`}>
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <SectionHeader eyebrow={eyebrow} title={title} description={description} />
        <div className="flex flex-wrap gap-2 sm:justify-end">
          {schemaBadge && <StatusPill tone={assertSupportedChartSchema(schema) ? 'review' : 'warning'}>{schemaBadge}</StatusPill>}
          <StatusPill tone={getChartFreshnessTone(trustMeta)}>{trustLabel}</StatusPill>
        </div>
      </div>
      <div className={compact ? 'mt-3' : 'mt-4'}>
        {hasData ? children : (
          <EmptyStatePanel
            title={emptyState?.reason ?? 'NO_CHART_DATA'}
            description={emptyState?.message ?? '当前图表没有可展示的数据。'}
          />
        )}
      </div>
      {trustMeta?.source_refs && trustMeta.source_refs.length > 0 && (
        <p className="mt-3 break-all text-[11px] text-slate-400">
          source refs: {trustMeta.source_refs.join(', ')}
        </p>
      )}
      {footer && <div className="mt-3">{footer}</div>}
    </Surface>
  )
}
```

- [ ] **Step 2: Migrate Dashboard allocation panel**

Modify `DashboardAllocationPanel` to import `ChartFrame` and wrap `AllocationPieChart`:

```tsx
<ChartFrame
  eyebrow="Allocation"
  title="资产分布"
  description="schema-first allocation view with local fallback trust when backend chart payloads are absent."
  schema={chart?.schema}
  trustMeta={chart?.trustMeta}
  emptyState={chart?.emptyState}
  dataCount={data.length}
  compact
>
  <AllocationPieChart data={data} dimension={allocationDimension} />
</ChartFrame>
```

Keep the dimension tabs in the same panel header area or inside the `ChartFrame` footer.

- [ ] **Step 3: Simplify AllocationPieChart empty state**

Modify `AllocationPieChart` so empty rendering returns a neutral renderer area only when used outside `ChartFrame`:

```tsx
if (!data || data.length === 0) {
  return <div className="flex min-h-[300px] items-center justify-center text-slate-500">暂无数据</div>
}
```

Preserve router click behavior.

- [ ] **Step 4: Migrate Dashboard equity hero chart**

Wrap only the chart area in `ChartFrame` with local schema/trust:

```tsx
const equityChartSchema = {
  schema_version: 'chart.v1',
  chart_type: 'line',
  data_path: 'pnlHistory',
  dimensions: [{ field: 'date', label: 'Date' }],
  series: [{ field: 'pnl_percent', label: 'PnL %', color: lineColor }],
} as const

const equityTrustMeta = {
  freshness: 'DELAYED',
  source: 'LOCAL_DASHBOARD_HISTORY',
  source_refs: ['dashboard:pnlHistory'],
}
```

Then render:

```tsx
<ChartFrame
  eyebrow="Equity"
  title="资金曲线"
  description="本阶段仍使用前端本地曲线数据，等待后端 schema-first equity payload。"
  schema={equityChartSchema}
  trustMeta={equityTrustMeta}
  emptyState={{ is_empty: pnlHistory.length === 0, reason: pnlHistory.length === 0 ? 'NO_EQUITY_HISTORY' : null }}
  dataCount={pnlHistory.length}
  compact
>
  <div className="h-[280px] md:h-[340px]">
    ...
  </div>
</ChartFrame>
```

- [ ] **Step 5: Run TypeScript on migrated components**

Run:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected: TypeScript exits 0.

- [ ] **Step 6: Run targeted strict lint for Dashboard chart files**

Run:

```bash
cd frontend
./node_modules/.bin/eslint components/charts/ChartFrame.tsx components/dashboard/domain/DashboardAllocationPanel.tsx components/dashboard/AllocationPieChart.tsx components/dashboard/workbench/DashboardEquityHero.tsx lib/charts.ts lib/adapters/dashboard.ts --rule 'react-hooks/purity:error' --rule 'react-hooks/set-state-in-effect:error'
```

Expected: ESLint exits 0.

- [ ] **Step 7: Commit ChartFrame and Dashboard renderer migration**

Run:

```bash
git add frontend/components/charts/ChartFrame.tsx frontend/components/dashboard/domain/DashboardAllocationPanel.tsx frontend/components/dashboard/AllocationPieChart.tsx frontend/components/dashboard/workbench/DashboardEquityHero.tsx docs/superpowers/plans/2026-06-10-dev-p9d-chart-schema-freshness-migration-plan.md
git commit -m "feat: wrap dashboard charts with trust frame"
```

### Task 4: MAE/MFE Scatter And Sankey Migration

**Files:**
- Create: `frontend/lib/adapters/chart-views.ts`
- Create: `frontend/tests/chart-views.test.mts`
- Modify: `frontend/components/dashboard/MaeMfeScatterPlot.tsx`
- Modify: `frontend/components/PortfolioSankey.tsx`

- [ ] **Step 1: Write failing chart view adapter tests**

Create `frontend/tests/chart-views.test.mts`:

```ts
import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildMaeMfeScatterPoints,
  buildPortfolioSankeyChartView,
} from '../lib/adapters/chart-views.ts'

test('buildMaeMfeScatterPoints derives long position excursions', () => {
  const points = buildMaeMfeScatterPoints([{
    id: 1,
    symbol: 'NVDA',
    direction: 'LONG',
    average_entry_price: 100,
    max_price_during_hold: 130,
    min_price_during_hold: 90,
    realized_pnl: 25,
    total_quantity: 1,
  } as any])

  assert.deepEqual(points, [{
    id: 1,
    symbol: 'NVDA',
    mae: -10,
    mfe: 30,
    pnl: 25,
    pnlPercent: 25,
  }])
})

test('buildMaeMfeScatterPoints derives short position excursions', () => {
  const points = buildMaeMfeScatterPoints([{
    id: 2,
    symbol: 'TSLA',
    direction: 'SHORT',
    average_entry_price: 100,
    max_price_during_hold: 120,
    min_price_during_hold: 80,
    realized_pnl: -10,
    total_quantity: 1,
  } as any])

  assert.deepEqual(points[0], {
    id: 2,
    symbol: 'TSLA',
    mae: -20,
    mfe: 20,
    pnl: -10,
    pnlPercent: -10,
  })
})

test('buildPortfolioSankeyChartView exposes empty state instead of null rendering', () => {
  const view = buildPortfolioSankeyChartView({ nodes: [], links: [] })

  assert.equal(view.emptyState.is_empty, true)
  assert.equal(view.emptyState.reason, 'NO_SANKEY_NODES')
  assert.equal(view.schema.chart_type, 'sankey')
})
```

- [ ] **Step 2: Run chart view tests and verify RED**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/chart-views.test.mts
```

Expected: fails because `lib/adapters/chart-views.ts` does not exist.

- [ ] **Step 3: Implement chart view helpers**

Create `frontend/lib/adapters/chart-views.ts`:

```ts
import type { Position } from '../api.ts'
import type { ChartEmptyState, ChartSchema, ChartTrustMeta } from '../charts.ts'

export interface MaeMfeScatterPoint {
  id: number
  symbol: string
  mae: number
  mfe: number
  pnl: number
  pnlPercent: number
}

export function buildMaeMfeScatterPoints(positions: Position[]): MaeMfeScatterPoint[] {
  return positions
    .map((position) => {
      if (!position.average_entry_price || !position.max_price_during_hold || !position.min_price_during_hold) return null
      const entry = Number(position.average_entry_price)
      const max = Number(position.max_price_during_hold)
      const min = Number(position.min_price_during_hold)
      const quantity = Number(position.total_quantity || 1)
      const mfe = position.direction === 'LONG' ? ((max - entry) / entry) * 100 : ((entry - min) / entry) * 100
      const mae = position.direction === 'LONG' ? ((min - entry) / entry) * 100 : ((entry - max) / entry) * 100
      const pnl = Number(position.realized_pnl ?? 0)

      return {
        id: position.id,
        symbol: position.symbol,
        mae: Number(mae.toFixed(2)),
        mfe: Number(mfe.toFixed(2)),
        pnl,
        pnlPercent: Number((pnl / (entry * quantity || 1) * 100).toFixed(2)),
      }
    })
    .filter((point): point is MaeMfeScatterPoint => point !== null)
}

export const maeMfeScatterSchema: ChartSchema = {
  schema_version: 'chart.v1',
  chart_type: 'scatter',
  data_path: 'positions',
  dimensions: [{ field: 'mae', label: 'MAE %' }],
  series: [{ field: 'mfe', label: 'MFE %' }],
}

export const localLegacyAnalyticsTrust: ChartTrustMeta = {
  freshness: 'DELAYED',
  source: 'LOCAL_LEGACY_ANALYTICS',
  source_refs: ['legacy:positions'],
}

export function buildPortfolioSankeyChartView(data: { nodes: unknown[]; links: unknown[] }) {
  return {
    schema: {
      schema_version: 'chart.v1',
      chart_type: 'sankey',
      data_path: 'portfolio.sankey',
      dimensions: [{ field: 'nodes', label: 'Nodes' }],
      series: [{ field: 'links', label: 'Links' }],
    } satisfies ChartSchema,
    trustMeta: {
      freshness: 'DELAYED',
      source: 'LOCAL_PORTFOLIO_FLOW_VIEW',
      source_refs: ['dashboard:portfolio-sankey'],
    } satisfies ChartTrustMeta,
    emptyState: {
      is_empty: !data.nodes || data.nodes.length === 0,
      reason: !data.nodes || data.nodes.length === 0 ? 'NO_SANKEY_NODES' : null,
    } satisfies ChartEmptyState,
  }
}
```

- [ ] **Step 4: Run chart view tests**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/chart-views.test.mts
```

Expected: chart view tests pass.

- [ ] **Step 5: Wrap MAE/MFE scatter with ChartFrame**

Modify `MaeMfeScatterPlot.tsx`:

- Import `ChartFrame`.
- Import `buildMaeMfeScatterPoints`, `localLegacyAnalyticsTrust`, and `maeMfeScatterSchema`.
- Remove `useMemo`.
- Render `ChartFrame` with empty reason `NO_MAE_MFE_POINTS`.
- Keep the existing scatter chart internals and explanatory footer copy.

- [ ] **Step 6: Wrap PortfolioSankey with ChartFrame**

Modify `PortfolioSankey.tsx`:

- Import `ChartFrame`.
- Import `buildPortfolioSankeyChartView`.
- Render visible `ChartFrame` even when nodes are empty.
- Keep active node hover behavior and existing Sankey node renderer.

- [ ] **Step 7: Run tests, TypeScript, and targeted strict lint**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/chart-views.test.mts tests/charts.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
./node_modules/.bin/eslint components/dashboard/MaeMfeScatterPlot.tsx components/PortfolioSankey.tsx lib/adapters/chart-views.ts --rule 'react-hooks/purity:error' --rule 'react-hooks/set-state-in-effect:error'
```

Expected: all commands exit 0.

- [ ] **Step 8: Commit scatter and sankey migration**

Run:

```bash
git add frontend/lib/adapters/chart-views.ts frontend/tests/chart-views.test.mts frontend/components/dashboard/MaeMfeScatterPlot.tsx frontend/components/PortfolioSankey.tsx docs/superpowers/plans/2026-06-10-dev-p9d-chart-schema-freshness-migration-plan.md
git commit -m "feat: wrap legacy analytics charts with chart frame"
```

### Task 5: Insights Analysis Chart Deduplication

**Files:**
- Create: `frontend/lib/adapters/insight-charts.ts`
- Create: `frontend/tests/insight-charts.test.mts`
- Create: `frontend/components/insights/LegacyAnalysisChart.tsx`
- Modify: `frontend/app/insights/page.tsx`
- Modify: `frontend/components/insights/AnalysisAssistant.tsx`

- [ ] **Step 1: Write failing Insights chart adapter tests**

Create `frontend/tests/insight-charts.test.mts`:

```ts
import test from 'node:test'
import assert from 'node:assert/strict'

import { adaptLegacyAnalysisChart } from '../lib/adapters/insight-charts.ts'

test('adaptLegacyAnalysisChart maps grouped stats into bar chart rows', () => {
  const view = adaptLegacyAnalysisChart({
    analysis_type: 'strategy_health',
    raw_data: {
      stats: {
        breakout: { avg_pnl: 12.5, win_rate: 0.6, count: 5 },
      },
    },
  } as any)

  assert.equal(view.emptyState.is_empty, false)
  assert.equal(view.schema.chart_type, 'bar')
  assert.deepEqual(view.data, [{
    name: 'breakout',
    pnl: 12.5,
    winRate: 60,
    count: 5,
  }])
})

test('adaptLegacyAnalysisChart maps checklist comparison into two rows', () => {
  const view = adaptLegacyAnalysisChart({
    analysis_type: 'checklist_effect',
    raw_data: {
      checklist_completed: { avg_pnl: 8, count: 3 },
      checklist_ignored: { avg_pnl: -4, count: 2 },
    },
  } as any)

  assert.equal(view.emptyState.is_empty, false)
  assert.deepEqual(view.data, [
    { name: '已执行清单', pnl: 8, winRate: null, count: 3 },
    { name: '未执行/未完成', pnl: -4, winRate: null, count: 2 },
  ])
})

test('adaptLegacyAnalysisChart returns explicit empty state for unsupported raw data', () => {
  const view = adaptLegacyAnalysisChart({
    analysis_type: 'holding_period',
    raw_data: { unsupported: true },
  } as any)

  assert.equal(view.emptyState.is_empty, true)
  assert.equal(view.emptyState.reason, 'UNSUPPORTED_LEGACY_ANALYSIS_CHART')
  assert.deepEqual(view.data, [])
})
```

- [ ] **Step 2: Run Insights chart adapter tests and verify RED**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/insight-charts.test.mts
```

Expected: fails because `lib/adapters/insight-charts.ts` does not exist.

- [ ] **Step 3: Implement Insights chart adapter**

Create `frontend/lib/adapters/insight-charts.ts`:

```ts
import type { AnalysisResponse } from '../api.ts'
import type { ChartEmptyState, ChartSchema, ChartTrustMeta } from '../charts.ts'

export interface LegacyAnalysisChartRow {
  name: string
  pnl: number
  winRate: number | null
  count: number
}

export interface LegacyAnalysisChartView {
  data: LegacyAnalysisChartRow[]
  schema: ChartSchema
  trustMeta: ChartTrustMeta
  emptyState: ChartEmptyState
}

export function adaptLegacyAnalysisChart(result: Pick<AnalysisResponse, 'analysis_type' | 'raw_data' | 'created_at'> | null | undefined): LegacyAnalysisChartView {
  const baseSchema: ChartSchema = {
    schema_version: 'chart.v1',
    chart_type: 'bar',
    data_path: 'analysis.raw_data',
    dimensions: [{ field: 'name', label: 'Analysis bucket' }],
    series: [{ field: 'pnl', label: '平均盈亏' }],
  }
  const trustMeta: ChartTrustMeta = {
    as_of: result?.created_at,
    freshness: 'DELAYED',
    source: 'LOCAL_LEGACY_ANALYSIS',
    source_refs: result ? [`analysis:${result.analysis_type}`] : ['analysis:legacy'],
  }

  if (!result?.raw_data) {
    return { data: [], schema: baseSchema, trustMeta, emptyState: { is_empty: true, reason: 'NO_LEGACY_ANALYSIS_DATA' } }
  }

  if (result.raw_data.stats) {
    const rows = Object.entries(result.raw_data.stats).map(([name, value]: [string, any]) => ({
      name,
      pnl: Number(value.avg_pnl ?? 0),
      winRate: value.win_rate === undefined || value.win_rate === null ? null : Number((Number(value.win_rate) * 100).toFixed(1)),
      count: Number(value.count ?? 0),
    }))
    return { data: rows, schema: baseSchema, trustMeta, emptyState: { is_empty: rows.length === 0, reason: rows.length === 0 ? 'NO_GROUPED_ANALYSIS_ROWS' : null } }
  }

  if (result.analysis_type === 'checklist_effect') {
    const completed = result.raw_data.checklist_completed
    const ignored = result.raw_data.checklist_ignored
    const rows = [
      { name: '已执行清单', pnl: Number(completed?.avg_pnl ?? 0), winRate: null, count: Number(completed?.count ?? 0) },
      { name: '未执行/未完成', pnl: Number(ignored?.avg_pnl ?? 0), winRate: null, count: Number(ignored?.count ?? 0) },
    ]
    return { data: rows, schema: baseSchema, trustMeta, emptyState: { is_empty: false, reason: null } }
  }

  return { data: [], schema: baseSchema, trustMeta, emptyState: { is_empty: true, reason: 'UNSUPPORTED_LEGACY_ANALYSIS_CHART' } }
}
```

- [ ] **Step 4: Run Insights chart adapter tests**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/insight-charts.test.mts
```

Expected: tests pass.

- [ ] **Step 5: Create shared LegacyAnalysisChart component**

Create `frontend/components/insights/LegacyAnalysisChart.tsx`:

```tsx
'use client'

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { ChartFrame } from '@/components/charts/ChartFrame'
import { adaptLegacyAnalysisChart } from '@/lib/adapters/insight-charts'
import type { AnalysisResponse } from '@/lib/api'

interface LegacyAnalysisChartProps {
  result: AnalysisResponse | null | undefined
  compact?: boolean
}

export function LegacyAnalysisChart({ result, compact = false }: LegacyAnalysisChartProps) {
  const view = adaptLegacyAnalysisChart(result)

  return (
    <ChartFrame
      eyebrow="Legacy analysis"
      title="数据可视化"
      description="旧版 AI analysis response 被转换为统一 chart.v1 视图。"
      schema={view.schema}
      trustMeta={view.trustMeta}
      emptyState={view.emptyState}
      dataCount={view.data.length}
      compact={compact}
    >
      <div className={compact ? 'h-56 w-full' : 'h-64 w-full'}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={view.data}>
            <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
            <XAxis dataKey="name" fontSize={11} />
            <YAxis fontSize={11} />
            <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '12px' }} />
            <Bar dataKey="pnl" name="平均盈亏" radius={[4, 4, 0, 0]}>
              {view.data.map((entry) => (
                <Cell key={entry.name} fill={entry.pnl >= 0 ? '#34d399' : '#f87171'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    </ChartFrame>
  )
}
```

- [ ] **Step 6: Replace duplicate chart rendering in `/insights`**

Modify `frontend/app/insights/page.tsx`:

- Remove Recharts imports.
- Remove the local `renderChart` function.
- Import `LegacyAnalysisChart`.
- Replace `{renderChart()}` with:

```tsx
<LegacyAnalysisChart result={cachedResult} compact />
```

- [ ] **Step 7: Replace duplicate chart rendering in `AnalysisAssistant`**

Modify `frontend/components/insights/AnalysisAssistant.tsx`:

- Remove Recharts imports.
- Remove the local `renderChart` function.
- Import `LegacyAnalysisChart`.
- Replace `{renderChart()}` with:

```tsx
<LegacyAnalysisChart result={result} />
```

- [ ] **Step 8: Run Insights tests, TypeScript, and targeted strict lint**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/insight-charts.test.mts tests/insight-artifact-presentation.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
./node_modules/.bin/eslint components/insights/LegacyAnalysisChart.tsx components/insights/AnalysisAssistant.tsx app/insights/page.tsx lib/adapters/insight-charts.ts --rule 'react-hooks/purity:error' --rule 'react-hooks/set-state-in-effect:error'
```

Expected: all commands exit 0. Existing unrelated warnings are not introduced by P9D.

- [ ] **Step 9: Commit Insights chart deduplication**

Run:

```bash
git add frontend/lib/adapters/insight-charts.ts frontend/tests/insight-charts.test.mts frontend/components/insights/LegacyAnalysisChart.tsx frontend/app/insights/page.tsx frontend/components/insights/AnalysisAssistant.tsx docs/superpowers/plans/2026-06-10-dev-p9d-chart-schema-freshness-migration-plan.md
git commit -m "feat: unify legacy insight analysis charts"
```

### Task 6: Full Verification And Browser Smoke

**Files:**
- Modify: `docs/superpowers/plans/2026-06-10-dev-p9d-chart-schema-freshness-migration-plan.md`

- [ ] **Step 1: Run all frontend adapter tests**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/*.test.mts
```

Expected: all tests pass.

- [ ] **Step 2: Run TypeScript**

Run:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected: exits 0.

- [ ] **Step 3: Run lint**

Run:

```bash
cd frontend
npm run lint
```

Expected: exits 0. Existing warnings may remain if they are unchanged and documented.

- [ ] **Step 4: Run targeted strict React 19 lint for all P9D files**

Run:

```bash
cd frontend
./node_modules/.bin/eslint lib/charts.ts lib/chartSchemas.ts lib/insightArtifacts.ts lib/adapters/dashboard.ts lib/adapters/chart-views.ts lib/adapters/insight-charts.ts components/charts/ChartFrame.tsx components/dashboard/domain/DashboardAllocationPanel.tsx components/dashboard/AllocationPieChart.tsx components/dashboard/workbench/DashboardEquityHero.tsx components/dashboard/MaeMfeScatterPlot.tsx components/PortfolioSankey.tsx components/insights/LegacyAnalysisChart.tsx components/insights/AnalysisAssistant.tsx app/insights/page.tsx --rule 'react-hooks/purity:error' --rule 'react-hooks/set-state-in-effect:error'
```

Expected: exits 0.

- [ ] **Step 5: Run production build**

Run:

```bash
cd frontend
npm run build
```

Expected: exits 0. If Turbopack sandbox restrictions block the build, rerun with approval and record the reason.

- [ ] **Step 6: Browser smoke `/dashboard`**

Run dev server:

```bash
cd frontend
npm run dev
```

Open the local URL in the in-app browser and verify:

- Dashboard equity chart is wrapped in the shared frame.
- Dashboard allocation chart is wrapped in the shared frame.
- Schema/trust/freshness cues are visible.
- Mobile width keeps charts in one-column flow.

- [ ] **Step 7: Browser smoke `/insights`**

Using the same dev server, open `/insights` and verify:

- Auditable AI sidecar still renders artifact chart badges.
- Legacy analysis chart area uses the shared frame.
- Empty chart states are visible when no analysis result exists.
- No duplicate local Recharts renderer remains in the page.

- [ ] **Step 8: Record verification results in this plan**

Add a `Verification Results` section with exact command outcomes, browser URLs, and accepted existing warnings.

- [ ] **Step 9: Commit verification record**

Run:

```bash
git add docs/superpowers/plans/2026-06-10-dev-p9d-chart-schema-freshness-migration-plan.md
git commit -m "docs: close p9d chart migration plan"
```

### Task 7: Push Dev Branch

**Files:**
- No file edits unless generated files need restoration.

- [ ] **Step 1: Confirm generated files are clean**

Run:

```bash
git status --short
```

Expected: only `docs/superpowers/demos/` remains untracked. If `frontend/next-env.d.ts` or `frontend/tsconfig.tsbuildinfo` changed, restore only those generated files.

- [ ] **Step 2: Push `dev`**

Run:

```bash
git push origin dev
```

Expected: push succeeds. Do not create a PR.

## Final Acceptance Checklist

- [ ] Shared `frontend/lib/charts.ts` is the canonical frontend chart contract.
- [ ] `frontend/lib/insightArtifacts.ts` imports chart schema and validation from the shared chart module.
- [ ] Dashboard allocation, Dashboard equity, MAE/MFE scatter, Portfolio Sankey, and Insights analysis charts use `ChartFrame`.
- [ ] `/insights` and `AnalysisAssistant` use one `LegacyAnalysisChart` component.
- [ ] All P9D pure adapters are covered by Node tests.
- [ ] Full frontend tests, TypeScript, lint, strict targeted lint, and build pass.
- [ ] Browser smoke passes for `/dashboard` and `/insights`.
- [ ] Work is committed and pushed to `origin/dev`.
