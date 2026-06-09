# P9C Lifecycle Detail Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn `/positions/[id]` into a truth lifecycle workbench where the lifecycle read model is primary and legacy `Position / TradeBatch` surfaces are explicitly migration-only.

**Architecture:** Keep backend contracts unchanged. Move lifecycle page rules into tested adapter helpers, split the current monolithic detail page into focused lifecycle workbench components, and reduce `frontend/app/positions/[id]/page.tsx` to fetch, mutation, and top-level branching orchestration.

**Tech Stack:** Next.js App Router, React 19, TypeScript, Tailwind CSS, Node test runner, ESLint.

---

## File Structure

- Modify: `frontend/lib/adapters/lifecycle.ts`
  - Add page section, primary action, legacy panel, review tone, event rail, evidence panel, and empty-state helpers.
  - Keep existing lifecycle adapter exports backward compatible.
- Modify: `frontend/tests/lifecycle-adapter.test.mts`
  - Add TDD coverage for new pure helpers.
- Create: `frontend/components/positions/lifecycle/LifecycleWorkbench.tsx`
  - Loaded-state page composition for truth lifecycle.
- Create: `frontend/components/positions/lifecycle/LifecycleWorkbenchHeader.tsx`
  - Back navigation, title, status, account, side, and trust/status labels.
- Create: `frontend/components/positions/lifecycle/LifecycleHero.tsx`
  - Result summary, key numbers, thesis, execution quality, checklist count, and review state.
- Create: `frontend/components/positions/lifecycle/LifecycleActionPanel.tsx`
  - Truth narrative, reversal, and manual cash adjustment action entry points.
- Create: `frontend/components/positions/lifecycle/LifecycleEventRail.tsx`
  - Compact lifecycle event spine.
- Create: `frontend/components/positions/lifecycle/LifecycleEvidencePanel.tsx`
  - Evidence refs, cash effects, and trust metadata.
- Create: `frontend/components/positions/lifecycle/LifecycleAiSidecarPanel.tsx`
  - Artifact-backed AI sidecar cards.
- Create: `frontend/components/positions/lifecycle/LifecycleMigrationPanel.tsx`
  - Legacy summary, metadata, MAE/MFE, checklist/drift, batch records, review, lessons, and guarded legacy actions.
- Create: `frontend/components/positions/lifecycle/LifecycleModals.tsx`
  - Truth narrative and manual cash adjustment modals.
- Modify: `frontend/app/positions/[id]/page.tsx`
  - Reduce to route/auth state, data loading, mutation handlers, fallback branching, and workbench props.
- Modify: `docs/superpowers/plans/2026-06-09-dev-p9c-lifecycle-detail-workbench-plan.md`
  - Check off executed tasks and record verification evidence.

---

### Task 1: Add Lifecycle Workbench Adapter Helpers

**Files:**
- Modify: `frontend/tests/lifecycle-adapter.test.mts`
- Modify: `frontend/lib/adapters/lifecycle.ts`

- [x] **Step 1: Write failing tests for section order, review tone, and legacy panel state**

Append this block to `frontend/tests/lifecycle-adapter.test.mts`:

```ts
test('lifecycle page sections keep truth story before legacy migration tools', () => {
  assert.deepEqual(lifecycleAdapter.getLifecyclePageSections({ hasTruthLifecycle: true, hasLegacyPosition: true, viewport: 'desktop' }), [
    'header',
    'hero',
    'actions',
    'rail',
    'evidence',
    'migration',
  ])

  assert.deepEqual(lifecycleAdapter.getLifecyclePageSections({ hasTruthLifecycle: true, hasLegacyPosition: true, viewport: 'mobile' }), [
    'header',
    'hero',
    'actions',
    'rail',
    'ai',
    'evidence',
    'cash',
    'migration',
  ])

  assert.deepEqual(lifecycleAdapter.getLifecyclePageSections({ hasTruthLifecycle: false, hasLegacyPosition: true, viewport: 'desktop' }), [
    'header',
    'legacy-fallback',
  ])
})

test('lifecycle review tone maps status to labels and readable tones', () => {
  assert.deepEqual(lifecycleAdapter.getLifecycleReviewTone('OPEN'), {
    label: 'Open',
    tone: 'neutral',
    description: 'Position is still open; review remains in progress.',
  })
  assert.deepEqual(lifecycleAdapter.getLifecycleReviewTone('CLOSED_PENDING_REVIEW'), {
    label: 'Pending Review',
    tone: 'warning',
    description: 'Position is closed and waiting for review.',
  })
  assert.deepEqual(lifecycleAdapter.getLifecycleReviewTone('REVIEWED'), {
    label: 'Reviewed',
    tone: 'positive',
    description: 'Review evidence has been recorded.',
  })
})

test('lifecycle legacy panel state makes old DTO surfaces migration-only when truth exists', () => {
  assert.deepEqual(lifecycleAdapter.getLifecycleLegacyPanelState({ hasTruthLifecycle: true, hasLegacyPosition: true }), {
    shouldRender: true,
    mode: 'migration',
    title: 'Legacy migration tools',
    description: 'These sections still read from legacy Position / TradeBatch data and are secondary to the truth lifecycle.',
  })

  assert.deepEqual(lifecycleAdapter.getLifecycleLegacyPanelState({ hasTruthLifecycle: true, hasLegacyPosition: false }), {
    shouldRender: false,
    mode: 'hidden',
    title: 'Legacy migration tools',
    description: 'No legacy Position / TradeBatch data was loaded for this truth lifecycle.',
  })

  assert.deepEqual(lifecycleAdapter.getLifecycleLegacyPanelState({ hasTruthLifecycle: false, hasLegacyPosition: true }), {
    shouldRender: true,
    mode: 'fallback',
    title: 'Legacy fallback detail',
    description: 'Truth lifecycle is unavailable, so this page is showing legacy Position / TradeBatch data.',
  })
})
```

- [x] **Step 2: Run lifecycle adapter test and confirm failure**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/lifecycle-adapter.test.mts
```

Expected: FAIL because `getLifecyclePageSections`, `getLifecycleReviewTone`, and `getLifecycleLegacyPanelState` are not exported yet.

- [x] **Step 3: Implement section, tone, and legacy helpers**

Add this to `frontend/lib/adapters/lifecycle.ts` after `LifecycleReversalAction`:

```ts
export type LifecycleWorkbenchTone = 'neutral' | 'positive' | 'negative' | 'warning' | 'danger' | 'entry' | 'exit' | 'review' | 'ai'
export type LifecycleViewport = 'desktop' | 'mobile'
export type LifecyclePageSection = 'header' | 'hero' | 'actions' | 'rail' | 'ai' | 'evidence' | 'cash' | 'migration' | 'legacy-fallback'
export type LifecycleLegacyPanelMode = 'hidden' | 'migration' | 'fallback'

