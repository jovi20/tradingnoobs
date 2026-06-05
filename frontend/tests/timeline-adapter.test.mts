import test from 'node:test'
import assert from 'node:assert/strict'

import {
  formatTrustLabel,
  getInboxSeverityAccent,
  getReviewInboxSummary,
  getTimelineEmptyState,
  getTimelineEventAccent,
  getTimelineEventHref,
  getTimelineSourceModeLabel,
} from '../lib/adapters/timeline.ts'

test('formatTrustLabel joins freshness, value status, and maturity', () => {
  assert.equal(
    formatTrustLabel({
      as_of: '2026-04-15T00:00:00Z',
      freshness: 'DELAYED',
      source: 'DERIVED',
      value_status: 'ESTIMATED',
      maturity: 'EARLY_SIGNAL',
    }),
    'delayed · estimated · early_signal'
  )
})

test('getReviewInboxSummary reflects high priority counts', () => {
  assert.equal(getReviewInboxSummary({ total: 0, highPriority: 0 }), '当前没有需要立即处理的 Review Inbox 项。')
  assert.equal(getReviewInboxSummary({ total: 3, highPriority: 1 }), '3 项待处理 · 1 项高优先级')
})

test('getTimelineEmptyState returns copy for zero and small-data states', () => {
  assert.deepEqual(getTimelineEmptyState('ZERO'), {
    title: '先记录第一笔交易，时间线才会开始形成。',
    detail: '当前还没有任何交易或账户数据，建议先从快速记录开始。',
  })
  assert.deepEqual(getTimelineEmptyState('SMALL_DATA'), {
    title: '已经有基础数据，但现在更适合看事件线和单笔复盘。',
    detail: '继续记录更多交易后，Review Inbox 和宏观分析会更稳定。',
  })
})

test('accent helpers stay deterministic for timeline and inbox severity', () => {
  assert.equal(getTimelineEventAccent('AI_INSIGHT'), 'bg-slate-700')
  assert.match(getInboxSeverityAccent('CRITICAL'), /border-red-300/)
})

test('timeline event href prefers auditable AI artifact links', () => {
  assert.equal(
    getTimelineEventHref({
      event_public_id: 'insight-artifact:artifact-1',
      thread_public_id: 'run-1',
      event_type: 'AI_INSIGHT',
      occurred_at: '2026-06-05T00:00:00Z',
      headline: 'AI review',
      summary: 'Evidence-linked summary',
      instrument: {
        asset_label: 'Trading Noobs',
        instrument_label: 'Insight Artifact',
        symbol: 'AI',
        href: '/insights',
      },
      ai_annotation: {
        artifact_public_id: 'artifact-1',
        summary: 'Evidence-linked summary',
        href: '/insights/artifact-1',
      },
      href: '/insights',
    }),
    '/insights/artifact-1'
  )
})

test('getTimelineSourceModeLabel explains snapshot default and legacy fallback', () => {
  assert.equal(getTimelineSourceModeLabel('SNAPSHOT_ONLY'), 'Snapshot-first')
  assert.equal(getTimelineSourceModeLabel('LEGACY_MIXED'), 'Legacy mixed fallback')
})
