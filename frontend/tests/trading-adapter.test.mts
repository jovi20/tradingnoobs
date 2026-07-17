import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildTruthTradeEventFromBatchForm,
  getLegacyBatchMutationState,
  getLegacyPositionDeleteState,
  getLegacyReviewDisplayState,
  isAsciiExchangeCodeInput,
  isValidExchangeCodeInput,
  isValidSymbolInput,
  normalizeAsciiIdentityInput,
  normalizeExchangeCodeInput,
  normalizeReleasePositionIdentityInput,
  normalizeSymbolInput,
} from '../lib/adapters/trading.ts'

test('exchange-code input normalization trims, uppercases, and identifies non-ASCII input', () => {
  assert.equal(normalizeExchangeCodeInput('  nasdaq  '), 'NASDAQ')
  assert.equal(normalizeExchangeCodeInput('coinbase.us'), 'COINBASE.US')
  assert.equal(normalizeSymbolInput('  btc/usd  '), 'BTC/USD')
  assert.equal(isAsciiExchangeCodeInput('NYSE-ARCA_1'), true)
  assert.equal(isAsciiExchangeCodeInput('NASDAQ交易所'), false)
  assert.equal(isAsciiExchangeCodeInput('NÁSDAQ'), false)
  for (const spoof of ['ß', 'ı', 'ﬀ', 'naſdaq']) {
    assert.equal(isValidExchangeCodeInput(spoof), false)
  }
  assert.equal(isValidExchangeCodeInput('a'.repeat(32)), true)
  assert.equal(isValidExchangeCodeInput('a'.repeat(33)), false)
  assert.equal(isValidSymbolInput('BTC/USD'), true)
  assert.equal(isValidSymbolInput('a'.repeat(50)), true)
  assert.equal(isValidSymbolInput('a'.repeat(51)), false)
  assert.equal(isValidSymbolInput('ſpy'), false)
  assert.equal(isValidExchangeCodeInput(`NASDAQ\u00a0`), false)
  assert.equal(isValidSymbolInput(`\u2003AAPL`), false)
  assert.throws(() => normalizeAsciiIdentityInput(`NASDAQ\u00a0`), /must be ASCII/)
})

test('release identity rejects non-ASCII in all six raw tokens before ASCII trim and uppercase', () => {
  const validIdentity = {
    symbol: 'btc/usd',
    exchange_code: 'coinbase',
    asset_type: 'crypto',
    market: 'crypto',
    instrument_type: 'spot',
    quote_currency: 'usd',
  }

  assert.deepEqual(
    normalizeReleasePositionIdentityInput({
      symbol: '\t btc/usd \r',
      exchange_code: '\n coinbase \v',
      asset_type: '\f crypto ',
      market: ' crypto\t',
      instrument_type: ' spot\n',
      quote_currency: '\r usd ',
    }),
    {
      ok: true,
      identity: {
        symbol: 'BTC/USD',
        exchange_code: 'COINBASE',
        asset_type: 'CRYPTO',
        market: 'CRYPTO',
        instrument_type: 'SPOT',
        quote_currency: 'USD',
      },
    },
  )
  assert.deepEqual(
    normalizeReleasePositionIdentityInput({
      ...validIdentity,
      asset_type: ' etf ',
      market: ' us ',
    }),
    {
      ok: true,
      identity: {
        symbol: 'BTC/USD',
        exchange_code: 'COINBASE',
        asset_type: 'FUND',
        market: 'US',
        instrument_type: 'SPOT',
        quote_currency: 'USD',
      },
    },
  )

  const fields = [
    'symbol',
    'exchange_code',
    'asset_type',
    'market',
    'instrument_type',
    'quote_currency',
  ] as const
  for (const nonAsciiWhitespace of ['\u00a0', '\u2003']) {
    for (const field of fields) {
      const result = normalizeReleasePositionIdentityInput({
        ...validIdentity,
        [field]: `${nonAsciiWhitespace}${validIdentity[field]}`,
      })
      assert.deepEqual(result, { ok: false, field, reason: 'NON_ASCII' })
    }
  }

  assert.deepEqual(
    normalizeReleasePositionIdentityInput({
      ...validIdentity,
      symbol: ' ',
      quote_currency: `USD\u00a0`,
    }),
    { ok: false, field: 'quote_currency', reason: 'NON_ASCII' },
  )
})

