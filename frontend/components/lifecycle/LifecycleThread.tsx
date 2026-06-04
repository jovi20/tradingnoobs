import Link from 'next/link'
import {
    ArrowLeft,
    BookOpen,
    FileText,
    GitBranch,
    RadioTower,
    RefreshCw,
    Wallet,
} from 'lucide-react'
import { EvidenceLinkedInsightSidecar } from '@/components/insights/EvidenceLinkedInsightSidecar'
import { TrustMetaBadge } from '@/components/trust/TrustMetaBadge'
import type { InsightRun } from '@/lib/insightArtifacts'
import {
    formatTrustTimestamp,
    type EvidenceItem,
    type LifecycleNode,
    type LifecycleReadModel,
    type NarrativeSignal,
} from '@/lib/readModels'

interface LifecycleThreadProps {
    lifecycle?: LifecycleReadModel
    isLoading: boolean
    error: string | null
    insightRuns?: InsightRun[]
    isInsightLoading?: boolean
    insightError?: string | null
    onRefresh: () => void | Promise<unknown>
    onInsightRefresh?: () => void | Promise<unknown>
}

export function LifecycleThread({
    lifecycle,
    isLoading,
    error,
    insightRuns = [],
    isInsightLoading = false,
    insightError = null,
    onRefresh,
    onInsightRefresh = onRefresh,
}: LifecycleThreadProps) {
    return (
        <div className="relative -mx-4 -my-6 min-h-[calc(100vh-4rem)] overflow-hidden bg-[linear-gradient(145deg,#f8fafc_0%,#e5e7eb_45%,#f8fafc_100%)] px-4 py-6 dark:bg-[linear-gradient(145deg,#020617_0%,#111827_50%,#0f172a_100%)] md:-mx-6 md:px-6">
            <div className="pointer-events-none absolute left-[-8rem] top-20 h-80 w-80 rounded-full bg-emerald-200/20 blur-3xl dark:bg-emerald-400/10" />
            <section className="relative mx-auto max-w-7xl">
                <div className="mb-5 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-center gap-3">
                        <Link
                            href="/positions"
                            className="rounded-2xl border border-slate-200 bg-white/75 p-3 text-slate-600 shadow-sm backdrop-blur transition hover:-translate-x-0.5 dark:border-slate-800 dark:bg-slate-950/70 dark:text-slate-300"
                        >
                            <ArrowLeft className="h-5 w-5" />
                        </Link>
                        <div>
                            <p className="text-xs font-black uppercase tracking-[0.3em] text-slate-500">Lifecycle Thread</p>
                            <h1 className="text-3xl font-black tracking-[-0.04em] text-slate-950 dark:text-white md:text-5xl">
                                交易不是字段，是一条证据链。
                            </h1>
                        </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                        {lifecycle && <TrustMetaBadge meta={lifecycle.meta} />}
                        <button
                            onClick={() => onRefresh()}
                            className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-4 py-2 text-xs font-bold uppercase tracking-[0.18em] text-white shadow-lg shadow-slate-900/20 transition hover:-translate-y-0.5 dark:bg-white dark:text-slate-950"
                        >
                            <RefreshCw className={`h-3.5 w-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                            Refresh
                        </button>
                    </div>
                </div>

                {error && (
                    <div className="mb-5 rounded-2xl border border-red-200 bg-red-50 px-4 py-3 text-sm font-medium text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
                        Lifecycle load failed: {error}
                    </div>
                )}

                {isLoading && !lifecycle ? (
                    <LoadingState />
                ) : lifecycle ? (
                    <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
                        <main className="space-y-4">
                            <div className="rounded-[2rem] border border-slate-200 bg-white/80 p-5 shadow-xl shadow-slate-300/30 backdrop-blur dark:border-slate-800 dark:bg-slate-950/70 dark:shadow-slate-950/40">
                                <div className="flex flex-wrap items-center justify-between gap-3">
                                    <div>
                                        <p className="text-xs font-bold uppercase tracking-[0.24em] text-slate-500">
                                            Position
                                        </p>
                                        <h2 className="mt-1 font-mono text-sm font-black text-slate-950 dark:text-white md:text-lg">
                                            {lifecycle.position_public_id}
                                        </h2>
                                    </div>
                                    <div className="grid grid-cols-3 gap-2 text-center">
                                        <MiniStat label="Nodes" value={lifecycle.lifecycle_nodes.length} />
                                        <MiniStat label="Ledger" value={lifecycle.ledger_refs.length} />
                                        <MiniStat label="Evidence" value={lifecycle.evidence_items.length} />
                                    </div>
                                </div>
                            </div>

                            {lifecycle.lifecycle_nodes.length > 0 ? (
                                <div className="space-y-4">
                                    {lifecycle.lifecycle_nodes.map((node, index) => (
                                        <LifecycleNodeCard key={node.event_public_id} node={node} index={index} />
                                    ))}
                                </div>
                            ) : (
                                <EmptyState />
                            )}
                        </main>

                        <aside className="space-y-4">
                            <EvidenceLinkedInsightSidecar
                                runs={insightRuns}
                                isLoading={isInsightLoading}
                                error={insightError}
                                linkedObjectPublicId={lifecycle.position_public_id}
                                title="Lifecycle AI Sidecar"
                                onRefresh={onInsightRefresh}
                            />

                            <SidePanel title="Ledger Refs" icon={Wallet}>
                                {lifecycle.ledger_refs.length > 0 ? (
                                    <div className="space-y-2">
                                        {lifecycle.ledger_refs.map((ref) => (
                                            <code
                                                key={ref}
                                                className="block rounded-xl bg-slate-100 px-3 py-2 text-xs font-bold text-slate-700 dark:bg-slate-900 dark:text-slate-200"
                                            >
                                                {ref}
                                            </code>
                                        ))}
                                    </div>
                                ) : (
                                    <p className="text-sm text-slate-500 dark:text-slate-400">No ledger refs yet.</p>
                                )}
                            </SidePanel>

                            <SidePanel title="Evidence" icon={FileText}>
                                <EvidenceList items={lifecycle.evidence_items} />
                            </SidePanel>

                            <SidePanel title="Narrative Signals" icon={RadioTower}>
                                <NarrativeSignalList signals={lifecycle.narrative_signals} />
                            </SidePanel>
                        </aside>
                    </div>
                ) : (
                    <EmptyState />
                )}
            </section>
        </div>
    )
}

function LifecycleNodeCard({ node, index }: { node: LifecycleNode; index: number }) {
    return (
        <article className="relative rounded-[2rem] border border-slate-200 bg-white/85 p-5 shadow-lg shadow-slate-300/25 backdrop-blur dark:border-slate-800 dark:bg-slate-950/70 dark:shadow-slate-950/40">
            <div className="absolute left-7 top-16 bottom-[-1rem] hidden w-px bg-slate-200 dark:bg-slate-800 md:block" />
            <div className="flex gap-4">
                <div className="relative z-10 flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-slate-950 text-white shadow-lg shadow-slate-900/20 dark:bg-white dark:text-slate-950">
                    <GitBranch className="h-5 w-5" />
                </div>
                <div className="min-w-0 flex-1">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="rounded-full bg-slate-100 px-2.5 py-1 text-[10px] font-black uppercase tracking-[0.18em] text-slate-700 dark:bg-slate-900 dark:text-slate-200">
                            {index + 1}. {node.type}
                        </span>
                        <span className="text-xs font-semibold text-slate-500">
                            {formatTrustTimestamp(node.occurred_at)}
                        </span>
                    </div>
                    <h3 className="mt-3 font-mono text-sm font-black text-slate-950 dark:text-white">
                        {node.event_public_id}
                    </h3>

                    <div className="mt-4 grid gap-3 lg:grid-cols-2">
                        <FieldBlock title="Decision Fields" fields={node.decision_fields} />
                        <FieldBlock title="Execution Fields" fields={node.execution_fields} />
                    </div>

                    <div className="mt-4 flex flex-wrap gap-2">
                        {node.evidence_refs.map((ref) => (
                            <span
                                key={ref}
                                className="rounded-full border border-slate-200 bg-slate-50 px-2.5 py-1 text-xs font-semibold text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300"
                            >
                                evidence: {ref}
                            </span>
                        ))}
                    </div>
                </div>
            </div>
        </article>
    )
}

function FieldBlock({ title, fields }: { title: string; fields: Record<string, unknown> }) {
    const visibleFields = Object.entries(fields).filter(([, value]) => value !== null && value !== undefined && value !== '')

    return (
        <div className="rounded-2xl bg-slate-50 p-3 dark:bg-slate-900/80">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-slate-500">{title}</p>
            {visibleFields.length > 0 ? (
                <dl className="mt-3 space-y-2">
                    {visibleFields.map(([key, value]) => (
                        <div key={key}>
                            <dt className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">{key}</dt>
                            <dd className="mt-0.5 text-sm font-semibold text-slate-800 dark:text-slate-100">
                                {formatUnknown(value)}
                            </dd>
                        </div>
                    ))}
                </dl>
            ) : (
                <p className="mt-3 text-sm text-slate-500 dark:text-slate-400">No captured fields.</p>
            )}
        </div>
    )
}

function EvidenceList({ items }: { items: EvidenceItem[] }) {
    if (items.length === 0) {
        return <p className="text-sm text-slate-500 dark:text-slate-400">No evidence linked yet.</p>
    }

    return (
        <div className="space-y-3">
            {items.map((item) => (
                <article key={item.public_id} className="rounded-2xl bg-slate-50 p-3 dark:bg-slate-900">
                    <div className="flex items-center justify-between gap-2">
                        <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-black tracking-[0.16em] text-slate-600 dark:bg-slate-950 dark:text-slate-300">
                            {item.kind}
                        </span>
                        <span className="text-[10px] font-semibold text-slate-400">{item.confidence}</span>
                    </div>
                    <h3 className="mt-2 text-sm font-bold text-slate-950 dark:text-white">{item.source_name}</h3>
                    <p className="mt-1 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.summary}</p>
                    {item.invalidates_if && (
                        <p className="mt-2 rounded-xl bg-amber-50 px-3 py-2 text-xs font-semibold text-amber-800 dark:bg-amber-500/10 dark:text-amber-200">
                            Invalidates if: {item.invalidates_if}
                        </p>
                    )}
                </article>
            ))}
        </div>
    )
}

function NarrativeSignalList({ signals }: { signals: NarrativeSignal[] }) {
    if (signals.length === 0) {
        return <p className="text-sm text-slate-500 dark:text-slate-400">No linked external catalysts.</p>
    }

    return (
        <div className="space-y-3">
            {signals.map((signal) => (
                <article key={signal.public_id} className="rounded-2xl bg-slate-950 p-3 text-white dark:bg-slate-900">
                    <p className="text-[10px] font-black uppercase tracking-[0.18em] text-slate-400">
                        {signal.signal_type} · {signal.direction} · {signal.strength}
                    </p>
                    <p className="mt-2 text-sm leading-6 text-slate-200">
                        {signal.summary || `${signal.sample_size} evidence sample(s) linked.`}
                    </p>
                    <div className="mt-3">
                        <TrustMetaBadge meta={signal.trust_meta} compact />
                    </div>
                </article>
            ))}
        </div>
    )
}

function SidePanel({
    title,
    icon: Icon,
    children,
}: {
    title: string
    icon: typeof BookOpen
    children: React.ReactNode
}) {
    return (
        <section className="rounded-3xl border border-slate-200 bg-white/80 p-4 shadow-lg shadow-slate-300/25 backdrop-blur dark:border-slate-800 dark:bg-slate-950/70 dark:shadow-slate-950/40">
            <div className="mb-3 flex items-center gap-2 text-slate-950 dark:text-white">
                <Icon className="h-4 w-4" />
                <h2 className="font-black">{title}</h2>
            </div>
            {children}
        </section>
    )
}

function MiniStat({ label, value }: { label: string; value: number }) {
    return (
        <div className="rounded-2xl bg-slate-50 px-3 py-2 dark:bg-slate-900">
            <p className="text-[10px] font-bold uppercase tracking-[0.16em] text-slate-400">{label}</p>
            <p className="text-lg font-black text-slate-950 dark:text-white">{value}</p>
        </div>
    )
}

function LoadingState() {
    return (
        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_360px]">
            <div className="h-[32rem] animate-pulse rounded-[2rem] border border-slate-200 bg-white/60 dark:border-slate-800 dark:bg-slate-900/50" />
            <div className="h-[32rem] animate-pulse rounded-[2rem] border border-slate-200 bg-white/60 dark:border-slate-800 dark:bg-slate-900/50" />
        </div>
    )
}

function EmptyState() {
    return (
        <section className="rounded-[2rem] border border-dashed border-slate-300 bg-white/70 p-8 text-center shadow-sm dark:border-slate-700 dark:bg-slate-950/60">
            <GitBranch className="mx-auto h-8 w-8 text-slate-400" />
            <h3 className="mt-4 text-lg font-black text-slate-950 dark:text-white">No lifecycle nodes yet</h3>
            <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-slate-500 dark:text-slate-400">
                Open, add, reduce, close, and review events will appear here as an auditable thread.
            </p>
        </section>
    )
}

function formatUnknown(value: unknown): string {
    if (typeof value === 'string') return value
    if (typeof value === 'number' || typeof value === 'boolean') return String(value)
    return JSON.stringify(value)
}
