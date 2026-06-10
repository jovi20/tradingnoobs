import test from 'node:test'
import assert from 'node:assert/strict'

import { adaptLegacyAnalysisChart } from '../lib/adapters/insight-charts.ts'

test('adaptLegacyAnalysisChart maps grouped stats into bar chart rows', () => {
  const view = adaptLegacyAnalysisChart({
    analysis_type: 'strategy_health',
    created_at: '2026-06-10T08:00:00Z',
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
    created_at: '2026-06-10T08:00:00Z',
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
    created_at: '2026-06-10T08:00:00Z',
    raw_data: { unsupported: true },
  } as any)

  assert.equal(view.emptyState.is_empty, true)
  assert.equal(view.emptyState.reason, 'UNSUPPORTED_LEGACY_ANALYSIS_CHART')
  assert.deepEqual(view.data, [])
})
