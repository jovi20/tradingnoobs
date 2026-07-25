import { Ban, Edit3, Loader2, RotateCcw } from 'lucide-react'

import { Surface } from '@/components/ui/Surface'
import type { LifecyclePrimaryActions } from '@/lib/adapters/lifecycle'

interface LifecycleActionPanelProps {
    actions: LifecyclePrimaryActions
    isReversing: boolean
    isVoiding: boolean
    onEditNarrative: () => void
    onReverseLatest: () => void
    onVoid: () => void
}

export function LifecycleActionPanel({ actions, isReversing, isVoiding, onEditNarrative, onReverseLatest, onVoid }: LifecycleActionPanelProps) {
    return (
        <Surface className="border-ai/30 bg-ai/8 p-5">
            <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-ai">审计写入路径</p>
                    <h2 className="mt-2 text-lg font-black text-ink">更新交易生命周期</h2>
                    <p className="mt-2 max-w-3xl text-sm leading-6 text-ink-soft">
                        交易叙事和最新事件撤销都写入审计记录；持仓事件（PositionEvent）是复盘叙事的权威来源，旧版批次编辑仅用于数据迁移。
                    </p>
                </div>
                <div className="flex flex-col gap-2 sm:flex-row">
                    <button type="button" onClick={onEditNarrative} disabled={!actions.narrative.canRun} title={actions.narrative.reason} className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft disabled:cursor-not-allowed disabled:opacity-60">
                        <Edit3 className="h-4 w-4" />
                        {actions.narrative.label}
                    </button>
                    <button type="button" onClick={onReverseLatest} disabled={!actions.reversal.canRun || isReversing} title={actions.reversal.reason} className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-panel-subtle px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel disabled:cursor-not-allowed disabled:opacity-60">
                        {isReversing ? <Loader2 className="h-4 w-4 animate-spin" /> : <RotateCcw className="h-4 w-4" />}
                        {actions.reversal.label}
                    </button>
                    <button type="button" onClick={onVoid} disabled={!actions.void.canRun || isVoiding} title={actions.void.reason} className="inline-flex items-center justify-center gap-2 rounded-md border border-loss/40 bg-loss/8 px-4 py-2 text-sm font-medium text-loss transition-colors hover:bg-loss/15 disabled:cursor-not-allowed disabled:opacity-60">
                        {isVoiding ? <Loader2 className="h-4 w-4 animate-spin" /> : <Ban className="h-4 w-4" />}
                        {actions.void.label}
                    </button>
                </div>
            </div>
        </Surface>
    )
}
