import { Edit3, Loader2, RotateCcw, Wrench } from 'lucide-react'

import { Surface } from '@/components/ui/Surface'
import type { LifecyclePrimaryActions } from '@/lib/adapters/lifecycle'

interface LifecycleActionPanelProps {
    actions: LifecyclePrimaryActions
    isReversing: boolean
    onEditNarrative: () => void
    onReverseLatest: () => void
    onManualAdjustment: () => void
}

export function LifecycleActionPanel({ actions, isReversing, onEditNarrative, onReverseLatest, onManualAdjustment }: LifecycleActionPanelProps) {
    return (
        <Surface className="border-cyan-200 bg-cyan-50/80 p-5 dark:border-cyan-900 dark:bg-cyan-950/20">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-cyan-800 dark:text-cyan-200">Truth write path</p>
                    <h2 className="mt-2 text-lg font-black text-slate-950 dark:text-white">Write back to TradingPosition / PositionEvent</h2>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-slate-600 dark:text-slate-300">
                        Narrative fields, latest event reversal, and cash adjustment stay on the truth path. Legacy batch edits remain migration tools.
                    </p>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row">
                    <button type="button" onClick={onEditNarrative} disabled={!actions.narrative.canRun} title={actions.narrative.reason} className="btn btn-primary flex items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-60">
                        <Edit3 className="h-4 w-4" />
                        {actions.narrative.label}
                    </button>
                    <button type="button" onClick={onReverseLatest} disabled={!actions.reversal.canRun || isReversing} title={actions.reversal.reason} className="btn btn-secondary flex items-center justify-center gap-2 disabled:cursor-not-allowed disabled:opacity-60">
                        {isReversing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
                        {actions.reversal.label}
                    </button>
                    <button type="button" onClick={onManualAdjustment} disabled={!actions.cashAdjustment.canRun} title={actions.cashAdjustment.reason} className="btn btn-secondary flex items-center justify-center gap-2">
                        <Wrench className="h-4 w-4" />
                        {actions.cashAdjustment.label}
                    </button>
                </div>
            </div>
        </Surface>
    )
}
