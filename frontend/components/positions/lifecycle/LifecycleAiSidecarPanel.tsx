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
                <Brain className="h-4 w-4 text-ai" />
                <h2 className="text-sm font-black uppercase tracking-[0.18em] text-ink-muted">AI 证据结论</h2>
            </div>
            <p className="mt-2 text-xs text-ink-muted">{getLifecycleAiSidecarSummary(lifecycle)}</p>
            <div className="mt-5 space-y-3">
                {lifecycle.aiItems.length > 0 ? lifecycle.aiItems.map((item, index) => (
                    <div key={item.insight_artifact_public_id || item.insight_run_public_id || `${item.title}-${index}`} className="rounded-lg border border-line bg-panel p-4">
                        <div className="flex items-start justify-between gap-3">
                            <p className="text-sm font-black text-ink">{item.title || 'AI 结论'}</p>
                            {item.href && <a href={item.href} aria-label="打开分析结论"><ExternalLink className="h-4 w-4 text-ink-faint" /></a>}
                        </div>
                        <p className="mt-3 text-sm leading-6 text-ink-soft">{item.conclusion || '这条 AI 分析暂无结论。'}</p>
                    </div>
                )) : (
                    <p className="rounded-lg border border-dashed border-line-strong p-4 text-sm text-ink-muted">
                        暂无 AI 分析结论。只有带有证据引用的分析结果会显示在这里。
                    </p>
                )}
            </div>
        </Surface>
    )
}
