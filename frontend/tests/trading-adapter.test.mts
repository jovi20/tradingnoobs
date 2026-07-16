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
    reason: '价格、数量和盈亏已由审计生命周期（TradingPosition / PositionEvent）接管。',
  })

  assert.deepEqual(getLegacyBatchMutationState(false), {
    canMutate: true,
    label: '编辑',
    reason: '尚未建立审计生命周期，暂时保留旧批次的迁移编辑入口。',
  })
})

test('getLegacyPositionDeleteState disables destructive legacy deletes once truth lifecycle is available', () => {
  assert.deepEqual(getLegacyPositionDeleteState(true), {
    canDelete: false,
    label: '审计记录受保护',
    reason: 'TradingPosition 已成为审计依据，修正应通过撤销或调整流程完成。',
  })

  assert.deepEqual(getLegacyPositionDeleteState(false), {
    canDelete: true,
    label: '删除',
    reason: '尚未建立审计生命周期，暂时保留旧版持仓的迁移删除入口。',
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

test('getTruthFirstWriteFallbackState blocks silent legacy writes unless migration fallback is explicit', () => {
  assert.deepEqual(getTruthFirstWriteFallbackState(true, false), {
    canWriteLegacyFallback: false,
    label: '审计事件已就绪',
    reason: '审计生命周期（TradingPosition / PositionEvent）可用，日常加仓和平仓必须写入审计事件。',
  })

  assert.deepEqual(getTruthFirstWriteFallbackState(false, false), {
    canWriteLegacyFallback: false,
    label: '审计生命周期不可用',
    reason: '日常加仓和平仓需要审计生命周期；旧版批次写入仅限明确启用的迁移模式，不能静默执行。',
  })

  assert.deepEqual(getTruthFirstWriteFallbackState(false, true), {
    canWriteLegacyFallback: true,
    label: '已启用迁移模式',
    reason: '审计生命周期暂不可用，本次将明确写入旧版批次；完成后需要重新同步审计生命周期。',
  })
})