export interface LifecycleLegacyPanelState {
    shouldRender: boolean
    mode: LifecycleLegacyPanelMode
    title: string
    description: string
}
```

Add this near the summary helper functions in `frontend/lib/adapters/lifecycle.ts`:

```ts
export function getLifecyclePageSections(input: {
    hasTruthLifecycle: boolean
    hasLegacyPosition: boolean
    viewport: LifecycleViewport
}): LifecyclePageSection[] {
    if (!input.hasTruthLifecycle) {
        return input.hasLegacyPosition ? ['header', 'legacy-fallback'] : ['header']
    }

    if (input.viewport === 'mobile') {
        return ['header', 'hero', 'actions', 'rail', 'ai', 'evidence', 'cash', 'migration']
    }

    return ['header', 'hero', 'actions', 'rail', 'evidence', 'migration']
}

export function getLifecycleReviewTone(reviewStatus: LifecycleDetailViewModel['reviewStatus']): {
    label: string
    tone: LifecycleWorkbenchTone
    description: string
} {
    if (reviewStatus === 'CLOSED_PENDING_REVIEW') {
        return {
            label: 'Pending Review',
            tone: 'warning',
            description: 'Position is closed and waiting for review.',
        }
    }
    if (reviewStatus === 'REVIEWED') {
        return {
            label: 'Reviewed',
            tone: 'positive',
            description: 'Review evidence has been recorded.',
        }
    }
    return {
        label: 'Open',
        tone: 'neutral',
        description: 'Position is still open; review remains in progress.',
    }
}

export function getLifecycleLegacyPanelState(input: {
    hasTruthLifecycle: boolean
    hasLegacyPosition: boolean
}): LifecycleLegacyPanelState {
    if (input.hasTruthLifecycle && input.hasLegacyPosition) {
        return {
            shouldRender: true,
            mode: 'migration',
            title: 'Legacy migration tools',
            description: 'These sections still read from legacy Position / TradeBatch data and are secondary to the truth lifecycle.',
        }
    }

    if (input.hasTruthLifecycle) {
        return {
            shouldRender: false,
            mode: 'hidden',
            title: 'Legacy migration tools',
            description: 'No legacy Position / TradeBatch data was loaded for this truth lifecycle.',
        }
    }

    return {
        shouldRender: input.hasLegacyPosition,
        mode: input.hasLegacyPosition ? 'fallback' : 'hidden',
        title: input.hasLegacyPosition ? 'Legacy fallback detail' : 'Legacy migration tools',
        description: input.hasLegacyPosition
            ? 'Truth lifecycle is unavailable, so this page is showing legacy Position / TradeBatch data.'
            : 'No lifecycle or legacy position data is available.',
    }
}
```

- [x] **Step 4: Run lifecycle adapter test and confirm new tests pass**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/lifecycle-adapter.test.mts
```

Expected: PASS for existing tests and the new helper tests.

- [x] **Step 5: Write failing tests for primary actions, event rail, evidence panel, and empty states**

Append this block to `frontend/tests/lifecycle-adapter.test.mts`:

```ts
test('lifecycle primary actions combine narrative, reversal, and cash adjustment states', () => {
  const actions = lifecycleAdapter.getLifecyclePrimaryActions({
    hasEditableNarrativeEvent: true,
    reversal: {
      canReverse: true,
      eventPublicId: 'evt-reduce',
      nodeType: 'REDUCE',
      label: '撤销最新 truth 事件',
      reason: '将追加 REVERSAL 节点并重放 FIFO，不会静默改写历史事件。',
    },
  })

  assert.equal(actions.narrative.canRun, true)
  assert.equal(actions.narrative.label, '编辑 truth narrative')
  assert.equal(actions.reversal.canRun, true)
  assert.equal(actions.reversal.label, '撤销最新 truth 事件')
  assert.equal(actions.cashAdjustment.canRun, true)
  assert.equal(actions.cashAdjustment.label, '记录 cash adjustment')
})

test('lifecycle event rail items expose node tone and date labels', () => {
  const items = lifecycleAdapter.getLifecycleEventRailItems({
    nodes: [
      { node_public_id: 'evt-open', node_type: 'OPEN', occurred_at: '2026-06-01T09:30:00Z', title: 'OPEN', summary: 'Opened thesis' },
      { node_public_id: 'evt-ai', node_type: 'AI_CONCLUSION', occurred_at: '2026-06-02T09:30:00Z', title: 'AI', summary: 'AI conclusion' },
    ],
  })

  assert.deepEqual(items, [
    { id: 'evt-open', type: 'OPEN', title: 'OPEN', summary: 'Opened thesis', dateLabel: '2026/6/1', tone: 'entry' },
    { id: 'evt-ai', type: 'AI_CONCLUSION', title: 'AI', summary: 'AI conclusion', dateLabel: '2026/6/2', tone: 'ai' },
  ])
})

test('lifecycle evidence panel summary combines evidence, cash, and AI counts', () => {
  assert.deepEqual(lifecycleAdapter.getLifecycleEvidencePanelSummary({
    evidenceItems: [
      { ref_type: 'POSITION_EVENT', public_id: 'evt-open', label: 'OPEN', href: '/positions/tp-1' },
    ],
    cashEffects: [
      {
        ledger_entry_public_id: 'ledger-1',
        entry_type: 'REALIZED_PNL',
        amount: 25,
        amount_account_ccy: 25,
        currency: 'USD',
        occurred_at: '2026-06-02T09:30:00Z',
      },
    ],
    aiItems: [{ title: 'AI conclusion', conclusion: 'Evidence-backed note.' }],
  }), {
    evidenceLabel: '1 条 evidence · POSITION_EVENT',
    cashLabel: '1 条现金流水 · USD 25.00',
    aiLabel: '1 条 AI 结论 · 0 条证据',
  })
})

test('lifecycle empty state copy distinguishes missing truth from missing all data', () => {
  assert.equal(
    lifecycleAdapter.getLifecycleEmptyState({ hasTruthLifecycle: false, hasLegacyPosition: true }).title,
    'Truth lifecycle unavailable'
  )
  assert.equal(
    lifecycleAdapter.getLifecycleEmptyState({ hasTruthLifecycle: false, hasLegacyPosition: false }).title,
    'Position not found'
  )
})
```

- [x] **Step 6: Run lifecycle adapter test and confirm failure**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/lifecycle-adapter.test.mts
```

Expected: FAIL because `getLifecyclePrimaryActions`, `getLifecycleEventRailItems`, `getLifecycleEvidencePanelSummary`, and `getLifecycleEmptyState` are not exported yet.

- [x] **Step 7: Implement action, rail, evidence, and empty-state helpers**

Add this to `frontend/lib/adapters/lifecycle.ts` after `LifecycleLegacyPanelState`:

```ts
export interface LifecyclePrimaryAction {
    canRun: boolean
    label: string
    reason: string
}

export interface LifecyclePrimaryActions {
    narrative: LifecyclePrimaryAction
    reversal: LifecyclePrimaryAction
    cashAdjustment: LifecyclePrimaryAction
}

