import { Bot, Clock3, FileText, ShieldCheck, Sparkles } from 'lucide-react'

import {
    buildInsightArtifactDetailView,
    type InsightArtifactDetail,
} from '@/lib/insightArtifacts'

export function InsightArtifactDetailCard({ artifact }: { artifact: InsightArtifactDetail }) {
    const view = buildInsightArtifactDetailView(artifact)

    return (
        <article className="card overflow-hidden">
            <div className="relative border-b border-slate-200 bg-slate-950 p-6 text-white dark:border-slate-800 md:p-8">
                <div className="absolute inset-0 opacity-30">
                    <div className="absolute -right-16 -top-20 h-48 w-48 rounded-full bg-emerald-400 blur-3xl" />
                    <div className="absolute -bottom-24 left-8 h-56 w-56 rounded-full bg-sky-500 blur-3xl" />
                </div>
                <div className="relative">
                    <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-emerald-200">
                        <Sparkles className="h-3.5 w-3.5" />
                        {view.artifactType}
                    </div>
                    <h1 className="mt-3 max-w-3xl text-2xl font-bold tracking-tight md:text-3xl">{view.title}</h1>
                    <div className="mt-4 flex flex-wrap gap-2 text-xs text-slate-300">
                        <span className="inline-flex items-center gap-1 rounded-full bg-white/10 px-3 py-1">
                            <Bot className="h-3.5 w-3.5" />
                            {view.runType}
                        </span>
                        {view.createdAt && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-white/10 px-3 py-1">
                                <Clock3 className="h-3.5 w-3.5" />
                                {view.createdAt}
                            </span>
                        )}
                        {view.chartBadge && (
                            <span className="inline-flex items-center gap-1 rounded-full bg-emerald-300/15 px-3 py-1 text-emerald-100">
                                <ShieldCheck className="h-3.5 w-3.5" />
                                {view.chartBadge}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            <div className="grid gap-5 p-5 md:grid-cols-[minmax(0,1fr)_280px] md:p-6">
                <section className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-950/40">
                    <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Primary insight</p>
                    <p className="mt-4 text-base leading-8 text-slate-700 dark:text-slate-200">{view.primaryContent}</p>

                    {view.legacyReadOnlyContent && (
                        <div className="mt-6 rounded-2xl border border-amber-200/80 bg-amber-50/80 p-4 dark:border-amber-500/20 dark:bg-amber-500/10">
                            <div className="flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.18em] text-amber-700 dark:text-amber-200">
                                <FileText className="h-3.5 w-3.5" />
                                Legacy read-only markdown
                            </div>
                            <pre className="mt-3 whitespace-pre-wrap break-words font-sans text-sm leading-6 text-slate-700 dark:text-slate-200">
                                {view.legacyReadOnlyContent}
                            </pre>
                        </div>
                    )}
                </section>

                <aside className="space-y-4">
                    <AuditBlock title="Evidence refs" values={view.evidenceRefs} emptyLabel="No evidence refs recorded." />
                    <AuditBlock title="Source refs" values={view.sourceRefs} emptyLabel="No source refs recorded." />
                    <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/40">
                        <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">Trust</p>
                        <div className="mt-3 space-y-2 text-sm text-slate-600 dark:text-slate-300">
                            <p>freshness: {view.trustMeta.freshness ?? 'UNKNOWN'}</p>
                            <p>source: {view.trustMeta.source ?? 'UNKNOWN'}</p>
                        </div>
                    </div>
                </aside>
            </div>
        </article>
    )
}

function AuditBlock({ title, values, emptyLabel }: { title: string; values: string[]; emptyLabel: string }) {
    return (
        <div className="rounded-2xl border border-slate-200 bg-slate-50 p-4 dark:border-slate-800 dark:bg-slate-900/40">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-slate-400">{title}</p>
            {values.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                    {values.map((value) => (
                        <span
                            key={value}
                            className="rounded-full border border-slate-200 bg-white px-2.5 py-1 text-[11px] font-medium text-slate-600 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-300"
                        >
                            {value}
                        </span>
                    ))}
                </div>
            ) : (
                <p className="mt-3 text-sm text-slate-500">{emptyLabel}</p>
            )}
        </div>
    )
}
