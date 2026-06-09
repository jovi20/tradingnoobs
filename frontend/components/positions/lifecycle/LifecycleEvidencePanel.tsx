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
                    <FileText className="h-4 w-4 text-cyan-600" />
                    <h2 className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">Evidence and cash effects</h2>
                </div>
                <StatusPill tone="neutral">{summary.evidenceLabel}</StatusPill>
            </div>
            {lifecycle.evidenceItems.length > 0 ? (
                <div className="mt-5 grid gap-3 md:grid-cols-2">
                    {lifecycle.evidenceItems.map((item) => (
                        <a key={`${item.ref_type}-${item.public_id}`} href={item.href} className="rounded-2xl border border-slate-200 bg-slate-50 p-4 transition-colors hover:bg-white dark:border-slate-800 dark:bg-slate-900/70 dark:hover:bg-slate-900">
                            <div className="flex items-center justify-between gap-3">
                                <span className="text-[11px] font-bold uppercase tracking-[0.16em] text-cyan-700 dark:text-cyan-300">{item.ref_type}</span>
                                <ExternalLink className="h-3.5 w-3.5 text-slate-400" />
                            </div>
                            <p className="mt-2 text-sm font-bold text-slate-950 dark:text-white">{item.label}</p>
                        </a>
                    ))}
                </div>
            ) : (
                <p className="mt-5 rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                    暂无 evidence ref；后续 truth event、ledger 或 insight artifact 会在这里形成审计链。
                </p>
            )}
            <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/20">
                <div className="flex items-center gap-2 text-sm font-bold text-amber-900 dark:text-amber-100">
                    <Banknote className="h-4 w-4" />
                    {summary.cashLabel}
                </div>
            </div>
            <p className="mt-4 text-xs text-slate-500 dark:text-slate-400">
                {getLifecyclePreviewTrustSummary(lifecycle.trust)}
            </p>
        </Surface>
    )
}
