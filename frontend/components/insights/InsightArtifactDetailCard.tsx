import { Bot, Clock3, FileText, ShieldCheck, Sparkles } from 'lucide-react'

import {
    buildInsightArtifactDetailView,
    type InsightArtifactDetail,
} from '@/lib/insightArtifacts'

export function InsightArtifactDetailCard({ artifact }: { artifact: InsightArtifactDetail }) {
    const view = buildInsightArtifactDetailView(artifact)

    return (
        <article className="card overflow-hidden">
            <div className="relative border-b border-line bg-ink p-6 text-canvas dark:border-line md:p-8">
                <div className="absolute inset-0 opacity-30">
                    <div className="absolute -right-16 -top-20 h-48 w-48 rounded-full bg-profit blur-3xl" />
                    <div className="absolute -bottom-24 left-8 h-56 w-56 rounded-full bg-ai blur-3xl" />
                </div>
                <div className="relative">
                    <div className="flex flex-wrap items-center gap-2 text-xs font-semibold uppercase tracking-[0.2em] text-profit">
                        <Sparkles className="h-3.5 w-3.5" />
                        {view.artifactType}
                    </div>
                    <h1 className="mt-3 max-w-3xl text-2xl font-bold tracking-tight md:text-3xl">{view.title}</h1>
                    <div className="mt-4 flex flex-wrap gap-2 text-xs text-canvas/80">
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
                            <span className="inline-flex items-center gap-1 rounded-full bg-profit/15 px-3 py-1 text-profit">
                                <ShieldCheck className="h-3.5 w-3.5" />
                                {view.chartBadge}
                            </span>
                        )}
                    </div>
                </div>
            </div>

            <div className="grid gap-5 p-5 md:grid-cols-[minmax(0,1fr)_280px] md:p-6">
                <section className="rounded-lg border border-line bg-panel p-5">
                    <p className="text-xs font-black text-ink-faint">核心洞察</p>
                    <p className="mt-4 text-base leading-8 text-ink-soft">{view.primaryContent}</p>

                    {view.legacyReadOnlyContent && (
                        <div className="mt-6 rounded-lg border border-warning/30 bg-warning/12 p-4">
                            <div className="flex items-center gap-2 text-[11px] font-black uppercase tracking-[0.18em] text-warning">
                                <FileText className="h-3.5 w-3.5" />
                                旧版只读内容
                            </div>
                            <pre className="mt-3 whitespace-pre-wrap break-words font-sans text-sm leading-6 text-ink-soft">
                                {view.legacyReadOnlyContent}
                            </pre>
                        </div>
                    )}
                </section>

                <aside className="space-y-4">
                    <AuditBlock title="证据引用" values={view.evidenceRefs} emptyLabel="暂无证据引用。" />
                    <AuditBlock title="来源引用" values={view.sourceRefs} emptyLabel="暂无来源引用。" />
                    <div className="rounded-lg border border-line bg-panel-subtle p-4">
                        <p className="text-xs font-black text-ink-faint">可信信息</p>
                        <div className="mt-3 space-y-2 text-sm text-ink-soft">
                            <p>新鲜度：{view.trustMeta.freshness ?? '未知'}</p>
                            <p>来源：{view.trustMeta.source ?? '未知'}</p>
                        </div>
                    </div>
                </aside>
            </div>
        </article>
    )
}

function AuditBlock({ title, values, emptyLabel }: { title: string; values: string[]; emptyLabel: string }) {
    return (
        <div className="rounded-lg border border-line bg-panel-subtle p-4">
            <p className="text-xs font-black uppercase tracking-[0.18em] text-ink-faint">{title}</p>
            {values.length > 0 ? (
                <div className="mt-3 flex flex-wrap gap-2">
                    {values.map((value) => (
                        <span
                            key={value}
                            className="rounded-full border border-line bg-panel px-2.5 py-1 text-[11px] font-medium text-ink-soft"
                        >
                            {value}
                        </span>
                    ))}
                </div>
            ) : (
                <p className="mt-3 text-sm text-ink-muted">{emptyLabel}</p>
            )}
        </div>
    )
}
