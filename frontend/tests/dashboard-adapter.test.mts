import test from 'node:test'
import assert from 'node:assert/strict'

import {
  adaptDashboardPageData,
  buildDashboardStatusMetrics,
  calculateDashboardPeriodMetrics,
  formatDashboardAccountRows,
  getDashboardHistoryDays,
  getDashboardPeriodOptions,
} from '../lib/adapters/dashboard.ts'
import type { DashboardStats } from '../lib/api.ts'

function makeStats(overrides: Partial<DashboardStats> = {}): DashboardStats {
  return {
    journal_balance: 1000,
    realized_pnl: 120,
    win_rate: 55,
    avg_pnl_ratio: 1.7,
    total_trades: 10,
    open_positions: 2,
    closed_trades: 8,
    account_balances: [],
    ...overrides,
  }
}

test('calculateDashboardPeriodMetrics uses the latest cumulative realized values', () => {
  const result = calculateDashboardPeriodMetrics([
    { pnl: 100, pnl_percent: 5, date: '2026-04-01' },
    { pnl: 140, pnl_percent: 8, date: '2026-04-02' },
  ])

  assert.deepEqual(result, {
    periodPnl: 8,
    periodValue: 140,
  })
  assert.deepEqual(calculateDashboardPeriodMetrics([]), { periodPnl: 0, periodValue: 0 })
})

test('adaptDashboardPageData exposes only the journal-safe dashboard model', () => {
  const result = adaptDashboardPageData({
    stats: makeStats({
      account_balances: [{ name: 'IBKR Main', broker: 'IBKR', journal_balance: 700 }],
    }),
    openPositions: [],
    pnlHistory: [{ pnl: 120, pnl_percent: 6, date: '2026-04-01' }],
    displayCurrency: 'USD',
  })

  assert.equal(result.currencySymbol, '$')
  assert.deepEqual(result.summary, {
    journalBalance: 1000,
    realizedPnl: 120,
    winRate: 55,
    avgPnlRatio: 1.7,
    totalTrades: 10,
    openPositions: 2,
    closedTrades: 8,
  })
  assert.deepEqual(result.accountRows, [{ name: 'IBKR Main', broker: 'IBKR', balanceLabel: '$700' }])
  assert.deepEqual(result.periodMetrics, { periodPnl: 6, periodValue: 120 })
  assert.equal(Object.hasOwn(result, 'allocation'), false)
  assert.equal(Object.hasOwn(result, 'movers'), false)
  assert.equal(Object.hasOwn(result, 'riskAlerts'), false)
  assert.equal(Object.hasOwn(result, 'allPositions'), false)
})

test('dashboard status metrics use realized and journal-balance language', () => {
  const result = buildDashboardStatusMetrics({
    summary: {
      journalBalance: 10000,
      realizedPnl: -240,
      winRate: 42,
      avgPnlRatio: 0.8,
      totalTrades: 12,
      openPositions: 3,
      closedTrades: 9,
    },
    currencySymbol: '$',
  })

  assert.deepEqual(result.map((metric) => metric.label), [
    '累计已实现盈亏',
    '已实现胜率',
    '交易日志',
    '未平仓记录',
  ])
  assert.equal(result[0].value, '-$240')
  assert.equal(result[0].detail, '日志余额 $10,000')
  assert.equal(result[0].tone, 'negative')
  assert.equal(result[2].detail, '已平仓 9 笔')
  assert.equal(result[3].value, '3')
})

test('dashboard account rows label ledger-derived balances without percentages', () => {
  const rows = formatDashboardAccountRows([
    { name: 'IBKR Main', broker: 'IBKR', journal_balance: 12345.67 },
  ], '$')

  assert.deepEqual(rows, [{
    name: 'IBKR Main',
    broker: 'IBKR',
    balanceLabel: '$12,346',
  }])
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
