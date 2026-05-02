import Link from 'next/link'

import { getTimelineEventAccent } from '@/lib/adapters/timeline'
import type { TimelineEventCard as TimelineEventCardData } from '@/lib/read-models'

interface TimelineEventCardProps {
    event: TimelineEventCardData
}

export function TimelineEventCard({ event }: TimelineEventCardProps) {
    return (
        <Link
            href={event.href}
            className="block rounded-2xl border border-slate-200 bg-white p-4 transition hover:border-slate-300 hover:shadow-md dark:border-slate-700 dark:bg-slate-800"
        >
            <div className="flex items-start gap-3">
                <div className={`mt-1 h-2.5 w-2.5 rounded-full ${getTimelineEventAccent(event.event_type)}`} />
                <div className="min-w-0 flex-1">
                    <div className="flex items-start justify-between gap-3">
                        <div>
                            <p className="text-sm font-semibold">{event.headline}</p>
                            <p className="mt-1 text-xs text-slate-500">
                                {event.instrument.symbol}
                                {event.account ? ` · ${event.account.label}` : ''}
                                {` · ${new Date(event.occurred_at).toLocaleString('zh-CN')}`}
                            </p>
                        </div>
                        {event.impact_value?.amount !== undefined && (
                            <span className="text-sm font-semibold">
                                {event.impact_value.amount >= 0 ? '+' : ''}
                                {event.impact_value.amount.toLocaleString()}
                            </span>
                        )}
                    </div>
                    <p className="mt-2 text-sm text-slate-600 dark:text-slate-300">{event.summary}</p>
                </div>
            </div>
        </Link>
    )
}
