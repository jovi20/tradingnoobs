import test from 'node:test'
import assert from 'node:assert/strict'

import {
  formatAnalysisDateRangeLabel,
  getDefaultAnalysisDateRange,
  validateAnalysisDateRange,
} from '../lib/adapters/analysis.ts'
import { insightsAPI } from '../lib/api.ts'

test('getDefaultAnalysisDateRange returns the last 30 calendar days inclusively', () => {
  assert.deepEqual(getDefaultAnalysisDateRange(new Date('2026-06-11T12:00:00Z')), {
    startDate: '2026-05-13',
    endDate: '2026-06-11',
  })
})

test('validateAnalysisDateRange mirrors backend pair, order, and length rules', () => {
  assert.equal(validateAnalysisDateRange('2026-06-01', '2026-06-11'), null)
  assert.match(validateAnalysisDateRange('2026-06-01', '') ?? '', /结束日期/)
  assert.match(validateAnalysisDateRange('', '2026-06-11') ?? '', /开始日期/)
  assert.match(validateAnalysisDateRange('2026-06-11', '2026-06-01') ?? '', /不能晚于/)
  assert.match(validateAnalysisDateRange('2025-01-01', '2026-01-02') ?? '', /366/)
})

test('formatAnalysisDateRangeLabel produces compact Chinese range copy', () => {
  assert.equal(formatAnalysisDateRangeLabel('2026-06-01', '2026-06-11'), '2026-06-01 至 2026-06-11')
})

test('insightsAPI.listAnalysisHistory fetches the history endpoint with filters', async () => {
  const originalFetch = globalThis.fetch
  let requestedUrl = ''
  let requestedInit: RequestInit | undefined

  globalThis.fetch = (async (input: RequestInfo | URL, init?: RequestInit) => {
    requestedUrl = String(input)
    requestedInit = init
    return new Response(JSON.stringify([
      {
        run_public_id: 'run-1',
        artifact_public_id: 'artifact-1',
        analysis_type: 'strategy_health',
        title: 'Strategy health',
        summary: 'Keep sizing small.',
        created_at: '2026-06-11T00:00:00Z',
        date_range: { start_date: '2026-06-01', end_date: '2026-06-11', label: '2026-06-01 to 2026-06-11' },
        href: '/insights/artifact-1',
      },
    ]), { status: 200 })
  }) as typeof fetch

  try {
    const result = await insightsAPI.listAnalysisHistory('token-1', {
      analysis_type: 'strategy_health',
      limit: 5,
    })
    const url = new URL(requestedUrl)
    const requestHeaders = requestedInit?.headers as Record<string, string>

    assert.equal(url.pathname, '/api/insights/analyze/history')
    assert.equal(url.searchParams.get('analysis_type'), 'strategy_health')
    assert.equal(url.searchParams.get('limit'), '5')
    assert.equal(requestHeaders.Authorization, 'Bearer token-1')
    assert.equal(result[0].artifact_public_id, 'artifact-1')
  } finally {
    globalThis.fetch = originalFetch
  }
})
