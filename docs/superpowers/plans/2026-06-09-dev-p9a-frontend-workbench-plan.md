# Dev P9A Frontend Workbench Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rework the default Timeline home into a balanced decision workbench and establish the frontend UI foundation needed for subsequent page rewrites.

**Architecture:** Keep current backend/read-model contracts unchanged. Add small tested frontend helpers, introduce reusable UI primitives, split Timeline workbench composition into focused components, and only harden React 19 lint rules for files touched by P9A.

**Tech Stack:** Next.js 16, React 19, TypeScript, App Router, Tailwind CSS, React Query, Node test runner, ESLint CLI

---

## Source Design

- Design spec: `docs/superpowers/specs/2026-06-09-p9a-frontend-workbench-design.md`
- Existing frontend redesign spec: `docs/superpowers/specs/2026-04-07-frontend-experience-redesign-design.md`
- Existing Timeline contract: `docs/superpowers/specs/2026-04-13-timeline-review-inbox-contract.md`
- Current checkpoint: `docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md`

## Execution Rules

- Work on `dev`.
- Do not create a PR unless explicitly requested.
- Do not modify or remove `docs/superpowers/demos/`.
- Do not change backend API contracts in P9A.
- Do not rewrite Dashboard, lifecycle detail, positions, strategies, insights list, or settings pages in P9A.
- Do not expand `frontend/lib/api.ts` as part of this work unless TypeScript forces an import-only change.
- Use TDD for pure behavior helpers.
- Restore generated noise such as `frontend/next-env.d.ts` and `frontend/tsconfig.tsbuildinfo` before committing.
- If visual scope starts touching more than Timeline/nav/UI primitives, stop and record the proposed expansion before editing more files.

## File Map

### Create

- `frontend/lib/adapters/timeline-workbench.ts`
  - Pure formatting and tone helpers for the new Timeline workbench.
- `frontend/lib/navigation.ts`
  - Product nav item definitions, admin separation, and active-state helpers.
- `frontend/components/ui/PageFrame.tsx`
  - Page-level shell and section spacing.
- `frontend/components/ui/Surface.tsx`
  - Shared surface/panel variants.
- `frontend/components/ui/SectionHeader.tsx`
  - Shared section title/subtitle/action header.
- `frontend/components/ui/MetricTile.tsx`
  - Compact metric display for summary strips.
- `frontend/components/ui/StatusPill.tsx`
  - Generic status/freshness/severity pill.
- `frontend/components/ui/EmptyStatePanel.tsx`
  - Shared loading/empty/error panel.
- `frontend/components/navigation/ProductTopNav.tsx`
  - Desktop top navigation.
- `frontend/components/navigation/MobileBottomNav.tsx`
  - Mobile bottom navigation.
- `frontend/components/timeline/workbench/TimelineWorkbench.tsx`
  - Top-level loaded Timeline workbench composition.
- `frontend/components/timeline/workbench/TimelineWorkbenchHeader.tsx`
  - Title, as-of status, trust, refresh.
- `frontend/components/timeline/workbench/TimelineViewTabs.tsx`
  - Timeline view filter control.
- `frontend/components/timeline/workbench/TimelineFeedPanel.tsx`
  - Grouped feed panel and empty state.
- `frontend/components/timeline/workbench/TimelineEventCardV2.tsx`
  - Redesigned event card with progressive disclosure.
- `frontend/components/timeline/workbench/ReviewInboxPanel.tsx`
  - Review Inbox action rail.
- `frontend/components/timeline/workbench/TimelineDecisionRail.tsx`
  - Desktop rail and mobile secondary sections.
- `frontend/tests/timeline-workbench.test.mts`
  - Tests for new Timeline workbench helpers.
- `frontend/tests/navigation.test.mts`
  - Tests for nav helper behavior.

### Modify

- `frontend/app/timeline/page.tsx`
  - Reduce to data loading, view state, and workbench orchestration.
- `frontend/app/globals.css`
  - Add scoped P9A app-shell/surface tokens for the Timeline workbench.
- `frontend/components/Navbar.tsx`
  - Keep as public wrapper; delegate to navigation components.
- `frontend/eslint.config.mjs`
  - Keep global deferral for broad React 19 rules; do not remove until global cleanup stage.
- `docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md`
  - Record P9A completion after implementation.
- `docs/superpowers/plans/2026-06-09-dev-p9a-frontend-workbench-plan.md`
  - Track execution notes and verification.

### Inspect

- `frontend/components/timeline/FreshnessPill.tsx`
- `frontend/components/timeline/TimelineSummaryStrip.tsx`
- `frontend/components/timeline/TimelineEventCard.tsx`
- `frontend/components/timeline/ReviewInboxCard.tsx`

These legacy Timeline components should be deleted only if `rg` proves there are no remaining references outside the files themselves.

### Test/Verify

- `frontend/tests/timeline-adapter.test.mts`
- `frontend/tests/timeline-workbench.test.mts`
- `frontend/tests/navigation.test.mts`
- Full frontend test suite
- TypeScript
- ESLint
- Next build
- Backend smoke
- Alembic smoke

---

### Task 1: Baseline Current P9A State

**Files:**
- Modify: `docs/superpowers/plans/2026-06-09-dev-p9a-frontend-workbench-plan.md`
- Test/verify: `frontend`

- [x] **Step 1: Verify branch and working tree**

Run:
```bash
git status --short --branch
git log --oneline -5
```

Expected:
```text
Branch is dev...origin/dev.
Only docs/superpowers/demos/ may appear as untracked user content.
Recent history includes a96c4ed docs: record dev p8 next 16 upgrade.
```

- [x] **Step 2: Capture current frontend verification**

Run:
```bash
cd frontend
npm audit --json
node --experimental-strip-types --test tests/*.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
npm run build
```

Expected:
```text
npm audit reports 0 vulnerabilities.
Node tests pass.
TypeScript exits 0.
Lint exits 0, allowing existing warnings.
Next build exits 0 and includes /timeline.
```

If `npm audit` fails because the sandbox cannot resolve `registry.npmjs.org`, rerun it with network approval and record that reason in this plan.

- [x] **Step 3: Capture existing strict React 19 lint baseline for likely touched files**

Run:
```bash
cd frontend
./node_modules/.bin/eslint app/timeline/page.tsx components/Navbar.tsx components/ThemeToggle.tsx components/timeline/FreshnessPill.tsx components/timeline/ReviewInboxCard.tsx components/timeline/TimelineContextRail.tsx components/timeline/TimelineEventCard.tsx components/timeline/TimelineSummaryStrip.tsx --rule 'react-hooks/purity:error' --rule 'react-hooks/set-state-in-effect:error'
```

Expected:
```text
The command may fail before P9A because Navbar/ThemeToggle currently use mounted state effects.
Record exact files and rules. These are the touched-file hardening targets, not global blockers.
```

- [x] **Step 4: Record baseline notes in this plan**

Add an `Execution note` under Task 1 with:
```text
Audit result.
Node test count.
TypeScript result.
Lint result and warning count.
Build result.
Strict React 19 touched-file lint findings.
```

Execution note:

- `git status --short --branch`: `dev...origin/dev`, with only `docs/superpowers/demos/` untracked.
- Recent history includes `6d4ccd1 docs: add dev p9a frontend workbench plan` and `a96c4ed docs: record dev p8 next 16 upgrade`.
- `npm audit --json` in sandbox failed on DNS resolution for `registry.npmjs.org`; rerun with network approval reported 0 vulnerabilities.
- `node --experimental-strip-types --test tests/*.test.mts`: 41 tests passed, 0 failed.
- `./node_modules/.bin/tsc --noEmit --pretty false`: exited 0.
- `npm run lint`: exited 0 with 6 existing warnings.
- `npm run build`: exited 0 on Next 16.2.7 and output included `/timeline`.
- The original targeted lint command shape using `npm run lint -- ...files` is invalid for this repo because the script is `eslint .`, so it scans the whole frontend. The plan now uses `./node_modules/.bin/eslint <files> --rule ...` for true targeted strict lint.
- Corrected strict React 19 touched-file baseline: 2 errors from `components/Navbar.tsx` and `components/ThemeToggle.tsx` for `react-hooks/set-state-in-effect`, plus 1 `@next/next/no-img-element` warning in `Navbar`.

- [ ] **Step 5: Commit baseline notes**