export interface LifecycleEventRailItem {
    id: string
    type: string
    title: string
    summary: string
    dateLabel: string
    tone: LifecycleWorkbenchTone
}
```

Add this near the other helper functions in `frontend/lib/adapters/lifecycle.ts`:

```ts
function getLifecycleNodeTone(nodeType: string): LifecycleWorkbenchTone {
    if (nodeType === 'OPEN' || nodeType === 'ADD') return 'entry'
    if (nodeType === 'REDUCE' || nodeType === 'CLOSE') return 'exit'
    if (nodeType === 'REVIEW') return 'review'
    if (nodeType === 'AI_CONCLUSION') return 'ai'
    if (nodeType === 'REVERSAL' || nodeType === 'MANUAL_ADJUSTMENT') return 'warning'
    return 'neutral'
}

export function getLifecyclePrimaryActions(input: {
    hasEditableNarrativeEvent: boolean
    reversal: LifecycleReversalAction
}): LifecyclePrimaryActions {
    return {
        narrative: {
            canRun: input.hasEditableNarrativeEvent,
            label: '编辑 truth narrative',
            reason: input.hasEditableNarrativeEvent
                ? 'Write narrative fields back to the source PositionEvent.'
                : '当前 lifecycle 没有可编辑的 PositionEvent public_id。',
        },
        reversal: {
            canRun: input.reversal.canReverse,
            label: input.reversal.label,
            reason: input.reversal.reason,
        },
        cashAdjustment: {
            canRun: true,
            label: '记录 cash adjustment',
            reason: 'Append MANUAL_ADJUSTMENT event and CASH_ADJUSTMENT ledger entry without changing FIFO quantity.',
        },
    }
}

export function getLifecycleEventRailItems(input: Pick<LifecycleDetailViewModel, 'nodes'>): LifecycleEventRailItem[] {
    return input.nodes.map((node) => ({
        id: node.node_public_id,
        type: node.node_type,
        title: node.title,
        summary: node.summary,
        dateLabel: new Date(node.occurred_at).toLocaleDateString('zh-CN'),
        tone: getLifecycleNodeTone(node.node_type),
    }))
}

export function getLifecycleEvidencePanelSummary(input: Pick<LifecycleDetailViewModel, 'evidenceItems' | 'cashEffects' | 'aiItems'>) {
    return {
        evidenceLabel: getLifecycleEvidenceSummary(input),
        cashLabel: getLifecycleCashEffectSummary(input),
        aiLabel: getLifecycleAiSidecarSummary(input),
    }
}

export function getLifecycleEmptyState(input: {
    hasTruthLifecycle: boolean
    hasLegacyPosition: boolean
}): { title: string; description: string } {
    if (!input.hasTruthLifecycle && input.hasLegacyPosition) {
        return {
            title: 'Truth lifecycle unavailable',
            description: 'Legacy Position / TradeBatch data is available, but the truth lifecycle read model could not be loaded.',
        }
    }
    if (!input.hasTruthLifecycle) {
        return {
            title: 'Position not found',
            description: 'No truth lifecycle or legacy position data was available for this route.',
        }
    }
    return {
        title: 'Lifecycle ready',
        description: 'Truth lifecycle data is available.',
    }
}
```

- [x] **Step 8: Run lifecycle adapter test and confirm all helper tests pass**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/lifecycle-adapter.test.mts
```

Expected: PASS.

- [x] **Step 9: Commit adapter helpers**

Run:

```bash
git add frontend/lib/adapters/lifecycle.ts frontend/tests/lifecycle-adapter.test.mts docs/superpowers/plans/2026-06-09-dev-p9c-lifecycle-detail-workbench-plan.md
git commit -m "feat: add lifecycle workbench helpers"
```

Expected: commit succeeds with helper and test changes.

---

### Task 2: Create Lifecycle Workbench Truth Components

**Files:**
- Create: `frontend/components/positions/lifecycle/LifecycleWorkbench.tsx`
- Create: `frontend/components/positions/lifecycle/LifecycleWorkbenchHeader.tsx`
- Create: `frontend/components/positions/lifecycle/LifecycleHero.tsx`
- Create: `frontend/components/positions/lifecycle/LifecycleActionPanel.tsx`
- Create: `frontend/components/positions/lifecycle/LifecycleEventRail.tsx`
- Create: `frontend/components/positions/lifecycle/LifecycleEvidencePanel.tsx`
- Create: `frontend/components/positions/lifecycle/LifecycleAiSidecarPanel.tsx`
- Modify: `frontend/app/positions/[id]/page.tsx`

- [x] **Step 1: Create the header component**

Create `frontend/components/positions/lifecycle/LifecycleWorkbenchHeader.tsx` with:

```tsx
import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'
import { StatusPill } from '@/components/ui/StatusPill'
import { getLifecycleReviewTone, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'

interface LifecycleWorkbenchHeaderProps {
    lifecycle: LifecycleDetailViewModel
}

export function LifecycleWorkbenchHeader({ lifecycle }: LifecycleWorkbenchHeaderProps) {
    const reviewTone = getLifecycleReviewTone(lifecycle.reviewStatus)
    const isOpen = lifecycle.positionStatus === 'OPEN'

    return (
        <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="flex min-w-0 items-start gap-3">
                <Link href="/positions" className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800">
                    <ArrowLeft className="h-5 w-5" />
                </Link>
                <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                        <p className="text-xs font-bold uppercase tracking-[0.22em] text-cyan-700 dark:text-cyan-300">Lifecycle Command Center</p>
                        <StatusPill tone={isOpen ? 'review' : 'neutral'}>{isOpen ? 'Open Position' : 'Closed Position'}</StatusPill>
                        <StatusPill tone={reviewTone.tone}>{reviewTone.label}</StatusPill>
                    </div>
                    <h1 className="mt-2 truncate text-3xl font-black tracking-tight text-slate-950 dark:text-white md:text-5xl">
                        {lifecycle.positionTitle}
                    </h1>
                    <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                        {lifecycle.assetSymbol} · {lifecycle.instrumentLabel} · {lifecycle.accountLabel} · {lifecycle.side}
                    </p>
                </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-400">
                <p className="font-semibold uppercase tracking-[0.18em]">as of</p>
                <p className="mt-1">{new Date(lifecycle.trust.as_of).toLocaleString('zh-CN')}</p>
            </div>
        </header>
    )
}
```

- [x] **Step 2: Create the hero component**

Create `frontend/components/positions/lifecycle/LifecycleHero.tsx` with:

