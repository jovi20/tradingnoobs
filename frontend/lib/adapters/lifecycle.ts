import type { LifecycleDetailResponse } from '../read-models.ts'

export interface LifecycleDetailViewModel {
    positionTitle: string
    reviewStatus: LifecycleDetailResponse['data']['review_status']
    positionStatus: LifecycleDetailResponse['data']['position_summary']['status']
    positionRouteId: string
    truthPositionPublicId: string
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

export function adaptLifecycleDetail(response: LifecycleDetailResponse): LifecycleDetailViewModel {
    const summary = response.data.position_summary
    const thesis = response.data.thesis_block

    return {
        positionTitle: summary.title,
        reviewStatus: response.data.review_status,
        positionStatus: summary.status,
        positionRouteId: summary.public_id,
        truthPositionPublicId: summary.public_id,
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
        return `新真相层已同步 ${input.nodeCount} 个生命周期节点，且这笔交易仍待完成复盘。`
    }
    if (input.reviewStatus === 'OPEN') {
        return `新真相层已同步 ${input.nodeCount} 个生命周期节点，这笔交易仍处于进行中。`
    }
    return `新真相层已同步 ${input.nodeCount} 个生命周期节点。`
}

export function getLifecyclePreviewBadge(reviewStatus: LifecycleDetailViewModel['reviewStatus']) {
    if (reviewStatus === 'CLOSED_PENDING_REVIEW') {
        return {
            label: 'Pending Review',
            className: 'bg-amber-100 text-amber-700 dark:bg-amber-500/20 dark:text-amber-200',
        }
    }

    if (reviewStatus === 'OPEN') {
        return {
            label: 'Open',
            className: 'bg-sky-100 text-sky-700 dark:bg-sky-500/20 dark:text-sky-200',
        }
    }

    return {
        label: 'Reviewed',
        className: 'bg-emerald-100 text-emerald-700 dark:bg-emerald-500/20 dark:text-emerald-200',
    }
}

export function getLifecyclePreviewTrustSummary(trust: LifecycleDetailViewModel['trust']) {
    const pieces = [trust.freshness.toLowerCase(), trust.source.toLowerCase()]
    if (trust.value_status) {
        pieces.push(trust.value_status.toLowerCase())
    }
    if (trust.maturity) {
        pieces.push(trust.maturity.toLowerCase())
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
        return '暂无 evidence'
    }

    const refTypes = Array.from(new Set(input.evidenceItems.map((item) => item.ref_type)))
    return `${input.evidenceItems.length} 条 evidence · ${refTypes.join(', ')}`
}

export function getLifecycleAiSidecarSummary(input: Pick<LifecycleDetailViewModel, 'aiItems'>) {
    if (input.aiItems.length === 0) {
        return '暂无 AI 结论'
    }

    const evidenceCount = input.aiItems.reduce((sum, item) => sum + (item.evidence_refs?.length || 0), 0)
    return `${input.aiItems.length} 条 AI 结论 · ${evidenceCount} 条证据`
}
