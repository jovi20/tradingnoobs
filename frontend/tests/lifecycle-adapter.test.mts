import test from 'node:test'
import assert from 'node:assert/strict'

import {
  adaptLifecycleDetail,
  getLifecycleCashEffectSummary,
  getLifecyclePreviewBadge,
  getLifecyclePreviewSummary,
  getLifecyclePreviewTrustSummary,
} from '../lib/adapters/lifecycle.ts'
import * as lifecycleAdapter from '../lib/adapters/lifecycle.ts'

test('adaptLifecycleDetail maps truth lifecycle payload into preview-friendly view model', () => {
  const result = adaptLifecycleDetail({
    data: {
      review_status: 'CLOSED_PENDING_REVIEW',
      position_summary: {
        public_id: 'tp-1',
        title: 'AAPL',
        status: 'CLOSED',
        side: 'LONG',
        account: { public_id: 'acct-1', label: 'IBKR Main' },
        asset: { symbol: 'AAPL', asset_label: 'Apple Inc.', instrument_label: 'Apple Spot' },
        opened_at: '2026-04-01T09:30:00Z',
        closed_at: '2026-04-05T16:00:00Z',
        realized_pnl_gross: 180,
        realized_pnl_net: 180,
        total_fees: 0,
        holding_period_seconds: 3600,
        pnl_basis: {
          cost_basis_method: 'FIFO',
          realized_definition: 'EVENT_REALIZED',
          unrealized_definition: 'MARK_TO_MARKET',
          fee_treatment: 'NET_INCLUDED',
          fx_treatment: 'EVENT_TIME_ACCOUNT_CCY',
        },
      },
      thesis_block: {
        source_event_public_id: 'evt-1',
        thesis: 'Initial breakout entry',
        checklist_snapshot: [{ label: 'pre_market', checked: true }],
      },
      lifecycle_thread: {
        nodes: [
          { node_public_id: 'evt-1', node_type: 'OPEN', occurred_at: '2026-04-01T09:30:00Z', title: 'AAPL OPEN', summary: 'Open' },
          { node_public_id: 'evt-2', node_type: 'CLOSE', occurred_at: '2026-04-05T16:00:00Z', title: 'AAPL CLOSE', summary: 'Close' },
        ],
      },
      result_summary: {
        headline: 'AAPL lifecycle',
        summary: '包含 2 个事件节点。',
        key_numbers: [{ label: 'Realized Net', value: '180' }],
      },
      execution_quality: {
        execution_quality: 'GOOD',
        checklist_miss_count: 1,
      },
      discipline_profile: null,
      emotion_path: {
        points: [
          { occurred_at: '2026-04-01T09:30:00Z', emotion: 'Confident', confidence: 4 },
        ],
      },
      ledger_summary: {
        account_currency: 'USD',
        cash_effects: [
          {
            ledger_entry_public_id: 'ledger-1',
            entry_type: 'REALIZED_PNL',
            amount: 180,
            amount_account_ccy: 180,
            currency: 'USD',
            occurred_at: '2026-04-05T16:00:00Z',
            source_event_public_id: 'evt-2',
            description: 'AAPL realized PnL',
          },
        ],
      },
      evidence_list: {
        items: [
          { ref_type: 'POSITION_EVENT', public_id: 'evt-1', label: 'OPEN', href: '/positions/tp-1' },
          { ref_type: 'LEDGER_ENTRY', public_id: 'ledger-1', label: 'REALIZED_PNL', href: '/positions/tp-1' },
        ],
      },
      ai_sidecar: {
        items: [
          {
            insight_run_public_id: 'run-1',
            insight_artifact_public_id: 'artifact-1',
            title: '减仓节奏偏慢',
            conclusion: '第一段盈利兑现没有按计划执行，回吐扩大。',
            coverage_summary: '覆盖 OPEN/CLOSE 事件与 realized PnL ledger。',
            confidence_label: 'MEDIUM',
            recommended_action: '复盘首次减仓规则',
            evidence_refs: [
              { ref_type: 'POSITION_EVENT', public_id: 'evt-2', label: 'CLOSE', href: '/positions/tp-1' },
              { ref_type: 'LEDGER_ENTRY', public_id: 'ledger-1', label: 'REALIZED_PNL', href: '/positions/tp-1' },
            ],
            href: '/insights/artifact-1',
          },
        ],
      },
    },
    meta: {
      as_of: '2026-04-05T16:00:00Z',
      freshness: 'FRESH',
      source: 'DERIVED',
      maturity: 'EARLY_SIGNAL',
      value_status: 'FINAL',
    },
  })

  assert.equal(result.positionTitle, 'AAPL')
  assert.equal(result.reviewStatus, 'CLOSED_PENDING_REVIEW')
  assert.equal(result.positionStatus, 'CLOSED')
  assert.equal(result.assetLabel, 'Apple Inc.')
  assert.equal(result.accountLabel, 'IBKR Main')
  assert.equal(result.nodeCount, 2)
  assert.equal(result.thesis, 'Initial breakout entry')
  assert.equal(result.executionQuality, 'GOOD')
  assert.equal(result.checklistMissCount, 1)
  assert.equal(result.cashEffects.length, 1)
  assert.equal(result.cashEffects[0].entry_type, 'REALIZED_PNL')
  assert.equal(result.evidenceItems.length, 2)
  assert.equal(result.aiItems.length, 1)
  assert.equal(result.aiItems[0].title, '减仓节奏偏慢')
  assert.equal(result.aiItems[0].evidence_refs?.length, 2)
  assert.equal(result.emotionPoints.length, 1)
  assert.equal(getLifecycleCashEffectSummary(result), '1 条现金流水 · USD 180.00')
})