```tsx
import { Activity, ShieldCheck } from 'lucide-react'
import { MetricTile } from '@/components/ui/MetricTile'
import { Surface } from '@/components/ui/Surface'
import { getLifecycleReviewTone, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'

interface LifecycleHeroProps {
    lifecycle: LifecycleDetailViewModel
}

export function LifecycleHero({ lifecycle }: LifecycleHeroProps) {
    const reviewTone = getLifecycleReviewTone(lifecycle.reviewStatus)

    return (
        <Surface className="overflow-hidden border-slate-900 bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950 p-0 text-white dark:border-slate-700">
            <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="p-6 md:p-8">
                    <div className="flex items-center gap-2 text-sm font-bold text-cyan-100">
                        <ShieldCheck className="h-4 w-4" />
                        Truth thesis and result
                    </div>
                    <h2 className="mt-4 text-2xl font-black md:text-4xl">{lifecycle.summaryHeadline}</h2>
                    <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300 md:text-base">{lifecycle.summaryBody}</p>
                    <div className="mt-6 grid gap-3 md:grid-cols-3">
                        {lifecycle.keyNumbers.map((item) => (
                            <MetricTile key={item.label} label={item.label} value={item.value} detail="truth lifecycle read model" />
                        ))}
                    </div>
                    <div className="mt-6 rounded-3xl border border-white/10 bg-white/[0.06] p-5">
                        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-cyan-100">Thesis</p>
                        <p className="mt-3 text-sm leading-6 text-slate-200">{lifecycle.thesis || '这笔交易还没有结构化 thesis。'}</p>
                        <div className="mt-4 grid gap-3 md:grid-cols-3">
                            <HeroMini label="Invalidation" value={lifecycle.invalidationRule || '未记录'} />
                            <HeroMini label="Planned Exit" value={lifecycle.plannedExitRule || '未记录'} />
                            <HeroMini label="Sizing" value={lifecycle.sizingRationale || '未记录'} />
                        </div>
                    </div>
                </div>
                <aside className="border-t border-white/10 bg-black/20 p-6 lg:border-l lg:border-t-0">
                    <div className="flex items-center gap-2 text-sm font-bold">
                        <Activity className="h-4 w-4 text-amber-200" />
                        Execution quality
                    </div>
                    <p className="mt-4 text-3xl font-black">{lifecycle.executionQuality || 'UNKNOWN'}</p>
                    <p className="mt-2 text-sm text-slate-300">{reviewTone.description}</p>
                    <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.06] p-4">
                        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Checklist miss</p>
                        <p className="mt-2 text-2xl font-black">{lifecycle.checklistMissCount ?? 0}</p>
                    </div>
                </aside>
            </div>
        </Surface>
    )
}

function HeroMini({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p>
            <p className="mt-1 text-sm text-slate-200">{value}</p>
        </div>
    )
}
```

- [x] **Step 3: Create action, event, evidence, and AI panels**

Create `frontend/components/positions/lifecycle/LifecycleActionPanel.tsx` with:

```tsx
import { Edit3, RotateCcw, Wrench } from 'lucide-react'
import { Surface } from '@/components/ui/Surface'
import type { LifecyclePrimaryActions } from '@/lib/adapters/lifecycle'

interface LifecycleActionPanelProps {
    actions: LifecyclePrimaryActions
    isReversing: boolean
    onEditNarrative: () => void
    onReverseLatest: () => void
    onManualAdjustment: () => void
}

export function LifecycleActionPanel({ actions, isReversing, onEditNarrative, onReverseLatest, onManualAdjustment }: LifecycleActionPanelProps) {
    return (
        <Surface className="border-cyan-200 bg-cyan-50/80 p-5 dark:border-cyan-900 dark:bg-cyan-950/20">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-cyan-800 dark:text-cyan-200">Truth write path</p>
                    <h2 className="mt-2 text-lg font-black text-slate-950 dark:text-white">Write back to TradingPosition / PositionEvent</h2>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                        Narrative fields, latest event reversal, and cash adjustment stay on the truth path. Legacy batch edits remain migration tools.
                    </p>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row">
                    <button type="button" onClick={onEditNarrative} disabled={!actions.narrative.canRun} title={actions.narrative.reason} className="btn btn-primary flex items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-60">
                        <Edit3 className="h-4 w-4" />
                        {actions.narrative.label}
                    </button>
                    <button type="button" onClick={onReverseLatest} disabled={!actions.reversal.canRun || isReversing} title={actions.reversal.reason} className="btn btn-secondary flex items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-60">
                        <RotateCcw className="h-4 w-4" />
                        {actions.reversal.label}
                    </button>
                    <button type="button" onClick={onManualAdjustment} disabled={!actions.cashAdjustment.canRun} title={actions.cashAdjustment.reason} className="btn btn-secondary flex items-center justify-center gap-2">
                        <Wrench className="h-4 w-4" />
                        {actions.cashAdjustment.label}
                    </button>
                </div>
            </div>
        </Surface>
    )
}
```

Create `frontend/components/positions/lifecycle/LifecycleEventRail.tsx` with:

```tsx
import { GitBranch } from 'lucide-react'
import { StatusPill } from '@/components/ui/StatusPill'
import { Surface } from '@/components/ui/Surface'
import { getLifecycleEventRailItems, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'

interface LifecycleEventRailProps {
    lifecycle: LifecycleDetailViewModel
}

export function LifecycleEventRail({ lifecycle }: LifecycleEventRailProps) {
    const items = getLifecycleEventRailItems(lifecycle)

    return (
        <Surface className="p-5">
            <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-cyan-600" />
                <h2 className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">Lifecycle event spine</h2>
            </div>
            <div className="mt-5 space-y-3">
                {items.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900/70">
                        <div className="flex items-center justify-between gap-3">
                            <StatusPill tone={item.tone}>{item.type}</StatusPill>
                            <span className="text-xs text-slate-400">{item.dateLabel}</span>
                        </div>
                        <p className="mt-3 text-sm font-bold text-slate-950 dark:text-white">{item.title}</p>
                        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">{item.summary}</p>
                    </div>
                ))}
            </div>
        </Surface>
    )
}
```

Create `frontend/components/positions/lifecycle/LifecycleEvidencePanel.tsx` with:

```tsx
import { Banknote, ExternalLink, FileText } from 'lucide-react'
import { StatusPill } from '@/components/ui/StatusPill'
import { Surface } from '@/components/ui/Surface'
import { getLifecycleEvidencePanelSummary, getLifecyclePreviewTrustSummary, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'

interface LifecycleEvidencePanelProps {
    lifecycle: LifecycleDetailViewModel
}

export function LifecycleEvidencePanel({ lifecycle }: LifecycleEvidencePanelProps) {
    const summary = getLifecycleEvidencePanelSummary(lifecycle)

    return (
        <Surface className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-cyan-600" />
                    <h2 className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">Evidence and cash effects</h2>
                </div>
                <StatusPill tone="neutral">{summary.evidenceLabel}</StatusPill>
            </div>
            <div className="mt-5 grid gap-3 md:grid-cols-2">
                {lifecycle.evidenceItems.map((item) => (
                    <a key={`${item.ref_type}-${item.public_id}`} href={item.href} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:bg-white dark:border-slate-800 dark:bg-slate-900/70 dark:hover:bg-slate-900">
                        <div className="flex items-center justify-between gap-3">
                            <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-cyan-700 dark:text-cyan-300">{item.ref_type}</span>
                            <ExternalLink className="h-3.5 w-3.5 text-slate-400" />
                        </div>
                        <p className="mt-2 text-sm font-bold text-slate-950 dark:text-white">{item.label}</p>
                    </a>
                ))}
            </div>
            <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/20">
                <div className="flex items-center gap-2 text-sm font-bold text-amber-900 dark:text-amber-100">
                    <Banknote className="h-4 w-4" />
                    {summary.cashLabel}
                </div>
            </div>
            <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
                {getLifecyclePreviewTrustSummary(lifecycle.trust)}
            </p>
        </Surface>
    )
}
```

