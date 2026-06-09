import { Brain, ExternalLink } from 'lucide-react'

import { Surface } from '@/components/ui/Surface'
import { getLifecycleAiSidecarSummary, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'

interface LifecycleAiSidecarPanelProps {
    lifecycle: LifecycleDetailViewModel
}

export function LifecycleAiSidecarPanel({ lifecycle }: LifecycleAiSidecarPanelProps) {
    return (
        <Surface className="p-5">
            <div className="flex items-center gap-2">
                <Brain className="h-4 w-4 text-amber-600" />
                <h2 className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">AI evidence sidecar</h2>
            </div>
            <p className="mt-2 text-xs text-slate-500">{getLifecycleAiSidecarSummary(lifecycle)}</p>
            <div className="mt-5 space-y-3">
                {lifecycle.aiItems.length > 0 ? lifecycle.aiItems.map((item, index) => (
                    <div key={item.insight_artifact_public_id || item.insight_run_public_id || `${item.title}-${index}`} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900/70">
                        <div className="flex items-start justify-between gap-3">
                            <p className="text-sm font-black text-slate-950 dark:text-white">{item.title || 'AI conclusion'}</p>
                            {item.href && <a href={item.href} aria-label="Open insight artifact"><ExternalLink className="h-4 w-4 text-slate-400" /></a>}
                        </div>
                        <p className="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">{item.conclusion || '这条 AI artifact 暂无 conclusion。'}</p>
                    </div>
                )) : (
                    <p className="rounded-2xl border border-dashed border-slate-300 p-4 text-sm text-slate-500 dark:border-slate-700 dark:text-slate-400">
                        暂无 AI sidecar artifact。AI 结论必须通过 evidence-linked artifact 进入这里。
                    </p>
                )}
            </div>
        </Surface>
    )
}
