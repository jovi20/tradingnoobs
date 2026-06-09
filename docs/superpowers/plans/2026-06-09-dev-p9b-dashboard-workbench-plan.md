# P9B Dashboard Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `/dashboard` into a macro command center that explains portfolio health, risk posture, structure, and freshness while keeping `/timeline` as the default home.

**Architecture:** Keep backend contracts unchanged. Move Dashboard formatting decisions into tested adapter helpers, split the current monolithic page into focused workbench components, and reuse P9A UI primitives for page framing, surfaces, metric tiles, status pills, and empty states.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Tailwind CSS, Recharts, Node test runner, ESLint.

---

## File Structure

- Modify: `frontend/lib/adapters/dashboard.ts`
  - Add period, metric, risk, account, and mobile ordering helpers.
  - Keep existing adapter exports backward compatible.
- Modify: `frontend/tests/dashboard-adapter.test.mts`
  - Add TDD coverage for new pure helpers.
- Create: `frontend/components/dashboard/workbench/DashboardWorkbench.tsx`
  - Loaded-state page composition.
- Create: `frontend/components/dashboard/workbench/DashboardWorkbenchHeader.tsx`
  - Macro page title, status copy, quick links, and market status placement.
- Create: `frontend/components/dashboard/workbench/DashboardStatusRail.tsx`
  - Top portfolio health metric rail.
- Create: `frontend/components/dashboard/workbench/DashboardEquityHero.tsx`
  - Period tabs, period PnL copy, and equity chart.
- Create: `frontend/components/dashboard/workbench/DashboardRiskRail.tsx`
  - Risk posture, freshness copy, market status, weekly summary panel.
- Create: `frontend/components/dashboard/workbench/DashboardStructureGrid.tsx`
  - Allocation, account rows, risk metrics, and movers.
- Create: `frontend/components/dashboard/workbench/DashboardEvidenceStack.tsx`
  - Sankey, MAE/MFE, and open positions preview.
- Modify: `frontend/app/dashboard/page.tsx`
  - Reduce page to auth/data/loading/error orchestration and pass view model into workbench.
- Modify: `docs/superpowers/plans/2026-06-09-dev-p9b-dashboard-workbench-plan.md`
  - Check off executed tasks and record verification evidence.

---

### Task 1: Add Dashboard Workbench Adapter Helpers

**Files:**
- Modify: `frontend/tests/dashboard-adapter.test.mts`
- Modify: `frontend/lib/adapters/dashboard.ts`

- [x] **Step 1: Write failing tests for period helpers**

Append this block to `frontend/tests/dashboard-adapter.test.mts`:

```ts
import {
  buildDashboardStatusMetrics,
  formatDashboardAccountRows,
  getDashboardHistoryDays,
  getDashboardMobileSectionOrder,
  getDashboardPeriodOptions,
  getDashboardRiskPosture,
} from '../lib/adapters/dashboard.ts'

test('dashboard period helpers return stable day counts', () => {
  const now = new Date('2026-06-09T08:00:00Z')
  const options = getDashboardPeriodOptions(now)

  assert.deepEqual(options.map((option) => option.label), ['1周', '本月', '1月', '3月', '本年', '1年', '全部'])
  assert.equal(getDashboardHistoryDays('1周', now), 7)
  assert.equal(getDashboardHistoryDays('本月', now), 9)
  assert.equal(getDashboardHistoryDays('本年', now), 160)
  assert.equal(getDashboardHistoryDays('全部', now), 9999)
})

test('dashboard period helpers clamp first day of month and year', () => {
  const now = new Date('2026-01-01T08:00:00Z')

  assert.equal(getDashboardHistoryDays('本月', now), 1)
  assert.equal(getDashboardHistoryDays('本年', now), 1)
})
```

- [x] **Step 2: Run tests and confirm failure**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/dashboard-adapter.test.mts
```

Expected: FAIL because `getDashboardPeriodOptions` and `getDashboardHistoryDays` are not exported yet.

- [x] **Step 3: Implement period helper types and functions**

Add this near the top of `frontend/lib/adapters/dashboard.ts` after imports:

```ts
export type DashboardPeriodLabel = '1周' | '本月' | '1月' | '3月' | '本年' | '1年' | '全部'

export interface DashboardPeriodOption {
    label: DashboardPeriodLabel
    days: number
}

const fixedDashboardPeriodOptions: Array<DashboardPeriodOption> = [
    { label: '1周', days: 7 },
    { label: '1月', days: 30 },
    { label: '3月', days: 90 },
    { label: '1年', days: 365 },
    { label: '全部', days: 9999 },
]

function clampDashboardDays(days: number) {
    return Math.max(1, Math.ceil(days))
}

function getDaysElapsedSince(startDate: Date, now: Date) {
    const millisecondsPerDay = 1000 * 60 * 60 * 24
    return clampDashboardDays((now.getTime() - startDate.getTime()) / millisecondsPerDay + 1)
}

export function getDashboardHistoryDays(label: DashboardPeriodLabel, now: Date = new Date()) {
    if (label === '本月') return clampDashboardDays(now.getUTCDate())
    if (label === '本年') return getDaysElapsedSince(new Date(Date.UTC(now.getUTCFullYear(), 0, 1)), now)
    return fixedDashboardPeriodOptions.find((option) => option.label === label)?.days ?? 7
}

