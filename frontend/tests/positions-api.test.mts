import test from 'node:test'
import assert from 'node:assert/strict'

import { ApiRequestError, positionsAPI } from '../lib/api.ts'

test('uploadImportPreview sends owner account, file, and stable idempotency key', async () => {
  const calls: Array<{ input: string | URL | Request; init?: RequestInit }> = []
  const originalFetch = globalThis.fetch
  const responsePayload = {
    schema_version: 1,
    session_public_id: 'session-1',
    account_public_id: 'account-1',
    adapter_kind: 'GENERIC_BOOTSTRAP',
    file_format: 'CSV_UTF8',
    status: 'PREVIEW_READY',
    expires_at: '2026-07-26T10:00:00Z',
    total_rows: 1,
    valid_rows: 0,
    error_rows: 1,
    warning_rows: 0,
    rows: [],
    confirm_available: false,
  }
  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ input, init })
    return new Response(JSON.stringify(responsePayload), {
      status: 422,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    const file = new File(['symbol\nAAPL\n'], 'trades.csv', { type: 'text/csv' })
    const result = await positionsAPI.uploadImportPreview(
      'token-1',
      'account-1',
      file,
      'upload-key-1',
    )
    assert.equal(result.session_public_id, 'session-1')
    assert.equal(calls.length, 1)
    assert.equal(
      String(calls[0].input),
      'http://localhost:8000/api/positions/import/upload',
    )
    assert.equal(calls[0].init?.method, 'POST')
    const headers = calls[0].init?.headers as Record<string, string>
    assert.equal(headers.Authorization, 'Bearer token-1')
    assert.equal(headers['Idempotency-Key'], 'upload-key-1')
    assert.ok(calls[0].init?.body instanceof FormData)
    const form = calls[0].init?.body as FormData
    assert.equal(form.get('account_id'), 'account-1')
    assert.equal(form.get('adapter_kind'), 'GENERIC_BOOTSTRAP')
    assert.equal((form.get('file') as File).name, 'trades.csv')
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('import session read and template download remain authenticated', async () => {
  const calls: Array<{ input: string | URL | Request; init?: RequestInit }> = []
  const originalFetch = globalThis.fetch
  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ input, init })
    if (String(input).endsWith('/template')) {
      return new Response('asset_type,market\n', {
        status: 200,
        headers: { 'Content-Type': 'text/csv' },
      })
    }
    return new Response(JSON.stringify({
      schema_version: 1,
      session_public_id: 'session%2F1',
      account_public_id: 'account-1',
      adapter_kind: 'GENERIC_BOOTSTRAP',
      file_format: 'CSV_UTF8',
      status: 'PREVIEW_READY',
      expires_at: '2026-07-26T10:00:00Z',
      total_rows: 0,
      valid_rows: 0,
      error_rows: 0,
      warning_rows: 0,
      rows: [],
      confirm_available: false,
    }), {
      status: 200,
      headers: { 'Content-Type': 'application/json' },
    })
  }

  try {
    await positionsAPI.getImportSession('token-1', 'session/1')
    const blob = await positionsAPI.downloadImportTemplate('token-1')
    assert.equal(await blob.text(), 'asset_type,market\n')
    assert.equal(
      String(calls[0].input),
      'http://localhost:8000/api/positions/import/sessions/session%2F1',
    )
    assert.equal(
      String(calls[1].input),
      'http://localhost:8000/api/positions/import/template',
    )
    assert.equal(
      (calls[1].init?.headers as Record<string, string>).Authorization,
      'Bearer token-1',
    )
  } finally {
    globalThis.fetch = originalFetch
  }
})

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
    }, 'lifecycle-key-1')

    assert.equal(result.meta.source, 'MANUAL')
    assert.equal(calls.length, 1)
    assert.equal(String(calls[0].input), 'http://localhost:8000/api/trading-positions/tp-1/events')
    assert.equal(calls[0].init?.method, 'POST')
    assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer token-1')
    assert.equal(
      (calls[0].init?.headers as Record<string, string>)['Idempotency-Key'],
      'lifecycle-key-1',
    )
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
      reason: 'Broker correction',
      note: 'Broker correction',
    }, 'reverse-key-1', 'request-reverse-1')

    assert.equal(result.meta.source, 'MANUAL')
    assert.equal(calls.length, 1)
    assert.equal(String(calls[0].input), 'http://localhost:8000/api/trading-positions/tp-1/events/evt-2/reverse')
    assert.equal(calls[0].init?.method, 'POST')
    assert.equal((calls[0].init?.headers as Record<string, string>).Authorization, 'Bearer token-1')
    assert.equal((calls[0].init?.headers as Record<string, string>)['Idempotency-Key'], 'reverse-key-1')
    assert.equal((calls[0].init?.headers as Record<string, string>)['X-Request-ID'], 'request-reverse-1')
    assert.deepEqual(JSON.parse(String(calls[0].init?.body)), {
      occurred_at: '2026-04-04T12:00:00.000Z',
      reason: 'Broker correction',
      note: 'Broker correction',
    })
  } finally {
    globalThis.fetch = originalFetch
  }
})

test('voidTradingPosition posts an audited idempotent whole-position void', async () => {
  const calls: Array<{ input: string | URL | Request; init?: RequestInit }> = []
  const originalFetch = globalThis.fetch
  globalThis.fetch = async (input: string | URL | Request, init?: RequestInit) => {
    calls.push({ input, init })
    return new Response(JSON.stringify({
      data: { position_summary: { public_id: 'tp-1', status: 'VOID' } },
      meta: { source: 'MANUAL' },
    }), {
      status: 201,
      headers: { 'Content-Type': 'application/json' },
    })
  }
  try {
    await positionsAPI.voidTradingPosition('token-1', 'tp-1', {
      occurred_at: '2026-04-05T12:00:00.000Z',
      reason: 'Execution never occurred',
    }, 'void-key-1')
    assert.equal(String(calls[0].input), 'http://localhost:8000/api/trading-positions/tp-1/void')
    assert.equal(calls[0].init?.method, 'POST')
    assert.equal((calls[0].init?.headers as Record<string, string>)['Idempotency-Key'], 'void-key-1')
    assert.equal((calls[0].init?.headers as Record<string, string>)['X-Request-ID'], 'void-key-1')
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
      position_public_id: 'position-public-id',
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
      }, 'open-aapl-1'),
      (error: unknown) => {
        assert.ok(error instanceof ApiRequestError)
        assert.equal(error.status, 409)
        assert.equal(error.code, 'OPEN_POSITION_EXISTS')
        assert.equal(error.positionPublicId, 'position-public-id')
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