Run:
```bash
git add docs/superpowers/plans/2026-06-09-dev-p9a-frontend-workbench-plan.md
git commit -m "docs: record p9a frontend baseline"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 2: Add Timeline Workbench Pure Helpers

**Files:**
- Create: `frontend/tests/timeline-workbench.test.mts`
- Create: `frontend/lib/adapters/timeline-workbench.ts`

- [x] **Step 1: Add failing tests for summary metric formatting and tones**

Create `frontend/tests/timeline-workbench.test.mts`:
```ts
import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildTimelineSummaryMetrics,
  formatTimelineEventImpact,
  formatTimelineEventMeta,
  getTimelineEventTone,
  getWorkbenchMobileSectionOrder,
} from '../lib/adapters/timeline-workbench.ts'
import type { TimelineHomeViewModel } from '../lib/adapters/timeline.ts'
import type { SummaryBar, TimelineEventCard } from '../lib/read-models.ts'

const summaryBar: SummaryBar = {
  period_label: 'This week',
  trade_count: 7,
  review_completion_rate: 0.625,
  net_equity_change: -1234.56,
  priority_alert_count: 2,
  trust: {
    as_of: '2026-06-09T09:00:00Z',
    freshness: 'FRESH',
    source: 'DERIVED',
    value_status: 'ESTIMATED',
  },
}

const event: TimelineEventCard = {
  event_public_id: 'event-1',
  thread_public_id: 'position-1',
  event_type: 'REDUCE',
  occurred_at: '2026-06-09T08:30:00Z',
  headline: 'Reduced NVDA',
  summary: 'Trimmed the position after plan drift.',
  impact_value: {
    amount: -245.5,
    currency: 'USD',
  },
  instrument: {
    asset_label: 'NVIDIA',
    instrument_label: 'Common Stock',
    symbol: 'NVDA',
    href: '/positions/position-1',
  },
  account: {
    public_id: 'account-1',
    label: 'IBKR',
  },
  href: '/positions/position-1',
}

test('buildTimelineSummaryMetrics formats the four workbench metrics', () => {
  assert.deepEqual(buildTimelineSummaryMetrics(summaryBar), [
    { key: 'trades', label: '交易', value: '7', detail: 'This week', tone: 'neutral' },
    { key: 'review_rate', label: '复盘完成', value: '63%', detail: '纪律覆盖率', tone: 'positive' },
    { key: 'equity_change', label: '净值变化', value: '-1,234.56', detail: '估算', tone: 'negative' },
    { key: 'alerts', label: '重点提醒', value: '2', detail: '需要处理', tone: 'warning' },
  ])
})

test('formatTimelineEventImpact returns signed amount labels and tones', () => {
  assert.deepEqual(formatTimelineEventImpact(event), {
    label: '-245.5 USD',
    tone: 'negative',
  })
  assert.equal(formatTimelineEventImpact({ ...event, impact_value: undefined }), null)
})

test('formatTimelineEventMeta joins symbol, account, and zh-CN timestamp', () => {
  assert.match(formatTimelineEventMeta(event), /^NVDA · IBKR · /)
})

test('getTimelineEventTone maps trade, review, AI, and exception events', () => {
  assert.equal(getTimelineEventTone('OPEN'), 'entry')
  assert.equal(getTimelineEventTone('REVIEW_COMPLETED'), 'review')
  assert.equal(getTimelineEventTone('AI_INSIGHT'), 'ai')
  assert.equal(getTimelineEventTone('SYNC_EXCEPTION'), 'danger')
})

test('getWorkbenchMobileSectionOrder puts actionable review inbox before feed', () => {
  const withReview = {
    reviewInbox: { total: 2, highPriority: 1 },
  } as TimelineHomeViewModel
  const withoutReview = {
    reviewInbox: { total: 0, highPriority: 0 },
  } as TimelineHomeViewModel

  assert.deepEqual(getWorkbenchMobileSectionOrder(withReview), ['summary', 'filters', 'review', 'timeline', 'context'])
  assert.deepEqual(getWorkbenchMobileSectionOrder(withoutReview), ['summary', 'filters', 'timeline', 'context'])
})
```

- [x] **Step 2: Run the new test to verify RED**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/timeline-workbench.test.mts
```

Expected:
```text
FAIL because ../lib/adapters/timeline-workbench.ts does not exist.
```

- [x] **Step 3: Implement timeline workbench helpers**

Create `frontend/lib/adapters/timeline-workbench.ts`:
```ts
import type { SummaryBar, TimelineEventCard, TimelineEventType } from '../read-models.ts'
import type { TimelineHomeViewModel } from './timeline.ts'

export type WorkbenchTone = 'neutral' | 'positive' | 'negative' | 'warning' | 'danger' | 'entry' | 'exit' | 'review' | 'ai'

export interface TimelineSummaryMetric {
    key: 'trades' | 'review_rate' | 'equity_change' | 'alerts'
    label: string
    value: string
    detail: string
    tone: WorkbenchTone
}

export interface TimelineImpactLabel {
    label: string
    tone: WorkbenchTone
}

export type MobileWorkbenchSection = 'summary' | 'filters' | 'review' | 'timeline' | 'context'

export function buildTimelineSummaryMetrics(summaryBar: SummaryBar): TimelineSummaryMetric[] {
    const reviewRate = summaryBar.review_completion_rate === null
        ? '-'
        : `${Math.round(summaryBar.review_completion_rate * 100)}%`
    const equityChange = summaryBar.net_equity_change === null
        ? '-'
        : summaryBar.net_equity_change.toLocaleString(undefined, { maximumFractionDigits: 2 })
    const equityTone: WorkbenchTone = summaryBar.net_equity_change === null
        ? 'neutral'
        : summaryBar.net_equity_change < 0
            ? 'negative'
            : 'positive'

    return [
        {
            key: 'trades',
            label: '交易',
            value: String(summaryBar.trade_count),
            detail: summaryBar.period_label,
            tone: 'neutral',
        },
        {
            key: 'review_rate',
            label: '复盘完成',
            value: reviewRate,
            detail: '纪律覆盖率',
            tone: summaryBar.review_completion_rate !== null && summaryBar.review_completion_rate >= 0.6
                ? 'positive'
                : 'warning',
        },
        {
            key: 'equity_change',
            label: '净值变化',
            value: equityChange,
            detail: summaryBar.trust?.value_status === 'ESTIMATED' ? '估算' : '最终',
            tone: equityTone,
        },
        {
            key: 'alerts',
            label: '重点提醒',
            value: String(summaryBar.priority_alert_count),
            detail: summaryBar.priority_alert_count > 0 ? '需要处理' : '无待办',
            tone: summaryBar.priority_alert_count > 0 ? 'warning' : 'positive',
        },
    ]
}

export function formatTimelineEventImpact(event: TimelineEventCard): TimelineImpactLabel | null {
    const amount = event.impact_value?.amount
    if (amount === undefined) return null
    const currency = event.impact_value?.currency ? ` ${event.impact_value.currency}` : ''
    const sign = amount > 0 ? '+' : ''
    return {
        label: `${sign}${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}${currency}`,
        tone: amount < 0 ? 'negative' : 'positive',
    }
}

export function formatTimelineEventMeta(event: TimelineEventCard): string {
    const pieces = [event.instrument.symbol]
    if (event.account?.label) pieces.push(event.account.label)
    pieces.push(new Date(event.occurred_at).toLocaleString('zh-CN'))
    return pieces.join(' · ')
}

export function getTimelineEventTone(eventType: TimelineEventType): WorkbenchTone {
    switch (eventType) {
        case 'OPEN':
        case 'ADD':
            return 'entry'
        case 'REDUCE':
        case 'CLOSE':
            return 'exit'
        case 'REVIEW_COMPLETED':
            return 'review'
        case 'AI_INSIGHT':
            return 'ai'
        case 'CHECKLIST_MISS':
        case 'LOSING_STREAK_ALERT':
        case 'DATA_STALE':
        case 'SYNC_EXCEPTION':
            return 'danger'
        default:
            return 'neutral'
    }
}

export function getWorkbenchMobileSectionOrder(timelineHome: Pick<TimelineHomeViewModel, 'reviewInbox'>): MobileWorkbenchSection[] {
    if (timelineHome.reviewInbox.total > 0) {
        return ['summary', 'filters', 'review', 'timeline', 'context']
    }
    return ['summary', 'filters', 'timeline', 'context']
}
```

