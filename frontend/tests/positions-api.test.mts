import test from 'node:test'
import assert from 'node:assert/strict'

import { positionsAPI } from '../lib/api.ts'

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
