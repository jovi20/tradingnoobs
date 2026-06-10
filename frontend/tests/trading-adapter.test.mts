import test from 'node:test'
import assert from 'node:assert/strict'

import {
  buildTruthTradeEventFromBatchForm,
  getLegacyBatchMutationState,
  getLegacyPositionDeleteState,
  getLegacyReviewDisplayState,
  getTruthFirstWriteFallbackState,
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

test('getLegacyBatchMutationState disables legacy batch edits once truth lifecycle is available', () => {
  assert.deepEqual(getLegacyBatchMutationState(true), {
    canMutate: false,
    label: '迁移只读',
    reason: '价格、数量和 PnL 已由 TradingPosition / PositionEvent truth path 接管。',
  })

  assert.deepEqual(getLegacyBatchMutationState(false), {
    canMutate: true,
    label: '编辑',
    reason: '尚未解析到 truth lifecycle，保留 legacy batch 迁移编辑入口。',
  })
})

test('getLegacyPositionDeleteState disables destructive legacy deletes once truth lifecycle is available', () => {
  assert.deepEqual(getLegacyPositionDeleteState(true), {
    canDelete: false,
    label: 'Truth 受保护',
    reason: 'TradingPosition 已成为审计真相，删除需要走后续 reversal / adjustment 流程。',
  })

  assert.deepEqual(getLegacyPositionDeleteState(false), {
    canDelete: true,
    label: '删除',
    reason: '尚未解析到 truth lifecycle，保留 legacy position 迁移删除入口。',
  })
})

test('getLegacyReviewDisplayState labels legacy reviews as migration-only beside truth lifecycle', () => {
  assert.deepEqual(getLegacyReviewDisplayState(true, true), {
    shouldDisplay: true,
    isMigrationOnly: true,
    label: 'Legacy review migration',
    reason: '复盘正文仍来自 legacy Position.trade_review；新的结构化叙事请写入 truth narrative 或 evidence-linked artifact。',
  })
  assert.deepEqual(getLegacyReviewDisplayState(true, false), {
    shouldDisplay: false,
    isMigrationOnly: true,
    label: 'Legacy review migration',
    reason: 'truth lifecycle 已接管详情主叙事，且 legacy Position.trade_review 为空。',
  })
  assert.deepEqual(getLegacyReviewDisplayState(false, true), {
    shouldDisplay: true,
    isMigrationOnly: false,
    label: '交易复盘',
    reason: '尚未解析到 truth lifecycle，继续展示 legacy Position.trade_review。',
  })
})

test('getTruthFirstWriteFallbackState blocks silent legacy writes unless migration fallback is explicit', () => {
  assert.deepEqual(getTruthFirstWriteFallbackState(true, false), {
    canWriteLegacyFallback: false,
    label: 'Truth write path ready',
    reason: 'TradingPosition / PositionEvent truth path is available; ordinary writes must use the truth event route.',
  })

  assert.deepEqual(getTruthFirstWriteFallbackState(false, false), {
    canWriteLegacyFallback: false,
    label: 'Truth lifecycle unavailable',
    reason: '普通加仓/平仓需要 TradingPosition truth lifecycle；legacy batch 写入已降级为 migration fallback，不能静默作为普通路径执行。',
  })

  assert.deepEqual(getTruthFirstWriteFallbackState(false, true), {
    canWriteLegacyFallback: true,
    label: 'Migration fallback enabled',
    reason: 'Truth lifecycle 暂不可用，本次将显式使用 legacy batch migration fallback；完成后需要重新同步 truth lifecycle。',
  })
})