- [x] **Step 4: Run helper tests to verify GREEN**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/timeline-workbench.test.mts
```

Expected:
```text
All tests in timeline-workbench.test.mts pass.
```

- [x] **Step 5: Run existing Timeline adapter tests**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/timeline-adapter.test.mts tests/timeline-workbench.test.mts
```

Expected:
```text
Existing Timeline adapter tests and new workbench helper tests pass.
```

Execution note:

- RED verified: `node --experimental-strip-types --test tests/timeline-workbench.test.mts` failed with `ERR_MODULE_NOT_FOUND` for `frontend/lib/adapters/timeline-workbench.ts`.
- GREEN verified: `tests/timeline-workbench.test.mts` passed 5 tests.
- Focused regression verified: `tests/timeline-adapter.test.mts tests/timeline-workbench.test.mts` passed 11 tests.

- [ ] **Step 6: Commit helper foundation**

Run:
```bash
git add frontend/lib/adapters/timeline-workbench.ts frontend/tests/timeline-workbench.test.mts
git commit -m "feat: add timeline workbench view helpers"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 3: Add Design-System UI Primitives

**Files:**
- Create: `frontend/components/ui/PageFrame.tsx`
- Create: `frontend/components/ui/Surface.tsx`
- Create: `frontend/components/ui/SectionHeader.tsx`
- Create: `frontend/components/ui/MetricTile.tsx`
- Create: `frontend/components/ui/StatusPill.tsx`
- Create: `frontend/components/ui/EmptyStatePanel.tsx`
- Modify: `frontend/app/globals.css`

- [x] **Step 1: Create `Surface` primitive**

Create `frontend/components/ui/Surface.tsx`:
```tsx
import type { ReactNode } from 'react'

type SurfaceVariant = 'panel' | 'rail' | 'soft' | 'danger' | 'warning'

const variantClasses: Record<SurfaceVariant, string> = {
    panel: 'border-slate-200/80 bg-white/90 shadow-sm shadow-slate-200/70 dark:border-slate-800 dark:bg-slate-900/80 dark:shadow-slate-950/40',
    rail: 'border-slate-200 bg-slate-50/90 dark:border-slate-800 dark:bg-slate-900/60',
    soft: 'border-slate-200/70 bg-slate-100/70 dark:border-slate-800 dark:bg-slate-800/60',
    danger: 'border-red-200 bg-red-50 text-red-800 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200',
    warning: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200',
}

interface SurfaceProps {
    children: ReactNode
    className?: string
    variant?: SurfaceVariant
    as?: 'section' | 'div' | 'aside'
}

export function Surface({ children, className = '', variant = 'panel', as: Component = 'section' }: SurfaceProps) {
    return (
        <Component className={`rounded-[1.35rem] border ${variantClasses[variant]} ${className}`}>
            {children}
        </Component>
    )
}
```

- [x] **Step 2: Create `PageFrame` primitive**

Create `frontend/components/ui/PageFrame.tsx`:
```tsx
import type { ReactNode } from 'react'

interface PageFrameProps {
    children: ReactNode
    className?: string
    density?: 'normal' | 'wide'
}

export function PageFrame({ children, className = '', density = 'wide' }: PageFrameProps) {
    const maxWidth = density === 'wide' ? 'max-w-7xl' : 'max-w-5xl'
    return (
        <div className={`mx-auto w-full ${maxWidth} space-y-6 pb-24 md:pb-8 ${className}`}>
            {children}
        </div>
    )
}
```

- [x] **Step 3: Create `SectionHeader` primitive**

Create `frontend/components/ui/SectionHeader.tsx`:
```tsx
import type { ReactNode } from 'react'

interface SectionHeaderProps {
    title: string
    eyebrow?: string
    description?: string
    action?: ReactNode
}

export function SectionHeader({ title, eyebrow, description, action }: SectionHeaderProps) {
    return (
        <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
                {eyebrow && (
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                        {eyebrow}
                    </p>
                )}
                <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-950 dark:text-slate-50">
                    {title}
                </h2>
                {description && (
                    <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                        {description}
                    </p>
                )}
            </div>
            {action && <div className="shrink-0">{action}</div>}
        </div>
    )
}
```

- [x] **Step 4: Create `MetricTile` primitive**

Create `frontend/components/ui/MetricTile.tsx`:
```tsx
import type { WorkbenchTone } from '@/lib/adapters/timeline-workbench'

const toneClasses: Record<WorkbenchTone, string> = {
    neutral: 'text-slate-900 dark:text-slate-100',
    positive: 'text-emerald-700 dark:text-emerald-300',
    negative: 'text-red-700 dark:text-red-300',
    warning: 'text-amber-700 dark:text-amber-300',
    danger: 'text-red-700 dark:text-red-300',
    entry: 'text-emerald-700 dark:text-emerald-300',
    exit: 'text-amber-700 dark:text-amber-300',
    review: 'text-sky-700 dark:text-sky-300',
    ai: 'text-slate-700 dark:text-slate-200',
}

interface MetricTileProps {
    label: string
    value: string
    detail: string
    tone?: WorkbenchTone
}

export function MetricTile({ label, value, detail, tone = 'neutral' }: MetricTileProps) {
    return (
        <div className="rounded-2xl border border-slate-200/80 bg-white/80 p-4 dark:border-slate-800 dark:bg-slate-900/70">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{label}</p>
            <p className={`mt-2 text-2xl font-semibold tracking-tight ${toneClasses[tone]}`}>{value}</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{detail}</p>
        </div>
    )
}
```

- [x] **Step 5: Create `StatusPill` primitive**

Create `frontend/components/ui/StatusPill.tsx`:
```tsx
import type { WorkbenchTone } from '@/lib/adapters/timeline-workbench'

const toneClasses: Record<WorkbenchTone, string> = {
    neutral: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    positive: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    negative: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300',
    warning: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
    danger: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300',
    entry: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    exit: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
    review: 'bg-sky-50 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300',
    ai: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
}

interface StatusPillProps {
    children: string
    tone?: WorkbenchTone
    className?: string
}

