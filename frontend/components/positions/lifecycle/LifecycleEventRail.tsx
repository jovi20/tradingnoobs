import { GitBranch } from 'lucide-react'

import { StatusPill } from '@/components/ui/StatusPill'
import { Surface } from '@/components/ui/Surface'
import { getLifecycleEventRailItems, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'

interface LifecycleEventRailProps {
    lifecycle: LifecycleDetailViewModel
}

export function LifecycleEventRail({ lifecycle }: LifecycleEventRailProps) {
    const items = getLifecycleEventRailItems(lifecycle)

    return (
        <Surface className="p-5">
            <div className="flex items-center gap-2">
                <GitBranch className="h-4 w-4 text-ai" />
                <h2 className="text-sm font-black uppercase tracking-[0.18em] text-ink-muted">事件时间线</h2>
            </div>
            <div className="mt-5 space-y-3">
                {items.map((item) => (
                    <div key={item.id} className="rounded-lg border border-line bg-panel p-4">
                        <div className="flex items-center justify-between gap-3">
                            <StatusPill tone={item.tone}>{item.type}</StatusPill>
                            <span className="text-xs text-ink-faint tn-nums">{item.dateLabel}</span>
                        </div>
                        <p className="mt-3 text-sm font-bold text-ink">{item.title}</p>
                        <p className="mt-1 text-sm leading-6 text-ink-muted">{item.summary}</p>
                    </div>
                ))}
            </div>
        </Surface>
    )
}
