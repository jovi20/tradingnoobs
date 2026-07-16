import assert from 'node:assert/strict'
import test from 'node:test'

import {
  buildMarketDataStatus,
  getMarketFreshnessLabel,
  getMarketFreshnessTone,
  getMarketProviderLabel,
} from '../lib/adapters/market-data.ts'

test('market freshness labels and tones stay stable', () => {
  assert.equal(getMarketFreshnessLabel('FRESH'), '实时')
  assert.equal(getMarketFreshnessLabel('CACHED'), '缓存')
  assert.equal(getMarketFreshnessLabel('UNAVAILABLE'), '不可用')
  assert.equal(getMarketFreshnessLabel('UNKNOWN_VENDOR_STATE'), '未知')

  assert.equal(getMarketFreshnessTone({ freshness: 'FRESH', degraded: false }), 'positive')
  assert.equal(getMarketFreshnessTone({ freshness: 'CACHED', degraded: false }), 'neutral')
  assert.equal(getMarketFreshnessTone({ freshness: 'UNAVAILABLE', degraded: true }), 'danger')
  assert.equal(getMarketFreshnessTone({ freshness: 'FRESH', degraded: true }), 'warning')
})

test('market provider labels are readable', () => {
  assert.equal(getMarketProviderLabel('finnhub'), 'Finnhub')
  assert.equal(getMarketProviderLabel('yfinance'), 'YFinance')
  assert.equal(getMarketProviderLabel('akshare'), 'AKShare')
  assert.equal(getMarketProviderLabel(undefined), '自动路由')
})

test('buildMarketDataStatus replaces raw provider failures with localized user copy', () => {
  const status = buildMarketDataStatus({
    provider: 'yfinance',
    freshness: 'FRESH',
    degraded: true,
    degraded_reason: 'finnhub failed: quota exceeded',
    source_refs: ['provider:finnhub', 'provider:yfinance', 'symbol:MSFT'],
    as_of: '2026-07-15T10:00:00Z',
  })

  assert.equal(status.providerLabel, 'YFinance')
  assert.equal(status.freshnessLabel, '实时')
  assert.equal(status.tone, 'warning')
  assert.equal(status.degradedReason, '主行情源暂不可用，已自动切换备用数据源。')
  assert.deepEqual(status.sourceRefs, ['provider:finnhub', 'provider:yfinance', 'symbol:MSFT'])
  assert.equal(status.asOf, '2026-07-15T10:00:00Z')

  const unavailable = buildMarketDataStatus({
    freshness: 'UNAVAILABLE',
    degraded: true,
    degraded_reason: 'all providers failed',
  })
  assert.equal(unavailable.degradedReason, '行情源暂不可用，请稍后重试。')
  assert.equal(unavailable.asOf, null)
})