export function getDashboardPeriodOptions(now: Date = new Date()): Array<DashboardPeriodOption> {
    return [
        { label: '1周', days: getDashboardHistoryDays('1周', now) },
        { label: '本月', days: getDashboardHistoryDays('本月', now) },
        { label: '1月', days: getDashboardHistoryDays('1月', now) },
        { label: '3月', days: getDashboardHistoryDays('3月', now) },
        { label: '本年', days: getDashboardHistoryDays('本年', now) },
        { label: '1年', days: getDashboardHistoryDays('1年', now) },
        { label: '全部', days: getDashboardHistoryDays('全部', now) },
    ]
}
```

- [x] **Step 4: Run tests and confirm period helpers pass**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/dashboard-adapter.test.mts
```

Expected: PASS for existing tests and the new period helper tests.

- [x] **Step 5: Write failing tests for metrics, risk, account rows, and mobile order**

Append this block to `frontend/tests/dashboard-adapter.test.mts`:

```ts
test('dashboard status metrics summarize portfolio state with tones', () => {
  const result = buildDashboardStatusMetrics({
    stats: {
      total_pnl: -240,
      win_rate: 42,
      avg_pnl_ratio: 0.8,
      open_positions: 3,
      max_drawdown: 0.18,
      total_assets: 10000,
    },
    currencySymbol: '$',
  })

  assert.equal(result[0].label, '总盈亏')
  assert.equal(result[0].value, '-$240')
  assert.equal(result[0].tone, 'negative')
  assert.equal(result[2].label, '最大回撤')
  assert.equal(result[2].tone, 'warning')
  assert.equal(result[3].value, '3')
})

test('dashboard risk posture maps drawdown and ratios to readable state', () => {
  assert.equal(getDashboardRiskPosture({ max_drawdown: 0.05, sharpe_ratio: 1.4 }).tone, 'positive')
  assert.equal(getDashboardRiskPosture({ max_drawdown: 0.18, sharpe_ratio: 0.9 }).tone, 'warning')
  assert.equal(getDashboardRiskPosture({ max_drawdown: 0.32, sharpe_ratio: 0.4 }).tone, 'danger')
})

test('dashboard account rows format values and preserve broker context', () => {
  const rows = formatDashboardAccountRows([
    { name: 'IBKR Main', broker: 'IBKR', value: 12345.67, percent: 61.2 },
  ], '$')

  assert.deepEqual(rows, [{
    name: 'IBKR Main',
    broker: 'IBKR',
    valueLabel: '$12,346',
    percentLabel: '61.2%',
  }])
})

test('dashboard mobile section order keeps summary before evidence', () => {
  assert.deepEqual(getDashboardMobileSectionOrder(true, true), [
    'header',
    'status',
    'equity',
    'risk',
    'structure',
    'movers',
    'positions',
    'evidence',
  ])
  assert.deepEqual(getDashboardMobileSectionOrder(false, false), [
    'header',
    'status',
    'equity',
    'risk',
    'structure',
    'movers',
  ])
})
```

- [x] **Step 6: Run tests and confirm failure**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/dashboard-adapter.test.mts
```

Expected: FAIL because metric, risk, account, and mobile-order helpers are not exported yet.

- [x] **Step 7: Implement helper types and functions**

Add this to `frontend/lib/adapters/dashboard.ts` after the period helpers:

```ts
type DashboardTone = 'neutral' | 'positive' | 'negative' | 'warning' | 'danger'

export interface DashboardStatusMetric {
    label: string
    value: string
    detail: string
    tone: DashboardTone
}

export interface DashboardRiskPosture {
    label: string
    detail: string
    tone: DashboardTone
}

export type DashboardMobileSection = 'header' | 'status' | 'equity' | 'risk' | 'structure' | 'movers' | 'positions' | 'evidence'

function formatSignedCurrency(value: number, currencySymbol: string) {
    const prefix = value >= 0 ? '+' : '-'
    return `${prefix}${currencySymbol}${Math.abs(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
}

function formatPercentValue(value: number) {
    return `${value.toFixed(1)}%`
}

function formatDrawdown(maxDrawdown?: number) {
    if (maxDrawdown === undefined || maxDrawdown === null) return 'N/A'
    return `-${(maxDrawdown * 100).toFixed(1)}%`
}

export function getDashboardRiskPosture(
    stats: Pick<DashboardStats, 'max_drawdown' | 'sharpe_ratio'>
): DashboardRiskPosture {
    const drawdown = stats.max_drawdown ?? 0
    const sharpe = stats.sharpe_ratio ?? 0
    if (drawdown >= 0.25 || sharpe < 0.5) {
        return { label: '风险偏高', detail: '回撤或风险调整收益已经进入警戒区', tone: 'danger' }
    }
    if (drawdown >= 0.12 || sharpe < 1) {
        return { label: '需要观察', detail: '组合仍可运行，但风险质量需要复盘', tone: 'warning' }
    }
    return { label: '状态健康', detail: '回撤和风险调整收益保持在可接受区间', tone: 'positive' }
}

export function buildDashboardStatusMetrics({
    stats,
    currencySymbol,
}: {
    stats: Pick<DashboardStats, 'total_pnl' | 'win_rate' | 'avg_pnl_ratio' | 'open_positions' | 'max_drawdown' | 'total_assets'>
    currencySymbol: string
}): DashboardStatusMetric[] {
    const riskPosture = getDashboardRiskPosture({ max_drawdown: stats.max_drawdown, sharpe_ratio: undefined })
    return [
        {
            label: '总盈亏',
            value: formatSignedCurrency(stats.total_pnl, currencySymbol),
            detail: `资产 ${currencySymbol}${stats.total_assets.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
            tone: stats.total_pnl >= 0 ? 'positive' : 'negative',
        },
        {
            label: '胜率质量',
            value: formatPercentValue(stats.win_rate),
            detail: `盈亏比 ${stats.avg_pnl_ratio.toFixed(2)}`,
            tone: stats.win_rate >= 50 && stats.avg_pnl_ratio >= 1 ? 'positive' : 'warning',
        },
        {
            label: '最大回撤',
            value: formatDrawdown(stats.max_drawdown),
            detail: riskPosture.label,
            tone: riskPosture.tone,
        },
        {
            label: '持仓暴露',
            value: `${stats.open_positions}`,
            detail: '当前打开的交易对象',
            tone: stats.open_positions > 0 ? 'neutral' : 'warning',
        },
    ]
}

