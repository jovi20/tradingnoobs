import { Activity, Database, Inbox, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react'
import { ReviewInboxPanel } from '@/components/read-models/ReviewInboxPanel'
import { TimelineEventCard } from '@/components/read-models/TimelineEventCard'
import { EvidenceLinkedInsightSidecar } from '@/components/insights/EvidenceLinkedInsightSidecar'
import { TrustMetaBadge } from '@/components/trust/TrustMetaBadge'
import type { InsightRun } from '@/lib/insightArtifacts'
import { formatTrustTimestamp, type HomeReadModel } from '@/lib/readModels'

interface TimelineHomeProps {
    home?: HomeReadModel
    isLoading: boolean
    error: string | null
    insightRuns?: InsightRun[]
    isInsightLoading?: boolean
    insightError?: string | null
    onRefresh: () => void | Promise<unknown>
    onInsightRefresh?: () => void | Promise<unknown>
}

export function TimelineHome({
    home,
    isLoading,
    error,
    insightRuns = [],
    isInsightLoading = false,
    insightError = null,
    onRefresh,
    onInsightRefresh = onRefresh,
}: TimelineHomeProps) {
    const timelineEvents = home?.timeline_events ?? []
    const reviewItems = home?.review_inbox ?? []
    const contextRail = home?.context_rail

    return (
        <div className="relative -mx-4 -my-6 min-h-[calc(100vh-4rem)] overflow-hidden bg-[radial-gradient(circle_at_top_left,rgba(15,23,42,0.10),transparent_32%),linear-gradient(135deg,#f8fafc_0%,#e2e8f0_46%,#f1f5f9_100%)] px-4 py-6 dark:bg-[radial-gradient(circle_at_top_left,rgba(148,163,184,0.16),transparent_30%),linear-gradient(135deg,#020617_0%,#0f172a_52%,#111827_100%)] md:-mx-6 md:px-6">
            <div className="pointer-events-none absolute right-[-12rem] top-[-10rem] h-96 w-96 rounded-full border border-slate-300/40 dark:border-slate-700/60" />
            <div className="pointer-events-none absolute bottom-[-16rem] left-[-10rem] h-[28rem] w-[28rem] rounded-full bg-amber-200/20 blur-3xl dark:bg-amber-400/10" />

            <section className="relative mx-auto max-w-7xl">
                <div className="mb-6 rounded-[2rem] border border-white/70 bg-white/75 p-5 shadow-2xl shadow-slate-300/30 backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/70 dark:shadow-slate-950/50">
                    <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
                        <div>
                            <p className="text-xs font-black uppercase tracking-[0.35em] text-slate-500 dark:text-slate-400">
                                Timeline Workbench
                            </p>
                            <h1 className="mt-3 max-w-3xl text-4xl font-black tracking-[-0.05em] text-slate-950 dark:text-white md:text-6xl">
                                先处理动作，再看结果。
                            </h1>
                            <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-300 md:text-base">
                                首页现在围绕交易事件流、Review Inbox 和证据可信度组织。Dashboard 退回宏观视角，复盘动作成为默认入口。
                            </p>
                        </div>
                        <div className="flex flex-wrap items-center gap-2">
                            {home && <TrustMetaBadge meta={home.meta} />}
                            <button
                                onClick={() => onRefresh()}
                                className="inline-flex items-center gap-2 rounded-full border border-slate-200 bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-[0.2em] text-white shadow-lg shadow-slate-900/20 transition hover:-translate-y-0.5 dark:border-slate-700 dark:bg-white dark:text-slate-950"
                            >
                                <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                                Refresh
                            </button>
                        </div>
                    </div>

                    {error && (
                        <div className="mt-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
                            Read model load failed: {error}
                        </div>
                    )}

                    <div className="mt-6 grid gap-3 md:grid-cols-4">
                        <SummaryTile
                            icon={Inbox}
                            label="Review Inbox"
                            value={reviewItems.length.toString()}
                            caption="需要处理的复盘动作"
                        />
                        <SummaryTile
                            icon={Activity}
                            label="Timeline Events"
                            value={timelineEvents.length.toString()}
                            caption="已进入主叙事的事件"
                        />
                        <SummaryTile
                            icon={ShieldCheck}
                            label="Open Positions"
                            value={(contextRail?.open_positions ?? 0).toString()}
                            caption="仍在生命周期内"
                        />
                        <SummaryTile
                            icon={Database}
                            label="As Of"
                            value={home ? formatTrustTimestamp(home.meta.as_of) : '--'}
                            caption="数据生成时间"
                        />
                    </div>
                </div>

                {isLoading && !home ? (
                    <LoadingState />
                ) : (
                    <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)_320px]">
                        <ReviewInboxPanel items={reviewItems} />

                        <main className="space-y-4">
                            <div className="flex items-center justify-between">
                                <div>
                                    <p className="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">Main Timeline</p>
                                    <h2 className="text-2xl font-black tracking-tight text-slate-950 dark:text-white">交易事件流</h2>
                                </div>
                                <span className="rounded-full border border-slate-200 bg-white/70 px-3 py-1 text-xs font-semibold text-slate-500 dark:border-slate-800 dark:bg-slate-950/60 dark:text-slate-300">
                                    action-worthy only
                                </span>
                            </div>
                            {timelineEvents.length > 0 ? (
                                timelineEvents.map((event) => (
                                    <TimelineEventCard key={event.public_id} event={event} />
                                ))
                            ) : (
                                <EmptyTimeline />
                            )}
                        </main>

                        <aside className="space-y-4">
                            <EvidenceLinkedInsightSidecar
                                runs={insightRuns}
                                isLoading={isInsightLoading}
                                error={insightError}
                                onRefresh={onInsightRefresh}
                            />

                            <section className="rounded-3xl border border-slate-200 bg-white/80 p-4 shadow-lg shadow-slate-200/40 backdrop-blur dark:border-slate-800 dark:bg-slate-950/70 dark:shadow-slate-950/40">
                                <div className="flex items-center gap-2 text-slate-950 dark:text-white">
                                    <Sparkles className="h-4 w-4" />
                                    <h2 className="font-black">Context Rail</h2>
                                </div>
                                <p className="mt-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                                    保持克制：这里只总结上下文、信任状态和下一步入口，不复制 Dashboard 数据墙。
                                </p>
                                <dl className="mt-4 space-y-3">
                                    <RailMetric label="Closed Positions" value={contextRail?.closed_positions ?? 0} />
                                    <RailMetric label="Open Positions" value={contextRail?.open_positions ?? 0} />
                                    <RailMetric label="Evidence Links" value={timelineEvents.reduce((sum, event) => sum + event.evidence_refs.length, 0)} />
                                </dl>
                            </section>

                            {home && (
                                <section className="rounded-3xl border border-slate-200 bg-slate-950 p-4 text-white shadow-xl shadow-slate-900/30 dark:border-slate-800">
                                    <p className="text-xs font-bold uppercase tracking-[0.24em] text-slate-400">Trust Layer</p>
                                    <div className="mt-3">
                                        <TrustMetaBadge meta={home.meta} compact />
                                    </div>
                                    <p className="mt-3 text-sm leading-6 text-slate-300">
                                        Source refs: {home.meta.source_refs.length > 0 ? home.meta.source_refs.join(', ') : 'none'}
                                    </p>
                                </section>
                            )}
                        </aside>
                    </div>
                )}
            </section>
        </div>
    )
}