test('buildTruthTradeEventFromBatchForm maps entry batches to ADD truth events', () => {
  const event = buildTruthTradeEventFromBatchForm(
    {
      type: 'ENTRY',
      price: 190,
      quantity: 3,
      time: '2026-04-03T15:30:00.000Z',
      reason: 'Add on continuation',
      emotion: 'calm',
      confidence: 4,
    },
    {
      total_quantity: 5,
      asset_metadata: { currency: 'USD' },
    },
  )

  assert.deepEqual(event, {
    event_type: 'ADD',
    quantity: 3,
    price: 190,
    currency: 'USD',
    occurred_at: '2026-04-03T15:30:00.000Z',
    reason: 'Add on continuation',
    emotion: 'calm',
    confidence: 4,
  })
})

test('buildTruthTradeEventFromBatchForm maps partial and full exits to REDUCE or CLOSE', () => {
  assert.equal(
    buildTruthTradeEventFromBatchForm(
      { type: 'EXIT', price: 210, quantity: 2, time: '2026-04-03T15:30:00.000Z' },
      { total_quantity: 5, asset_metadata: { currency: 'USD' } },
    ).event_type,
    'REDUCE',
  )

  assert.equal(
    buildTruthTradeEventFromBatchForm(
      { type: 'EXIT', price: 210, quantity: 5, time: '2026-04-03T15:30:00.000Z' },
      { total_quantity: 5, asset_metadata: { currency: 'USD' } },
    ).event_type,
    'CLOSE',
  )
})

test('getLegacyBatchMutationState keeps legacy batch edits read-only on every product path', () => {
  assert.deepEqual(getLegacyBatchMutationState(true), {
    canMutate: false,
    label: '迁移只读',
    reason: '旧版批次在普通产品入口中只读；价格、数量和盈亏修正必须走审计事件。',
  })

  assert.deepEqual(getLegacyBatchMutationState(false), {
    canMutate: false,
    label: '迁移只读',
    reason: '旧版批次在普通产品入口中只读；价格、数量和盈亏修正必须走审计事件。',
  })
})

test('getLegacyPositionDeleteState keeps hard delete disabled on every product path', () => {
  assert.deepEqual(getLegacyPositionDeleteState(true), {
    canDelete: false,
    label: '审计记录受保护',
    reason: '旧版持仓不能从普通产品入口硬删除；修正应通过审计撤销、作废或归档流程完成。',
  })

  assert.deepEqual(getLegacyPositionDeleteState(false), {
    canDelete: false,
    label: '审计记录受保护',
    reason: '旧版持仓不能从普通产品入口硬删除；修正应通过审计撤销、作废或归档流程完成。',
  })
})

test('getLegacyReviewDisplayState labels legacy reviews as migration-only beside truth lifecycle', () => {
  assert.deepEqual(getLegacyReviewDisplayState(true, true), {
    shouldDisplay: true,
    isMigrationOnly: true,
    label: '旧版复盘迁移记录',
    reason: '这段复盘来自旧版 Position.trade_review，仅作为迁移参考；新的结构化叙事请写入审计事件。',
  })
  assert.deepEqual(getLegacyReviewDisplayState(true, false), {
    shouldDisplay: false,
    isMigrationOnly: true,
    label: '旧版复盘迁移记录',
    reason: '审计生命周期已接管详情叙事，且旧版 Position.trade_review 为空。',
  })
  assert.deepEqual(getLegacyReviewDisplayState(false, true), {
    shouldDisplay: true,
    isMigrationOnly: false,
    label: '交易复盘',
    reason: '尚未建立审计生命周期，当前继续展示旧版复盘记录。',
  })
})
