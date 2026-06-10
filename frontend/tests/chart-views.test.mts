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
