import type { LifecycleDetailResponse } from '../read-models.ts'

export interface LifecycleDetailViewModel {
    positionTitle: string
    reviewStatus: LifecycleDetailResponse['data']['review_status']
    positionStatus: LifecycleDetailResponse['data']['position_summary']['status']
    positionRouteId: string
    truthPositionPublicId: string
    thesisSourceEventPublicId: string | null
    side: LifecycleDetailResponse['data']['position_summary']['side']
    accountLabel: string
    accountPublicId: string
    assetSymbol: string
    assetLabel: string
    instrumentLabel: string
    openedAt: string
    closedAt?: string
    realizedPnlNet?: number
    realizedPnlGross?: number
    totalFees?: number
    quantityOpened: number
    quantityClosed: number
    openQuantity: number
    averageOpenPrice?: number
    averageClosePrice?: number
    baseCurrency: string
    holdingPeriodSeconds?: number
    nodeCount: number
    thesis: string | null
    invalidationRule: string | null
    plannedExitRule: string | null
    sizingRationale: string | null
    checklistSnapshot: LifecycleDetailResponse['data']['thesis_block']['checklist_snapshot']
    summaryHeadline: string
    summaryBody: string
    keyNumbers: Array<{ label: string; value: string }>
    executionQuality?: string
    checklistMissCount?: number
    nodes: LifecycleDetailResponse['data']['lifecycle_thread']['nodes']
    cashEffects: LifecycleDetailResponse['data']['ledger_summary']['cash_effects']
    evidenceItems: LifecycleDetailResponse['data']['evidence_list']['items']
    emotionPoints: NonNullable<LifecycleDetailResponse['data']['emotion_path']>['points']
    aiItems: LifecycleDetailResponse['data']['ai_sidecar']['items']
    trust: LifecycleDetailResponse['meta']
}

export interface LifecycleNarrativeDraft {
    eventPublicId: string
    reason: string
    emotion: string
    confidence: number
    thesis: string
    invalidationRule: string
    plannedExitRule: string
    sizingRationale: string
    note: string
    checklistSnapshot: Record<string, boolean>
}

export interface LifecycleReversalAction {
    canReverse: boolean
    eventPublicId: string | null
    nodeType?: 'ADD' | 'REDUCE' | 'CLOSE'
    label: string
    reason: string
}

export type LifecycleWorkbenchTone = 'neutral' | 'positive' | 'negative' | 'warning' | 'danger' | 'entry' | 'exit' | 'review' | 'ai'
export type LifecycleViewport = 'desktop' | 'mobile'
export type LifecyclePageSection = 'header' | 'hero' | 'actions' | 'rail' | 'ai' | 'evidence' | 'cash' | 'migration' | 'legacy-fallback'
export type LifecycleLegacyPanelMode = 'hidden' | 'migration' | 'fallback'

export interface LifecycleLegacyPanelState {
    shouldRender: boolean
    mode: LifecycleLegacyPanelMode
    title: string
    description: string
}

export interface LifecyclePrimaryAction {
    canRun: boolean
    label: string
    reason: string
}

export interface LifecyclePrimaryActions {
    narrative: LifecyclePrimaryAction
    reversal: LifecyclePrimaryAction
    cashAdjustment: LifecyclePrimaryAction
}

export interface LifecycleEventRailItem {
    id: string
    type: string
    title: string
    summary: string
    dateLabel: string
    tone: LifecycleWorkbenchTone
}

