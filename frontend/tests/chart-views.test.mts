import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildMaeMfeScatterPoints,
  buildPortfolioSankeyChartView,
  shouldRenderEquityLineChart,
  shouldRenderPortfolioSankey,
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

test('shouldRenderPortfolioSankey blocks empty data before Recharts receives it', () => {
  const emptyView = buildPortfolioSankeyChartView({ nodes: [], links: [] })
  const unlinkedView = buildPortfolioSankeyChartView({ nodes: [{ name: 'Total Assets' }], links: [] })
  const populatedView = buildPortfolioSankeyChartView({
    nodes: [{ name: 'Cash' }, { name: 'Equity' }],
    links: [{ source: 0, target: 1, value: 100 }],
  })

  assert.equal(shouldRenderPortfolioSankey(emptyView), false)
  assert.equal(shouldRenderPortfolioSankey(unlinkedView), false)
  assert.equal(shouldRenderPortfolioSankey(populatedView), true)
})

test('shouldRenderEquityLineChart treats all-zero bootstrap history as empty', () => {
  assert.equal(shouldRenderEquityLineChart([
    { date: '2026-06-10', pnl: 0, pnl_percent: 0, total_equity: 0 },
    { date: '2026-06-11', pnl: 0, pnl_percent: 0, total_equity: 0 },
  ]), false)
  assert.equal(shouldRenderEquityLineChart([
    { date: '2026-06-10', pnl: 0, pnl_percent: 0, total_equity: 100000 },
    { date: '2026-06-11', pnl: 0, pnl_percent: 0, total_equity: 100000 },
  ]), true)
  assert.equal(shouldRenderEquityLineChart([
    { date: '2026-06-10', pnl: -100, pnl_percent: -0.1, total_equity: 99900 },
    { date: '2026-06-11', pnl: 50, pnl_percent: 0.05, total_equity: 99950 },
  ]), true)
})
