import { GitBranch, ShieldCheck } from 'lucide-react'

import {
    getLifecyclePreviewBadge,
    getLifecyclePreviewSummary,
    getLifecyclePreviewTrustSummary,
    type LifecycleDetailViewModel,
} from '@/lib/adapters/lifecycle'

interface TruthLifecyclePreviewProps {
    lifecycle: LifecycleDetailViewModel
}

export function TruthLifecyclePreview({ lifecycle }: TruthLifecyclePreviewProps) {
    const badge = getLifecyclePreviewBadge(lifecycle.reviewStatus)

    return (
        <div className="card p-5 border-slate-200 dark:border-slate-700 bg-slate-50/70 dark:bg-slate-900/40">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <GitBranch className="w-4 h-4 text-slate-500" />
                        <h2 className="text-sm font-bold uppercase tracking-wider text-slate-500">Truth Preview</h2>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}>
                            {badge.label}
                        </span>
                    </div>
                    <p className="mt-2 text-lg font-semibold text-slate-900 dark:text-white">{lifecycle.summaryHeadline}</p>
                    <p className="mt-1 text-sm text-slate-500">{getLifecyclePreviewSummary(lifecycle)}</p>
                    <p className="mt-1 text-xs text-slate-400">
                        as of {new Date(lifecycle.trust.as_of).toLocaleString('zh-CN')} · {getLifecyclePreviewTrustSummary(lifecycle.trust)}
                    </p>
                </div>
                <ShieldCheck className="w-5 h-5 text-slate-400 shrink-0" />
            </div>

            {lifecycle.thesis && (
                <div className="mt-4 rounded-xl border border-slate-200 dark:border-slate-700 p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-slate-400">初始 Thesis</p>
                    <p className="mt-2 text-sm text-slate-700 dark:text-slate-300">{lifecycle.thesis}</p>
                </div>
            )}

            <div className="mt-4 grid gap-3 md:grid-cols-3">
                {lifecycle.keyNumbers.map((item) => (
                    <div key={item.label} className="rounded-xl bg-white px-4 py-3 dark:bg-slate-800">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-slate-400">{item.label}</p>
                        <p className="mt-1 text-lg font-semibold text-slate-900 dark:text-white">{item.value}</p>
                    </div>
                ))}
            </div>

            <div className="mt-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-400 mb-2">Lifecycle 节点</p>
                <div className="flex flex-wrap gap-2">
                    {lifecycle.nodes.map((node) => (
                        <span
                            key={node.node_public_id}
                            className="rounded-full bg-white px-3 py-1.5 text-xs font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300"
                        >
                            {node.node_type}
                        </span>
                    ))}
                </div>
            </div>
        </div>
    )
}
