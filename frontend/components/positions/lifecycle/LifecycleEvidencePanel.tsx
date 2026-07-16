import { Banknote, ExternalLink, FileText } from 'lucide-react'

import { StatusPill } from '@/components/ui/StatusPill'
import { Surface } from '@/components/ui/Surface'
import { getLifecycleEvidencePanelSummary, getLifecyclePreviewTrustSummary, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'

interface LifecycleEvidencePanelProps {
    lifecycle: LifecycleDetailViewModel
}

export function LifecycleEvidencePanel({ lifecycle }: LifecycleEvidencePanelProps) {
    const summary = getLifecycleEvidencePanelSummary(lifecycle)

    return (
        <Surface className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                    <FileText className="h-4 w-4 text-ai" />
                    <h2 className="text-sm font-black uppercase tracking-[0.18em] text-ink-muted">证据与现金影响</h2>
                </div>
                <StatusPill tone="neutral">{summary.evidenceLabel}</StatusPill>
            </div>
            {lifecycle.evidenceItems.length > 0 ? (
                <div className="mt-5 grid gap-3 md:grid-cols-2">
                    {lifecycle.evidenceItems.map((item) => (
                        <a key={`${item.ref_type}-${item.public_id}`} href={item.href} className="rounded-lg border border-line bg-panel-subtle p-4 transition-colors hover:bg-panel">
                            <div className="flex items-center justify-between gap-3">
                                <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-ai">{item.ref_type}</span>
                                <ExternalLink className="h-3.5 w-3.5 text-ink-faint" />
                            </div>
                            <p className="mt-2 text-sm font-bold text-ink">{item.label}</p>
                        </a>
                    ))}
                </div>
            ) : (
                <p className="mt-5 rounded-lg border border-dashed border-line-strong p-4 text-sm text-ink-muted">
                    暂无关联证据；后续审计事件、账户流水或分析结论会在这里形成审计链。
                </p>
            )}
            <div className="mt-5 rounded-lg border border-warning/30 bg-warning/8 p-4">
                <div className="flex items-center gap-2 text-sm font-bold text-warning">
                    <Banknote className="h-4 w-4" />
                    {summary.cashLabel}
                </div>
            </div>
            <p className="mt-4 text-xs text-ink-muted">
                {getLifecyclePreviewTrustSummary(lifecycle.trust)}
            </p>
        </Surface>
    )
}