export function adaptLifecycleDetail(response: LifecycleDetailResponse): LifecycleDetailViewModel {
    const summary = response.data.position_summary
    const thesis = response.data.thesis_block

    return {
        positionTitle: summary.title,
        reviewStatus: response.data.review_status,
        positionStatus: summary.status,
        positionRouteId: summary.route_public_id || summary.public_id,
        truthPositionPublicId: summary.public_id,
        thesisSourceEventPublicId: thesis.source_event_public_id || null,
        side: summary.side,
        accountLabel: summary.account.label,
        accountPublicId: summary.account.public_id,
        assetSymbol: summary.asset.symbol,
        assetLabel: summary.asset.asset_label,
        instrumentLabel: summary.asset.instrument_label,
        openedAt: summary.opened_at,
        closedAt: summary.closed_at,
        realizedPnlNet: summary.realized_pnl_net,
        realizedPnlGross: summary.realized_pnl_gross,
        totalFees: summary.total_fees,
        quantityOpened: Number(summary.quantity_opened || 0),
        quantityClosed: Number(summary.quantity_closed || 0),
        openQuantity: Number(
            summary.open_quantity
            ?? Math.max(0, Number(summary.quantity_opened || 0) - Number(summary.quantity_closed || 0))
        ),
        averageOpenPrice: summary.average_open_price,
        averageClosePrice: summary.average_close_price,
        baseCurrency: summary.base_currency || 'USD',
        holdingPeriodSeconds: summary.holding_period_seconds,
        nodeCount: response.data.lifecycle_thread.nodes.length,
        thesis: thesis.thesis || null,
        invalidationRule: thesis.invalidation_rule || null,
        plannedExitRule: thesis.planned_exit_rule || null,
        sizingRationale: thesis.sizing_rationale || null,
        checklistSnapshot: thesis.checklist_snapshot || [],
        summaryHeadline: response.data.result_summary.headline,
        summaryBody: response.data.result_summary.summary,
        keyNumbers: response.data.result_summary.key_numbers,
        executionQuality: response.data.execution_quality.execution_quality,
        checklistMissCount: response.data.execution_quality.checklist_miss_count,
        nodes: response.data.lifecycle_thread.nodes,
        cashEffects: response.data.ledger_summary.cash_effects,
        evidenceItems: response.data.evidence_list.items,
        emotionPoints: response.data.emotion_path?.points || [],
        aiItems: response.data.ai_sidecar.items,
        trust: response.meta,
    }
}

export function getLifecyclePreviewSummary(input: { reviewStatus: LifecycleDetailViewModel['reviewStatus']; nodeCount: number }) {
    if (input.reviewStatus === 'CLOSED_PENDING_REVIEW') {
        return `审计生命周期已同步 ${input.nodeCount} 个事件节点，这笔交易仍待完成复盘。`
    }
    if (input.reviewStatus === 'OPEN') {
        return `审计生命周期已同步 ${input.nodeCount} 个事件节点，这笔交易仍处于进行中。`
    }
    return `审计生命周期已同步 ${input.nodeCount} 个事件节点。`
}

export function getLifecyclePageSections(input: {
    hasTruthLifecycle: boolean
    hasLegacyPosition: boolean
    viewport: LifecycleViewport
}): LifecyclePageSection[] {
    if (!input.hasTruthLifecycle) {
        return input.hasLegacyPosition ? ['header', 'legacy-fallback'] : ['header']
    }

    if (input.viewport === 'mobile') {
        return ['header', 'hero', 'actions', 'rail', 'ai', 'evidence', 'cash', 'migration']
    }

    return ['header', 'hero', 'actions', 'rail', 'evidence', 'migration']
}

export function getLifecycleReviewTone(reviewStatus: LifecycleDetailViewModel['reviewStatus']): {
    label: string
    tone: LifecycleWorkbenchTone
    description: string
} {
    if (reviewStatus === 'CLOSED_PENDING_REVIEW') {
        return {
            label: '待复盘',
            tone: 'warning',
            description: '持仓已关闭，等待完成复盘。',
        }
    }
    if (reviewStatus === 'REVIEWED') {
        return {
            label: '已复盘',
            tone: 'positive',
            description: '复盘结论和证据已经记录。',
        }
    }
    return {
        label: '持仓中',
        tone: 'neutral',
        description: '持仓仍在进行，复盘会随事件持续补充。',
    }
}

export function getLifecycleLegacyPanelState(input: {
    hasTruthLifecycle: boolean
    hasLegacyPosition: boolean
}): LifecycleLegacyPanelState {
    if (input.hasTruthLifecycle && input.hasLegacyPosition) {
        return {
            shouldRender: true,
            mode: 'migration',
            title: '旧版数据迁移工具',
            description: '以下内容仍读取旧版持仓和批次数据（Position / TradeBatch），仅作为审计生命周期的迁移辅助信息。',
        }
    }

    if (input.hasTruthLifecycle) {
        return {
            shouldRender: false,
            mode: 'hidden',
            title: '旧版数据迁移工具',
            description: '当前审计生命周期没有关联的旧版持仓或批次数据。',
        }
    }

    return {
        shouldRender: input.hasLegacyPosition,
        mode: input.hasLegacyPosition ? 'fallback' : 'hidden',
        title: input.hasLegacyPosition ? '旧版持仓详情' : '旧版数据迁移工具',
        description: input.hasLegacyPosition
            ? '审计生命周期暂不可用，当前仅展示旧版持仓和批次数据。'
            : '当前没有可用的审计生命周期或旧版持仓数据。',
    }
}

