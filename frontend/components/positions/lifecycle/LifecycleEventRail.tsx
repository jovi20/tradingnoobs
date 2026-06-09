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
                <GitBranch className="h-4 w-4 text-cyan-600" />
                <h2 className="text-sm font-black uppercase tracking-[0.18em] text-slate-500">Lifecycle event spine</h2>
            </div>
            <div className="mt-5 space-y-3">
                {items.map((item) => (
                    <div key={item.id} className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900/70">
                        <div className="flex items-center justify-between gap-3">
                            <StatusPill tone={item.tone}>{item.type}</StatusPill>
                            <span className="text-xs text-slate-400">{item.dateLabel}</span>
                        </div>
                        <p className="mt-3 text-sm font-bold text-slate-950 dark:text-white">{item.title}</p>
                        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">{item.summary}</p>
                    </div>
                ))}
            </div>
        </Surface>
    )
}
