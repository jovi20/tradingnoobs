import { Wrench } from 'lucide-react'

import { Surface } from '@/components/ui/Surface'
import type { LifecycleLegacyPanelState } from '@/lib/adapters/lifecycle'
import type { PositionViewModel } from '@/lib/adapters/trading'

interface LifecycleMigrationPanelProps {
    position: PositionViewModel
    hasTruthLifecycle: boolean
    panel: LifecycleLegacyPanelState
}

export function LifecycleMigrationPanel({ position, panel }: LifecycleMigrationPanelProps) {
    return (
        <Surface className="border-amber-200 bg-amber-50/70 p-5 dark:border-amber-900 dark:bg-amber-950/20">
            <div className="flex items-start gap-3">
                <div className="rounded-2xl bg-amber-100 p-2 text-amber-700 dark:bg-amber-500/15 dark:text-amber-200">
                    <Wrench className="h-5 w-5" />
                </div>
                <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-amber-800 dark:text-amber-200">{panel.title}</p>
                    <p className="mt-2 text-sm leading-6 text-amber-900 dark:text-amber-100">{panel.description}</p>
                    <p className="mt-3 text-xs text-amber-800/80 dark:text-amber-200/80">
                        Loaded legacy position: {position.symbol}
                    </p>
                </div>
            </div>
        </Surface>
    )
}
