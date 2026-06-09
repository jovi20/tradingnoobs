import Link from 'next/link'
import { ChevronRight } from 'lucide-react'

import {
    formatTimelineEventImpact,
    formatTimelineEventMeta,
    getTimelineEventTone,
} from '@/lib/adapters/timeline-workbench'
import { getTimelineEventHref } from '@/lib/adapters/timeline'
import type { TimelineEventCard } from '@/lib/read-models'
import { StatusPill } from '@/components/ui/StatusPill'

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
        <article className="rounded-[1.35rem] border border-slate-200 bg-white/90 p-4 shadow-sm shadow-slate-200/60 dark:border-slate-800 dark:bg-slate-900/80 dark:shadow-slate-950/30">
            <div className="flex items-start gap-3">
                <div className="mt-1.5 h-3 w-3 rounded-full bg-slate-300 ring-4 ring-slate-100 dark:ring-slate-800" />
                <div className="min-w-0 flex-1">
                    <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0">
                            <div className="flex flex-wrap items-center gap-2">
                                <StatusPill tone={tone}>{event.event_type}</StatusPill>
                                <span className="text-xs text-slate-400">{formatTimelineEventMeta(event)}</span>
                            </div>
                            <h3 className="mt-2 text-base font-semibold tracking-tight text-slate-950 dark:text-white">
                                {event.headline}
                            </h3>
                            <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                                {event.summary}
                            </p>
                        </div>
                        {impact && (
                            <div className="shrink-0 text-right">
                                <p className="text-xs uppercase tracking-[0.18em] text-slate-400">impact</p>
                                <p className="mt-1 text-sm font-semibold text-slate-950 dark:text-white">{impact.label}</p>
                            </div>
                        )}
                    </div>

                    {hasDetail && (
                        <details className="mt-4 rounded-2xl bg-slate-50 px-4 py-3 dark:bg-slate-800/60">
                            <summary className="cursor-pointer text-xs font-semibold text-slate-500 dark:text-slate-300">
                                展开证据与执行细节
                            </summary>
                            <div className="mt-3 space-y-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                                {event.thesis_excerpt && <p><strong>Thesis:</strong> {event.thesis_excerpt}</p>}
                                {event.invalidation_excerpt && <p><strong>Invalidation:</strong> {event.invalidation_excerpt}</p>}
                                {event.checklist_summary && <p><strong>Checklist:</strong> {event.checklist_summary}</p>}
                                {event.emotion && <p><strong>Emotion:</strong> {event.emotion}</p>}
                                {event.confidence !== undefined && <p><strong>Confidence:</strong> {event.confidence}</p>}
                                {event.ai_annotation && (
                                    <p><strong>AI:</strong> {event.ai_annotation.summary}</p>
                                )}
                            </div>
                        </details>
                    )}

                    <Link href={href} className="mt-4 inline-flex items-center gap-1 text-xs font-semibold text-slate-700 hover:text-slate-950 dark:text-slate-300 dark:hover:text-white">
                        打开关联记录
                        <ChevronRight className="h-3.5 w-3.5" />
                    </Link>
                </div>
            </div>
        </article>
    )
}
