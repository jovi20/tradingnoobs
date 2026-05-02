import type {
    ReviewInboxItem,
    TimelineEventCard,
    TimelineGroup,
    TimelineHomeResponse,
    TimelineView,
    TrustMeta,
} from '../read-models.ts'

export interface TimelineHomeViewModel {
    pageState: TimelineHomeResponse['data']['page_state']
    activeView: TimelineView
    summaryBar: TimelineHomeResponse['data']['summary_bar']
    reviewInbox: {
        total: number
        highPriority: number
        items: ReviewInboxItem[]
        trust?: TrustMeta
    }
    timeline: {
        groups: TimelineGroup[]
        nextCursor?: string
        trust?: TrustMeta
    }
    contextRail: TimelineHomeResponse['data']['context_rail']
    pageMeta: TrustMeta
}

export function adaptTimelineHome(response: TimelineHomeResponse): TimelineHomeViewModel {
    return {
        pageState: response.data.page_state,
        activeView: response.data.timeline.active_view,
        summaryBar: response.data.summary_bar,
        reviewInbox: {
            total: response.data.review_inbox.counts.total,
            highPriority: response.data.review_inbox.counts.high_priority,
            items: response.data.review_inbox.items,
            trust: response.data.review_inbox.trust,
        },
        timeline: {
            groups: response.data.timeline.groups,
            nextCursor: response.data.timeline.next_cursor,
            trust: response.data.timeline.trust,
        },
        contextRail: response.data.context_rail,
        pageMeta: response.meta,
    }
}

export function formatTrustLabel(trust?: TrustMeta): string | null {
    if (!trust) return null
    const pieces = [trust.freshness.toLowerCase()]
    if (trust.value_status) pieces.push(trust.value_status.toLowerCase())
    if (trust.maturity) pieces.push(trust.maturity.toLowerCase())
    return pieces.join(' · ')
}

export function getReviewInboxSummary(input: { total: number; highPriority: number }): string {
    if (input.total === 0) {
        return '当前没有需要立即处理的 Review Inbox 项。'
    }
    return input.highPriority > 0
        ? `${input.total} 项待处理 · ${input.highPriority} 项高优先级`
        : `${input.total} 项待处理`
}

export function getTimelineEmptyState(pageState: TimelineHomeViewModel['pageState']) {
    switch (pageState) {
        case 'ZERO':
            return {
                title: '先记录第一笔交易，时间线才会开始形成。',
                detail: '当前还没有任何交易或账户数据，建议先从快速记录开始。',
            }
        case 'SMALL_DATA':
            return {
                title: '已经有基础数据，但现在更适合看事件线和单笔复盘。',
                detail: '继续记录更多交易后，Review Inbox 和宏观分析会更稳定。',
            }
        case 'EMPTY_CONFIGURED':
            return {
                title: '账户已经配置好，但还没有新的事件进入时间线。',
                detail: '接下来可以新增一笔交易，或者检查同步配置。',
            }
        default:
            return {
                title: '当前还没有时间线事件。',
                detail: '先记录几笔交易后，这里会开始形成线程。',
            }
    }
}

export function getTimelineEventAccent(event: TimelineEventCard['event_type']): string {
    switch (event) {
        case 'OPEN':
        case 'ADD':
            return 'bg-emerald-500'
        case 'REDUCE':
        case 'CLOSE':
            return 'bg-amber-500'
        case 'REVIEW_COMPLETED':
            return 'bg-sky-500'
        case 'AI_INSIGHT':
            return 'bg-slate-700'
        case 'CHECKLIST_MISS':
        case 'LOSING_STREAK_ALERT':
        case 'DATA_STALE':
        case 'SYNC_EXCEPTION':
            return 'bg-red-500'
        default:
            return 'bg-slate-400'
    }
}

export function getInboxSeverityAccent(severity: ReviewInboxItem['severity']): string {
    switch (severity) {
        case 'CRITICAL':
            return 'border-red-300 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-900/20 dark:text-red-300'
        case 'WARNING':
            return 'border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-900/20 dark:text-amber-300'
        case 'NOTICE':
            return 'border-sky-300 bg-sky-50 text-sky-700 dark:border-sky-900/60 dark:bg-sky-900/20 dark:text-sky-300'
        default:
            return 'border-slate-300 bg-slate-50 text-slate-700 dark:border-slate-700 dark:bg-slate-800/80 dark:text-slate-300'
    }
}
