import test from 'node:test'
import assert from 'node:assert/strict'

import {
  adaptDashboardPageData,
  calculateDashboardPeriodMetrics,
  getDashboardAllocationChart,
  getDashboardAllocationData,
  getDashboardMovers,
} from '../lib/adapters/dashboard.ts'

test('calculateDashboardPeriodMetrics returns deltas from pnl history', () => {
  const result = calculateDashboardPeriodMetrics([
    { pnl: 100, pnl_percent: 5, date: '2026-04-01' },
    { pnl: 140, pnl_percent: 8, date: '2026-04-02' },
  ])

  assert.deepEqual(result, {
    periodPnl: 3,
    periodValue: 40,
  })
})

test('adaptDashboardPageData exposes currency symbol and open position count safely', () => {
  const result = adaptDashboardPageData({
    stats: {
      total_assets: 1000,
      total_pnl: 120,
      win_rate: 55,
      avg_pnl_ratio: 1.7,
      total_trades: 10,
      open_positions: 2,
      closed_trades: 8,
      asset_allocation: [],
      core_type_allocation: [{ name: 'STOCK', value: 700, percent: 70 }],
      market_allocation: [{ name: 'US', value: 700, percent: 70 }],
      risk_level_allocation: [{ name: 'MODERATE', value: 700, percent: 70 }],
      account_allocation: [{ name: 'IBKR', broker: 'IBKR', value: 700, percent: 70 }],
      top_movers: [{ id: 1, symbol: 'NVDA', change_percent: 3.2, current_price: 910, currency: 'USD' }],
      bottom_movers: [{ id: 2, symbol: 'TSLA', change_percent: -2.1, current_price: 170, currency: 'USD' }],
    },
    openPositions: [{ id: 1, routeId: 'pos-1' }, { id: 2, routeId: 'pos-2' }],
    allPositions: [],
    pnlHistory: [{ pnl: 0, pnl_percent: 0, date: '2026-04-01' }],
    displayCurrency: 'USD',
  })

  assert.equal(result.currencySymbol, '$')
  assert.equal(result.totalPnl, 120)
  assert.equal(result.isPositive, true)
  assert.equal(result.openPositionsCount, 2)
  assert.equal(result.accountAllocation.length, 1)
  assert.equal(result.movers.top[0].symbol, 'NVDA')
  assert.deepEqual(result.periodMetrics, { periodPnl: 0, periodValue: 0 })
})

test('dashboard allocation helper selects the correct allocation slice for dimension', () => {
  const stats = {
    core_type_allocation: [{ name: 'STOCK', value: 700, percent: 70 }],
    market_allocation: [{ name: 'US', value: 700, percent: 70 }],
    risk_level_allocation: [{ name: 'MODERATE', value: 700, percent: 70 }],
  }

  assert.deepEqual(getDashboardAllocationData(stats, 'CORE_TYPE'), stats.core_type_allocation)
  assert.deepEqual(getDashboardAllocationData(stats, 'MARKET'), stats.market_allocation)
  assert.deepEqual(getDashboardAllocationData(stats, 'RISK'), stats.risk_level_allocation)
})

test('dashboard allocation helper prefers schema-first chart payloads when available', () => {
  const stats = {
    core_type_allocation: [{ name: 'LEGACY', value: 1, percent: 1 }],
    market_allocation: [],
    risk_level_allocation: [],
    chart_payloads: {
      core_type: {
        chart_schema: {
          schema_version: 'chart.v1',
          chart_type: 'bar',
          data_path: 'core_type_allocation',
          dimensions: [{ field: 'name', label: 'Asset type allocation' }],
          series: [{ field: 'value', label: 'Value' }],
        },
        data: [{ name: 'EQUITY', value: 700, percent: 70 }],
        empty_state: { is_empty: false, reason: null },
        trust_meta: {
          freshness: 'FRESH',
          source: 'DASHBOARD_DERIVED_READ_MODEL',
          source_refs: ['dashboard:allocation:CORE_TYPE'],
        },
      },
    },
  }

  assert.deepEqual(getDashboardAllocationData(stats, 'CORE_TYPE'), [
    { name: 'EQUITY', value: 700, percent: 70 },
  ])
})

test('dashboard allocation chart exposes trust and empty state from schema payload', () => {
  const stats = {
    core_type_allocation: [],
    market_allocation: [],
    risk_level_allocation: [],
    chart_payloads: {
      core_type: {
        chart_schema: {
          schema_version: 'chart.v1',
          chart_type: 'bar',
          data_path: 'core_type_allocation',
          series: [{ field: 'value', label: 'Value' }],
        },
        data: [],
        empty_state: { is_empty: true, reason: 'NO_ALLOCATION_DATA' },
        trust_meta: {
          freshness: 'FRESH',
          source: 'DASHBOARD_DERIVED_READ_MODEL',
          source_refs: ['dashboard:stats'],
        },
      },
    },
  }

  const chart = getDashboardAllocationChart(stats, 'CORE_TYPE')
  assert.equal(chart.isEmpty, true)
  assert.equal(chart.emptyState.reason, 'NO_ALLOCATION_DATA')
  assert.equal(chart.trustMeta.source, 'DASHBOARD_DERIVED_READ_MODEL')
})

test('dashboard movers helper preserves top and bottom movers', () => {
  const stats = {
    top_movers: [{ id: 1, symbol: 'NVDA', change_percent: 3.2, current_price: 910, currency: 'USD' }],
    bottom_movers: [{ id: 2, symbol: 'TSLA', change_percent: -2.1, current_price: 170, currency: 'USD' }],
  }

  const result = getDashboardMovers(stats)
  assert.equal(result.top.length, 1)
  assert.equal(result.bottom.length, 1)
  assert.equal(result.bottom[0].symbol, 'TSLA')
})
