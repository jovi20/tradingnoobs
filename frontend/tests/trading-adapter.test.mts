import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildTruthTradeEventFromBatchForm,
} from '../lib/adapters/trading.ts'

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
