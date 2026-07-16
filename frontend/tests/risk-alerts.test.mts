import test from 'node:test'
import assert from 'node:assert/strict'

import {
  formatRiskAlertReason,
  getRiskAlertSeverityLabel,
  getRiskAlertTone,
  summarizeRiskAlerts,
} from '../lib/adapters/risk-alerts.ts'

test('getRiskAlertTone maps alert severity to dashboard tones', () => {
  assert.equal(getRiskAlertTone('CRITICAL'), 'danger')
  assert.equal(getRiskAlertTone('WARNING'), 'warning')
  assert.equal(getRiskAlertTone('NOTICE'), 'review')
  assert.equal(getRiskAlertTone('INFO'), 'neutral')
})

test('risk alert severity and fallback reasons use Chinese user copy', () => {
  assert.equal(getRiskAlertSeverityLabel('CRITICAL'), '严重')
  assert.equal(getRiskAlertSeverityLabel('WARNING'), '警告')
  assert.equal(formatRiskAlertReason({
    kind: 'CONCENTRATION',
    reason: 'Concentration warning.',
  }), '单一持仓敞口已超过组合集中度阈值。')
  assert.equal(formatRiskAlertReason({
    kind: 'DRAWDOWN',
    reason: '组合回撤已超过设定的风险阈值。',
  }), '组合回撤已超过设定的风险阈值。')
})

test('summarizeRiskAlerts prefers critical alert summary', () => {
  const summary = summarizeRiskAlerts([
    {
      public_id: 'risk:concentration:MSFT',
      kind: 'CONCENTRATION',
      severity: 'WARNING',
      summary: 'MSFT 持仓集中度达到 38%',
      reason: 'Concentration warning.',
      recommended_action: { kind: 'OPEN_DASHBOARD', label: '查看组合结构', href: '/dashboard' },
      source_refs: [],
      trust: { freshness: 'FRESH', source: 'DERIVED' },
    },
    {
      public_id: 'risk:daily_loss:2026-06-11',
      kind: 'DAILY_LOSS_LIMIT',
      severity: 'CRITICAL',
      summary: '今日亏损已达到 -6.00%',
      reason: 'Daily equity change crossed the -5% critical threshold.',
      recommended_action: { kind: 'OPEN_DASHBOARD', label: '查看组合风险', href: '/dashboard' },
      source_refs: [],
      trust: { freshness: 'FRESH', source: 'DERIVED' },
    },
  ])

  assert.equal(summary.headline, '今日亏损已达到 -6.00%')
  assert.equal(summary.tone, 'danger')
  assert.equal(summary.detail, '当日损益已超过设定的风险阈值。')
  assert.equal(summary.countLabel, '2 条提醒')
})

test('summarizeRiskAlerts returns calm copy for empty alerts', () => {
  const summary = summarizeRiskAlerts([])

  assert.equal(summary.headline, '暂无风险预警')
  assert.equal(summary.tone, 'positive')
  assert.equal(summary.countLabel, '0 条提醒')
})
