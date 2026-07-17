import test from 'node:test'
import assert from 'node:assert/strict'

import { ApiRequestError, positionsAPI } from '../lib/api.ts'

test('createTradingPositionTradeEvent posts price and quantity changes to the truth event route', async () => {
  const calls: Array<{ input: string | URL | Request; init?: RequestInit }> = []
  const originalFetch = globalThis.fetch

  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ input, init })
    return new Response(JSON.stringify({
      data: { position_summary: { public_id: 'tp-1' } },
      meta: { source: 'MANUAL' },
    }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    const result = await positionsAPI.createTradingPositionTradeEvent('token-1', 'tp-1', {
      event_type: 'ADD',
      quantity: 3,
      price: 190,
      currency: 'USD',
      occurred_at: '2026-04-03T15:30:00.000Z',
      reason: 'Add on continuation',
    })

    assert.equal(result.meta.source, 'MANUAL')
    assert.equal(calls.length, 1)
    assert.equal(String(calls[0].input), 'http://localhost:8000/api/trading-positions/tp-1/events')
    assert.equal(calls[0].init?.method, 'POST')
    assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer token-1')
    assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
      event_type: 'ADD',
      quantity: 3,
      price: 190,
      currency: 'USD',
      occurred_at: '2026-04-03T15:30:00.000Z',
      reason: 'Add on continuation',
    })
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('reverseTradingPositionTradeEvent posts guarded reversals to the truth event route', async () => {
  const calls: Array<{ input: string | URL | Request; init?: RequestInit }> = []
  const originalFetch = globalThis.fetch

  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ input, init })
    return new Response(JSON.stringify({
      data: { position_summary: { public_id: 'tp-1' } },
      meta: { source: 'MANUAL' },
    }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    const result = await positionsAPI.reverseTradingPositionTradeEvent('token-1', 'tp-1', 'evt-2', {
      occurred_at: '2026-04-04T12:00:00.000Z',
      note: 'Broker correction',
    })

    assert.equal(result.meta.source, 'MANUAL')
    assert.equal(calls.length, 1)
    assert.equal(String(calls[0].input), 'http://localhost:8000/api/trading-positions/tp-1/events/evt-2/reverse')
    assert.equal(calls[0].init?.method, 'POST')
    assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer token-1')
    assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
      occurred_at: '2026-04-04T12:00:00.000Z',
      note: 'Broker correction',
    })
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('positions API client does not expose disabled manual adjustment writes', () => {
  assert.equal('createTradingPositionManualAdjustment' in positionsAPI, false)
})

test('checkOpen sends the complete identity in query parameters without path-splitting symbols', async () => {
  const calls: Array<string> = []
  const originalFetch = globalThis.fetch
  globalThis.fetch = async (input: string | URL | Request) => {
    calls.push(String(input))
    return new Response('null', {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    const result = await positionsAPI.checkOpen('token-1', {
      account_id: 'acct-1',
      symbol: 'BTC/USD',
      exchange_code: 'COINBASE',
      direction: 'LONG',
      asset_type: 'CRYPTO',
      market: 'CRYPTO',
      instrument_type: 'SPOT',
      quote_currency: 'USD',
    })

    assert.equal(result, null)
    assert.equal(calls.length, 1)
    const url = new URL(calls[0])
    assert.equal(url.pathname, '/api/positions/check/open')
    assert.equal(url.searchParams.get('symbol'), 'BTC/USD')
    assert.equal(url.searchParams.get('exchange_code'), 'COINBASE')
    assert.equal(url.searchParams.get('direction'), 'LONG')
    assert.equal(url.searchParams.get('account_id'), 'acct-1')
    assert.equal(url.searchParams.get('asset_type'), 'CRYPTO')
    assert.equal(url.searchParams.get('market'), 'CRYPTO')
    assert.equal(url.searchParams.get('instrument_type'), 'SPOT')
    assert.equal(url.searchParams.get('quote_currency'), 'USD')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('duplicate OPEN conflict surfaces a readable localized structured API error', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({
    detail: {
      code: 'OPEN_POSITION_EXISTS',
      message: 'An open position already exists for this identity and direction',
      field: 'direction',
    },
  }), {
    status: 409,
    headers: { 'Content-Type': 'application/json' },
  })

  try {
    await assert.rejects(
      positionsAPI.create('token-1', {
        account_id: 1,
        symbol: 'AAPL',
        exchange_code: 'NASDAQ',
        asset_type: 'STOCK',
        direction: 'LONG',
        entry_price: 200,
        quantity: 1,
        entry_time: '2026-07-17T10:00:00.000Z',
        asset_metadata: {
          core_type: 'STOCK',
          market: 'US',
          currency: 'USD',
          instrument: 'SPOT',
        },
      }),
      (error: unknown) => {
        assert.ok(error instanceof ApiRequestError)
        assert.equal(error.status, 409)
        assert.equal(error.code, 'OPEN_POSITION_EXISTS')
        assert.equal(error.message, '同一账户中已存在相同标的和方向的未平仓仓位，请加仓到已有仓位。')
        assert.doesNotMatch(error.message, /\[object Object\]/)
        return true
      },
    )
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('unknown structured API errors prefer detail.message and retain detail.code', async () => {
  const originalFetch = globalThis.fetch
  globalThis.fetch = async () => new Response(JSON.stringify({
    detail: {
      code: 'IDENTITY_INVALID',
      message: 'Identity failed validation',
    },
  }), {
    status: 422,
    headers: { 'Content-Type': 'application/json' },
  })

  try {
    await assert.rejects(
      positionsAPI.checkOpen('token-1', {
        account_id: 'acct-1',
        symbol: 'AAPL',
        exchange_code: 'NASDAQ',
        direction: 'LONG',
        asset_type: 'STOCK',
        market: 'US',
        instrument_type: 'SPOT',
        quote_currency: 'USD',
      }),
      (error: unknown) => {
        assert.ok(error instanceof ApiRequestError)
        assert.equal(error.status, 422)
        assert.equal(error.code, 'IDENTITY_INVALID')
        assert.equal(error.message, 'Identity failed validation')
        return true
      },
    )
  } finally {
    globalThis.fetch = originalFetch
  }
})