function getLifecycleNodeTone(nodeType: string): LifecycleWorkbenchTone {
    if (nodeType === 'OPEN' || nodeType === 'ADD') return 'entry'
    if (nodeType === 'REDUCE' || nodeType === 'CLOSE') return 'exit'
    if (nodeType === 'REVIEW') return 'review'
    if (nodeType === 'AI_CONCLUSION') return 'ai'
    if (nodeType === 'REVERSAL' || nodeType === 'MANUAL_ADJUSTMENT') return 'warning'
    return 'neutral'
}

export function getLifecyclePrimaryActions(input: {
    hasEditableNarrativeEvent: boolean
    reversal: LifecycleReversalAction
}): LifecyclePrimaryActions {
    return {
        narrative: {
            canRun: input.hasEditableNarrativeEvent,
            label: '编辑交易叙事',
            reason: input.hasEditableNarrativeEvent
                ? '将叙事字段写回对应的 PositionEvent。'
                : '当前生命周期没有可编辑的 PositionEvent 标识。',
        },
        reversal: {
            canRun: input.reversal.canReverse,
            label: input.reversal.label,
            reason: input.reversal.reason,
        },
        cashAdjustment: {
            canRun: true,
            label: '记录现金调整',
            reason: '追加 MANUAL_ADJUSTMENT 事件和 CASH_ADJUSTMENT 流水，不改变 FIFO 持仓数量。',
        },
    }
}

export function getLifecycleEventRailItems(input: Pick<LifecycleDetailViewModel, 'nodes'>): LifecycleEventRailItem[] {
    const typeLabels: Record<string, string> = {
        OPEN: '开仓',
        ADD: '加仓',
        REDUCE: '减仓',
        CLOSE: '平仓',
        REVERSAL: '撤销',
        MANUAL_ADJUSTMENT: '现金调整',
        DIVIDEND: '股息',
        AI_CONCLUSION: 'AI 结论',
    }
    return input.nodes.map((node) => ({
        id: node.node_public_id,
        type: typeLabels[node.node_type] || '其他事件',
        title: node.title,
        summary: node.summary,
        dateLabel: new Date(node.occurred_at).toLocaleDateString('zh-CN'),
        tone: getLifecycleNodeTone(node.node_type),
    }))
}

export function getLifecycleEvidencePanelSummary(input: Pick<LifecycleDetailViewModel, 'evidenceItems' | 'cashEffects' | 'aiItems'>) {
    return {
        evidenceLabel: getLifecycleEvidenceSummary(input),
        cashLabel: getLifecycleCashEffectSummary(input),
        aiLabel: getLifecycleAiSidecarSummary(input),
    }
}

export function getLifecycleEmptyState(input: {
    hasTruthLifecycle: boolean
    hasLegacyPosition: boolean
}): { title: string; description: string } {
    if (!input.hasTruthLifecycle && input.hasLegacyPosition) {
        return {
            title: '审计生命周期不可用',
            description: '旧版 Position / TradeBatch 数据仍可读取，但审计生命周期暂时无法加载。',
        }
    }
    if (!input.hasTruthLifecycle) {
        return {
            title: '未找到持仓',
            description: '当前地址没有可用的审计生命周期或旧版持仓数据。',
        }
    }
    return {
        title: '审计生命周期已就绪',
        description: '交易生命周期数据可以正常读取。',
    }
}

export function getLifecyclePreviewBadge(reviewStatus: LifecycleDetailViewModel['reviewStatus']) {
    if (reviewStatus === 'CLOSED_PENDING_REVIEW') {
        return {
            label: '待复盘',
            className: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200',
        }
    }

    if (reviewStatus === 'OPEN') {
        return {
            label: '持仓中',
            className: 'bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-200',
        }
    }

    return {
        label: '已复盘',
        className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
    }
}