Create `frontend/components/positions/lifecycle/LifecycleAiSidecarPanel.tsx` with:

```tsx
import { Brain, ExternalLink } from 'lucide-react'
import { Surface } from '@/components/ui/Surface'
import { getLifecycleAiSidecarSummary, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'

interface LifecycleAiSidecarPanelProps {
    lifecycle: LifecycleDetailViewModel
}

export function LifecycleAiSidecarPanel({ lifecycle }: LifecycleAiSidecarPanelProps) {
    return (
        <Surface className="p-5">
            <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-amber-600" />
                <h2 className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">AI evidence sidecar</h2>
            </div>
            <p className="mt-2 text-xs text-slate-500">{getLifecycleAiSidecarSummary(lifecycle)}</p>
            <div className="mt-5 space-y-3">
                {lifecycle.aiItems.length > 0 ? lifecycle.aiItems.map((item, index) => (
                    <div key={item.insight_artifact_public_id || item.insight_run_public_id || `${item.title}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900/70">
                        <div className="flex items-start justify-between gap-3">
                            <p className="text-sm font-black text-slate-950 dark:text-white">{item.title || 'AI conclusion'}</p>
                            {item.href && <a href={item.href} aria-label="Open insight artifact"><ExternalLink className="h-4 w-4 text-slate-400" /></a>}
                        </div>
                        <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.conclusion || '这条 AI artifact 暂无 conclusion。'}</p>
                    </div>
                )) : (
                    <p className="rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                        暂无 AI sidecar artifact。AI 结论必须通过 evidence-linked artifact 进入这里。
                    </p>
                )}
            </div>
        </Surface>
    )
}
```

- [x] **Step 4: Create the workbench composition component**

Create `frontend/components/positions/lifecycle/LifecycleWorkbench.tsx` with:

```tsx
import { PageFrame } from '@/components/ui/PageFrame'
import {
    getLifecycleLegacyPanelState,
    getLifecyclePrimaryActions,
    getLifecycleReversalAction,
    type LifecycleDetailViewModel,
} from '@/lib/adapters/lifecycle'
import type { PositionViewModel } from '@/lib/adapters/trading'
import { LifecycleActionPanel } from './LifecycleActionPanel'
import { LifecycleAiSidecarPanel } from './LifecycleAiSidecarPanel'
import { LifecycleEventRail } from './LifecycleEventRail'
import { LifecycleEvidencePanel } from './LifecycleEvidencePanel'
import { LifecycleHero } from './LifecycleHero'
import { LifecycleMigrationPanel } from './LifecycleMigrationPanel'
import { LifecycleWorkbenchHeader } from './LifecycleWorkbenchHeader'

interface LifecycleWorkbenchProps {
    lifecycle: LifecycleDetailViewModel
    legacyPosition: PositionViewModel | null
    isReversing: boolean
    onEditNarrative: () => void
    onReverseLatest: () => void
    onManualAdjustment: () => void
}

export function LifecycleWorkbench({
    lifecycle,
    legacyPosition,
    isReversing,
    onEditNarrative,
    onReverseLatest,
    onManualAdjustment,
}: LifecycleWorkbenchProps) {
    const reversal = getLifecycleReversalAction(lifecycle)
    const actions = getLifecyclePrimaryActions({
        hasEditableNarrativeEvent: Boolean(lifecycle.thesisSourceEventPublicId || lifecycle.nodes[0]?.node_public_id),
        reversal,
    })
    const legacyPanel = getLifecycleLegacyPanelState({
        hasTruthLifecycle: true,
        hasLegacyPosition: Boolean(legacyPosition),
    })

    return (
        <PageFrame className="space-y-6 pb-20 md:pb-6">
            <LifecycleWorkbenchHeader lifecycle={lifecycle} />
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
                <div className="space-y-6">
                    <LifecycleHero lifecycle={lifecycle} />
                    <LifecycleActionPanel
                        actions={actions}
                        isReversing={isReversing}
                        onEditNarrative={onEditNarrative}
                        onReverseLatest={onReverseLatest}
                        onManualAdjustment={onManualAdjustment}
                    />
                    <LifecycleEvidencePanel lifecycle={lifecycle} />
                </div>
                <aside className="space-y-6">
                    <LifecycleEventRail lifecycle={lifecycle} />
                    <LifecycleAiSidecarPanel lifecycle={lifecycle} />
                </aside>
            </div>
            {legacyPanel.shouldRender && legacyPosition && (
                <LifecycleMigrationPanel position={legacyPosition} hasTruthLifecycle panel={legacyPanel} />
            )}
        </PageFrame>
    )
}
```

- [x] **Step 5: Create temporary migration panel placeholder for typecheck**

Create `frontend/components/positions/lifecycle/LifecycleMigrationPanel.tsx` with:

```tsx
import { Wrench } from 'lucide-react'
import { Surface } from '@/components/ui/Surface'
import type { LifecycleLegacyPanelState } from '@/lib/adapters/lifecycle'
import type { PositionViewModel } from '@/lib/adapters/trading'

interface LifecycleMigrationPanelProps {
    position: PositionViewModel
    hasTruthLifecycle: boolean
    panel: LifecycleLegacyPanelState
}

export function LifecycleMigrationPanel({ position, panel }: LifecycleMigrationPanelProps) {
    return (
        <Surface className="border-amber-200 bg-amber-50/70 p-5 dark:border-amber-900 dark:bg-amber-950/20">
            <div className="flex items-start gap-3">
                <div className="rounded-2xl bg-amber-100 p-2 text-amber-700 dark:bg-amber-500/15 dark:text-amber-200">
                    <Wrench className="h-5 w-5" />
                </div>
                <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-amber-800 dark:text-amber-200">{panel.title}</p>
                    <p className="mt-2 text-sm leading-6 text-amber-900 dark:text-amber-100">{panel.description}</p>
                    <p className="mt-3 text-xs text-amber-800/80 dark:text-amber-200/80">
                        Loaded legacy position: {position.symbol}
                    </p>
                </div>
            </div>
        </Surface>
    )
}
```

- [x] **Step 6: Temporarily render workbench below existing truth detail to validate imports**

In `frontend/app/positions/[id]/page.tsx`, add this import:

```ts
import { LifecycleWorkbench } from '@/components/positions/lifecycle/LifecycleWorkbench'
```

Temporarily replace the existing `<TruthLifecycleDetail lifecycle={truthLifecycle} />` block with:

```tsx
<LifecycleWorkbench
    lifecycle={truthLifecycle}
    legacyPosition={position}
    isReversing={isReversingTruthEvent}
    onEditNarrative={openTruthNarrativeModal}
    onReverseLatest={handleReverseLatestTruthEvent}
    onManualAdjustment={openManualAdjustmentModal}
