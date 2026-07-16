import test from 'node:test'
import assert from 'node:assert/strict'

import {
  adaptLifecycleDetail,
  getLifecycleCashEffectSummary,
  getLifecycleReversalAction,
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
        route_public_id: 'legacy-position-1',
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
        quantity_opened: 10,
        quantity_closed: 10,
        open_quantity: 0,
        average_open_price: 185,
        average_close_price: 203,
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
  assert.equal(result.positionRouteId, 'legacy-position-1')
  assert.equal(result.truthPositionPublicId, 'tp-1')
  assert.equal(result.openQuantity, 0)
  assert.equal(result.averageOpenPrice, 185)
  assert.equal(result.assetLabel, 'Apple Inc.')
  assert.equal(result.accountLabel, 'IBKR Main')
  assert.equal(result.nodeCount, 2)
  assert.equal(result.thesisSourceEventPublicId, 'evt-1')
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

test('lifecycle narrative draft targets the thesis source event for truth writes', () => {
  const lifecycle = adaptLifecycleDetail({
    data: {
      review_status: 'OPEN',
      position_summary: {
        public_id: 'tp-1',
        title: 'AAPL',
        status: 'OPEN',
        side: 'LONG',
        account: { public_id: 'acct-1', label: 'IBKR Main' },
        asset: { symbol: 'AAPL', asset_label: 'Apple Inc.', instrument_label: 'Apple Spot' },
        opened_at: '2026-04-01T09:30:00Z',
        pnl_basis: {
          cost_basis_method: 'FIFO',
          realized_definition: 'EVENT_REALIZED',
          unrealized_definition: 'MARK_TO_MARKET',
          fee_treatment: 'NET_INCLUDED',
          fx_treatment: 'EVENT_TIME_ACCOUNT_CCY',
        },
      },
      thesis_block: {
        source_event_public_id: 'evt-open',
        thesis: 'Opening thesis',
        invalidation_rule: 'Lose prior low',
        planned_exit_rule: 'Scale at 2R',
        sizing_rationale: 'Half size until confirmation',
        checklist_snapshot: [
          { label: 'pre_market', checked: true },
          { label: 'risk_check', checked: false },
        ],
      },
      lifecycle_thread: {
        nodes: [
          {
            node_public_id: 'evt-open',
            node_type: 'OPEN',
            occurred_at: '2026-04-01T09:30:00Z',
            title: 'AAPL OPEN',
            summary: 'Initial breakout entry',
            emotion: 'Focused',
            confidence: 4,
            note: 'Followed the entry plan.',
          },
          { node_public_id: 'evt-add', node_type: 'ADD', occurred_at: '2026-04-02T09:30:00Z', title: 'AAPL ADD', summary: 'Added on continuation' },
        ],
      },
      result_summary: { headline: 'AAPL lifecycle', summary: '包含 2 个事件节点。', key_numbers: [] },
      execution_quality: {},
      discipline_profile: null,
      emotion_path: null,
      ledger_summary: { account_currency: 'USD', cash_effects: [] },
      evidence_list: { items: [] },
      ai_sidecar: { items: [] },
    },
    meta: {
      as_of: '2026-04-01T09:30:00Z',
      freshness: 'FRESH',
      source: 'DERIVED',
    },
  })

  assert.equal(typeof lifecycleAdapter.getLifecycleNarrativeDraft, 'function')
  assert.deepEqual(lifecycleAdapter.getLifecycleNarrativeDraft(lifecycle), {
    eventPublicId: 'evt-open',
    reason: 'Initial breakout entry',
    emotion: 'Focused',
    confidence: 4,
    thesis: 'Opening thesis',
    invalidationRule: 'Lose prior low',
    plannedExitRule: 'Scale at 2R',
    sizingRationale: 'Half size until confirmation',
    note: 'Followed the entry plan.',
    checklistSnapshot: {
      pre_market: true,
      risk_check: false,
    },
  })
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
    '2 条证据 · POSITION_EVENT, LEDGER_ENTRY'
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

test('getLifecycleReversalAction only exposes the latest unreversed truth trade event', () => {
  assert.deepEqual(
    getLifecycleReversalAction({
      nodes: [
        {
          node_public_id: 'evt-open',
          node_type: 'OPEN',
          occurred_at: '2026-04-01T09:30:00Z',
          title: 'MSFT OPEN',
          summary: 'Initial entry',
        },
        {
          node_public_id: 'evt-reduce',
          node_type: 'REDUCE',
          occurred_at: '2026-04-03T15:30:00Z',
          title: 'MSFT REDUCE',
          summary: 'Scale out',
        },
      ],
    }),
    {
      canReverse: true,
      eventPublicId: 'evt-reduce',
      nodeType: 'REDUCE',
      label: '撤销最新事件',
      reason: '将追加 REVERSAL 节点并重放 FIFO，不会静默改写历史事件。',
    },
  )

  assert.deepEqual(
    getLifecycleReversalAction({
      nodes: [
        {
          node_public_id: 'evt-open',
          node_type: 'OPEN',
          occurred_at: '2026-04-01T09:30:00Z',
          title: 'MSFT OPEN',
          summary: 'Initial entry',
        },
        {
          node_public_id: 'evt-reduce',
          node_type: 'REDUCE',
          occurred_at: '2026-04-03T15:30:00Z',
          title: 'MSFT REDUCE',
          summary: 'Scale out',
        },
        {
          node_public_id: 'evt-reversal',
          node_type: 'REVERSAL',
          occurred_at: '2026-04-04T12:00:00Z',
          title: 'MSFT REVERSAL',
          summary: 'Broker correction',
          reverses_event_public_id: 'evt-reduce',
        },
      ],
    }),
    {
      canReverse: false,
      eventPublicId: null,
      label: '暂无可撤销事件',
      reason: '开仓事件需要完整的作废或归档语义，当前不可撤销。',
    },
  )
})

test('getLifecyclePreviewSummary produces stable copy', () => {
  assert.equal(
    getLifecyclePreviewSummary({ reviewStatus: 'CLOSED_PENDING_REVIEW', nodeCount: 2 }),
    '审计生命周期已同步 2 个事件节点，这笔交易仍待完成复盘。'
  )
})

test('getLifecyclePreviewBadge maps review status to stable label and style token', () => {
  assert.deepEqual(getLifecyclePreviewBadge('CLOSED_PENDING_REVIEW'), {
    label: '待复盘',
    className: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200',
  })

  assert.deepEqual(getLifecyclePreviewBadge('OPEN'), {
    label: '持仓中',
    className: 'bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-200',
  })

  assert.deepEqual(getLifecyclePreviewBadge('REVIEWED'), {
    label: '已复盘',
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
    '最新 · 系统计算 · 已确认 · 早期信号'
  )
})

test('lifecycle page sections keep truth story before legacy migration tools', () => {
  assert.deepEqual(lifecycleAdapter.getLifecyclePageSections({ hasTruthLifecycle: true, hasLegacyPosition: true, viewport: 'desktop' }), [
    'header',
    'hero',
    'actions',
    'rail',
    'evidence',
    'migration',
  ])

  assert.deepEqual(lifecycleAdapter.getLifecyclePageSections({ hasTruthLifecycle: true, hasLegacyPosition: true, viewport: 'mobile' }), [
    'header',
    'hero',
    'actions',
    'rail',
    'ai',
    'evidence',
    'cash',
    'migration',
  ])

  assert.deepEqual(lifecycleAdapter.getLifecyclePageSections({ hasTruthLifecycle: false, hasLegacyPosition: true, viewport: 'desktop' }), [
    'header',
    'legacy-fallback',
  ])
})

test('lifecycle review tone maps status to labels and readable tones', () => {
  assert.deepEqual(lifecycleAdapter.getLifecycleReviewTone('OPEN'), {
    label: '持仓中',
    tone: 'neutral',
    description: '持仓仍在进行，复盘会随事件持续补充。',
  })
  assert.deepEqual(lifecycleAdapter.getLifecycleReviewTone('CLOSED_PENDING_REVIEW'), {
    label: '待复盘',
    tone: 'warning',
    description: '持仓已关闭，等待完成复盘。',
  })
  assert.deepEqual(lifecycleAdapter.getLifecycleReviewTone('REVIEWED'), {
    label: '已复盘',
    tone: 'positive',
    description: '复盘结论和证据已经记录。',
  })
})

test('lifecycle legacy panel state makes old DTO surfaces migration-only when truth exists', () => {
  assert.deepEqual(lifecycleAdapter.getLifecycleLegacyPanelState({ hasTruthLifecycle: true, hasLegacyPosition: true }), {
    shouldRender: true,
    mode: 'migration',
    title: '旧版数据迁移工具',
    description: '以下内容仍读取旧版持仓和批次数据（Position / TradeBatch），仅作为审计生命周期的迁移辅助信息。',
  })

  assert.deepEqual(lifecycleAdapter.getLifecycleLegacyPanelState({ hasTruthLifecycle: true, hasLegacyPosition: false }), {
    shouldRender: false,
    mode: 'hidden',
    title: '旧版数据迁移工具',
    description: '当前审计生命周期没有关联的旧版持仓或批次数据。',
  })

  assert.deepEqual(lifecycleAdapter.getLifecycleLegacyPanelState({ hasTruthLifecycle: false, hasLegacyPosition: true }), {
    shouldRender: true,
    mode: 'fallback',
    title: '旧版持仓详情',
    description: '审计生命周期暂不可用，当前仅展示旧版持仓和批次数据。',
  })
})

test('lifecycle primary actions combine narrative, reversal, and cash adjustment states', () => {
  const actions = lifecycleAdapter.getLifecyclePrimaryActions({
    hasEditableNarrativeEvent: true,
    reversal: {
      canReverse: true,
      eventPublicId: 'evt-reduce',
      nodeType: 'REDUCE',
      label: '撤销最新事件',
      reason: '将追加 REVERSAL 节点并重放 FIFO，不会静默改写历史事件。',
    },
  })

  assert.equal(actions.narrative.canRun, true)
  assert.equal(actions.narrative.label, '编辑交易叙事')
  assert.equal(actions.reversal.canRun, true)
  assert.equal(actions.reversal.label, '撤销最新事件')
  assert.equal(actions.cashAdjustment.canRun, true)
  assert.equal(actions.cashAdjustment.label, '记录现金调整')
})

test('lifecycle event rail items expose node tone and date labels', () => {
  const items = lifecycleAdapter.getLifecycleEventRailItems({
    nodes: [
      { node_public_id: 'evt-open', node_type: 'OPEN', occurred_at: '2026-06-01T09:30:00Z', title: 'OPEN', summary: 'Opened thesis' },
      { node_public_id: 'evt-ai', node_type: 'AI_CONCLUSION', occurred_at: '2026-06-02T09:30:00Z', title: 'AI', summary: 'AI conclusion' },
    ],
  })

  assert.deepEqual(items, [
    { id: 'evt-open', type: '开仓', title: 'OPEN', summary: 'Opened thesis', dateLabel: '2026/6/1', tone: 'entry' },
    { id: 'evt-ai', type: 'AI 结论', title: 'AI', summary: 'AI conclusion', dateLabel: '2026/6/2', tone: 'ai' },
  ])
})

test('lifecycle evidence panel summary combines evidence, cash, and AI counts', () => {
  assert.deepEqual(lifecycleAdapter.getLifecycleEvidencePanelSummary({
    evidenceItems: [
      { ref_type: 'POSITION_EVENT', public_id: 'evt-open', label: 'OPEN', href: '/positions/tp-1' },
    ],
    cashEffects: [
      {
        ledger_entry_public_id: 'ledger-1',
        entry_type: 'REALIZED_PNL',
        amount: 25,
        amount_account_ccy: 25,
        currency: 'USD',
        occurred_at: '2026-06-02T09:30:00Z',
      },
    ],
    aiItems: [{ title: 'AI conclusion', conclusion: 'Evidence-backed note.' }],
  }), {
    evidenceLabel: '1 条证据 · POSITION_EVENT',
    cashLabel: '1 条现金流水 · USD 25.00',
    aiLabel: '1 条 AI 结论 · 0 条证据',
  })
})

test('lifecycle empty state copy distinguishes missing truth from missing all data', () => {
  assert.equal(
    lifecycleAdapter.getLifecycleEmptyState({ hasTruthLifecycle: false, hasLegacyPosition: true }).title,
    '审计生命周期不可用'
  )
  assert.equal(
    lifecycleAdapter.getLifecycleEmptyState({ hasTruthLifecycle: false, hasLegacyPosition: false }).title,
    '未找到持仓'
  )
})
