import test from 'node:test'
import assert from 'node:assert/strict'

import {
  adaptDashboardPageData,
  buildDashboardStatusMetrics,
  calculateDashboardPeriodMetrics,
  formatDashboardAccountRows,
  getDashboardAllocationChart,
  getDashboardAllocationData,
  getDashboardHistoryDays,
  getDashboardMobileSectionOrder,
  getDashboardMovers,
  getDashboardPeriodOptions,
  getDashboardRiskPosture,
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

test('dashboard allocation chart synthesizes local trust for legacy fallback data', () => {
  const stats = {
    core_type_allocation: [{ name: 'STOCK', value: 700, percent: 70 }],
    market_allocation: [],
    risk_level_allocation: [],
  }

  const chart = getDashboardAllocationChart(stats, 'CORE_TYPE')
  assert.equal(chart.isEmpty, false)
  assert.equal(chart.schema?.chart_type, 'pie')
  assert.equal(chart.trustMeta.source, 'LOCAL_FALLBACK_VIEW')
  assert.deepEqual(chart.data, [{ name: 'STOCK', value: 700, percent: 70 }])
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

test('dashboard risk posture is danger when a critical risk alert exists', () => {
  const posture = getDashboardRiskPosture({
    max_drawdown: 0.05,
    sharpe_ratio: 1.4,
    risk_summary: {
      as_of: '2026-06-11T10:30:00Z',
      base_currency: 'USD',
      portfolio: {
        gross_exposure: 100000,
        net_liquidation_value: 94000,
        daily_pnl: -6000,
        daily_pnl_percent: -6,
        max_drawdown: 0.06,
      },
      alerts: [{
        public_id: 'risk:daily_loss:2026-06-11',
        kind: 'DAILY_LOSS_LIMIT',
        severity: 'CRITICAL',
        summary: '今日亏损已达到 -6.00%',
        reason: 'Daily equity change crossed the -5% critical threshold.',
        recommended_action: {
          kind: 'OPEN_DASHBOARD',
          label: '查看组合风险',
          href: '/dashboard',
        },
        source_refs: ['daily_snapshot:2026-06-11'],
        trust: {
          freshness: 'FRESH',
          source: 'DERIVED',
          value_status: 'ESTIMATED',
        },
      }],
      trust: {
        freshness: 'FRESH',
        source: 'DERIVED',
        source_refs: ['TradingPosition', 'AccountLedgerEntry', 'DailySnapshot'],
      },
    },
  })

  assert.equal(posture.tone, 'danger')
  assert.equal(posture.label, '风险预警')
})

test('adaptDashboardPageData exposes risk alerts from stats', () => {
  const result = adaptDashboardPageData({
    stats: {
      total_assets: 1000,
      total_pnl: -120,
      win_rate: 40,
      avg_pnl_ratio: 0.7,
      total_trades: 10,
      open_positions: 2,
      closed_trades: 8,
      asset_allocation: [],
      core_type_allocation: [],
      market_allocation: [],
      risk_level_allocation: [],
      account_allocation: [],
      top_movers: [],
      bottom_movers: [],
      risk_summary: {
        as_of: '2026-06-11T10:30:00Z',
        base_currency: 'USD',
        portfolio: {
          gross_exposure: 100000,
          net_liquidation_value: 94000,
          daily_pnl: -6000,
          daily_pnl_percent: -6,
          max_drawdown: 0.06,
        },
        alerts: [{
          public_id: 'risk:daily_loss:2026-06-11',
          kind: 'DAILY_LOSS_LIMIT',
          severity: 'CRITICAL',
          summary: '今日亏损已达到 -6.00%',
          reason: 'Daily equity change crossed the -5% critical threshold.',
          recommended_action: {
            kind: 'OPEN_DASHBOARD',
            label: '查看组合风险',
            href: '/dashboard',
          },
          source_refs: ['daily_snapshot:2026-06-11'],
          trust: {
            freshness: 'FRESH',
            source: 'DERIVED',
            value_status: 'ESTIMATED',
          },
        }],
        trust: {
          freshness: 'FRESH',
          source: 'DERIVED',
          source_refs: ['TradingPosition', 'AccountLedgerEntry', 'DailySnapshot'],
        },
      },
    },
    openPositions: [],
    allPositions: [],
    pnlHistory: [],
    displayCurrency: 'USD',
  })

  assert.equal(result.riskAlerts.length, 1)
  assert.equal(result.riskAlerts[0].severity, 'CRITICAL')
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