/>
```

Remove the old `TruthLifecycleDetail` import if it becomes unused.

- [x] **Step 7: Run TypeScript check**

Run:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected: PASS, or only type errors that point to props/import typos in the new workbench components. Fix those typos before continuing.

- [x] **Step 8: Commit truth workbench scaffold**

Run:

```bash
git add frontend/app/positions/[id]/page.tsx frontend/components/positions/lifecycle docs/superpowers/plans/2026-06-09-dev-p9c-lifecycle-detail-workbench-plan.md
git commit -m "feat: add lifecycle workbench shell"
```

Expected: commit succeeds with scaffold components and page import/render wiring.

---

### Task 3: Move Legacy Sections Into Migration Panel

**Files:**
- Modify: `frontend/components/positions/lifecycle/LifecycleMigrationPanel.tsx`
- Modify: `frontend/app/positions/[id]/page.tsx`

- [x] **Step 1: Expand migration panel props**

Replace `LifecycleMigrationPanelProps` in `frontend/components/positions/lifecycle/LifecycleMigrationPanel.tsx` with:

```tsx
interface LifecycleMigrationPanelProps {
    position: PositionViewModel
    hasTruthLifecycle: boolean
    panel: LifecycleLegacyPanelState
    sortedBatches: TradeBatchViewModel[]
    isAnalyzing: boolean
    legacyBatchMutationState: ReturnType<typeof getLegacyBatchMutationState>
    legacyReviewDisplayState: ReturnType<typeof getLegacyReviewDisplayState>
    onEditMetadata: () => void
    onEditExtremes: () => void
    onAnalyze: () => void
    onEditBatch: (batch: TradeBatchViewModel) => void
}
```

Add these imports:

```tsx
import {
    ArrowDownCircle,
    ArrowUpCircle,
    Award,
    Calendar,
    Edit3,
    Loader2,
    MessageSquare,
    Target,
    TrendingUp,
    Wrench,
} from 'lucide-react'
import {
    getCoreTypeLabel,
    getCurrencySymbol,
    getMarketLabel,
    getRiskLevelInfo,
    type AssetCoreType,
    type AssetMarket,
    type AssetRiskLevel,
} from '@/lib/symbolUtils'
import {
    getLegacyBatchMutationState,
    getLegacyReviewDisplayState,
    type TradeBatchViewModel,
} from '@/lib/adapters/trading'
```

- [x] **Step 2: Move legacy summary and metadata cards**

In `LifecycleMigrationPanel`, replace the placeholder body with the summary and metadata JSX currently in `frontend/app/positions/[id]/page.tsx` under:

```tsx
{/* Summary Card */}
{/* Metadata Card */}
```

Wrap them inside:

```tsx
<div className="mt-5 space-y-5">
    {/* moved summary card */}
    {/* moved metadata card */}
</div>
```

When moving the metadata edit button, call `onEditMetadata` instead of `openMetadataModal`.

- [x] **Step 3: Move MAE/MFE, drift, and checklist sections**

Move these existing sections from `frontend/app/positions/[id]/page.tsx` into `LifecycleMigrationPanel` after metadata:

```tsx
{/* Price Extremes & MAE/MFE Card */}
{/* Phase 1: Plan Drift Analysis Card */}
{/* Phase 1: Checklist Responses Card */}
```

Change the MAE/MFE edit button body to call `onEditExtremes`.

Change the analysis button body to call `onAnalyze` and use the `isAnalyzing` prop.

- [x] **Step 4: Move batch records, legacy review, and lessons**

Move these existing sections from `frontend/app/positions/[id]/page.tsx` into `LifecycleMigrationPanel` after checklist:

```tsx
{/* Trade Batches */}
{/* Review Section */}
{/* Lessons */}
```

Change edit batch action from:

```tsx
onClick={() => openEditModal(batch)}
```

to:

```tsx
onClick={() => onEditBatch(batch)}
```

Keep `legacyBatchMutationState` and `legacyReviewDisplayState` props as the source of migration-only labels.

- [x] **Step 5: Pass migration props from LifecycleWorkbench**

Update `LifecycleWorkbenchProps` in `frontend/components/positions/lifecycle/LifecycleWorkbench.tsx` with:

```tsx
import {
    getLegacyBatchMutationState,
    getLegacyReviewDisplayState,
    type TradeBatchViewModel,
} from '@/lib/adapters/trading'

interface LifecycleWorkbenchProps {
    lifecycle: LifecycleDetailViewModel
    legacyPosition: PositionViewModel | null
    sortedBatches: TradeBatchViewModel[]
    isAnalyzing: boolean
    isReversing: boolean
    onEditNarrative: () => void
    onReverseLatest: () => void
    onManualAdjustment: () => void
    onEditMetadata: () => void
    onEditExtremes: () => void
    onAnalyze: () => void
    onEditBatch: (batch: TradeBatchViewModel) => void
}
```

Inside `LifecycleWorkbench`, derive:

```tsx
const legacyBatchMutationState = getLegacyBatchMutationState(Boolean(lifecycle))
const legacyReviewDisplayState = getLegacyReviewDisplayState(Boolean(lifecycle), Boolean(legacyPosition?.trade_review))
```

Pass the new props to `LifecycleMigrationPanel`:

```tsx
<LifecycleMigrationPanel
    position={legacyPosition}
    hasTruthLifecycle
    panel={legacyPanel}
    sortedBatches={sortedBatches}
    isAnalyzing={isAnalyzing}
    legacyBatchMutationState={legacyBatchMutationState}
    legacyReviewDisplayState={legacyReviewDisplayState}
    onEditMetadata={onEditMetadata}
    onEditExtremes={onEditExtremes}
    onAnalyze={onAnalyze}
    onEditBatch={onEditBatch}
/>
```

- [x] **Step 6: Remove moved legacy JSX from page**

Delete the moved sections from `frontend/app/positions/[id]/page.tsx`:

```tsx
{/* Summary Card */}
{/* Metadata Card */}
{/* Price Extremes & MAE/MFE Card */}
{/* Phase 1: Plan Drift Analysis Card */}
{/* Phase 1: Checklist Responses Card */}
{/* Trade Batches */}
{/* Review Section */}
{/* Lessons */}
```

Keep the edit batch, metadata, extremes, truth narrative, and manual adjustment modals in the page for now.

- [x] **Step 7: Update workbench invocation in page**

In `frontend/app/positions/[id]/page.tsx`, pass the new props:

```tsx
<LifecycleWorkbench
    lifecycle={truthLifecycle}
    legacyPosition={position}
    sortedBatches={sortedBatches}
    isAnalyzing={isAnalyzing}
    isReversing={isReversingTruthEvent}
    onEditNarrative={openTruthNarrativeModal}
    onReverseLatest={handleReverseLatestTruthEvent}
    onManualAdjustment={openManualAdjustmentModal}
    onEditMetadata={openMetadataModal}
    onEditExtremes={() => {
        if (!position) return
        setExtremesForm({
            max_price: Number(position.max_price_during_hold || 0),
            min_price: Number(position.min_price_during_hold || 0),
        })
        setEditingExtremes(true)
    }}
    onAnalyze={handleAnalyze}
    onEditBatch={openEditModal}
