import type { LifecycleDetailResponse } from '../read-models.ts'

export interface LifecycleDetailViewModel {
    positionTitle: string
    reviewStatus: LifecycleDetailResponse['data']['review_status']
    positionRouteId: string
    truthPositionPublicId: string
    nodeCount: number
    thesis: string | null
    summaryHeadline: string
    summaryBody: string
    keyNumbers: Array<{ label: string; value: string }>
    nodes: LifecycleDetailResponse['data']['lifecycle_thread']['nodes']
    trust: LifecycleDetailResponse['meta']
}

export function adaptLifecycleDetail(response: LifecycleDetailResponse): LifecycleDetailViewModel {
    return {
        positionTitle: response.data.position_summary.title,
        reviewStatus: response.data.review_status,
        positionRouteId: response.data.position_summary.public_id,
        truthPositionPublicId: response.data.position_summary.public_id,
        nodeCount: response.data.lifecycle_thread.nodes.length,
        thesis: response.data.thesis_block.thesis || null,
        summaryHeadline: response.data.result_summary.headline,
        summaryBody: response.data.result_summary.summary,
        keyNumbers: response.data.result_summary.key_numbers,
        nodes: response.data.lifecycle_thread.nodes,
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
