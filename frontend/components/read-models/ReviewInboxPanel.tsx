import { AlertCircle, ArrowUpRight, CheckCircle2 } from 'lucide-react'
import { TrustMetaBadge } from '@/components/trust/TrustMetaBadge'
import type { ReviewInboxItem } from '@/lib/readModels'

interface ReviewInboxPanelProps {
    items: ReviewInboxItem[]
}

const severityStyles: Record<string, string> = {
    INFO: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    LOW: 'bg-blue-50 text-blue-700 dark:bg-blue-500/10 dark:text-blue-200',
    MEDIUM: 'bg-amber-50 text-amber-800 dark:bg-amber-500/10 dark:text-amber-200',
    HIGH: 'bg-orange-50 text-orange-800 dark:bg-orange-500/10 dark:text-orange-200',
    BLOCKING: 'bg-red-50 text-red-800 dark:bg-red-500/10 dark:text-red-200',
}

export function ReviewInboxPanel({ items }: ReviewInboxPanelProps) {
    if (items.length === 0) {
        return (
            <section className="rounded-3xl border border-dashed border-slate-300 bg-white/70 p-5 text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-900/50 dark:text-slate-400">
                <div className="flex items-center gap-2 font-semibold text-slate-700 dark:text-slate-200">
                    <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                    Review Inbox clear
                </div>
                <p className="mt-2">没有需要立刻处理的复盘动作。继续保持，别让小胜利变成噪音。</p>
            </section>
        )
    }

    return (
        <section className="rounded-3xl border border-slate-200 bg-white/80 p-4 shadow-lg shadow-slate-200/50 backdrop-blur dark:border-slate-800 dark:bg-slate-950/70 dark:shadow-slate-950/40">
            <div className="mb-3 flex items-center justify-between">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-500">Review Inbox</p>
                    <h2 className="text-lg font-bold text-slate-950 dark:text-white">下一步该处理什么</h2>
                </div>
                <span className="rounded-full bg-slate-950 px-2.5 py-1 text-xs font-semibold text-white dark:bg-white dark:text-slate-950">
                    {items.length}
                </span>
            </div>

            <div className="space-y-3">
                {items.map((item) => (
                    <article
                        key={`${item.kind}-${item.linked_object_public_id}`}
                        className="rounded-2xl border border-slate-100 bg-slate-50/80 p-3 dark:border-slate-800 dark:bg-slate-900/80"
                    >
                        <div className="flex items-start gap-3">
                            <div className="mt-0.5 rounded-full bg-white p-2 text-amber-600 shadow-sm dark:bg-slate-950 dark:text-amber-300">
                                <AlertCircle className="h-4 w-4" />
                            </div>
                            <div className="min-w-0 flex-1">
                                <div className="flex flex-wrap items-center gap-2">
                                    <span
                                        className={`rounded-full px-2 py-0.5 text-[10px] font-bold tracking-[0.14em] ${severityStyles[item.severity] ?? severityStyles.INFO}`}
                                    >
                                        {item.severity}
                                    </span>
                                    <span className="text-xs font-medium text-slate-500">{item.kind}</span>
                                </div>
                                <h3 className="mt-2 text-sm font-bold text-slate-950 dark:text-white">{item.summary}</h3>
                                <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.reason}</p>
                                <div className="mt-3 flex flex-wrap items-center gap-2">
                                    <TrustMetaBadge meta={item.trust_meta} compact />
                                    <span className="inline-flex items-center gap-1 text-xs font-semibold text-slate-500">
                                        {item.recommended_action}
                                        <ArrowUpRight className="h-3 w-3" />
                                    </span>
                                </div>
                            </div>
                        </div>
                    </article>
                ))}
            </div>
        </section>
    )
}