export function formatDashboardAccountRows(
    accountAllocation: DashboardStats['account_allocation'],
    currencySymbol: string
) {
    return accountAllocation.map((account) => ({
        name: account.name,
        broker: account.broker,
        valueLabel: `${currencySymbol}${account.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        percentLabel: `${account.percent.toFixed(1)}%`,
    }))
}

export function getDashboardMobileSectionOrder(hasPositions: boolean, hasEvidence: boolean): DashboardMobileSection[] {
    return [
        'header',
        'status',
        'equity',
        'risk',
        'structure',
        'movers',
        ...(hasPositions ? ['positions' as const] : []),
        ...(hasEvidence ? ['evidence' as const] : []),
    ]
}
```

- [x] **Step 8: Run adapter tests**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/dashboard-adapter.test.mts
```

Expected: PASS for all Dashboard adapter tests.

- [x] **Step 9: Commit adapter helpers**

Run:

```bash
git add frontend/lib/adapters/dashboard.ts frontend/tests/dashboard-adapter.test.mts
git commit -m "feat: add dashboard workbench helpers"
```

---

### Task 2: Create Dashboard Workbench Components

**Files:**
- Create: `frontend/components/dashboard/workbench/DashboardWorkbench.tsx`
- Create: `frontend/components/dashboard/workbench/DashboardWorkbenchHeader.tsx`
- Create: `frontend/components/dashboard/workbench/DashboardStatusRail.tsx`
- Create: `frontend/components/dashboard/workbench/DashboardEquityHero.tsx`
- Create: `frontend/components/dashboard/workbench/DashboardRiskRail.tsx`
- Create: `frontend/components/dashboard/workbench/DashboardStructureGrid.tsx`
- Create: `frontend/components/dashboard/workbench/DashboardEvidenceStack.tsx`

- [ ] **Step 1: Create the workbench component directory**

Run:

```bash
mkdir -p frontend/components/dashboard/workbench
```

Expected: directory exists at `frontend/components/dashboard/workbench`.

- [ ] **Step 2: Create `DashboardStatusRail.tsx`**

Create `frontend/components/dashboard/workbench/DashboardStatusRail.tsx`:

```tsx
import { MetricTile } from '@/components/ui/MetricTile'
import type { DashboardStatusMetric } from '@/lib/adapters/dashboard'

const toneMap = {
    neutral: 'neutral',
    positive: 'positive',
    negative: 'negative',
    warning: 'warning',
    danger: 'danger',
} as const

interface DashboardStatusRailProps {
    metrics: DashboardStatusMetric[]
}

export function DashboardStatusRail({ metrics }: DashboardStatusRailProps) {
    return (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {metrics.map((metric) => (
                <MetricTile
                    key={metric.label}
                    label={metric.label}
                    value={metric.value}
                    detail={metric.detail}
                    tone={toneMap[metric.tone]}
                />
            ))}
        </div>
    )
}
```

- [ ] **Step 3: Create `DashboardWorkbenchHeader.tsx`**

Create `frontend/components/dashboard/workbench/DashboardWorkbenchHeader.tsx`:

```tsx
import Link from 'next/link'
import { BarChart3, Calendar, FileText, TrendingUp } from 'lucide-react'
import MarketStatus from '@/components/MarketStatus'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { StatusPill } from '@/components/ui/StatusPill'
import type { DashboardRiskPosture } from '@/lib/adapters/dashboard'

const quickLinks = [
    { href: '/positions/new', label: '新增交易', icon: TrendingUp },
    { href: '/strategies', label: '策略', icon: BarChart3 },
    { href: '/daily', label: '日历', icon: Calendar },
    { href: '/insights', label: '洞察', icon: FileText },
]

interface DashboardWorkbenchHeaderProps {
    riskPosture: DashboardRiskPosture
}

export function DashboardWorkbenchHeader({ riskPosture }: DashboardWorkbenchHeaderProps) {
    return (
        <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-start">
            <SectionHeader
                eyebrow="Macro Command Center"
                title="整体状态怎么样"
                description="Dashboard 负责解释组合健康度、结构、风险和数据新鲜度；最近事件继续回到时间线处理。"
                action={<StatusPill tone={riskPosture.tone}>{riskPosture.label}</StatusPill>}
            />
            <div className="flex flex-col gap-3 lg:items-end">
                <div className="flex max-w-full gap-2 overflow-x-auto pb-1">
                    {quickLinks.map((item) => {
                        const Icon = item.icon
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className="inline-flex shrink-0 items-center gap-2 rounded-full border border-slate-200 bg-white/80 px-3 py-2 text-xs font-semibold text-slate-700 transition-colors hover:border-slate-300 hover:bg-white dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-200"
                            >
                                <Icon className="h-3.5 w-3.5" />
                                {item.label}
                            </Link>
                        )
                    })}
                </div>
                <MarketStatus />
            </div>
        </div>
    )
}
```

- [ ] **Step 4: Create `DashboardEquityHero.tsx`**

Create `frontend/components/dashboard/workbench/DashboardEquityHero.tsx`:

```tsx
import { Line, LineChart, ResponsiveContainer, XAxis, YAxis, Tooltip, CartesianGrid } from 'recharts'
import { Surface } from '@/components/ui/Surface'
import { SectionHeader } from '@/components/ui/SectionHeader'
import type { DashboardPeriodLabel, DashboardPeriodOption, DashboardPeriodMetrics } from '@/lib/adapters/dashboard'

interface DashboardEquityHeroProps {
    periodOptions: DashboardPeriodOption[]
    selectedPeriod: DashboardPeriodLabel
    onSelectPeriod: (label: DashboardPeriodLabel) => void
    periodMetrics: DashboardPeriodMetrics
    pnlHistory: Array<{ date: string; pnl: number; pnl_percent: number }>
    currencySymbol: string
    upClassName: string
    downClassName: string
    lineColor: string
}

export function DashboardEquityHero({
    periodOptions,
    selectedPeriod,
    onSelectPeriod,
    periodMetrics,
    pnlHistory,
    currencySymbol,
    upClassName,
    downClassName,
    lineColor,
}: DashboardEquityHeroProps) {
    const isPositive = periodMetrics.periodPnl >= 0
    const trendClassName = isPositive ? upClassName : downClassName
    const periodValueClassName = periodMetrics.periodValue >= 0 ? upClassName : downClassName

    return (
        <Surface className="overflow-hidden p-4 md:p-6">
            <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-start">
                <SectionHeader
                    eyebrow="Equity / Drawdown"
                    title="资金曲线"
                    description="主图回答当前阶段收益方向，风险解释放在右侧 rail。"
                />
                <div className="flex flex-wrap gap-1">
                    {periodOptions.map((option) => (
                        <button
                            key={option.label}
                            type="button"
                            onClick={() => onSelectPeriod(option.label)}
                            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                                selectedPeriod === option.label
                                    ? 'bg-slate-950 text-white dark:bg-slate-100 dark:text-slate-950'
                                    : 'bg-slate-100 text-slate-500 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                            }`}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            </div>
            <div className="mt-4 flex flex-wrap items-end gap-2">
                <p className={`text-3xl font-semibold tracking-tight ${trendClassName}`}>
                    {periodMetrics.periodPnl >= 0 ? '+' : ''}{periodMetrics.periodPnl.toFixed(2)}%
                </p>
                <p className={`pb-1 text-sm font-semibold ${periodValueClassName}`}>
                    ({periodMetrics.periodValue >= 0 ? '+' : ''}{currencySymbol}{Math.abs(periodMetrics.periodValue).toLocaleString()})
                </p>
                <p className="pb-1 text-xs text-slate-400">{selectedPeriod}阶段盈亏</p>
            </div>
            <div className="mt-5 h-[280px] md:h-[340px]">
                {pnlHistory.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={pnlHistory}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={(value) => String(value).slice(5)} />
                            <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => `${value}%`} />
                            <Tooltip formatter={(value: number) => [`${value.toFixed(2)}%`, '盈亏率']} labelFormatter={(label) => `日期: ${label}`} />
                            <Line type="monotone" dataKey="pnl_percent" stroke={lineColor} strokeWidth={2.5} dot={false} />
                        </LineChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-slate-200 text-sm text-slate-500 dark:border-slate-800">
                        暂无资金曲线数据
                    </div>
                )}
            </div>
        </Surface>
    )
}
```

- [ ] **Step 5: Create `DashboardRiskRail.tsx`**

Create `frontend/components/dashboard/workbench/DashboardRiskRail.tsx`:

```tsx
import { Activity, Database, Sparkles } from 'lucide-react'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { StatusPill } from '@/components/ui/StatusPill'
import { Surface } from '@/components/ui/Surface'
import type { DashboardRiskPosture } from '@/lib/adapters/dashboard'

interface DashboardRiskRailProps {
    riskPosture: DashboardRiskPosture
    openPositionsCount: number
    hasPnlHistory: boolean
}

export function DashboardRiskRail({ riskPosture, openPositionsCount, hasPnlHistory }: DashboardRiskRailProps) {
    return (
        <aside className="space-y-4">
            <Surface variant="rail" className="p-4">
                <SectionHeader
                    eyebrow="Risk Posture"
                    title={riskPosture.label}
                    description={riskPosture.detail}
                    action={<StatusPill tone={riskPosture.tone}>{riskPosture.tone}</StatusPill>}
                />
                <div className="mt-4 h-2 rounded-full bg-slate-200 dark:bg-slate-800">
                    <div className={`h-2 rounded-full ${riskPosture.tone === 'danger' ? 'w-full bg-red-500' : riskPosture.tone === 'warning' ? 'w-2/3 bg-amber-500' : 'w-1/3 bg-emerald-500'}`} />
                </div>
            </Surface>
            <Surface className="p-4">
                <div className="flex items-start gap-3">
                    <Database className="mt-1 h-4 w-4 text-slate-400" />
                    <div>
                        <p className="text-sm font-semibold text-slate-950 dark:text-slate-50">数据新鲜度</p>
                        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                            {hasPnlHistory ? '资金曲线已加载，Dashboard 使用当前聚合数据。' : '资金曲线暂无数据，先展示结构和风险摘要。'}
                        </p>
                    </div>
                </div>
            </Surface>
            <Surface className="p-4">
                <div className="flex items-start gap-3">
                    <Activity className="mt-1 h-4 w-4 text-slate-400" />
                    <div>
                        <p className="text-sm font-semibold text-slate-950 dark:text-slate-50">组合活动</p>
                        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                            当前有 {openPositionsCount} 个打开交易对象，细节仍从交易页进入。
                        </p>
                    </div>
                </div>
            </Surface>
            <Surface className="p-4">
                <div className="flex items-start gap-3">
                    <Sparkles className="mt-1 h-4 w-4 text-amber-500" />
                    <div>
                        <p className="text-sm font-semibold text-slate-950 dark:text-slate-50">周度摘要</p>
                        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                            本阶段先使用风险和结构数据生成可读摘要；AI insight 深读继续保留在洞察页。
                        </p>
                    </div>
                </div>
            </Surface>
        </aside>
    )
}
```

- [ ] **Step 6: Create `DashboardStructureGrid.tsx`**

Create `frontend/components/dashboard/workbench/DashboardStructureGrid.tsx`:

```tsx
import type { AssetAllocation } from '@/lib/api'
import type { DashboardAllocationChartView, DashboardAllocationDimension } from '@/lib/chartSchemas'
import { DashboardAllocationPanel } from '@/components/dashboard/domain/DashboardAllocationPanel'
import { DashboardMoversPanel } from '@/components/dashboard/domain/DashboardMoversPanel'
import RiskMetricsCard from '@/components/dashboard/RiskMetricsCard'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import type { DashboardRiskPosture } from '@/lib/adapters/dashboard'
import type { DashboardStats, PositionMover } from '@/lib/api'

interface AccountRow {
    name: string
    broker: string
    valueLabel: string
    percentLabel: string
}

interface DashboardStructureGridProps {
    allocationDimension: DashboardAllocationDimension
    onChangeAllocationDimension: (dimension: DashboardAllocationDimension) => void
    allocationData: AssetAllocation[]
    allocationChart: DashboardAllocationChartView
    accountRows: AccountRow[]
    stats: DashboardStats
    movers: {
        top: PositionMover[]
        bottom: PositionMover[]
    }
    riskPosture: DashboardRiskPosture
}

export function DashboardStructureGrid({
    allocationDimension,
    onChangeAllocationDimension,
    allocationData,
    allocationChart,
    accountRows,
    stats,
    movers,
    riskPosture,
}: DashboardStructureGridProps) {
    return (
        <div className="grid gap-6 xl:grid-cols-[1.25fr_0.9fr]">
            <div className="space-y-6">
                <DashboardAllocationPanel
                    allocationDimension={allocationDimension}
                    onChangeDimension={onChangeAllocationDimension}
                    data={allocationData}
                    chart={allocationChart}
                />
                <Surface className="p-4">
                    <SectionHeader eyebrow="Accounts" title="账户分布" description="账户层面的资金结构，辅助判断集中度。" />
                    <div className="mt-4 space-y-3">
                        {accountRows.map((account) => (
                            <div key={`${account.name}-${account.broker}`} className="flex items-center justify-between gap-4 rounded-2xl bg-slate-50 px-3 py-3 text-sm dark:bg-slate-800/60">
                                <div className="min-w-0">
                                    <p className="truncate font-semibold text-slate-900 dark:text-slate-100">{account.name}</p>
                                    <p className="text-xs text-slate-400">{account.broker}</p>
                                </div>
                                <div className="shrink-0 text-right">
                                    <p className="font-semibold text-slate-900 dark:text-slate-100">{account.valueLabel}</p>
                                    <p className="text-xs text-slate-400">{account.percentLabel}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </Surface>
            </div>
            <div className="space-y-6">
                <Surface variant={riskPosture.tone === 'danger' ? 'danger' : riskPosture.tone === 'warning' ? 'warning' : 'panel'} className="p-4">
                    <SectionHeader eyebrow="Macro Risk" title={riskPosture.label} description={riskPosture.detail} />
                </Surface>
                <RiskMetricsCard
                    sharpe={stats.sharpe_ratio}
                    sortino={stats.sortino_ratio}
                    calmar={stats.calmar_ratio}
                    maxDrawdown={stats.max_drawdown}
                />
                <DashboardMoversPanel top={movers.top} bottom={movers.bottom} />
            </div>
        </div>
    )
}
```

- [ ] **Step 7: Create `DashboardEvidenceStack.tsx`**

Create `frontend/components/dashboard/workbench/DashboardEvidenceStack.tsx`:

```tsx
import Link from 'next/link'
import PortfolioSankey from '@/components/PortfolioSankey'
import PositionCard from '@/components/dashboard/PositionCard'
import { MaeMfeScatterPlot } from '@/components/dashboard/MaeMfeScatterPlot'
import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import type { DashboardStats } from '@/lib/api'
import type { PositionViewModel } from '@/lib/adapters/trading'

interface DashboardEvidenceStackProps {
    stats: DashboardStats
    openPositions: Array<Pick<PositionViewModel, 'id' | 'routeId'> & Partial<PositionViewModel>>
    allPositions: PositionViewModel[]
    isMobileSankey: boolean
}

export function DashboardEvidenceStack({ stats, openPositions, allPositions, isMobileSankey }: DashboardEvidenceStackProps) {
    return (
        <div className="space-y-6">
            {stats.portfolio_flow && stats.portfolio_flow.nodes.length > 0 && (
                <PortfolioSankey data={stats.portfolio_flow} totalAssets={stats.total_assets} isMobile={isMobileSankey} />
            )}
            {allPositions.length > 0 && (
                <Surface className="p-1">
                    <MaeMfeScatterPlot positions={allPositions} />
                </Surface>
            )}
            <Surface className="p-4">
                <SectionHeader
                    eyebrow="Open Positions"
                    title="持仓中"
                    description="这里只保留宏观预览，逐笔故事继续进入交易详情。"
                    action={openPositions.length > 6 ? (
                        <Link href="/positions" className="text-xs font-semibold text-primary-600 hover:text-primary-700">
                            查看更多
                        </Link>
                    ) : null}
                />
                {openPositions.length === 0 ? (
                    <div className="mt-4">
                        <EmptyStatePanel title="暂无持仓" detail="当前没有打开交易对象，Dashboard 会优先展示历史结构和风险摘要。" />
                    </div>
                ) : (
                    <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                        {openPositions.slice(0, 6).map((position) => (
                            <PositionCard key={position.id} position={position as PositionViewModel} />
                        ))}
                    </div>
                )}
            </Surface>
        </div>
    )
}
```

- [ ] **Step 8: Create `DashboardWorkbench.tsx`**

Create `frontend/components/dashboard/workbench/DashboardWorkbench.tsx`:

```tsx
import { useMemo, useState } from 'react'
import { PageFrame } from '@/components/ui/PageFrame'
import {
    adaptDashboardPageData,
    buildDashboardStatusMetrics,
    formatDashboardAccountRows,
    getDashboardAllocationChart,
    getDashboardAllocationData,
    getDashboardHistoryDays,
    getDashboardPeriodOptions,
    getDashboardRiskPosture,
    type DashboardPeriodLabel,
} from '@/lib/adapters/dashboard'
import type { DashboardAllocationDimension } from '@/lib/chartSchemas'
import type { DashboardStats } from '@/lib/api'
import type { PositionViewModel } from '@/lib/adapters/trading'
import { DashboardEquityHero } from './DashboardEquityHero'
import { DashboardEvidenceStack } from './DashboardEvidenceStack'
import { DashboardRiskRail } from './DashboardRiskRail'
import { DashboardStatusRail } from './DashboardStatusRail'
import { DashboardStructureGrid } from './DashboardStructureGrid'
import { DashboardWorkbenchHeader } from './DashboardWorkbenchHeader'

interface DashboardWorkbenchProps {
    stats: DashboardStats
    pnlHistory: Array<{ date: string; pnl: number; pnl_percent: number }>
    openPositions: PositionViewModel[]
    allPositions: PositionViewModel[]
    displayCurrency?: string
    selectedPeriod: DashboardPeriodLabel
    onChangePeriod: (label: DashboardPeriodLabel, days: number) => void
    isMobileSankey: boolean
    trend: {
        upClassName: string
        downClassName: string
        lineColor: string
    }
}

export function DashboardWorkbench({
    stats,
    pnlHistory,
    openPositions,
    allPositions,
    displayCurrency,
    selectedPeriod,
    onChangePeriod,
    isMobileSankey,
    trend,
}: DashboardWorkbenchProps) {
    const [allocationDimension, setAllocationDimension] = useState<DashboardAllocationDimension>('CORE_TYPE')
    const now = useMemo(() => new Date(), [])
    const dashboard = adaptDashboardPageData({ stats, openPositions, allPositions, pnlHistory, displayCurrency })
    const riskPosture = getDashboardRiskPosture(stats)
    const periodOptions = getDashboardPeriodOptions(now)
    const statusMetrics = buildDashboardStatusMetrics({ stats, currencySymbol: dashboard.currencySymbol })
    const accountRows = formatDashboardAccountRows(dashboard.accountAllocation, dashboard.currencySymbol)

    return (
        <PageFrame className="space-y-6">
            <DashboardWorkbenchHeader riskPosture={riskPosture} />
            <DashboardStatusRail metrics={statusMetrics} />
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
                <DashboardEquityHero
                    periodOptions={periodOptions}
                    selectedPeriod={selectedPeriod}
                    onSelectPeriod={(label) => onChangePeriod(label, getDashboardHistoryDays(label, now))}
                    periodMetrics={dashboard.periodMetrics}
                    pnlHistory={dashboard.pnlHistory}
                    currencySymbol={dashboard.currencySymbol}
                    upClassName={trend.upClassName}
                    downClassName={trend.downClassName}
                    lineColor={trend.lineColor}
                />
                <DashboardRiskRail
                    riskPosture={riskPosture}
                    openPositionsCount={dashboard.openPositionsCount}
                    hasPnlHistory={dashboard.pnlHistory.length > 0}
                />
            </div>
            <DashboardStructureGrid
                allocationDimension={allocationDimension}
                onChangeAllocationDimension={setAllocationDimension}
                allocationData={getDashboardAllocationData(stats, allocationDimension)}
                allocationChart={getDashboardAllocationChart(stats, allocationDimension)}
                accountRows={accountRows}
                stats={stats}
                movers={dashboard.movers}
                riskPosture={riskPosture}
            />
            <DashboardEvidenceStack
                stats={stats}
                openPositions={dashboard.openPositions}
                allPositions={dashboard.allPositions}
                isMobileSankey={isMobileSankey}
            />
        </PageFrame>
    )
}
```

- [ ] **Step 9: Run TypeScript to expose component typing gaps**

Run:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected: TypeScript may fail on prop shapes, especially `PositionViewModel` narrowing. Fix exact compiler errors without changing backend contracts.

- [ ] **Step 10: Commit component scaffold once TypeScript passes after page wiring**

Do not commit yet if the page still imports old inline Dashboard composition. Commit after Task 3 wires the page and TypeScript passes.

---

### Task 3: Replace Dashboard Page Composition

**Files:**
- Modify: `frontend/app/dashboard/page.tsx`

- [ ] **Step 1: Replace inline page composition with workbench orchestration**

Rewrite `frontend/app/dashboard/page.tsx` so it keeps only client state, data loading, and loaded workbench rendering:

```tsx
'use client'

import { useState, useSyncExternalStore } from 'react'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useTrendColor } from '@/hooks/useTrendColor'
import { useDashboardData } from '@/hooks/useDashboardData'
import { DashboardWorkbench } from '@/components/dashboard/workbench/DashboardWorkbench'
import type { DashboardPeriodLabel } from '@/lib/adapters/dashboard'

function subscribeToViewport(callback: () => void) {
    window.addEventListener('resize', callback)
    return () => window.removeEventListener('resize', callback)
}

function getSankeyViewportSnapshot() {
    return window.innerWidth < 640
}

function getSankeyServerSnapshot() {
    return false
}

function useIsMobileSankey() {
    return useSyncExternalStore(subscribeToViewport, getSankeyViewportSnapshot, getSankeyServerSnapshot)
}

export default function DashboardPage() {
    const { token, settings } = useAuth()
    const trendColor = useTrendColor()
    const [selectedPeriod, setSelectedPeriod] = useState<DashboardPeriodLabel>('1周')
    const [historyDays, setHistoryDays] = useState<number>(7)
    const isMobileSankey = useIsMobileSankey()
    const { stats, pnlHistory, openPositions, allPositions, isLoading, error } = useDashboardData(token, historyDays)

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (!stats) return null

    return (
        <div className="pb-20 md:pb-6">
            {error && (
                <div className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
                    Error loading dashboard data: {error}
                </div>
            )}
            <DashboardWorkbench
                stats={stats}
                pnlHistory={pnlHistory}
                openPositions={openPositions}
                allPositions={allPositions}
                displayCurrency={settings?.display_currency}
                selectedPeriod={selectedPeriod}
                onChangePeriod={(label, days) => {
                    setSelectedPeriod(label)
                    setHistoryDays(days)
                }}
                isMobileSankey={isMobileSankey}
                trend={{
                    upClassName: trendColor.upColor,
                    downClassName: trendColor.downColor,
                    lineColor: trendColor.upHex,
                }}
            />
        </div>
    )
}
```

- [ ] **Step 2: Run adapter tests**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/dashboard-adapter.test.mts
```

Expected: PASS.

- [ ] **Step 3: Run TypeScript**

Run:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected: PASS.

- [ ] **Step 4: Run targeted Dashboard strict lint**

Run:

```bash
cd frontend
./node_modules/.bin/eslint app/dashboard/page.tsx components/dashboard/workbench/DashboardWorkbench.tsx components/dashboard/workbench/DashboardWorkbenchHeader.tsx components/dashboard/workbench/DashboardStatusRail.tsx components/dashboard/workbench/DashboardEquityHero.tsx components/dashboard/workbench/DashboardRiskRail.tsx components/dashboard/workbench/DashboardStructureGrid.tsx components/dashboard/workbench/DashboardEvidenceStack.tsx lib/adapters/dashboard.ts --rule 'react-hooks/purity:error' --rule 'react-hooks/set-state-in-effect:error'
```

Expected: PASS.

- [ ] **Step 5: Commit Dashboard workbench implementation**

Run:

```bash
git add frontend/app/dashboard/page.tsx frontend/components/dashboard/workbench frontend/lib/adapters/dashboard.ts frontend/tests/dashboard-adapter.test.mts
git commit -m "feat: redesign dashboard as macro workbench"
```

---

### Task 4: Full Frontend Verification

**Files:**
- Modify: `docs/superpowers/plans/2026-06-09-dev-p9b-dashboard-workbench-plan.md`

- [ ] **Step 1: Run frontend audit**

Run:

```bash
cd frontend
npm audit --audit-level=high
```

Expected: 0 high or critical vulnerabilities.

- [ ] **Step 2: Run all frontend adapter tests**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/*.test.mts
```

Expected: all `.mts` tests pass.

- [ ] **Step 3: Run TypeScript**

Run:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected: PASS.

- [ ] **Step 4: Run lint**

Run:

```bash
cd frontend
npm run lint
```

Expected: exit 0. Existing warnings outside P9B can remain if they match the known P9A baseline.

- [ ] **Step 5: Run production build**

Run:

```bash
cd frontend
npm run build
```

Expected: build exits 0 and includes `/dashboard` and `/timeline`.

- [ ] **Step 6: Restore generated frontend files before commit**

Run:

```bash
git checkout -- frontend/next-env.d.ts frontend/tsconfig.tsbuildinfo
```

Expected: generated files are restored if the build changed them. Do not revert user-authored files.

- [ ] **Step 7: Record verification evidence**

Add a `## Verification Evidence` section to this plan with exact command results:

```md
## Verification Evidence

- `npm audit --audit-level=high`: exited 0 with 0 high/critical vulnerabilities.
- `node --experimental-strip-types --test tests/*.test.mts`: exited 0; all frontend adapter tests passed.
- `./node_modules/.bin/tsc --noEmit --pretty false`: exited 0.
- `npm run lint`: exited 0; remaining warnings were unchanged from the known baseline if present.
- `npm run build`: exited 0 and included `/dashboard`.
```

- [ ] **Step 8: Commit verification notes**

Run:

```bash
git add docs/superpowers/plans/2026-06-09-dev-p9b-dashboard-workbench-plan.md
git commit -m "docs: record p9b dashboard verification"
```

---

### Task 5: Browser Smoke And Dev Branch Push

**Files:**
- Modify: `docs/superpowers/plans/2026-06-09-dev-p9b-dashboard-workbench-plan.md`

- [ ] **Step 1: Start local frontend server**

Run:

```bash
cd frontend
npm run dev
```

Expected: local Next.js app is reachable on the printed localhost URL.

- [ ] **Step 2: Browser smoke desktop Dashboard**

Open:

```text
http://localhost:3000/dashboard
```

Expected:

- Desktop layout shows Macro Command Center header, status rail, equity hero, right risk rail, structure grid, and evidence stack.
- Dashboard does not look like the default homepage.
- Navigation still allows returning to Timeline.

- [ ] **Step 3: Browser smoke mobile Dashboard**

Use a 390px wide viewport and open:

```text
http://localhost:3000/dashboard
```

Expected:

- Mobile layout is one column.
- Status rail and equity hero appear before secondary evidence charts.
- Bottom navigation remains usable.

- [ ] **Step 4: Browser smoke Timeline redirect**

Open:

```text
http://localhost:3000/
```

Expected: app redirects to `/timeline`.

- [ ] **Step 5: Record browser smoke evidence**

Add browser evidence to this plan:

```md
## Browser Smoke

- Desktop `/dashboard`: Macro Command Center layout visible with status rail, equity hero, risk rail, structure grid, and evidence stack.
- Mobile `/dashboard` at 390px: single-column summary-first layout; bottom nav usable.
- `/`: redirects to `/timeline`.
```

- [ ] **Step 6: Commit browser smoke notes**

Run:

```bash
git add docs/superpowers/plans/2026-06-09-dev-p9b-dashboard-workbench-plan.md
git commit -m "docs: close p9b dashboard smoke"
```

- [ ] **Step 7: Push dev branch**

Run:

```bash
git push origin dev
```

Expected: `origin/dev` receives P9B design, implementation, and verification commits. No PR is created.

---

## Final Acceptance Checklist

- [ ] P9B design spec exists at `docs/superpowers/specs/2026-06-09-p9b-dashboard-workbench-design.md`.
- [ ] `/dashboard` is a macro command center, not a revived homepage.
- [ ] `/` still redirects to `/timeline`.
- [ ] Dashboard page file is an orchestration shell.
- [ ] New workbench components live under `frontend/components/dashboard/workbench/`.
- [ ] Dashboard helper logic lives in `frontend/lib/adapters/dashboard.ts` and is covered by tests.
- [ ] Existing backend/API contracts are unchanged.
- [ ] `docs/superpowers/demos/` remains untouched.
- [ ] Frontend audit, adapter tests, TypeScript, lint, and build pass.
- [ ] Browser smoke covers desktop Dashboard, mobile Dashboard, and `/` redirect.
- [ ] P9B commits are pushed to `origin/dev`.