test('lifecycle detail summaries make evidence and AI sidecar auditable', () => {
  assert.equal(typeof lifecycleAdapter.getLifecycleEvidenceSummary, 'function')
  assert.equal(typeof lifecycleAdapter.getLifecycleAiSidecarSummary, 'function')

  assert.equal(
    lifecycleAdapter.getLifecycleEvidenceSummary({
      evidenceItems: [
        { ref_type: 'POSITION_EVENT', public_id: 'evt-1', label: 'OPEN', href: '/positions/tp-1' },
        { ref_type: 'LEDGER_ENTRY', public_id: 'ledger-1', label: 'REALIZED_PNL', href: '/positions/tp-1' },
      ],
    }),
    '2 条 evidence · POSITION_EVENT, LEDGER_ENTRY'
  )

  assert.equal(
    lifecycleAdapter.getLifecycleAiSidecarSummary({
      aiItems: [
        {
          title: '减仓节奏偏慢',
          conclusion: '第一段盈利兑现没有按计划执行，回吐扩大。',
          evidence_refs: [
            { ref_type: 'POSITION_EVENT', public_id: 'evt-2', label: 'CLOSE', href: '/positions/tp-1' },
            { ref_type: 'LEDGER_ENTRY', public_id: 'ledger-1', label: 'REALIZED_PNL', href: '/positions/tp-1' },
          ],
        },
      ],
    }),
    '1 条 AI 结论 · 2 条证据'
  )
})

test('getLifecyclePreviewSummary produces stable copy', () => {
  assert.equal(
    getLifecyclePreviewSummary({ reviewStatus: 'CLOSED_PENDING_REVIEW', nodeCount: 2 }),
    '新真相层已同步 2 个生命周期节点，且这笔交易仍待完成复盘。'
  )
})

test('getLifecyclePreviewBadge maps review status to stable label and style token', () => {
  assert.deepEqual(getLifecyclePreviewBadge('CLOSED_PENDING_REVIEW'), {
    label: 'Pending Review',
    className: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200',
  })

  assert.deepEqual(getLifecyclePreviewBadge('OPEN'), {
    label: 'Open',
    className: 'bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-200',
  })

  assert.deepEqual(getLifecyclePreviewBadge('REVIEWED'), {
    label: 'Reviewed',
    className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
  })
})

test('getLifecyclePreviewTrustSummary surfaces freshness, source, and value status', () => {
  assert.equal(
    getLifecyclePreviewTrustSummary({
      as_of: '2026-04-05T16:00:00Z',
      freshness: 'FRESH',
      source: 'DERIVED',
      maturity: 'EARLY_SIGNAL',
      value_status: 'FINAL',
    }),
    'fresh · derived · final · early_signal'
  )
})
