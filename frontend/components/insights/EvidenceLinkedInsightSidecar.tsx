import {
    Bot,
    FileCheck2,
    GitPullRequestArrow,
    RefreshCw,
    ShieldCheck,
    Sparkles,
} from 'lucide-react'
import { TrustMetaBadge } from '@/components/trust/TrustMetaBadge'
import {
    assertSupportedChartSchema,
    type InsightArtifact,
    type InsightRun,
} from '@/lib/insightArtifacts'
import { formatTrustTimestamp } from '@/lib/readModels'

interface EvidenceLinkedInsightSidecarProps {
    runs?: InsightRun[]
    isLoading: boolean
    error: string | null
    linkedObjectPublicId?: string
    title?: string
    limit?: number
    onRefresh: () => void | Promise<unknown>
}

interface SidecarArtifact {
    run: InsightRun
    artifact: InsightArtifact
}

export function EvidenceLinkedInsightSidecar({
    runs = [],
    isLoading,
    error,
    linkedObjectPublicId,
    title = 'Evidence AI Sidecar',
    limit = 3,
    onRefresh,
}: EvidenceLinkedInsightSidecarProps) {
    const artifacts = collectEvidenceLinkedArtifacts(runs, linkedObjectPublicId).slice(0, limit)

    return (
        <section className="overflow-hidden rounded-3xl border border-slate-200 bg-[linear-gradient(145deg,rgba(15,23,42,0.97),rgba(30,41,59,0.94))] text-white shadow-xl shadow-slate-900/25 dark:border-slate-800">
            <div className="relative p-4">
                <div className="pointer-events-none absolute right-[-4rem] top-[-4rem] h-32 w-32 rounded-full bg-amber-300/20 blur-2xl" />
                <div className="relative flex items-start justify-between gap-3">
                    <div>
                        <p className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.24em] text-amber-200">
                            <Sparkles className="h-3.5 w-3.5" />
                            Auditable AI
                        </p>
                        <h2 className="mt-2 text-lg font-black tracking-tight">{title}</h2>
                        <p className="mt-2 text-sm leading-6 text-slate-300">
                            只展示带证据引用和信任元数据的 AI artifact；旧 markdown 正文不会在这里直接渲染。
                        </p>
                    </div>
                    <button
                        onClick={() => onRefresh()}
                        className="rounded-2xl border border-white/10 bg-white/10 p-2 text-slate-200 transition hover:-translate-y-0.5 hover:bg-white/15"
                        aria-label="Refresh evidence-linked insights"
                    >
                        <RefreshCw className={`h-4 w-4 ${isLoading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            {error && (
                <div className="mx-4 mb-4 rounded-2xl border border-red-300/30 bg-red-500/10 px-3 py-2 text-sm font-medium text-red-100">
                    Insight artifact load failed: {error}
                </div>
            )}

            <div className="space-y-3 px-4 pb-4">
                {isLoading && artifacts.length === 0 ? (
                    <LoadingCards />
                ) : artifacts.length > 0 ? (
                    artifacts.map(({ run, artifact }) => (
                        <InsightArtifactCard key={artifact.public_id} run={run} artifact={artifact} />
                    ))
                ) : (
                    <EmptySidecar linkedObjectPublicId={linkedObjectPublicId} />
                )}
            </div>
        </section>
    )
}

function collectEvidenceLinkedArtifacts(
    runs: InsightRun[],
    linkedObjectPublicId?: string,
): SidecarArtifact[] {
    return runs
        .flatMap((run) =>
            run.artifacts.map((artifact) => ({
                run,
                artifact,
            })),
        )
        .filter(({ run, artifact }) => {
            if (artifact.evidence_refs.length === 0) return false
            if (artifact.trust_meta.source_refs.length === 0) return false
            if (!linkedObjectPublicId) return true

            const payloadLinkedObject = artifact.payload.linked_object_public_id
            return (
                run.input_refs.includes(linkedObjectPublicId) ||
                artifact.evidence_refs.includes(linkedObjectPublicId) ||
                artifact.trust_meta.source_refs.includes(linkedObjectPublicId) ||
                payloadLinkedObject === linkedObjectPublicId
            )
        })
}

function InsightArtifactCard({ run, artifact }: SidecarArtifact) {
    const hasRenderableChart = assertSupportedChartSchema(artifact.chart_schema)

    return (
        <article className="rounded-2xl border border-white/10 bg-white/[0.06] p-3 shadow-lg shadow-slate-950/20">
            <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-amber-200 px-2 py-0.5 text-[10px] font-black uppercase tracking-[0.16em] text-slate-950">
                            {artifact.artifact_type}
                        </span>
                        <span className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">
                            {run.status}
                        </span>
                    </div>
                    <h3 className="mt-2 text-sm font-black leading-5 text-white">{artifact.title}</h3>
                </div>
                <Bot className="mt-1 h-4 w-4 shrink-0 text-amber-200" />
            </div>

            <p className="mt-3 text-sm leading-6 text-slate-300">{artifact.summary}</p>

            <div className="mt-3 flex flex-wrap gap-2">
                {artifact.evidence_refs.map((ref) => (
                    <span
                        key={ref}
                        className="inline-flex items-center gap-1 rounded-full border border-white/10 bg-slate-950/50 px-2 py-1 text-[10px] font-semibold text-slate-300"
                    >
                        <FileCheck2 className="h-3 w-3 text-emerald-200" />
                        {ref}
                    </span>
                ))}
            </div>

            <div className="mt-3 grid gap-2">
                <TrustMetaBadge meta={artifact.trust_meta} compact />
                <div className="flex flex-wrap items-center gap-2 text-[10px] font-bold uppercase tracking-[0.14em] text-slate-400">
                    <span className="inline-flex items-center gap-1">
                        <GitPullRequestArrow className="h-3 w-3" />
                        {run.run_type}
                    </span>
                    <span>{formatTrustTimestamp(run.started_at)}</span>
                    {hasRenderableChart && (
                        <span className="inline-flex items-center gap-1 rounded-full bg-emerald-300/15 px-2 py-1 text-emerald-100">
                            <ShieldCheck className="h-3 w-3" />
                            {artifact.chart_schema?.schema_version}
                        </span>
                    )}
                </div>
            </div>

            {artifact.content_markdown && (
                <p className="mt-3 rounded-xl border border-amber-200/20 bg-amber-300/10 px-3 py-2 text-xs font-semibold leading-5 text-amber-100">
                    Markdown body withheld here; use the audited summary, evidence refs, and artifact payload.
                </p>
            )}
        </article>
    )
}

function LoadingCards() {
    return (
        <div className="space-y-3">
            {[0, 1].map((item) => (
                <div key={item} className="h-32 animate-pulse rounded-2xl bg-white/[0.07]" />
            ))}
        </div>
    )
}

function EmptySidecar({ linkedObjectPublicId }: { linkedObjectPublicId?: string }) {
    return (
        <div className="rounded-2xl border border-dashed border-white/15 bg-white/[0.04] p-4 text-sm leading-6 text-slate-300">
            <p className="font-bold text-white">暂无可审计 AI artifact</p>
            <p className="mt-1">
                {linkedObjectPublicId
                    ? '当前对象还没有匹配的 insight run。'
                    : '新 AI 卡片会在 insight_runs / insight_artifacts 写入后出现。'}
            </p>
        </div>
    )
}
