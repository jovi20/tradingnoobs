'use client'

import Link from 'next/link'
import { useState } from 'react'
import { Clock3, Loader2, RefreshCcw } from 'lucide-react'

import { useAuth } from '@/contexts/AuthContext'
import { EvidenceLinkedInsightSidecar } from '@/components/insights/EvidenceLinkedInsightSidecar'
import { formatTrustLabel, getReviewInboxSummary, getTimelineEmptyState } from '@/lib/adapters/timeline'
import { useInsightRuns } from '@/hooks/useInsightRuns'
import { useTimelineHomeData } from '@/hooks/useTimelineHomeData'
import type { TimelineView } from '@/lib/read-models'
import { FreshnessPill } from '@/components/timeline/FreshnessPill'
import { ReviewInboxCard } from '@/components/timeline/ReviewInboxCard'
import { TimelineEventCard } from '@/components/timeline/TimelineEventCard'
import { TimelineContextRail } from '@/components/timeline/TimelineContextRail'
import { TimelineSummaryStrip } from '@/components/timeline/TimelineSummaryStrip'

const VIEW_OPTIONS: Array<{ value: TimelineView; label: string }> = [
    { value: 'ALL', label: '全部' },
    { value: 'TRADING', label: '仅交易' },
    { value: 'REVIEW', label: '仅复盘' },
    { value: 'AI', label: '仅 AI' },
    { value: 'EXCEPTION', label: '仅异常' },
]

export default function TimelinePage() {
    const { token } = useAuth()
    const [view, setView] = useState<TimelineView>('ALL')
    const { timelineHome, isLoading, error, refresh } = useTimelineHomeData(token, view)
    const insightRunsQuery = useInsightRuns(token)

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (!timelineHome) {
        return (
            <div className="card p-8 text-center">
                <p className="text-slate-500">暂时没有可展示的时间线数据。</p>
            </div>
        )
    }

    const pageTrust = formatTrustLabel(timelineHome.pageMeta)
    const timelineEmptyState = getTimelineEmptyState(timelineHome.pageState)

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
                <div>
                    <div className="flex items-center gap-2">
                        <Clock3 className="w-5 h-5 text-slate-500" />
                        <h1 className="text-2xl font-bold">时间线</h1>
                    </div>
                    <p className="mt-1 text-sm text-slate-500">
                        先看最近发生了什么，再决定现在最值得处理什么。
                    </p>
                    <p className="mt-2 text-xs text-slate-400">
                        as of {new Date(timelineHome.pageMeta.as_of).toLocaleString('zh-CN')}
                        {pageTrust ? ` · ${pageTrust}` : ''}
                    </p>
                </div>

                <div className="flex flex-wrap items-center gap-2">
                    <div className="flex items-center gap-1 rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
                        {VIEW_OPTIONS.map((option) => (
                            <button
                                key={option.value}
                                type="button"
                                onClick={() => setView(option.value)}
                                className={`rounded-lg px-3 py-1.5 text-xs font-medium transition ${
                                    view === option.value
                                        ? 'bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white'
                                        : 'text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200'
                                }`}
                            >
                                {option.label}
                            </button>
                        ))}
                    </div>

                    <button
                        type="button"
                        onClick={() => refresh()}
                        className="btn btn-secondary flex items-center gap-2"
                    >
                        <RefreshCcw className="w-4 h-4" />
                        刷新
                    </button>
                </div>
            </div>

            <div className="grid gap-4 lg:grid-cols-[minmax(0,1.7fr)_minmax(280px,0.9fr)]">
                <div className="space-y-4">
                    <TimelineSummaryStrip summaryBar={timelineHome.summaryBar} />

                    <div className="card p-4 md:p-5">
                        <div className="mb-4 flex items-center justify-between">
                            <div>
                                <h2 className="text-lg font-semibold">Review Inbox</h2>
                                <p className="text-xs text-slate-500">{getReviewInboxSummary(timelineHome.reviewInbox)}</p>
                            </div>
                            <FreshnessPill trust={timelineHome.reviewInbox.trust} />
                        </div>

                        {timelineHome.reviewInbox.items.length === 0 ? (
                            <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-slate-500 dark:border-slate-700">
                                当前没有需要立即处理的 Review Inbox 项。
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {timelineHome.reviewInbox.items.map((item) => (
                                    <ReviewInboxCard key={item.public_id} item={item} />
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="card p-4 md:p-5">
                        <div className="mb-4">
                            <h2 className="text-lg font-semibold">主时间线</h2>
                            <p className="text-xs text-slate-500">按天分组，优先展示交易与需要处理的事件。</p>
                        </div>

                        {timelineHome.timeline.groups.length === 0 ? (
                            <div className="rounded-xl border border-dashed border-slate-200 p-6 text-center text-sm text-slate-500 dark:border-slate-700">
                                <p className="font-medium">{timelineEmptyState.title}</p>
                                <p className="mt-2">{timelineEmptyState.detail}</p>
                            </div>
                        ) : (
                            <div className="space-y-5">
                                {timelineHome.timeline.groups.map((group) => (
                                    <div key={group.group_key} className="space-y-3">
                                        <div className="flex items-center gap-2">
                                            <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
                                            <span className="text-xs font-semibold uppercase tracking-wide text-slate-400">
                                                {group.group_label}
                                            </span>
                                            <div className="h-px flex-1 bg-slate-200 dark:bg-slate-700" />
                                        </div>

                                        {group.items.map((event) => (
                                            <TimelineEventCard key={event.event_public_id} event={event} />
                                        ))}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                <div className="space-y-4">
                    <EvidenceLinkedInsightSidecar
                        runs={insightRunsQuery.data}
                        isLoading={insightRunsQuery.isLoading}
                        error={insightRunsQuery.error ? insightRunsQuery.error.message : null}
                        title="Timeline AI Sidecar"
                        onRefresh={() => insightRunsQuery.refetch()}
                    />
                    <TimelineContextRail
                        contextRail={timelineHome.contextRail}
                        onSelectView={(value) => setView(value as TimelineView)}
                    />
                </div>
            </div>
        </div>
    )
}
