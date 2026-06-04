import { ArrowRight, CircleDot, ListChecks } from 'lucide-react'
import Link from 'next/link'
import { TrustMetaBadge } from '@/components/trust/TrustMetaBadge'
import { formatTrustTimestamp, type TimelineEvent } from '@/lib/readModels'

interface TimelineEventCardProps {
    event: TimelineEvent
}

const eventTone: Record<string, string> = {
    OPEN: 'border-l-emerald-500',
    ADD: 'border-l-blue-500',
    REDUCE: 'border-l-amber-500',
    CLOSE: 'border-l-slate-500',
    CHECKLIST_MISS: 'border-l-red-500',
    EXTERNAL_CATALYST: 'border-l-cyan-500',
}

export function TimelineEventCard({ event }: TimelineEventCardProps) {
    return (
        <article
            className={`group rounded-3xl border border-slate-200 border-l-4 bg-white/85 p-4 shadow-lg shadow-slate-200/40 backdrop-blur transition duration-300 hover:-translate-y-0.5 hover:shadow-xl dark:border-slate-800 dark:bg-slate-950/70 dark:shadow-slate-950/40 ${eventTone[event.type] ?? 'border-l-slate-300'}`}
        >
            <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center gap-1 rounded-full bg-slate-950 px-2.5 py-1 text-[10px] font-bold uppercase tracking-[0.18em] text-white dark:bg-white dark:text-slate-950">
                            <CircleDot className="h-3 w-3" />
                            {event.type}
                        </span>
                        <span className="text-xs font-medium text-slate-500">{formatTrustTimestamp(event.occurred_at)}</span>
                    </div>
                    <h3 className="mt-3 text-lg font-black tracking-tight text-slate-950 dark:text-white">
                        {event.subject}
                    </h3>
                    <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{event.summary}</p>
                </div>
                <TrustMetaBadge meta={event.trust_meta} compact />
            </div>

            <dl className="mt-4 grid grid-cols-3 gap-2">
                {Object.entries(event.impact).slice(0, 3).map(([key, value]) => (
                    <div key={key} className="rounded-2xl bg-slate-50 px-3 py-2 dark:bg-slate-900">
                        <dt className="truncate text-[10px] font-semibold uppercase tracking-[0.16em] text-slate-400">
                            {key}
                        </dt>
                        <dd className="mt-1 truncate text-sm font-bold text-slate-900 dark:text-slate-100">
                            {value ?? 'n/a'}
                        </dd>
                    </div>
                ))}
            </dl>

            <div className="mt-4 flex flex-wrap items-center justify-between gap-3 border-t border-slate-100 pt-3 dark:border-slate-800">
                <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-500">
                    <ListChecks className="h-3.5 w-3.5" />
                    {event.evidence_refs.length} evidence refs
                </span>
                <Link
                    href={`/positions/${event.linked_object_public_id}`}
                    className="inline-flex items-center gap-1 text-xs font-bold text-slate-900 transition group-hover:gap-2 dark:text-slate-100"
                >
                    打开生命周期
                    <ArrowRight className="h-3.5 w-3.5" />
                </Link>
            </div>
        </article>
    )
}
