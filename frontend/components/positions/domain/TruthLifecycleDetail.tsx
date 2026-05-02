import type { ReactNode } from 'react'
import { Activity, Banknote, Brain, CheckCircle2, GitBranch, ShieldCheck } from 'lucide-react'

import {
    getLifecycleCashEffectSummary,
    getLifecyclePreviewBadge,
    getLifecyclePreviewTrustSummary,
    type LifecycleDetailViewModel,
} from '@/lib/adapters/lifecycle'

interface TruthLifecycleDetailProps {
    lifecycle: LifecycleDetailViewModel
}

export function TruthLifecycleDetail({ lifecycle }: TruthLifecycleDetailProps) {
    const badge = getLifecyclePreviewBadge(lifecycle.reviewStatus)

    return (
        <section className="card overflow-hidden border-slate-200 bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800 text-white shadow-xl dark:border-slate-700">
            <div className="grid gap-0 lg:grid-cols-[1.3fr_0.7fr]">
                <div className="p-6 md:p-8">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-slate-200">
                            <GitBranch className="h-3.5 w-3.5" />
                            Truth Lifecycle
                        </span>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${badge.className}`}>
                            {badge.label}
                        </span>
                    </div>

                    <div className="mt-5">
                        <h2 className="text-2xl font-black tracking-tight md:text-4xl">{lifecycle.positionTitle}</h2>
                        <p className="mt-2 max-w-2xl text-sm text-slate-300 md:text-base">
                            {lifecycle.summaryBody}
                        </p>
                    </div>

                    <div className="mt-6 grid gap-3 sm:grid-cols-3">
                        {lifecycle.keyNumbers.map((item) => (
                            <div key={item.label} className="rounded-2xl border border-white/10 bg-white/10 p-4 backdrop-blur">
                                <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{item.label}</p>
                                <p className="mt-1 text-xl font-bold">{item.value}</p>
                            </div>
                        ))}
                    </div>

                    <div className="mt-6 rounded-3xl border border-white/10 bg-white/[0.06] p-5">
                        <div className="flex items-center gap-2 text-sm font-bold text-slate-100">
                            <ShieldCheck className="h-4 w-4 text-emerald-300" />
                            Thesis and Discipline
                        </div>
                        <p className="mt-3 text-sm leading-6 text-slate-300">
                            {lifecycle.thesis || '这笔交易还没有结构化 thesis。'}
                        </p>
                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                            <TruthDetailMini label="Invalidation" value={lifecycle.invalidationRule || '未记录'} />
                            <TruthDetailMini label="Planned Exit" value={lifecycle.plannedExitRule || '未记录'} />
                            <TruthDetailMini label="Sizing" value={lifecycle.sizingRationale || '未记录'} />
                            <TruthDetailMini label="Checklist Miss" value={`${lifecycle.checklistMissCount ?? 0}`} />
                        </div>
                    </div>
                </div>

                <aside className="border-t border-white/10 bg-black/20 p-6 lg:border-l lg:border-t-0">
                    <div className="space-y-5">
                        <TruthSideMetric
                            icon={<Activity className="h-4 w-4" />}
                            label="Execution"
                            value={lifecycle.executionQuality || 'UNKNOWN'}
                        />
                        <TruthSideMetric
                            icon={<Banknote className="h-4 w-4" />}
                            label="Cash Effects"
                            value={getLifecycleCashEffectSummary(lifecycle)}
                        />
                        <TruthSideMetric
                            icon={<Brain className="h-4 w-4" />}
                            label="AI Sidecar"
                            value={`${lifecycle.aiItems.length} items`}
                        />
                    </div>

                    <div className="mt-6">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">Lifecycle Thread</p>
                        <div className="mt-4 space-y-3">
                            {lifecycle.nodes.map((node) => (
                                <div key={node.node_public_id} className="rounded-2xl border border-white/10 bg-white/[0.06] p-4">
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="text-sm font-bold">{node.node_type}</span>
                                        <span className="text-[11px] text-slate-500">
                                            {new Date(node.occurred_at).toLocaleDateString('zh-CN')}
                                        </span>
                                    </div>
                                    <p className="mt-2 text-sm text-slate-300">{node.summary}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    <p className="mt-6 text-xs text-slate-500">
                        as of {new Date(lifecycle.trust.as_of).toLocaleString('zh-CN')} · {getLifecyclePreviewTrustSummary(lifecycle.trust)}
                    </p>
                </aside>
            </div>
        </section>
    )
}

function TruthDetailMini({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-2xl bg-black/20 p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{label}</p>
            <p className="mt-1 text-sm text-slate-200">{value}</p>
        </div>
    )
}

function TruthSideMetric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
    return (
        <div className="rounded-2xl border border-white/10 bg-white/[0.06] p-4">
            <div className="flex items-center gap-2 text-slate-400">
                {icon}
                <span className="text-[11px] font-semibold uppercase tracking-[0.2em]">{label}</span>
            </div>
            <div className="mt-2 flex items-center gap-2 text-lg font-bold text-white">
                <CheckCircle2 className="h-4 w-4 text-emerald-300" />
                {value}
            </div>
        </div>
    )
}