function SummaryTile({
    icon: Icon,
    label,
    value,
    caption,
}: {
    icon: typeof Activity
    label: string
    value: string
    caption: string
}) {
    return (
        <div className="rounded-3xl border border-slate-200 bg-slate-50/80 p-4 dark:border-slate-800 dark:bg-slate-900/70">
            <div className="flex items-center justify-between">
                <span className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">{label}</span>
                <Icon className="h-4 w-4 text-slate-400" />
            </div>
            <p className="mt-4 text-3xl font-black tracking-tight text-slate-950 dark:text-white">{value}</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{caption}</p>
        </div>
    )
}

function RailMetric({ label, value }: { label: string; value: number }) {
    return (
        <div className="flex items-center justify-between rounded-2xl bg-slate-50 px-3 py-2 dark:bg-slate-900">
            <dt className="text-xs font-semibold uppercase tracking-[0.16em] text-slate-500">{label}</dt>
            <dd className="text-sm font-black text-slate-950 dark:text-white">{value}</dd>
        </div>
    )
}

function LoadingState() {
    return (
        <div className="grid gap-5 xl:grid-cols-[360px_minmax(0,1fr)_320px]">
            {[0, 1, 2].map((item) => (
                <div
                    key={item}
                    className="h-72 animate-pulse rounded-3xl border border-slate-200 bg-white/60 dark:border-slate-800 dark:bg-slate-900/50"
                />
            ))}
        </div>
    )
}

function EmptyTimeline() {
    return (
        <section className="rounded-3xl border border-dashed border-slate-300 bg-white/70 p-8 text-center shadow-sm dark:border-slate-700 dark:bg-slate-950/60">
            <Activity className="mx-auto h-8 w-8 text-slate-400" />
            <h3 className="mt-4 text-lg font-black text-slate-950 dark:text-white">还没有时间线事件</h3>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500 dark:text-slate-400">
                记录第一笔交易或导入成交后，这里会按交易生命周期组织事件，而不是展示一面指标墙。
            </p>
        </section>
    )
}
