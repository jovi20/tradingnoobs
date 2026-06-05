import { Bot, ExternalLink, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react'

import { assertSupportedChartSchema, type InsightArtifact, type InsightRun } from '@/lib/insightArtifacts'

interface EvidenceLinkedInsightSidecarProps {
    runs?: InsightRun[]
    isLoading: boolean
    error: string | null
    title?: string
    limit?: number
    onRefresh: () => void | Promise<unknown>
}

export function EvidenceLinkedInsightSidecar({
    runs = [],
    isLoading,
    error,
    title = 'Auditable AI',
    limit = 4,
    onRefresh,
}: EvidenceLinkedInsightSidecarProps) {
    const artifacts = runs.flatMap((run) => run.artifacts.map((artifact) => ({ run, artifact }))).slice(0, limit)

    return (
        <div className="card p-4">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">Auditable AI</p>
                    <h2 className="mt-1 text-lg font-semibold">{title}</h2>
                    <p className="mt-1 text-sm text-slate-500">
                        这里只展示带 artifact、source refs 和 evidence refs 的 AI 结果。
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => onRefresh()}
                    className="rounded-xl border border-slate-200 p-2 text-slate-500 transition hover:bg-slate-50 dark:border-slate-700 dark:hover:bg-slate-800"
                >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
            </div>

            {error && (
                <div className="mt-4 rounded-xl border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300">
                    Insight artifacts load failed: {error}
                </div>
            )}

            <div className="mt-4 space-y-3">
                {artifacts.length > 0 ? (
                    artifacts.map(({ run, artifact }) => (
                        <ArtifactCard key={artifact.public_id} artifact={artifact} run={run} />
                    ))
                ) : (
                    <div className="rounded-xl border border-dashed border-slate-200 p-4 text-sm text-slate-500 dark:border-slate-700">
                        暂无可审计 AI artifact。新的 artifact 在 `/api/v1/insights/runs` 写入后会出现在这里。
                    </div>
                )}
            </div>
        </div>
    )
}

function ArtifactCard({ artifact, run }: { artifact: InsightArtifact; run: InsightRun }) {
    return (
        <div className="rounded-2xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-700 dark:bg-slate-900/40">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-slate-400">
                        <Sparkles className="w-3.5 h-3.5" />
                        {artifact.artifact_type}
                    </div>
                    <p className="mt-2 font-semibold text-slate-900 dark:text-white">{artifact.title}</p>
                </div>
                <Bot className="w-4 h-4 text-slate-400" />
            </div>

            <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{artifact.summary}</p>

            <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded-full bg-slate-200 px-2.5 py-1 text-[11px] font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
                    {run.run_type}
                </span>
                {assertSupportedChartSchema(artifact.chart_schema) && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-100 px-2.5 py-1 text-[11px] font-medium text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-300">
                        <ShieldCheck className="w-3 h-3" />
                        {artifact.chart_schema?.schema_version}
                    </span>
                )}
            </div>

            {(artifact.evidence_refs?.length || 0) > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                    {artifact.evidence_refs.map((ref) => (
                        <span
                            key={ref}
                            className="rounded-full border border-slate-200 px-2.5 py-1 text-[11px] text-slate-500 dark:border-slate-700 dark:text-slate-400"
                        >
                            {ref}
                        </span>
                    ))}
                </div>
            )}

            {(artifact.trust_meta.source_refs?.length || 0) > 0 && (
                <p className="mt-3 text-xs text-slate-400">
                    source refs: {artifact.trust_meta.source_refs?.join(', ')}
                </p>
            )}

            <a
                href="/insights"
                className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary-600"
            >
                打开 AI 洞察
                <ExternalLink className="w-3 h-3" />
            </a>
        </div>
    )
}
