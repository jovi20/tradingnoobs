import Link from 'next/link'
import { ChevronRight } from 'lucide-react'

import {
    formatTimelineEventImpact,
    formatTimelineEventMeta,
    getTimelineEventTypeLabel,
    getTimelineEventTone,
} from '@/lib/adapters/timeline-workbench'
import { getTimelineEventHref } from '@/lib/adapters/timeline'
import type { TimelineEventCard } from '@/lib/read-models'
import { cn } from '@/lib/cn'
import { StatusPill } from '@/components/ui/StatusPill'
import { toneDot, toneText } from '@/components/ui/tone'

interface TimelineEventCardV2Props {
    event: TimelineEventCard
}

export function TimelineEventCardV2({ event }: TimelineEventCardV2Props) {
    const impact = formatTimelineEventImpact(event)
    const tone = getTimelineEventTone(event.event_type)
    const href = getTimelineEventHref(event)
    const hasDetail = Boolean(
        event.thesis_excerpt ||
        event.invalidation_excerpt ||
        event.checklist_summary ||
        event.ai_annotation ||
        event.emotion ||
        event.confidence ||
        event.tags?.length
    )

    return (
        <article className="group relative rounded-lg border border-line bg-panel p-4 shadow-panel transition-colors hover:border-line-strong dark:shadow-none">
            <div className="flex items-start gap-3.5">
                {/* Time spine marker */}
                <div className="relative mt-1 flex flex-col items-center self-stretch">
                    <span className={cn('h-2.5 w-2.5 shrink-0 rounded-full ring-4 ring-panel-subtle', toneDot[tone])} />
                    <span className="mt-1 w-px flex-1 bg-line" />
                </div>

                <div className="min-w-0 flex-1">
                    <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                                <StatusPill tone={tone}>{getTimelineEventTypeLabel(event.event_type)}</StatusPill>
                                <span className="text-xs text-ink-faint">{formatTimelineEventMeta(event)}</span>
                            </div>
                            <h3 className="mt-2 text-base font-semibold tracking-tight text-ink">
                                {event.headline}
                            </h3>
                            <p className="mt-1.5 text-sm leading-6 text-ink-muted">
                                {event.summary}
                            </p>
                        </div>
                        {impact && (
                            <div className="shrink-0 text-right">
                                <p className="text-[10px] font-medium text-ink-faint">影响</p>
                                <p className={cn('mt-1 text-sm font-semibold tn-nums', toneText[tone])}>{impact.label}</p>
                            </div>
                        )}
                    </div>

                    {hasDetail && (
                        <details className="group/details mt-3 rounded-md border border-line bg-panel-subtle/60 px-4 py-2.5">
                            <summary className="flex cursor-pointer items-center gap-1.5 text-xs font-semibold text-ink-muted transition-colors hover:text-ink [&::-webkit-details-marker]:hidden">
                                <ChevronRight className="h-3.5 w-3.5 transition-transform group-open/details:rotate-90" />
                                展开证据与执行细节
                            </summary>
                            <div className="mt-3 space-y-1.5 text-sm leading-6 text-ink-soft">
                                {event.thesis_excerpt && <p><span className="font-semibold text-ink">交易计划</span> · {event.thesis_excerpt}</p>}
                                {event.invalidation_excerpt && <p><span className="font-semibold text-ink">失效条件</span> · {event.invalidation_excerpt}</p>}
                                {event.checklist_summary && <p><span className="font-semibold text-ink">检查清单</span> · {event.checklist_summary}</p>}
                                {event.emotion && <p><span className="font-semibold text-ink">情绪</span> · {event.emotion}</p>}
                                {event.confidence !== undefined && <p><span className="font-semibold text-ink">信心度</span> · {event.confidence}</p>}
                                {event.ai_annotation && (
                                    <p><span className="font-semibold text-ai">AI</span> · {event.ai_annotation.summary}</p>
                                )}
                                {event.tags && event.tags.length > 0 && (
                                    <div className="flex flex-wrap gap-1.5 pt-1">
                                        {event.tags.map((tag) => (
                                            <span key={tag} className="rounded-full bg-panel px-2 py-0.5 text-[11px] text-ink-muted">#{tag}</span>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </details>
                    )}

                    <Link href={href} className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-ink-soft transition-colors hover:text-ink">
                        打开关联记录
                        <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                </div>
            </div>
        </article>
    )
}
