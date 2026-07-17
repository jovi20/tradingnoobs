import type { ReviewInboxItem, SummaryBar, TimelineEventCard, TimelineEventType } from '../read-models.ts'
import type { TimelineHomeViewModel } from './timeline.ts'

export type WorkbenchTone =
    | 'neutral'
    | 'positive'
    | 'negative'
    | 'warning'
    | 'danger'
    | 'entry'
    | 'exit'
    | 'review'
    | 'ai'

export interface TimelineSummaryMetric {
    key: 'trades' | 'review_rate' | 'alerts'
    label: string
    value: string
    detail: string
    tone: WorkbenchTone
}

export interface TimelineImpactLabel {
    label: string
    tone: WorkbenchTone
}

export type MobileWorkbenchSection = 'summary' | 'filters' | 'review' | 'timeline' | 'context'

const EVENT_TYPE_LABELS: Record<TimelineEventType, string> = {
    OPEN: '开仓',
    ADD: '加仓',
    REDUCE: '减仓',
    CLOSE: '平仓',
    REVIEW_COMPLETED: '已复盘',
    AI_INSIGHT: 'AI 洞察',
    CHECKLIST_MISS: '检查项遗漏',
    LOSING_STREAK_ALERT: '连续亏损提醒',
    DATA_STALE: '数据延迟',
    SYNC_EXCEPTION: '同步异常',
}

function formatPeriodLabel(value: string): string {
    const normalized = value.trim().toUpperCase().replaceAll(' ', '_')
    const labels: Record<string, string> = {
        THIS_WEEK: '本周',
        TODAY: '今日',
        LAST_7_DAYS: '近 7 日',
    }
    return labels[normalized] ?? value
}

export function getTimelineEventTypeLabel(eventType: TimelineEventType): string {
    return EVENT_TYPE_LABELS[eventType]
}

export function buildTimelineSummaryMetrics(summaryBar: SummaryBar): TimelineSummaryMetric[] {
    const rawReviewRate = summaryBar.review_completion_rate
    const reviewRate = typeof rawReviewRate === 'number' && Number.isFinite(rawReviewRate)
        ? rawReviewRate
        : null
    const reviewRateLabel = reviewRate !== null
        ? `${Math.round(reviewRate * 100)}%`
        : '-'

    return [
        {
            key: 'trades',
            label: '交易',
            value: String(summaryBar.trade_count),
            detail: formatPeriodLabel(summaryBar.period_label),
            tone: 'neutral',
        },
        {
            key: 'review_rate',
            label: '复盘完成',
            value: reviewRateLabel,
            detail: '纪律覆盖率',
            tone: reviewRate !== null
                ? reviewRate >= 0.6 ? 'positive' : 'warning'
                : 'neutral',
        },
        {
            key: 'alerts',
            label: '重点提醒',
            value: String(summaryBar.priority_alert_count),
            detail: summaryBar.priority_alert_count > 0 ? '需要处理' : '无待办',
            tone: summaryBar.priority_alert_count > 0 ? 'warning' : 'positive',
        },
    ]
}

export function formatTimelineEventImpact(event: TimelineEventCard): TimelineImpactLabel | null {
    const amount = event.impact_value?.amount
    if (amount === undefined) return null
    const currency = event.impact_value?.currency ? ` ${event.impact_value.currency}` : ''
    const sign = amount > 0 ? '+' : ''
    return {
        label: `${sign}${amount.toLocaleString(undefined, { maximumFractionDigits: 2 })}${currency}`,
        tone: amount < 0 ? 'negative' : 'positive',
    }
}

export function formatTimelineEventMeta(event: TimelineEventCard): string {
    const pieces = [event.instrument.symbol]
    if (event.account?.label) pieces.push(event.account.label)
    pieces.push(new Date(event.occurred_at).toLocaleString('zh-CN'))
    return pieces.join(' · ')
}

export function getTimelineEventTone(eventType: TimelineEventType): WorkbenchTone {
    switch (eventType) {
        case 'OPEN':
        case 'ADD':
            return 'entry'
        case 'REDUCE':
        case 'CLOSE':
            return 'exit'
        case 'REVIEW_COMPLETED':
            return 'review'
        case 'AI_INSIGHT':
            return 'ai'
        case 'CHECKLIST_MISS':
        case 'LOSING_STREAK_ALERT':
        case 'DATA_STALE':
        case 'SYNC_EXCEPTION':
            return 'danger'
        default:
            return 'neutral'
    }
}

export function getReviewInboxKindLabel(kind: ReviewInboxItem['kind']): string {
    switch (kind) {
        case 'DAILY_LOSS_LIMIT':
            return '单日亏损上限'
        case 'PORTFOLIO_CONCENTRATION':
            return '组合集中度'
        case 'DRAWDOWN_ALERT':
            return '组合回撤'
        case 'MISSING_REVIEW':
            return '待补复盘'
        case 'MISSING_THESIS':
            return '待补交易计划'
        case 'CHECKLIST_MISS':
            return '纪律偏离'
        case 'LOSING_STREAK':
            return '连续亏损'
        case 'DATA_STALE':
            return '数据延迟'
        case 'SYNC_EXCEPTION':
            return '同步异常'
        default:
            return kind
    }
}

export function getReviewInboxTone(item: Pick<ReviewInboxItem, 'kind' | 'severity'>): WorkbenchTone {
    if (item.severity === 'CRITICAL') return 'danger'
    if (item.kind === 'DAILY_LOSS_LIMIT' || item.kind === 'DRAWDOWN_ALERT') return 'danger'
    if (item.severity === 'WARNING' || item.kind === 'PORTFOLIO_CONCENTRATION') return 'warning'
    if (item.kind === 'MISSING_REVIEW') return 'review'
    return 'neutral'
}

export function getWorkbenchMobileSectionOrder(timelineHome: Pick<TimelineHomeViewModel, 'reviewInbox'>): MobileWorkbenchSection[] {
    if (timelineHome.reviewInbox.total > 0) {
        return ['summary', 'filters', 'review', 'timeline', 'context']
    }
    return ['summary', 'filters', 'timeline', 'context']
}