export function StatusPill({ children, tone = 'neutral', className = '' }: StatusPillProps) {
    return (
        <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold ${toneClasses[tone]} ${className}`}>
            {children}
        </span>
    )
}
```

- [x] **Step 6: Create `EmptyStatePanel` primitive**

Create `frontend/components/ui/EmptyStatePanel.tsx`:
```tsx
import type { ReactNode } from 'react'

interface EmptyStatePanelProps {
    title: string
    detail?: string
    action?: ReactNode
}

export function EmptyStatePanel({ title, detail, action }: EmptyStatePanelProps) {
    return (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 p-8 text-center dark:border-slate-700 dark:bg-slate-900/50">
            <p className="font-semibold text-slate-900 dark:text-slate-100">{title}</p>
            {detail && <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">{detail}</p>}
            {action && <div className="mt-5">{action}</div>}
        </div>
    )
}
```

- [x] **Step 7: Add scoped app-shell background tokens**

Modify `frontend/app/globals.css` by adding this block after the `body` rule:
```css
.tn-decision-desk {
  background:
    radial-gradient(circle at top left, rgba(245, 158, 11, 0.10), transparent 30rem),
    radial-gradient(circle at top right, rgba(15, 23, 42, 0.08), transparent 28rem),
    linear-gradient(135deg, rgba(248, 250, 252, 0.96), rgba(226, 232, 240, 0.86));
}

.dark .tn-decision-desk {
  background:
    radial-gradient(circle at top left, rgba(245, 158, 11, 0.12), transparent 30rem),
    radial-gradient(circle at top right, rgba(59, 130, 246, 0.10), transparent 28rem),
    linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(30, 41, 59, 0.92));
}
```

- [x] **Step 8: Verify design-system primitives compile**

Run:
```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected:
```text
TypeScript exits 0.
```

Execution note:

- Created six presentational UI primitives under `frontend/components/ui/`.
- Added scoped `.tn-decision-desk` background tokens to `frontend/app/globals.css`.
- `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.

- [ ] **Step 9: Commit UI primitives**

Run:
```bash
git add frontend/components/ui/PageFrame.tsx frontend/components/ui/Surface.tsx frontend/components/ui/SectionHeader.tsx frontend/components/ui/MetricTile.tsx frontend/components/ui/StatusPill.tsx frontend/components/ui/EmptyStatePanel.tsx frontend/app/globals.css
git commit -m "feat: add frontend workbench UI primitives"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 4: Split And Harden Navigation Shell

**Files:**
- Create: `frontend/tests/navigation.test.mts`
- Create: `frontend/lib/navigation.ts`
- Create: `frontend/components/navigation/ProductTopNav.tsx`
- Create: `frontend/components/navigation/MobileBottomNav.tsx`
- Modify: `frontend/components/Navbar.tsx`

- [x] **Step 1: Add failing navigation helper tests**

Create `frontend/tests/navigation.test.mts`:
```ts
import test from 'node:test'
import assert from 'node:assert/strict'

import {
  getVisibleNavigationItems,
  isNavigationItemActive,
} from '../lib/navigation.ts'

test('regular users do not see admin navigation as a primary product item', () => {
  const items = getVisibleNavigationItems('user')
  assert.deepEqual(items.map((item) => item.href), [
    '/timeline',
    '/dashboard',
    '/positions',
    '/strategies',
    '/daily',
    '/insights',
    '/settings',
  ])
})

test('admins receive a separated ops item after product navigation', () => {
  const items = getVisibleNavigationItems('admin')
  assert.equal(items.at(-2)?.href, '/admin/jobs')
  assert.equal(items.at(-2)?.section, 'ops')
  assert.equal(items.at(-1)?.href, '/settings')
})

test('navigation active state handles nested paths', () => {
  assert.equal(isNavigationItemActive('/positions', '/positions/abc123'), true)
  assert.equal(isNavigationItemActive('/timeline', '/timeline'), true)
  assert.equal(isNavigationItemActive('/timeline', '/dashboard'), false)
})
```

- [x] **Step 2: Run navigation tests to verify RED**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/navigation.test.mts
```

Expected:
```text
FAIL because ../lib/navigation.ts does not exist.
```

- [x] **Step 3: Implement navigation helpers**

Create `frontend/lib/navigation.ts`:
```ts
export type UserRole = 'admin' | 'user' | null | undefined
export type NavigationSection = 'product' | 'ops' | 'settings'

export interface NavigationItem {
    href: string
    label: string
    icon: 'timeline' | 'dashboard' | 'positions' | 'strategies' | 'daily' | 'insights' | 'settings' | 'adminJobs'
    section: NavigationSection
}

const productItems: NavigationItem[] = [
    { href: '/timeline', label: '时间线', icon: 'timeline', section: 'product' },
    { href: '/dashboard', label: '看板', icon: 'dashboard', section: 'product' },
    { href: '/positions', label: '交易', icon: 'positions', section: 'product' },
    { href: '/strategies', label: '策略', icon: 'strategies', section: 'product' },
    { href: '/daily', label: '日历', icon: 'daily', section: 'product' },
    { href: '/insights', label: '洞察', icon: 'insights', section: 'product' },
]

const adminItems: NavigationItem[] = [
    { href: '/admin/jobs', label: 'Ops', icon: 'adminJobs', section: 'ops' },
]

const settingsItem: NavigationItem = { href: '/settings', label: '设置', icon: 'settings', section: 'settings' }

export function getVisibleNavigationItems(role: UserRole): NavigationItem[] {
    if (role === 'admin') {
        return [...productItems, ...adminItems, settingsItem]
    }
    return [...productItems, settingsItem]
}

export function isNavigationItemActive(href: string, pathname: string): boolean {
    if (href === '/timeline') return pathname === href
    return pathname === href || pathname.startsWith(`${href}/`)
}
```

- [x] **Step 4: Run navigation tests to verify GREEN**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/navigation.test.mts
```

Expected:
```text
All navigation tests pass.
```

- [x] **Step 5: Create `ProductTopNav`**

Create `frontend/components/navigation/ProductTopNav.tsx`:
```tsx
'use client'

import Link from 'next/link'
import {
    Briefcase,
    Calendar,
    Clock3,
    FileText,
    LayoutDashboard,
    Layers,
    Settings,
    ShieldCheck,
} from 'lucide-react'

import { isNavigationItemActive, type NavigationItem } from '@/lib/navigation'

const iconMap = {
    timeline: Clock3,
    dashboard: LayoutDashboard,
    positions: Briefcase,
    strategies: Layers,
    daily: Calendar,
    insights: FileText,
    settings: Settings,
    adminJobs: ShieldCheck,
}

interface ProductTopNavProps {
    items: NavigationItem[]
    pathname: string
}

export function ProductTopNav({ items, pathname }: ProductTopNavProps) {
    return (
        <div className="hidden items-center gap-1 md:flex">
            {items.map((item) => {
                const Icon = iconMap[item.icon]
                const isActive = isNavigationItemActive(item.href, pathname)
                const isOps = item.section === 'ops'
                return (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={`inline-flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-medium transition ${
                            isActive
                                ? 'bg-slate-950 text-white shadow-sm dark:bg-white dark:text-slate-950'
                                : isOps
                                    ? 'border border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200'
                                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100'
                        }`}
                    >
                        <Icon className="h-4 w-4" />
                        <span>{item.label}</span>
                    </Link>
                )
            })}
        </div>
    )
}
```

- [x] **Step 6: Create `MobileBottomNav`**

Create `frontend/components/navigation/MobileBottomNav.tsx`:
```tsx
'use client'

import Link from 'next/link'
import {
    Briefcase,
    Calendar,
    Clock3,
    FileText,
    LayoutDashboard,
    Layers,
    Settings,
    ShieldCheck,
} from 'lucide-react'

import { isNavigationItemActive, type NavigationItem } from '@/lib/navigation'

const iconMap = {
    timeline: Clock3,
    dashboard: LayoutDashboard,
    positions: Briefcase,
    strategies: Layers,
    daily: Calendar,
    insights: FileText,
    settings: Settings,
    adminJobs: ShieldCheck,
}

interface MobileBottomNavProps {
    items: NavigationItem[]
    pathname: string
}

export function MobileBottomNav({ items, pathname }: MobileBottomNavProps) {
    return (
        <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-slate-200 bg-white/95 backdrop-blur-xl pb-safe dark:border-slate-800 dark:bg-slate-950/95 md:hidden">
            <div className="grid grid-cols-5 gap-1 px-2 py-2">
                {items.slice(0, 5).map((item) => {
                    const Icon = iconMap[item.icon]
                    const isActive = isNavigationItemActive(item.href, pathname)
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex flex-col items-center rounded-2xl px-2 py-2 text-[11px] font-medium transition ${
                                isActive
                                    ? 'bg-slate-950 text-white dark:bg-white dark:text-slate-950'
                                    : 'text-slate-500 dark:text-slate-400'
                            }`}
                        >
                            <Icon className="h-5 w-5" />
                            <span className="mt-1">{item.label}</span>
                        </Link>
                    )
                })}
            </div>
        </div>
    )
}
```

- [x] **Step 7: Refactor `Navbar` into wrapper**

Modify `frontend/components/Navbar.tsx` so it keeps the public export but delegates nav rendering:
```tsx
'use client'

import Link from 'next/link'
import Image from 'next/image'
import { LogOut, User } from 'lucide-react'
import { usePathname } from 'next/navigation'

import { ThemeToggle } from './ThemeToggle'
import { useAuth } from '@/contexts/AuthContext'
import { getVisibleNavigationItems } from '@/lib/navigation'
import { ProductTopNav } from '@/components/navigation/ProductTopNav'
import { MobileBottomNav } from '@/components/navigation/MobileBottomNav'

export function Navbar() {
    const pathname = usePathname()
    const { user, isAuthenticated, logout } = useAuth()
    const visibleNavItems = getVisibleNavigationItems(user?.role)

    if (pathname === '/login' || pathname === '/register') {
        return null
    }

    return (
        <>
            <nav className="sticky top-0 z-50 border-b border-slate-200/80 bg-white/88 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/88">
                <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4">
                    <Link href="/timeline" className="flex items-center gap-3">
                        <div className="relative h-9 w-9 overflow-hidden rounded-2xl bg-slate-950 p-1.5 dark:bg-white">
                            <Image
                                src="/logo.png"
                                alt="Trading Noobs"
                                width={28}
                                height={28}
                                className="h-full w-full object-contain"
                                priority
                            />
                        </div>
                        <div className="leading-tight">
                            <span className="block text-base font-semibold tracking-tight text-slate-950 dark:text-white">
                                Trading Noobs
                            </span>
                            <span className="hidden text-[11px] uppercase tracking-[0.18em] text-slate-400 sm:block">
                                Decision Journal
                            </span>
                        </div>
                    </Link>

                    {isAuthenticated && <ProductTopNav items={visibleNavItems} pathname={pathname} />}

                    <div className="flex items-center gap-3">
                        <ThemeToggle />
                        {isAuthenticated && (
                            <>
                                <div className="hidden items-center gap-2 text-sm text-slate-500 lg:flex">
                                    <User className="h-4 w-4" />
                                    <span>{user?.email}</span>
                                </div>
                                <button
                                    onClick={logout}
                                    className="rounded-xl p-2 text-slate-500 transition hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-950/30"
                                    title="退出登录"
                                >
                                    <LogOut className="h-5 w-5" />
                                </button>
                            </>
                        )}
                    </div>
                </div>
            </nav>

            {isAuthenticated && <MobileBottomNav items={visibleNavItems} pathname={pathname} />}
        </>
    )
}
```

- [x] **Step 8: Run navigation and TypeScript verification**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/navigation.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected:
```text
Navigation tests pass.
TypeScript exits 0.
```

- [x] **Step 9: Run targeted strict React 19 lint on navigation files**

Run:
```bash
cd frontend
./node_modules/.bin/eslint components/Navbar.tsx components/navigation/ProductTopNav.tsx components/navigation/MobileBottomNav.tsx lib/navigation.ts --rule 'react-hooks/purity:error' --rule 'react-hooks/set-state-in-effect:error'
```

Expected:
```text
ESLint exits 0 for navigation files.
```

Execution note:

- RED verified: `tests/navigation.test.mts` failed with `ERR_MODULE_NOT_FOUND` for `frontend/lib/navigation.ts`.
- GREEN verified: navigation helper tests passed 3 tests.
- `Navbar` was split into wrapper + `ProductTopNav` + `MobileBottomNav`.
- `MobileBottomNav` intentionally renders all visible items in a horizontal scroll row rather than using the original 5-item slice, so mobile does not lose Insights or Settings entry points.
- `Navbar` now uses `next/image` for `/logo.png`, removing the previous `@next/next/no-img-element` warning from this touched file.
- `UserRole` helper input was widened to `string | null | undefined` because the auth context exposes `user.role` as a generic string.
- `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- Targeted strict React 19 lint for navigation files exited 0.

- [ ] **Step 10: Commit navigation split**

Run:
```bash
git add frontend/lib/navigation.ts frontend/tests/navigation.test.mts frontend/components/Navbar.tsx frontend/components/navigation/ProductTopNav.tsx frontend/components/navigation/MobileBottomNav.tsx
git commit -m "feat: split product navigation shell"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 5: Build Timeline Workbench Components

**Files:**
- Create: `frontend/components/timeline/workbench/TimelineWorkbenchHeader.tsx`
- Create: `frontend/components/timeline/workbench/TimelineViewTabs.tsx`
- Create: `frontend/components/timeline/workbench/TimelineEventCardV2.tsx`
- Create: `frontend/components/timeline/workbench/TimelineFeedPanel.tsx`
- Create: `frontend/components/timeline/workbench/ReviewInboxPanel.tsx`
- Create: `frontend/components/timeline/workbench/TimelineDecisionRail.tsx`
- Create: `frontend/components/timeline/workbench/TimelineWorkbench.tsx`
- Modify: `frontend/app/timeline/page.tsx`

- [x] **Step 1: Create `TimelineWorkbenchHeader`**

Create `frontend/components/timeline/workbench/TimelineWorkbenchHeader.tsx`:
```tsx
import { Clock3, RefreshCcw } from 'lucide-react'

import { formatTrustLabel } from '@/lib/adapters/timeline'
import { StatusPill } from '@/components/ui/StatusPill'
import type { TrustMeta } from '@/lib/read-models'

interface TimelineWorkbenchHeaderProps {
    pageMeta: TrustMeta
    onRefresh: () => void
}

export function TimelineWorkbenchHeader({ pageMeta, onRefresh }: TimelineWorkbenchHeaderProps) {
    const trustLabel = formatTrustLabel(pageMeta)

    return (
        <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div className="max-w-3xl">
                <div className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-3 py-1.5 text-xs font-semibold text-white dark:bg-white dark:text-slate-950">
                    <Clock3 className="h-3.5 w-3.5" />
                    Timeline-first home
                </div>
                <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 dark:text-white md:text-4xl">
                    决策时间流
                </h1>
                <p className="mt-3 text-sm leading-6 text-slate-500 dark:text-slate-400 md:text-base">
                    先看最近发生了什么，再处理最值得复盘的偏差、风险和证据。
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                    <span>as of {new Date(pageMeta.as_of).toLocaleString('zh-CN')}</span>
                    {trustLabel && <StatusPill>{trustLabel}</StatusPill>}
                </div>
            </div>

            <button type="button" onClick={onRefresh} className="btn btn-secondary inline-flex items-center gap-2 self-start md:self-auto">
                <RefreshCcw className="h-4 w-4" />
                刷新
            </button>
        </header>
    )
}
```

- [x] **Step 2: Create `TimelineViewTabs`**

Create `frontend/components/timeline/workbench/TimelineViewTabs.tsx`:
```tsx
import type { TimelineView } from '@/lib/read-models'

const viewOptions: Array<{ value: TimelineView; label: string }> = [
    { value: 'ALL', label: '全部' },
    { value: 'TRADING', label: '交易' },
    { value: 'REVIEW', label: '复盘' },
    { value: 'AI', label: 'AI' },
    { value: 'EXCEPTION', label: '异常' },
]

interface TimelineViewTabsProps {
    value: TimelineView
    onChange: (value: TimelineView) => void
}

export function TimelineViewTabs({ value, onChange }: TimelineViewTabsProps) {
    return (
        <div className="flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white/70 p-2 dark:border-slate-800 dark:bg-slate-900/70">
            {viewOptions.map((option) => (
                <button
                    key={option.value}
                    type="button"
                    onClick={() => onChange(option.value)}
                    className={`rounded-xl px-3 py-2 text-xs font-semibold transition ${
                        value === option.value
                            ? 'bg-slate-950 text-white shadow-sm dark:bg-white dark:text-slate-950'
                            : 'text-slate-500 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100'
                    }`}
                >
                    {option.label}
                </button>
            ))}
        </div>
    )
}
```

- [x] **Step 3: Create `TimelineEventCardV2`**

Create `frontend/components/timeline/workbench/TimelineEventCardV2.tsx`:
```tsx
import Link from 'next/link'
import { ChevronRight } from 'lucide-react'

import {
    formatTimelineEventImpact,
    formatTimelineEventMeta,
    getTimelineEventTone,
} from '@/lib/adapters/timeline-workbench'
import { getTimelineEventHref } from '@/lib/adapters/timeline'
import type { TimelineEventCard } from '@/lib/read-models'
import { StatusPill } from '@/components/ui/StatusPill'

interface TimelineEventCardV2Props {
    event: TimelineEventCard
}

export function TimelineEventCardV2({ event }: TimelineEventCardV2Props) {
    const impact = formatTimelineEventImpact(event)
    const tone = getTimelineEventTone(event.event_type)
    const href = getTimelineEventHref(event)
    const hasDetail = Boolean(
        event.thesis_excerpt ||
        event.invalidation_excerpt ||
        event.checklist_summary ||
        event.ai_annotation ||
        event.emotion ||
        event.confidence ||
        event.tags?.length
    )

    return (
        <article className="rounded-[1.35rem] border border-slate-200 bg-white/90 p-4 shadow-sm shadow-slate-200/60 dark:border-slate-800 dark:bg-slate-900/80 dark:shadow-slate-950/30">
            <div className="flex items-start gap-3">
                <div className="mt-1.5 h-3 w-3 rounded-full bg-slate-300 ring-4 ring-slate-100 dark:ring-slate-800" />
                <div className="min-w-0 flex-1">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                                <StatusPill tone={tone}>{event.event_type}</StatusPill>
                                <span className="text-xs text-slate-400">{formatTimelineEventMeta(event)}</span>
                            </div>
                            <h3 className="mt-2 text-base font-semibold tracking-tight text-slate-950 dark:text-white">
                                {event.headline}
                            </h3>
                            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                                {event.summary}
                            </p>
                        </div>
                        {impact && (
                            <div className="shrink-0 text-right">
                                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">impact</p>
                                <p className="mt-1 text-sm font-semibold text-slate-950 dark:text-white">{impact.label}</p>
                            </div>
                        )}
                    </div>

                    {hasDetail && (
                        <details className="mt-4 rounded-2xl bg-slate-50 px-4 py-3 dark:bg-slate-800/60">
                            <summary className="cursor-pointer text-xs font-semibold text-slate-500 dark:text-slate-300">
                                展开证据与执行细节
                            </summary>
                            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                                {event.thesis_excerpt && <p><strong>Thesis:</strong> {event.thesis_excerpt}</p>}
                                {event.invalidation_excerpt && <p><strong>Invalidation:</strong> {event.invalidation_excerpt}</p>}
                                {event.checklist_summary && <p><strong>Checklist:</strong> {event.checklist_summary}</p>}
                                {event.emotion && <p><strong>Emotion:</strong> {event.emotion}</p>}
                                {event.confidence !== undefined && <p><strong>Confidence:</strong> {event.confidence}</p>}
                                {event.ai_annotation && (
                                    <p><strong>AI:</strong> {event.ai_annotation.summary}</p>
                                )}
                            </div>
                        </details>
                    )}

                    <Link href={href} className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-slate-700 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white">
                        打开关联记录
                        <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                </div>
            </div>
        </article>
    )
}
```

- [x] **Step 4: Create `TimelineFeedPanel`**

Create `frontend/components/timeline/workbench/TimelineFeedPanel.tsx`:
```tsx
import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import { getTimelineEmptyState } from '@/lib/adapters/timeline'
import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'
import { TimelineEventCardV2 } from './TimelineEventCardV2'

interface TimelineFeedPanelProps {
    timelineHome: TimelineHomeViewModel
}

export function TimelineFeedPanel({ timelineHome }: TimelineFeedPanelProps) {
    const emptyState = getTimelineEmptyState(timelineHome.pageState)

    return (
        <Surface className="p-4 md:p-5">
            <SectionHeader
                eyebrow="Main feed"
                title="主时间线"
                description="按天分组，优先展示交易、复盘、AI 证据和异常。"
            />

            {timelineHome.timeline.groups.length === 0 ? (
                <div className="mt-5">
                    <EmptyStatePanel title={emptyState.title} detail={emptyState.detail} />
                </div>
            ) : (
                <div className="mt-5 space-y-6">
                    {timelineHome.timeline.groups.map((group) => (
                        <div key={group.group_key} className="space-y-3">
                            <div className="flex items-center gap-3">
                                <div className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
                                <span className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                                    {group.group_label}
                                </span>
                                <div className="h-px flex-1 bg-slate-200 dark:bg-slate-800" />
                            </div>
                            {group.items.map((event) => (
                                <TimelineEventCardV2 key={event.event_public_id} event={event} />
                            ))}
                        </div>
                    ))}
                </div>
            )}
        </Surface>
    )
}
```

- [x] **Step 5: Create `ReviewInboxPanel`**

Create `frontend/components/timeline/workbench/ReviewInboxPanel.tsx`:
```tsx
import Link from 'next/link'
import { AlertTriangle, CheckCircle2, ChevronRight } from 'lucide-react'

import { getReviewInboxSummary } from '@/lib/adapters/timeline'
import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import { StatusPill } from '@/components/ui/StatusPill'

interface ReviewInboxPanelProps {
    reviewInbox: TimelineHomeViewModel['reviewInbox']
}

export function ReviewInboxPanel({ reviewInbox }: ReviewInboxPanelProps) {
    return (
        <Surface variant="rail" className="p-4">
            <SectionHeader
                eyebrow="Review Inbox"
                title="待处理复盘"
                description={getReviewInboxSummary(reviewInbox)}
            />

            {reviewInbox.items.length === 0 ? (
                <div className="mt-5 rounded-2xl border border-dashed border-slate-300 p-5 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                    当前没有需要立即处理的 Review Inbox 项。
                </div>
            ) : (
                <div className="mt-5 space-y-3">
                    {reviewInbox.items.map((item) => (
                        <div key={item.public_id} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/60">
                            <div className="flex items-start justify-between gap-3">
                                <div className="min-w-0">
                                    <StatusPill tone={item.severity === 'CRITICAL' ? 'danger' : item.severity === 'WARNING' ? 'warning' : 'review'}>
                                        {item.kind}
                                    </StatusPill>
                                    <p className="mt-2 text-sm font-semibold text-slate-950 dark:text-white">{item.summary}</p>
                                    <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{item.reason}</p>
                                </div>
                                {item.severity === 'CRITICAL' ? (
                                    <AlertTriangle className="mt-1 h-4 w-4 shrink-0 text-red-500" />
                                ) : (
                                    <CheckCircle2 className="mt-1 h-4 w-4 shrink-0 text-slate-400" />
                                )}
                            </div>
                            <Link href={item.recommended_action.href} className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-slate-700 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white">
                                {item.recommended_action.label}
                                <ChevronRight className="h-3.5 w-3.5" />
                            </Link>
                        </div>
                    ))}
                </div>
            )}
        </Surface>
    )
}
```

- [x] **Step 6: Create `TimelineDecisionRail`**

Create `frontend/components/timeline/workbench/TimelineDecisionRail.tsx`:
```tsx
import { EvidenceLinkedInsightSidecar } from '@/components/insights/EvidenceLinkedInsightSidecar'
import { TimelineContextRail } from '@/components/timeline/TimelineContextRail'
import type { InsightRun } from '@/lib/insightArtifacts'
import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'
import type { TimelineView } from '@/lib/read-models'
import { ReviewInboxPanel } from './ReviewInboxPanel'

interface TimelineDecisionRailProps {
    timelineHome: TimelineHomeViewModel
    insightRuns?: InsightRun[]
    insightRunsLoading: boolean
    insightRunsError: string | null
    onRefreshInsights: () => void
    onSelectView: (value: TimelineView) => void
    hideReviewInbox?: boolean
}

export function TimelineDecisionRail({
    timelineHome,
    insightRuns,
    insightRunsLoading,
    insightRunsError,
    onRefreshInsights,
    onSelectView,
    hideReviewInbox = false,
}: TimelineDecisionRailProps) {
    return (
        <aside className="space-y-4">
            {!hideReviewInbox && <ReviewInboxPanel reviewInbox={timelineHome.reviewInbox} />}
            <EvidenceLinkedInsightSidecar
                runs={insightRuns}
                isLoading={insightRunsLoading}
                error={insightRunsError}
                title="Timeline AI Sidecar"
                onRefresh={onRefreshInsights}
            />
            <TimelineContextRail
                contextRail={timelineHome.contextRail}
                onSelectView={(value) => onSelectView(value as TimelineView)}
            />
        </aside>
    )
}
```

- [x] **Step 7: Create `TimelineWorkbench`**

Create `frontend/components/timeline/workbench/TimelineWorkbench.tsx`:
```tsx
import { buildTimelineSummaryMetrics } from '@/lib/adapters/timeline-workbench'
import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'
import type { InsightRun } from '@/lib/insightArtifacts'
import type { TimelineView } from '@/lib/read-models'
import { MetricTile } from '@/components/ui/MetricTile'
import { PageFrame } from '@/components/ui/PageFrame'
import { ReviewInboxPanel } from './ReviewInboxPanel'
import { TimelineDecisionRail } from './TimelineDecisionRail'
import { TimelineFeedPanel } from './TimelineFeedPanel'
import { TimelineViewTabs } from './TimelineViewTabs'
import { TimelineWorkbenchHeader } from './TimelineWorkbenchHeader'

interface TimelineWorkbenchProps {
    timelineHome: TimelineHomeViewModel
    view: TimelineView
    onChangeView: (value: TimelineView) => void
    onRefresh: () => void
    insightRuns?: InsightRun[]
    insightRunsLoading: boolean
    insightRunsError: string | null
    onRefreshInsights: () => void
}

export function TimelineWorkbench({
    timelineHome,
    view,
    onChangeView,
    onRefresh,
    insightRuns,
    insightRunsLoading,
    insightRunsError,
    onRefreshInsights,
}: TimelineWorkbenchProps) {
    const metrics = buildTimelineSummaryMetrics(timelineHome.summaryBar)

    return (
        <PageFrame className="tn-decision-desk rounded-[2rem] px-0 py-0">
            <div className="space-y-6">
                <TimelineWorkbenchHeader pageMeta={timelineHome.pageMeta} onRefresh={onRefresh} />

                <div className="grid gap-3 md:grid-cols-4">
                    {metrics.map((metric) => (
                        <MetricTile
                            key={metric.key}
                            label={metric.label}
                            value={metric.value}
                            detail={metric.detail}
                            tone={metric.tone}
                        />
                    ))}
                </div>

                <TimelineViewTabs value={view} onChange={onChangeView} />

                {timelineHome.reviewInbox.total > 0 && (
                    <div className="lg:hidden">
                        <ReviewInboxPanel reviewInbox={timelineHome.reviewInbox} />
                    </div>
                )}

                <div className="grid gap-5 lg:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.9fr)]">
                    <TimelineFeedPanel timelineHome={timelineHome} />
                    <div className="hidden lg:block">
                        <TimelineDecisionRail
                            timelineHome={timelineHome}
                            insightRuns={insightRuns}
                            insightRunsLoading={insightRunsLoading}
                            insightRunsError={insightRunsError}
                            onRefreshInsights={onRefreshInsights}
                            onSelectView={onChangeView}
                        />
                    </div>
                </div>

                <div className="lg:hidden">
                    <TimelineDecisionRail
                        timelineHome={timelineHome}
                        insightRuns={insightRuns}
                        insightRunsLoading={insightRunsLoading}
                        insightRunsError={insightRunsError}
                        onRefreshInsights={onRefreshInsights}
                        onSelectView={onChangeView}
                        hideReviewInbox={timelineHome.reviewInbox.total > 0}
                    />
                </div>
            </div>
        </PageFrame>
    )
}
```

- [x] **Step 8: Replace `/timeline` page composition**

Modify `frontend/app/timeline/page.tsx` to reduce it to data orchestration:
```tsx
'use client'

import { useState } from 'react'
import { Loader2 } from 'lucide-react'

import { useAuth } from '@/contexts/AuthContext'
import { useInsightRuns } from '@/hooks/useInsightRuns'
import { useTimelineHomeData } from '@/hooks/useTimelineHomeData'
import type { TimelineView } from '@/lib/read-models'
import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { TimelineWorkbench } from '@/components/timeline/workbench/TimelineWorkbench'

export default function TimelinePage() {
    const { token } = useAuth()
    const [view, setView] = useState<TimelineView>('ALL')
    const { timelineHome, isLoading, error, refresh } = useTimelineHomeData(token, view)
    const insightRunsQuery = useInsightRuns(token)

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            </div>
        )
    }

    if (error) {
        return (
            <EmptyStatePanel
                title="时间线暂时无法加载。"
                detail={error.message}
                action={<button type="button" onClick={() => refresh()} className="btn btn-secondary">重试</button>}
            />
        )
    }

    if (!timelineHome) {
        return (
            <EmptyStatePanel
                title="暂时没有可展示的时间线数据。"
                detail="先记录交易或检查同步设置，时间线会在有事件后形成。"
            />
        )
    }

    return (
        <TimelineWorkbench
            timelineHome={timelineHome}
            view={view}
            onChangeView={setView}
            onRefresh={refresh}
            insightRuns={insightRunsQuery.data}
            insightRunsLoading={insightRunsQuery.isLoading}
            insightRunsError={insightRunsQuery.error ? insightRunsQuery.error.message : null}
            onRefreshInsights={() => insightRunsQuery.refetch()}
        />
    )
}
```

- [x] **Step 9: Run TypeScript and fix exact type mismatches**

Run:
```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected:
```text
TypeScript exits 0.
```

- [x] **Step 10: Run focused Timeline tests**

Run:
```bash
cd frontend
node --experimental-strip-types --test tests/timeline-adapter.test.mts tests/timeline-workbench.test.mts
```

Expected:
```text
Timeline adapter and workbench helper tests pass.
```

- [x] **Step 11: Run targeted strict React 19 lint on Timeline workbench files**

Run:
```bash
cd frontend
./node_modules/.bin/eslint app/timeline/page.tsx components/timeline/workbench/TimelineWorkbench.tsx components/timeline/workbench/TimelineWorkbenchHeader.tsx components/timeline/workbench/TimelineViewTabs.tsx components/timeline/workbench/TimelineEventCardV2.tsx components/timeline/workbench/TimelineFeedPanel.tsx components/timeline/workbench/ReviewInboxPanel.tsx components/timeline/workbench/TimelineDecisionRail.tsx --rule 'react-hooks/purity:error' --rule 'react-hooks/set-state-in-effect:error'
```

Expected:
```text
ESLint exits 0 for P9A Timeline files.
```

Execution note:

- Added `frontend/components/timeline/workbench/` component tree and reduced `/timeline` page to data orchestration.
- Used the exact `InsightRun` type for AI sidecar props instead of temporary widened types.
- Fixed the page error state to use the `string | null` returned by `useTimelineHomeData`.
- Focused Timeline tests passed: 11 tests, 0 failures.
- `./node_modules/.bin/tsc --noEmit --pretty false` exited 0.
- Targeted strict React 19 lint for P9A Timeline files exited 0.

- [ ] **Step 12: Commit Timeline workbench**

Run:
```bash
git add frontend/app/timeline/page.tsx frontend/components/timeline/workbench/TimelineWorkbench.tsx frontend/components/timeline/workbench/TimelineWorkbenchHeader.tsx frontend/components/timeline/workbench/TimelineViewTabs.tsx frontend/components/timeline/workbench/TimelineEventCardV2.tsx frontend/components/timeline/workbench/TimelineFeedPanel.tsx frontend/components/timeline/workbench/ReviewInboxPanel.tsx frontend/components/timeline/workbench/TimelineDecisionRail.tsx
git commit -m "feat: redesign timeline as decision workbench"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 6: Polish Mobile Ordering And Legacy Timeline Compatibility

**Files:**
- Modify: `frontend/components/timeline/workbench/TimelineWorkbench.tsx`
- Modify: `frontend/components/timeline/workbench/TimelineDecisionRail.tsx`
- Modify: `frontend/components/timeline/TimelineSummaryStrip.tsx` if still referenced
- Modify: `frontend/components/timeline/FreshnessPill.tsx` if still referenced

- [ ] **Step 1: Check references to old Timeline components**

Run:
```bash
rg -n "TimelineSummaryStrip|TimelineEventCard|ReviewInboxCard|FreshnessPill" frontend/app frontend/components
```

Expected:
```text
Old components may still exist, but /timeline should no longer use TimelineSummaryStrip, TimelineEventCard, or ReviewInboxCard directly.
```

- [ ] **Step 2: Decide whether old components are still referenced**

If `rg` shows no references outside old component files:
```bash
git rm frontend/components/timeline/TimelineSummaryStrip.tsx frontend/components/timeline/TimelineEventCard.tsx frontend/components/timeline/ReviewInboxCard.tsx
```

If any are still referenced by non-P9A pages, keep them and do not remove compatibility components.

- [ ] **Step 3: Add mobile-first Review Inbox placement**

Modify `TimelineWorkbench.tsx` so mobile renders the Review Inbox before the feed when actionable, while desktop keeps it in the right rail. Use responsive classes rather than duplicating stateful logic:
```tsx
{timelineHome.reviewInbox.total > 0 && (
    <div className="lg:hidden">
        <ReviewInboxPanel reviewInbox={timelineHome.reviewInbox} />
    </div>
)}

<div className="grid gap-5 lg:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.9fr)]">
    <TimelineFeedPanel timelineHome={timelineHome} />
    <div className="hidden lg:block">
        <TimelineDecisionRail
            timelineHome={timelineHome}
            insightRuns={insightRuns}
            insightRunsLoading={insightRunsLoading}
            insightRunsError={insightRunsError}
            onRefreshInsights={onRefreshInsights}
            onSelectView={onChangeView}
        />
    </div>
</div>

<div className="lg:hidden">
    <TimelineDecisionRail
        timelineHome={timelineHome}
        insightRuns={insightRuns}
        insightRunsLoading={insightRunsLoading}
        insightRunsError={insightRunsError}
        onRefreshInsights={onRefreshInsights}
        onSelectView={onChangeView}
        hideReviewInbox={timelineHome.reviewInbox.total > 0}
    />
</div>
```

Then update `TimelineDecisionRail` to accept:
```tsx
hideReviewInbox?: boolean
```

And guard Review Inbox rendering:
```tsx
{!hideReviewInbox && <ReviewInboxPanel reviewInbox={timelineHome.reviewInbox} />}
```

- [ ] **Step 4: Verify TypeScript after mobile ordering**

Run:
```bash
cd frontend
./node_modules/.bin/tsc --noEmit --pretty false
```

Expected:
```text
TypeScript exits 0.
```

- [ ] **Step 5: Verify strict lint for touched workbench files**

Run:
```bash
cd frontend
./node_modules/.bin/eslint components/timeline/workbench/TimelineWorkbench.tsx components/timeline/workbench/TimelineDecisionRail.tsx --rule 'react-hooks/purity:error' --rule 'react-hooks/set-state-in-effect:error'
```

Expected:
```text
ESLint exits 0.
```

- [ ] **Step 6: Commit mobile ordering and cleanup**

Run:
```bash
git add frontend/components/timeline/workbench/TimelineWorkbench.tsx frontend/components/timeline/workbench/TimelineDecisionRail.tsx frontend/components/timeline
git commit -m "feat: tune timeline workbench mobile flow"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 7: Full Frontend Verification And Browser Smoke

**Files:**
- Modify: `docs/superpowers/plans/2026-06-09-dev-p9a-frontend-workbench-plan.md`

- [ ] **Step 1: Run full frontend verification**

Run:
```bash
cd frontend
npm audit --json
node --experimental-strip-types --test tests/*.test.mts
./node_modules/.bin/tsc --noEmit --pretty false
npm run lint
npm run build
```

Expected:
```text
npm audit reports 0 vulnerabilities.
All Node tests pass.
TypeScript exits 0.
Lint exits 0, allowing existing warnings.
Next build exits 0 and includes /timeline.
```

- [ ] **Step 2: Run targeted strict React 19 lint for all P9A files**

Run:
```bash
cd frontend
./node_modules/.bin/eslint app/timeline/page.tsx components/Navbar.tsx components/navigation/ProductTopNav.tsx components/navigation/MobileBottomNav.tsx components/timeline/workbench/TimelineWorkbench.tsx components/timeline/workbench/TimelineWorkbenchHeader.tsx components/timeline/workbench/TimelineViewTabs.tsx components/timeline/workbench/TimelineEventCardV2.tsx components/timeline/workbench/TimelineFeedPanel.tsx components/timeline/workbench/ReviewInboxPanel.tsx components/timeline/workbench/TimelineDecisionRail.tsx components/ui/PageFrame.tsx components/ui/Surface.tsx components/ui/SectionHeader.tsx components/ui/MetricTile.tsx components/ui/StatusPill.tsx components/ui/EmptyStatePanel.tsx lib/adapters/timeline-workbench.ts lib/navigation.ts --rule 'react-hooks/purity:error' --rule 'react-hooks/set-state-in-effect:error'
```

Expected:
```text
ESLint exits 0 for P9A-touched files with strict React 19 rules enabled.
```

- [ ] **Step 3: Start local frontend for visual smoke**

Run:
```bash
cd frontend
npm run dev
```

Expected:
```text
Next dev server starts. If Turbopack sandbox permissions fail, rerun with approval.
```

- [ ] **Step 4: Browser smoke `/timeline` desktop**

Open:
```text
http://localhost:3000/timeline
```

Verify:
```text
Desktop layout uses balanced two-column workbench.
Summary metrics are visible above the feed.
Timeline feed remains primary.
Review Inbox is visible in the right rail.
AI sidecar and context rail remain accessible.
No runtime console error appears during initial render.
```

- [ ] **Step 5: Browser smoke `/timeline` mobile viewport**

Use the browser's mobile viewport or narrow window.

Verify:
```text
Layout becomes one column.
Summary remains compact.
Review Inbox appears before Timeline when it has items.
Timeline feed is not hidden behind a secondary rail.
Bottom navigation remains usable.
```

- [ ] **Step 6: Browser smoke auth edge pages**

Open:
```text
http://localhost:3000/login
http://localhost:3000/register
```

Verify:
```text
Navbar remains hidden on login and register.
No logo/theme hydration error appears.
```

- [ ] **Step 7: Stop local dev server**

Stop the dev server with `Ctrl-C`.

Expected:
```text
No background frontend dev server remains running.
```

- [ ] **Step 8: Restore generated noise and verify repo hygiene**

Run:
```bash
git restore frontend/next-env.d.ts frontend/tsconfig.tsbuildinfo
git diff --check
git status --short --branch
```

Expected:
```text
Generated files are clean.
No whitespace errors.
Only intended P9A files are modified.
docs/superpowers/demos/ remains untracked and untouched.
```

- [ ] **Step 9: Record verification notes**

Update this plan with:
```text
Audit result.
Node test count.
TypeScript result.
Lint result and warning count.
Targeted strict React 19 lint result.
Build result.
Browser smoke observations.
Generated-noise cleanup.
```

- [ ] **Step 10: Commit final frontend verification notes**

Run:
```bash
git add docs/superpowers/plans/2026-06-09-dev-p9a-frontend-workbench-plan.md
git commit -m "docs: record p9a frontend verification"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

### Task 8: Backend Smoke And Final Checkpoint

**Files:**
- Modify: `docs/superpowers/plans/2026-06-09-dev-p9a-frontend-workbench-plan.md`
- Modify: `docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md`

- [ ] **Step 1: Run backend unittest smoke**

Run:
```bash
cd backend
../.venv313/bin/python -m unittest discover -s tests
```

Expected:
```text
Backend tests pass.
Known Yahoo/yfinance DNS warnings may appear under restricted network conditions and are acceptable if tests still pass.
```

- [ ] **Step 2: Run Alembic smoke**

Run from repo root:
```bash
DATABASE_URL=sqlite:////private/tmp/tradingnoobs_dev_p9a_frontend_workbench_final.db ./.venv313/bin/alembic -c backend/alembic.ini upgrade head
```

Expected:
```text
Alembic reaches 5e6f7a8b9cad.
```

- [ ] **Step 3: Update dev checkpoint**

Modify `docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md`:
```text
Add a 2026-06-09 P9A Frontend Workbench section.
Record stage commits.
Record final frontend versions remain Next 16 / React 19.
Record frontend audit/tests/tsc/lint/build results.
Record targeted strict React 19 lint result for P9A-touched files.
Record backend smoke and Alembic results.
Record docs/superpowers/demos/ untouched status.
```

- [ ] **Step 4: Update this plan with final status**

Add an `Execution note` under Task 8 with:
```text
Backend test result.
Alembic result.
Final HEAD commit before docs closeout.
Any warnings accepted.
```

- [ ] **Step 5: Commit and push final P9A docs**

Run:
```bash
git add docs/superpowers/plans/2026-06-09-dev-p9a-frontend-workbench-plan.md docs/superpowers/plans/2026-05-02-dev-branch-checkpoint.md
git commit -m "docs: record dev p9a frontend workbench"
git push origin dev
```

Expected:
```text
Commit succeeds and origin/dev advances.
```

---

## Final Acceptance Checklist

- [ ] `/` still redirects to `/timeline`.
- [ ] `/timeline` uses the existing Timeline Home API/hook.
- [ ] Desktop Timeline uses balanced workbench layout.
- [ ] Mobile Timeline uses readable one-column layout.
- [ ] Review Inbox is first-class on desktop and appears before feed on mobile when actionable.
- [ ] AI sidecar and context rail remain accessible.
- [ ] New UI primitives live under `frontend/components/ui/`.
- [ ] New Timeline workbench components live under `frontend/components/timeline/workbench/`.
- [ ] Navigation shell is split and admin/Ops is visually separated.
- [ ] P9A-touched files pass targeted React 19 strict lint.
- [ ] Full frontend verification passes.
- [ ] Backend smoke and Alembic smoke pass.
- [ ] `docs/superpowers/demos/` remains untouched.

## Known Deferrals

- Global removal of `react-hooks/purity` and `react-hooks/set-state-in-effect` deferrals from `frontend/eslint.config.mjs`.
- Dashboard redesign.
- Lifecycle detail hard cutover and visual rewrite.
- Chart schema migration.
- Backend timeline snapshot hard cutover beyond the current API behavior.
