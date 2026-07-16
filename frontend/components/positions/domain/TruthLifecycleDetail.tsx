import type { ReactNode } from 'react'
import { Activity, Banknote, Brain, CheckCircle2, ExternalLink, FileText, GitBranch, ShieldCheck, Sparkles } from 'lucide-react'

import {
    getLifecycleAiSidecarSummary,
    getLifecycleCashEffectSummary,
    getLifecycleEvidenceSummary,
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
        <section className="rounded-lg border border-line bg-panel text-ink shadow-panel dark:shadow-none overflow-hidden">
            <div className="grid gap-0 lg:grid-cols-[1.3fr_0.7fr]">
                <div className="p-6 md:p-8">
                    <div className="flex flex-wrap items-center gap-2">
                        <span className="inline-flex items-center gap-2 rounded-full bg-panel-subtle px-3 py-1 text-xs font-semibold uppercase tracking-[0.2em] text-ink-soft">
                            <GitBranch className="h-3.5 w-3.5" />
                            Truth Lifecycle
                        </span>
                        <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${badge.className}`}>
                            {badge.label}
                        </span>
                    </div>

                    <div className="mt-5">
                        <h2 className="text-2xl font-black tracking-tight md:text-4xl">{lifecycle.positionTitle}</h2>
                        <p className="mt-2 max-w-2xl text-sm text-ink-soft md:text-base">
                            {lifecycle.summaryBody}
                        </p>
                    </div>

                    <div className="mt-6 grid gap-3 sm:grid-cols-3">
                        {lifecycle.keyNumbers.map((item) => (
                            <div key={item.label} className="rounded-lg border border-line bg-panel-subtle p-4">
                                <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">{item.label}</p>
                                <p className="mt-1 text-xl font-bold tn-nums">{item.value}</p>
                            </div>
                        ))}
                    </div>

                    <div className="mt-6 rounded-lg border border-line bg-panel-subtle p-5">
                        <div className="flex items-center gap-2 text-sm font-bold text-ink">
                            <ShieldCheck className="h-4 w-4 text-profit" />
                            Thesis and Discipline
                        </div>
                        <p className="mt-3 text-sm leading-6 text-ink-soft">
                            {lifecycle.thesis || '这笔交易还没有结构化 thesis。'}
                        </p>
                        <div className="mt-4 grid gap-3 md:grid-cols-2">
                            <TruthDetailMini label="Invalidation" value={lifecycle.invalidationRule || '未记录'} />
                            <TruthDetailMini label="Planned Exit" value={lifecycle.plannedExitRule || '未记录'} />
                            <TruthDetailMini label="Sizing" value={lifecycle.sizingRationale || '未记录'} />
                            <TruthDetailMini label="Checklist Miss" value={`${lifecycle.checklistMissCount ?? 0}`} />
                        </div>
                    </div>

                    <div className="mt-6 rounded-lg border border-ai/25 bg-ai/8 p-5">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div className="flex items-center gap-2 text-sm font-bold text-ink">
                                <FileText className="h-4 w-4 text-ai" />
                                Evidence Board
                            </div>
                            <span className="rounded-full border border-ai/25 bg-ai/10 px-3 py-1 text-[11px] font-semibold uppercase tracking-[0.16em] text-ai">
                                {getLifecycleEvidenceSummary(lifecycle)}
                            </span>
                        </div>

                        {lifecycle.evidenceItems.length > 0 ? (
                            <div className="mt-4 grid gap-3 md:grid-cols-2">
                                {lifecycle.evidenceItems.map((item) => (
                                    <TruthEvidenceLink
                                        key={`${item.ref_type}-${item.public_id}`}
                                        label={item.label}
                                        refType={item.ref_type}
                                        href={item.href}
                                    />
                                ))}
                            </div>
                        ) : (
                            <p className="mt-3 text-sm text-ink-muted">
                                暂无 evidence ref；后续 truth event、ledger 或 insight artifact 写入后会在这里形成审计链。
                            </p>
                        )}
                    </div>
                </div>

                <aside className="border-t border-line bg-panel-subtle p-6 lg:border-l lg:border-t-0">
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
                            value={getLifecycleAiSidecarSummary(lifecycle)}
                        />
                    </div>

                    <div className="mt-6 rounded-lg border border-warning/25 bg-warning/8 p-5">
                        <div className="flex items-center gap-2 text-sm font-bold text-ink">
                            <Sparkles className="h-4 w-4 text-warning" />
                            AI Evidence Sidecar
                        </div>

                        {lifecycle.aiItems.length > 0 ? (
                            <div className="mt-4 space-y-3">
                                {lifecycle.aiItems.map((item, index) => (
                                    <div
                                        key={item.insight_artifact_public_id || item.insight_run_public_id || `${item.title}-${index}`}
                                        className="rounded-lg border border-line bg-panel p-4"
                                    >
                                        <div className="flex items-start justify-between gap-3">
                                            <div>
                                                <p className="text-sm font-bold text-ink">{item.title || 'AI conclusion'}</p>
                                                {item.confidence_label && (
                                                    <p className="mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] text-warning">
                                                        confidence · {item.confidence_label}
                                                    </p>
                                                )}
                                            </div>
                                            {item.href && (
                                                <a
                                                    href={item.href}
                                                    className="rounded-full bg-panel-subtle p-1.5 text-ink-muted transition-colors hover:bg-panel hover:text-ink"
                                                    aria-label="Open insight artifact"
                                                >
                                                    <ExternalLink className="h-3.5 w-3.5" />
                                                </a>
                                            )}
                                        </div>
                                        <p className="mt-3 text-sm leading-6 text-ink-soft">
                                            {item.conclusion || '这条 AI artifact 暂无 conclusion。'}
                                        </p>
                                        {item.coverage_summary && (
                                            <p className="mt-2 text-xs leading-5 text-ink-muted">
                                                {item.coverage_summary}
                                            </p>
                                        )}
                                        {item.recommended_action && (
                                            <p className="mt-3 rounded-md border border-warning/25 bg-warning/8 px-3 py-2 text-xs font-medium text-warning">
                                                建议：{item.recommended_action}
                                            </p>
                                        )}
                                        {(item.evidence_refs?.length || 0) > 0 && (
                                            <div className="mt-3 flex flex-wrap gap-2">
                                                {item.evidence_refs?.map((ref) => (
                                                    <TruthEvidencePill
                                                        key={`${ref.ref_type}-${ref.public_id}`}
                                                        label={ref.label}
                                                        refType={ref.ref_type}
                                                        href={ref.href}
                                                    />
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="mt-3 text-sm leading-6 text-ink-muted">
                                暂无 AI sidecar artifact。这里会承载 AI 结论、覆盖范围和它引用的 evidence，不替代主生命周期线程。
                            </p>
                        )}
                    </div>

                    <div className="mt-6">
                        <p className="text-xs font-semibold uppercase tracking-[0.2em] text-ink-muted">Lifecycle Thread</p>
                        <div className="mt-4 space-y-3">
                            {lifecycle.nodes.map((node) => (
                                <div key={node.node_public_id} className="rounded-lg border border-line bg-panel p-4">
                                    <div className="flex items-center justify-between gap-3">
                                        <span className="text-sm font-bold">{node.node_type}</span>
                                        <span className="text-[11px] text-ink-muted tn-nums">
                                            {new Date(node.occurred_at).toLocaleDateString('zh-CN')}
                                        </span>
                                    </div>
                                    <p className="mt-2 text-sm text-ink-soft">{node.summary}</p>
                                </div>
                            ))}
                        </div>
                    </div>

                    <p className="mt-6 text-xs text-ink-muted tn-nums">
                        as of {new Date(lifecycle.trust.as_of).toLocaleString('zh-CN')} · {getLifecyclePreviewTrustSummary(lifecycle.trust)}
                    </p>
                </aside>
            </div>
        </section>
    )
}

function TruthEvidenceLink({ label, refType, href }: { label: string; refType: string; href: string }) {
    return (
        <a
            href={href}
            className="group rounded-lg border border-line bg-panel p-4 transition-colors hover:border-ai/40 hover:bg-ai/8"
        >
            <div className="flex items-center justify-between gap-3">
                <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ai">{refType}</span>
                <ExternalLink className="h-3.5 w-3.5 text-ink-faint transition-colors group-hover:text-ai" />
            </div>
            <p className="mt-2 text-sm font-bold text-ink">{label}</p>
        </a>
    )
}

function TruthEvidencePill({ label, refType, href }: { label: string; refType: string; href: string }) {
    return (
        <a
            href={href}
            className="rounded-full border border-line bg-panel-subtle px-2.5 py-1 text-[11px] font-medium text-ink-soft transition-colors hover:border-line-strong hover:text-ink"
        >
            {label} · {refType}
        </a>
    )
}

function TruthDetailMini({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-lg border border-line bg-panel p-3">
            <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-muted">{label}</p>
            <p className="mt-1 text-sm text-ink-soft">{value}</p>
        </div>
    )
}

function TruthSideMetric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
    return (
        <div className="rounded-lg border border-line bg-panel p-4">
            <div className="flex items-center gap-2 text-ink-muted">
                {icon}
                <span className="text-[11px] font-semibold uppercase tracking-[0.2em]">{label}</span>
            </div>
            <div className="mt-2 flex items-center gap-2 text-lg font-bold text-ink">
                <CheckCircle2 className="h-4 w-4 text-profit" />
                {value}
            </div>
        </div>
    )
}