/>
```

- [x] **Step 8: Run TypeScript check**

Run:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected: PASS. If unused imports remain in `frontend/app/positions/[id]/page.tsx`, remove only the imports no longer referenced.

- [x] **Step 9: Commit migration panel extraction**

Run:

```bash
git add frontend/app/positions/[id]/page.tsx frontend/components/positions/lifecycle/LifecycleMigrationPanel.tsx frontend/components/positions/lifecycle/LifecycleWorkbench.tsx docs/superpowers/plans/2026-06-09-dev-p9c-lifecycle-detail-workbench-plan.md
git commit -m "feat: isolate lifecycle legacy migration tools"
```

Expected: commit succeeds with legacy sections moved into `LifecycleMigrationPanel`.

---

### Task 4: Move Truth Modals And Finish Page Shell Reduction

**Files:**
- Create: `frontend/components/positions/lifecycle/LifecycleModals.tsx`
- Modify: `frontend/app/positions/[id]/page.tsx`
- Modify: `frontend/components/positions/lifecycle/LifecycleWorkbench.tsx`

- [x] **Step 1: Create modal props and component**

Create `frontend/components/positions/lifecycle/LifecycleModals.tsx` with:

```tsx
import { Loader2, Plus } from 'lucide-react'
import DateTimePicker from '@/components/DateTimePicker'
import type { LifecycleNarrativeDraft } from '@/lib/adapters/lifecycle'

interface LifecycleModalsProps {
    editingTruthNarrative: boolean
    isSavingTruthNarrative: boolean
    truthNarrativeForm: LifecycleNarrativeDraft
    onChangeTruthNarrativeForm: (form: LifecycleNarrativeDraft) => void
    onCloseTruthNarrative: () => void
    onSaveTruthNarrative: () => void
    editingManualAdjustment: boolean
    isSavingManualAdjustment: boolean
    manualAdjustmentForm: {
        amount: number
        currency: string
        occurred_at: string
        note: string
    }
    onChangeManualAdjustmentForm: (form: LifecycleModalsProps['manualAdjustmentForm']) => void
    onCloseManualAdjustment: () => void
    onSaveManualAdjustment: () => void
}

