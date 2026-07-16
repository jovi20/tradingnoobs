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
        <div className="rounded-lg border border-line bg-panel-subtle p-5 shadow-panel dark:shadow-none">
            <div className="flex items-start justify-between gap-4">
                <div>
                    <div className="flex items-center gap-2">
                        <GitBranch className="w-4 h-4 text-ink-muted" />
                        <h2 className="text-sm font-bold uppercase tracking-wider text-ink-muted">Truth Preview</h2>
                        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${badge.className}`}>
                            {badge.label}
                        </span>
                    </div>
                    <p className="mt-2 text-lg font-semibold text-ink">{lifecycle.summaryHeadline}</p>
                    <p className="mt-1 text-sm text-ink-muted">{getLifecyclePreviewSummary(lifecycle)}</p>
                    <p className="mt-1 text-xs text-ink-faint tn-nums">
                        as of {new Date(lifecycle.trust.as_of).toLocaleString('zh-CN')} · {getLifecyclePreviewTrustSummary(lifecycle.trust)}
                    </p>
                </div>
                <ShieldCheck className="w-5 h-5 text-ink-faint shrink-0" />
            </div>

            {lifecycle.thesis && (
                <div className="mt-4 rounded-md border border-line p-4">
                    <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint">初始 Thesis</p>
                    <p className="mt-2 text-sm text-ink-soft">{lifecycle.thesis}</p>
                </div>
            )}

            <div className="mt-4 grid gap-3 md:grid-cols-3">
                {lifecycle.keyNumbers.map((item) => (
                    <div key={item.label} className="rounded-md bg-panel px-4 py-3">
                        <p className="text-[11px] font-semibold uppercase tracking-wide text-ink-faint">{item.label}</p>
                        <p className="mt-1 text-lg font-semibold text-ink tn-nums">{item.value}</p>
                    </div>
                ))}
            </div>

            <div className="mt-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-ink-faint mb-2">Lifecycle 节点</p>
                <div className="flex flex-wrap gap-2">
                    {lifecycle.nodes.map((node) => (
                        <span
                            key={node.node_public_id}
                            className="rounded-full bg-panel px-3 py-1.5 text-xs font-medium text-ink-soft"
                        >
                            {node.node_type}
                        </span>
                    ))}
                </div>
            </div>
        </div>
    )
}
