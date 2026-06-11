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

test('buildMarketDataStatus exposes degraded reason when present', () => {
  const status = buildMarketDataStatus({
    provider: 'yfinance',
    freshness: 'FRESH',
    degraded: true,
    degraded_reason: 'finnhub failed: quota exceeded',
    source_refs: ['provider:finnhub', 'provider:yfinance', 'symbol:MSFT'],
  })

  assert.equal(status.providerLabel, 'YFinance')
  assert.equal(status.freshnessLabel, '实时')
  assert.equal(status.tone, 'warning')
  assert.equal(status.degradedReason, 'finnhub failed: quota exceeded')
  assert.deepEqual(status.sourceRefs, ['provider:finnhub', 'provider:yfinance', 'symbol:MSFT'])
})