export function getLifecyclePreviewTrustSummary(trust: LifecycleDetailViewModel['trust']) {
    const labels: Record<string, string> = {
        FRESH: '最新',
        DELAYED: '延迟',
        STALE: '已过期',
        DEGRADED: '已降级',
        DERIVED: '系统计算',
        SYNCED: '同步数据',
        USER_INPUT: '用户录入',
        AI_GENERATED: 'AI 生成',
        FINAL: '已确认',
        ESTIMATED: '估算',
        INSUFFICIENT_SAMPLE: '样本不足',
        EARLY_SIGNAL: '早期信号',
        STABLE: '稳定',
    }
    const pieces = [labels[trust.freshness] || '状态未知', labels[trust.source] || '来源未知']
    if (trust.value_status) {
        pieces.push(labels[trust.value_status] || '数值状态未知')
    }
    if (trust.maturity) {
        pieces.push(labels[trust.maturity] || '成熟度未知')
    }
    return pieces.join(' · ')
}

export function getLifecycleCashEffectSummary(input: Pick<LifecycleDetailViewModel, 'cashEffects'>) {
    if (input.cashEffects.length === 0) {
        return '暂无现金流水'
    }

    const firstCurrency = input.cashEffects[0].currency
    const total = input.cashEffects.reduce((sum, item) => sum + Number(item.amount || 0), 0)
    return `${input.cashEffects.length} 条现金流水 · ${firstCurrency} ${total.toFixed(2)}`
}

export function getLifecycleEvidenceSummary(input: Pick<LifecycleDetailViewModel, 'evidenceItems'>) {
    if (input.evidenceItems.length === 0) {
        return '暂无证据'
    }

    const refTypes = Array.from(new Set(input.evidenceItems.map((item) => item.ref_type)))
    return `${input.evidenceItems.length} 条证据 · ${refTypes.join(', ')}`
}

export function getLifecycleAiSidecarSummary(input: Pick<LifecycleDetailViewModel, 'aiItems'>) {
    if (input.aiItems.length === 0) {
        return '暂无 AI 结论'
    }

    const evidenceCount = input.aiItems.reduce((sum, item) => sum + (item.evidence_refs?.length || 0), 0)
    return `${input.aiItems.length} 条 AI 结论 · ${evidenceCount} 条证据`
}

export function getLifecycleNarrativeDraft(lifecycle: LifecycleDetailViewModel): LifecycleNarrativeDraft {
    const targetEventPublicId = lifecycle.thesisSourceEventPublicId || lifecycle.nodes[0]?.node_public_id || ''
    const targetNode = lifecycle.nodes.find((node) => node.node_public_id === targetEventPublicId) || lifecycle.nodes[0]

    return {
        eventPublicId: targetEventPublicId,
        reason: targetNode?.summary || '',
        emotion: targetNode?.emotion || '',
        confidence: targetNode?.confidence || 3,
        thesis: lifecycle.thesis || '',
        invalidationRule: lifecycle.invalidationRule || '',
        plannedExitRule: lifecycle.plannedExitRule || '',
        sizingRationale: lifecycle.sizingRationale || '',
        note: targetNode?.note || '',
        checklistSnapshot: Object.fromEntries(
            (lifecycle.checklistSnapshot || []).map((item) => [item.label, Boolean(item.checked)])
        ),
    }
}

export function getLifecycleReversalAction(input: Pick<LifecycleDetailViewModel, 'nodes'>): LifecycleReversalAction {
    const reversibleTypes = new Set(['ADD', 'REDUCE', 'CLOSE'])
    const reversedEventPublicIds = new Set(
        input.nodes
            .filter((node) => node.node_type === 'REVERSAL' && node.reverses_event_public_id)
            .map((node) => String(node.reverses_event_public_id))
    )
    const latestReversibleNode = [...input.nodes]
        .reverse()
        .find((node) => reversibleTypes.has(node.node_type) && !reversedEventPublicIds.has(node.node_public_id))

    if (latestReversibleNode) {
        return {
            canReverse: true,
            eventPublicId: latestReversibleNode.node_public_id,
            nodeType: latestReversibleNode.node_type as 'ADD' | 'REDUCE' | 'CLOSE',
            label: '撤销最新事件',
            reason: '将追加 REVERSAL 节点并重放 FIFO，不会静默改写历史事件。',
        }
    }

    if (input.nodes.some((node) => node.node_type === 'OPEN')) {
        return {
            canReverse: false,
            eventPublicId: null,
            label: '暂无可撤销事件',
            reason: '开仓事件需要完整的作废或归档语义，当前不可撤销。',
        }
    }

    return {
        canReverse: false,
        eventPublicId: null,
        label: '暂无可撤销事件',
        reason: '当前生命周期还没有可撤销的交易事件。',
    }
}
