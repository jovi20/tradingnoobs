import { Loader2, Plus } from 'lucide-react'

import DateTimePicker from '@/components/DateTimePicker'
import type { LifecycleNarrativeDraft } from '@/lib/adapters/lifecycle'

interface ManualAdjustmentForm {
    amount: number
    currency: string
    occurred_at: string
    note: string
}

interface LifecycleModalsProps {
    editingTruthNarrative: boolean
    isSavingTruthNarrative: boolean
    truthNarrativeForm: LifecycleNarrativeDraft
    onChangeTruthNarrativeForm: (form: LifecycleNarrativeDraft) => void
    onCloseTruthNarrative: () => void
    onSaveTruthNarrative: () => void
    editingManualAdjustment: boolean
    isSavingManualAdjustment: boolean
    manualAdjustmentForm: ManualAdjustmentForm
    onChangeManualAdjustmentForm: (form: ManualAdjustmentForm) => void
    onCloseManualAdjustment: () => void
    onSaveManualAdjustment: () => void
}

export function LifecycleModals(props: LifecycleModalsProps) {
    return (
        <>
            {props.editingTruthNarrative && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
                    <div className="card max-h-[90vh] w-full max-w-2xl overflow-y-auto shadow-2xl animate-in zoom-in duration-200">
                        <div className="flex items-start justify-between gap-4 border-b border-slate-100 p-6 dark:border-slate-800">
                            <div>
                                <p className="text-xs font-bold uppercase tracking-[0.18em] text-cyan-600 dark:text-cyan-300">
                                    PositionEvent narrative
                                </p>
                                <h3 className="mt-1 text-lg font-bold">编辑 truth 叙事字段</h3>
                                <p className="mt-1 text-xs text-slate-500">
                                    Event public_id: {props.truthNarrativeForm.eventPublicId}
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={props.onCloseTruthNarrative}
                                className="rounded-lg p-2 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                            >
                                <Plus className="h-5 w-5 rotate-45" />
                            </button>
                        </div>
                        <div className="space-y-4 p-6">
                            <div>
                                <label className="mb-1 block text-sm font-medium">事件摘要 / Reason</label>
                                <textarea
                                    value={props.truthNarrativeForm.reason}
                                    onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, reason: event.target.value })}
                                    className="input min-h-[80px]"
                                    placeholder="这一步为什么发生？"
                                />
                            </div>
                            <div>
                                <label className="mb-1 block text-sm font-medium">Thesis</label>
                                <textarea
                                    value={props.truthNarrativeForm.thesis}
                                    onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, thesis: event.target.value })}
                                    className="input min-h-[90px]"
                                    placeholder="这笔交易的核心假设是什么？"
                                />
                            </div>
                            <div className="grid gap-4 md:grid-cols-2">
                                <div>
                                    <label className="mb-1 block text-sm font-medium">Invalidation Rule</label>
                                    <textarea
                                        value={props.truthNarrativeForm.invalidationRule}
                                        onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, invalidationRule: event.target.value })}
                                        className="input min-h-[80px]"
                                        placeholder="什么情况说明交易假设失效？"
                                    />
                                </div>
                                <div>
                                    <label className="mb-1 block text-sm font-medium">Planned Exit</label>
                                    <textarea
                                        value={props.truthNarrativeForm.plannedExitRule}
                                        onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, plannedExitRule: event.target.value })}
                                        className="input min-h-[80px]"
                                        placeholder="计划如何退出？"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="mb-1 block text-sm font-medium">Sizing Rationale</label>
                                <textarea
                                    value={props.truthNarrativeForm.sizingRationale}
                                    onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, sizingRationale: event.target.value })}
                                    className="input min-h-[80px]"
                                    placeholder="为什么是这个仓位？"
                                />
                            </div>
                            <div className="grid gap-4 md:grid-cols-2">
                                <div>
                                    <label className="mb-1 block text-sm font-medium">Emotion</label>
                                    <input
                                        value={props.truthNarrativeForm.emotion}
                                        onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, emotion: event.target.value })}
                                        className="input"
                                        placeholder="Focused, Calm..."
                                    />
                                </div>
                                <div>
                                    <label className="mb-1 block text-sm font-medium">Confidence (1-5)</label>
                                    <input
                                        type="range"
                                        min="1"
                                        max="5"
                                        value={props.truthNarrativeForm.confidence}
                                        onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, confidence: parseInt(event.target.value) })}
                                        className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-slate-200 accent-cyan-500"
                                    />
                                    <p className="mt-1 text-xs text-slate-500">当前：{props.truthNarrativeForm.confidence}/5</p>
                                </div>
                            </div>
                            <div>
                                <label className="mb-1 block text-sm font-medium">Note</label>
                                <textarea
                                    value={props.truthNarrativeForm.note}
                                    onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, note: event.target.value })}
                                    className="input min-h-[70px]"
                                    placeholder="补充备注"
                                />
                            </div>
                            <div className="rounded-2xl border border-cyan-200 bg-cyan-50 p-3 text-xs leading-5 text-cyan-900 dark:border-cyan-900 dark:bg-cyan-950/30 dark:text-cyan-200">
                                保存会写入 `PositionEvent` 的叙事字段，并刷新上方 lifecycle read model。不会修改成交价、数量或 PnL。
                            </div>
                        </div>
                        <div className="flex justify-end space-x-3 border-t border-slate-100 p-6 dark:border-slate-800">
                            <button type="button" onClick={props.onCloseTruthNarrative} className="btn btn-secondary">
                                取消
                            </button>
                            <button
                                type="button"
                                onClick={props.onSaveTruthNarrative}
                                disabled={props.isSavingTruthNarrative}
                                className="btn btn-primary flex items-center space-x-2"
                            >
                                {props.isSavingTruthNarrative && <Loader2 className="h-4 w-4 animate-spin" />}
                                <span>保存到 truth event</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {props.editingManualAdjustment && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/60 p-4 backdrop-blur-sm">
                    <div className="card w-full max-w-lg shadow-2xl animate-in zoom-in duration-200">
                        <div className="flex items-start justify-between gap-4 border-b border-slate-100 p-6 dark:border-slate-800">
                            <div>
                                <p className="text-xs font-bold uppercase tracking-[0.18em] text-amber-600 dark:text-amber-300">
                                    PositionEvent adjustment
                                </p>
                                <h3 className="mt-1 text-lg font-bold">记录 cash adjustment</h3>
                                <p className="mt-1 text-xs text-slate-500">
                                    只写入 MANUAL_ADJUSTMENT event 和 CASH_ADJUSTMENT ledger，不修改 FIFO 数量或 realized PnL。
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={props.onCloseManualAdjustment}
                                className="rounded-lg p-2 transition-colors hover:bg-slate-100 dark:hover:bg-slate-800"
                            >
                                <Plus className="h-5 w-5 rotate-45" />
                            </button>
                        </div>
                        <div className="space-y-4 p-6">
                            <div className="grid gap-4 md:grid-cols-[1fr_120px]">
                                <div>
                                    <label className="mb-1 block text-sm font-medium">调整金额</label>
                                    <input
                                        type="number"
                                        step="any"
                                        value={props.manualAdjustmentForm.amount}
                                        onChange={(event) => props.onChangeManualAdjustmentForm({
                                            ...props.manualAdjustmentForm,
                                            amount: Number(event.target.value),
                                        })}
                                        className="input"
                                        placeholder="-7.25"
                                    />
                                </div>
                                <div>
                                    <label className="mb-1 block text-sm font-medium">币种</label>
                                    <input
                                        value={props.manualAdjustmentForm.currency}
                                        onChange={(event) => props.onChangeManualAdjustmentForm({
                                            ...props.manualAdjustmentForm,
                                            currency: event.target.value.toUpperCase(),
                                        })}
                                        className="input"
                                        placeholder="USD"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="mb-1 block text-sm font-medium">发生时间</label>
                                <DateTimePicker
                                    value={props.manualAdjustmentForm.occurred_at}
                                    onChange={(value) => props.onChangeManualAdjustmentForm({
                                        ...props.manualAdjustmentForm,
                                        occurred_at: value,
                                    })}
                                />
                            </div>
                            <div>
                                <label className="mb-1 block text-sm font-medium">说明 / Note</label>
                                <textarea
                                    value={props.manualAdjustmentForm.note}
                                    onChange={(event) => props.onChangeManualAdjustmentForm({
                                        ...props.manualAdjustmentForm,
                                        note: event.target.value,
                                    })}
                                    className="input min-h-[90px]"
                                    placeholder="例如：Broker cash correction / fee rebate / reconciliation adjustment"
                                />
                            </div>
                            <div className="rounded-2xl border border-amber-200 bg-amber-50 p-3 text-xs leading-5 text-amber-900 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
                                正数会增加 ledger cash effect，负数会减少 cash effect；这不是交易成交修正，也不会改写任何历史事件。
                            </div>
                        </div>
                        <div className="flex justify-end space-x-3 border-t border-slate-100 p-6 dark:border-slate-800">
                            <button type="button" onClick={props.onCloseManualAdjustment} className="btn btn-secondary">
                                取消
                            </button>
                            <button
                                type="button"
                                onClick={props.onSaveManualAdjustment}
                                disabled={props.isSavingManualAdjustment}
                                className="btn btn-primary flex items-center space-x-2"
                            >
                                {props.isSavingManualAdjustment && <Loader2 className="h-4 w-4 animate-spin" />}
                                <span>保存 adjustment</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
