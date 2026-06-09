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