export function LifecycleModals(props: LifecycleModalsProps) {
    return (
        <>
            {props.editingTruthNarrative && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
                    <div className="card max-h-[90vh] w-full max-w-2xl overflow-y-auto shadow-2xl animate-in zoom-in duration-200">
                        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-start justify-between gap-4">
                            <div>
                                <p className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-600 dark:text-cyan-300">PositionEvent narrative</p>
                                <h3 className="mt-1 text-lg font-bold">编辑 truth 叙事字段</h3>
                                <p className="mt-1 text-xs text-slate-500">Event public_id: {props.truthNarrativeForm.eventPublicId}</p>
                            </div>
                            <button onClick={props.onCloseTruthNarrative} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors">
                                <Plus className="w-5 h-5 rotate-45" />
                            </button>
                        </div>
                        <div className="p-6 space-y-4">
                            <textarea value={props.truthNarrativeForm.reason} onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, reason: event.target.value })} className="input min-h-[80px]" placeholder="这一步为什么发生？" />
                            <textarea value={props.truthNarrativeForm.thesis} onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, thesis: event.target.value })} className="input min-h-[90px]" placeholder="这笔交易的核心假设是什么？" />
                            <div className="grid gap-4 md:grid-cols-2">
                                <textarea value={props.truthNarrativeForm.invalidationRule} onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, invalidationRule: event.target.value })} className="input min-h-[80px]" placeholder="什么情况说明交易假设失效？" />
                                <textarea value={props.truthNarrativeForm.plannedExitRule} onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, plannedExitRule: event.target.value })} className="input min-h-[80px]" placeholder="计划如何退出？" />
                            </div>
                            <textarea value={props.truthNarrativeForm.sizingRationale} onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, sizingRationale: event.target.value })} className="input min-h-[80px]" placeholder="为什么是这个仓位？" />
                            <input value={props.truthNarrativeForm.emotion} onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, emotion: event.target.value })} className="input" placeholder="Focused, Calm..." />
                            <input type="range" min="1" max="5" value={props.truthNarrativeForm.confidence} onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, confidence: parseInt(event.target.value) })} className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-cyan-500" />
                            <textarea value={props.truthNarrativeForm.note} onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, note: event.target.value })} className="input min-h-[70px]" placeholder="补充备注" />
                        </div>
                        <div className="p-6 border-t border-slate-100 dark:border-slate-800 flex justify-end space-x-3">
                            <button onClick={props.onCloseTruthNarrative} className="btn btn-secondary">取消</button>
                            <button onClick={props.onSaveTruthNarrative} disabled={props.isSavingTruthNarrative} className="btn btn-primary flex items-center space-x-2">
                                {props.isSavingTruthNarrative && <Loader2 className="w-4 h-4 animate-spin" />}
                                <span>保存到 truth event</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {props.editingManualAdjustment && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-sm">
                    <div className="card w-full max-w-lg shadow-2xl animate-in zoom-in duration-200">
                        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-start justify-between gap-4">
                            <div>
                                <p className="text-xs font-bold uppercase tracking-[0.18em] text-amber-600 dark:text-amber-300">PositionEvent adjustment</p>
                                <h3 className="mt-1 text-lg font-bold">记录 cash adjustment</h3>
                                <p className="mt-1 text-xs text-slate-500">只写入 MANUAL_ADJUSTMENT event 和 CASH_ADJUSTMENT ledger，不修改 FIFO 数量或 realized PnL。</p>
                            </div>
                            <button onClick={props.onCloseManualAdjustment} className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors">
                                <Plus className="w-5 h-5 rotate-45" />
                            </button>
                        </div>
                        <div className="p-6 space-y-4">
                            <div className="grid gap-4 md:grid-cols-[1fr_120px]">
                                <input type="number" step="any" value={props.manualAdjustmentForm.amount} onChange={(event) => props.onChangeManualAdjustmentForm({ ...props.manualAdjustmentForm, amount: Number(event.target.value) })} className="input" placeholder="-7.25" />
                                <input value={props.manualAdjustmentForm.currency} onChange={(event) => props.onChangeManualAdjustmentForm({ ...props.manualAdjustmentForm, currency: event.target.value.toUpperCase() })} className="input" placeholder="USD" />
                            </div>
                            <DateTimePicker value={props.manualAdjustmentForm.occurred_at} onChange={(value) => props.onChangeManualAdjustmentForm({ ...props.manualAdjustmentForm, occurred_at: value })} />
                            <textarea value={props.manualAdjustmentForm.note} onChange={(event) => props.onChangeManualAdjustmentForm({ ...props.manualAdjustmentForm, note: event.target.value })} className="input min-h-[90px]" placeholder="Broker cash correction / fee rebate / reconciliation adjustment" />
                        </div>
                        <div className="p-6 border-t border-slate-100 dark:border-slate-800 flex justify-end space-x-3">
                            <button onClick={props.onCloseManualAdjustment} className="btn btn-secondary">取消</button>
                            <button onClick={props.onSaveManualAdjustment} disabled={props.isSavingManualAdjustment} className="btn btn-primary flex items-center space-x-2">
                                {props.isSavingManualAdjustment && <Loader2 className="w-4 h-4 animate-spin" />}
                                <span>保存 adjustment</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
```

- [x] **Step 2: Render truth modals from page via component**

In `frontend/app/positions/[id]/page.tsx`, add:

```ts
import { LifecycleModals } from '@/components/positions/lifecycle/LifecycleModals'
```

Replace the existing `editingTruthNarrative` and `editingManualAdjustment` modal JSX blocks with:

```tsx
<LifecycleModals
    editingTruthNarrative={editingTruthNarrative}
    isSavingTruthNarrative={isSavingTruthNarrative}
    truthNarrativeForm={truthNarrativeForm}
    onChangeTruthNarrativeForm={setTruthNarrativeForm}
    onCloseTruthNarrative={() => setEditingTruthNarrative(false)}
    onSaveTruthNarrative={handleUpdateTruthNarrative}
    editingManualAdjustment={editingManualAdjustment}
    isSavingManualAdjustment={isSavingManualAdjustment}
    manualAdjustmentForm={manualAdjustmentForm}
    onChangeManualAdjustmentForm={setManualAdjustmentForm}
    onCloseManualAdjustment={() => setEditingManualAdjustment(false)}
    onSaveManualAdjustment={handleCreateManualAdjustment}
/>
```

- [x] **Step 3: Remove old truth write banner from page**

Delete the old inline block headed by:

```tsx
叙事字段现在写入 TradingPosition / PositionEvent
```

The new `LifecycleActionPanel` now owns this message and the three truth actions.

- [x] **Step 4: Keep legacy-only fallback but label it**

When `!truthLifecycle && position`, keep a simple legacy fallback wrapper in `frontend/app/positions/[id]/page.tsx`:

```tsx
<div className="card border-amber-200 bg-amber-50 p-5 text-sm text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-100">
    Truth lifecycle is unavailable, so this page is showing legacy Position / TradeBatch data.
</div>
```

Then render the remaining legacy fallback sections below it. Do not make fallback prettier than the truth workbench.

- [x] **Step 5: Run TypeScript and lint**

Run:

```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
```

Expected: TypeScript PASS. Lint PASS with only existing repository warnings.

- [x] **Step 6: Commit page shell reduction**

Run:

```bash
git add frontend/app/positions/[id]/page.tsx frontend/components/positions/lifecycle/LifecycleModals.tsx docs/superpowers/plans/2026-06-09-dev-p9c-lifecycle-detail-workbench-plan.md
git commit -m "feat: reduce lifecycle detail page shell"
```

Expected: commit succeeds.

---

### Task 5: Verification, Browser Smoke, And Plan Closure

**Files:**
- Modify: `docs/superpowers/plans/2026-06-09-dev-p9c-lifecycle-detail-workbench-plan.md`

- [ ] **Step 1: Run targeted lifecycle adapter test**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/lifecycle-adapter.test.mts
```

Expected: PASS.

- [ ] **Step 2: Run all frontend adapter tests**

Run:

```bash
cd frontend
node --experimental-strip-types --test tests/*.test.mts
```

Expected: PASS.

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

Expected: PASS with no new errors. Existing warnings are acceptable only if they predate P9C.

- [ ] **Step 5: Run production build**

Run:

```bash
cd frontend
npm run build
```

Expected: PASS and route list includes `/positions/[id]`.

- [ ] **Step 6: Browser smoke desktop and mobile**

Start the local backend/frontend the same way P9B smoke did, using a temporary backend DB outside the repo. Then verify:

```text
Desktop /positions/[public_id]
- Lifecycle Command Center header is visible.
- Hero appears before migration tools.
- Edit narrative, reverse latest truth event, and cash adjustment actions are visible.
- Event spine and AI sidecar are in the right rail.
- Legacy migration tools are amber/lower hierarchy.

Mobile 390x844 /positions/[public_id]
- Header, hero, actions, event spine, AI/evidence/cash, migration tools appear in one-column order.
- Primary truth actions are not hidden below legacy data.
```

Expected: smoke passes or any blocker is recorded with exact failing route and visible symptom.

- [ ] **Step 7: Restore generated files before committing**

Run:

```bash
git restore frontend/next-env.d.ts frontend/tsconfig.tsbuildinfo
```

Expected: generated files are not staged. If either file is absent from git status, continue.

- [ ] **Step 8: Record verification evidence in this plan**

Append a `## Verification Evidence` section to this file with exact commands run and outcomes:

```markdown
## Verification Evidence

- `node --experimental-strip-types --test tests/lifecycle-adapter.test.mts`: PASS
- `node --experimental-strip-types --test tests/*.test.mts`: PASS
- `./node_modules/.bin/tsc --noEmit --pretty false`: PASS
- `npm run lint`: PASS, with existing warnings only
- `npm run build`: PASS
- Browser smoke desktop `/positions/[public_id]`: PASS
- Browser smoke mobile 390x844 `/positions/[public_id]`: PASS
```

- [ ] **Step 9: Commit plan closure**

Run:

```bash
git add docs/superpowers/plans/2026-06-09-dev-p9c-lifecycle-detail-workbench-plan.md
git commit -m "docs: close p9c lifecycle workbench plan"
```

Expected: commit succeeds with verification evidence and checked-off tasks.

- [ ] **Step 10: Push dev**

Run:

```bash
git push origin dev
```

Expected: push succeeds. Do not create a PR unless explicitly requested.

---

## Self-Review Checklist

- Spec coverage: Tasks cover adapter helpers, lifecycle workbench components, page shell reduction, legacy migration isolation, truth write action preservation, testing, browser smoke, and `docs/superpowers/demos/` non-interference.
- Backend boundary: No task changes backend lifecycle or legacy bridge contracts.
- Test-first: Task 1 writes failing helper tests before implementation.
- Component boundary: New lifecycle components live under `frontend/components/positions/lifecycle/`.
- Verification coverage: Task 5 covers targeted tests, all adapter tests, TypeScript, lint, build, and desktop/mobile browser smoke.
