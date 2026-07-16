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
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-sm">
                    <div className="rounded-lg border border-line bg-panel shadow-panel dark:shadow-none max-h-[90vh] w-full max-w-2xl overflow-y-auto animate-in zoom-in duration-200">
                        <div className="flex items-start justify-between gap-4 border-b border-line p-6">
                            <div>
                                <p className="text-xs font-bold uppercase tracking-[0.18em] text-ai">
                                    审计生命周期
                                </p>
                                <h3 className="mt-1 text-lg font-bold">编辑交易叙事</h3>
                                <p className="mt-1 text-xs text-ink-muted">
                                    事件标识：{props.truthNarrativeForm.eventPublicId}
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={props.onCloseTruthNarrative}
                                aria-label="关闭交易叙事编辑"
                                title="关闭交易叙事编辑"
                                className="rounded-md p-2 transition-colors hover:bg-panel-subtle"
                            >
                                <Plus className="h-5 w-5 rotate-45" />
                            </button>
                        </div>
                        <div className="space-y-4 p-6">
                            <div>
                                <label className="mb-1 block text-sm font-medium">事件摘要</label>
                                <textarea
                                    value={props.truthNarrativeForm.reason}
                                    onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, reason: event.target.value })}
                                    className="input min-h-[80px]"
                                    placeholder="这一步为什么发生？"
                                />
                            </div>
                            <div>
                                <label className="mb-1 block text-sm font-medium">交易假设</label>
                                <textarea
                                    value={props.truthNarrativeForm.thesis}
                                    onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, thesis: event.target.value })}
                                    className="input min-h-[90px]"
                                    placeholder="这笔交易的核心假设是什么？"
                                />
                            </div>
                            <div className="grid gap-4 md:grid-cols-2">
                                <div>
                                    <label className="mb-1 block text-sm font-medium">失效条件</label>
                                    <textarea
                                        value={props.truthNarrativeForm.invalidationRule}
                                        onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, invalidationRule: event.target.value })}
                                        className="input min-h-[80px]"
                                        placeholder="什么情况说明交易假设失效？"
                                    />
                                </div>
                                <div>
                                    <label className="mb-1 block text-sm font-medium">退出计划</label>
                                    <textarea
                                        value={props.truthNarrativeForm.plannedExitRule}
                                        onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, plannedExitRule: event.target.value })}
                                        className="input min-h-[80px]"
                                        placeholder="计划如何退出？"
                                    />
                                </div>
                            </div>
                            <div>
                                <label className="mb-1 block text-sm font-medium">仓位依据</label>
                                <textarea
                                    value={props.truthNarrativeForm.sizingRationale}
                                    onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, sizingRationale: event.target.value })}
                                    className="input min-h-[80px]"
                                    placeholder="为什么是这个仓位？"
                                />
                            </div>
                            <div className="grid gap-4 md:grid-cols-2">
                                <div>
                                    <label className="mb-1 block text-sm font-medium">交易情绪</label>
                                    <input
                                        value={props.truthNarrativeForm.emotion}
                                        onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, emotion: event.target.value })}
                                        className="input"
                                        placeholder="例如：专注、冷静"
                                    />
                                </div>
                                <div>
                                    <label className="mb-1 block text-sm font-medium">信心度（1-5）</label>
                                    <input
                                        type="range"
                                        min="1"
                                        max="5"
                                        value={props.truthNarrativeForm.confidence}
                                        onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, confidence: parseInt(event.target.value) })}
                                        className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-panel-subtle accent-ai"
                                    />
                                    <p className="mt-1 text-xs text-ink-muted">当前：{props.truthNarrativeForm.confidence}/5</p>
                                </div>
                            </div>
                            <div>
                                <label className="mb-1 block text-sm font-medium">补充备注</label>
                                <textarea
                                    value={props.truthNarrativeForm.note}
                                    onChange={(event) => props.onChangeTruthNarrativeForm({ ...props.truthNarrativeForm, note: event.target.value })}
                                    className="input min-h-[70px]"
                                    placeholder="补充备注"
                                />
                            </div>
                            <div className="rounded-lg border border-ai/30 bg-ai/8 p-3 text-xs leading-5 text-ai">
                                保存后会更新持仓事件的叙事字段，并刷新上方审计生命周期。此操作不会修改成交价、数量或盈亏。
                            </div>
                        </div>
                        <div className="flex justify-end space-x-3 border-t border-line p-6">
                            <button type="button" onClick={props.onCloseTruthNarrative} className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-panel-subtle px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel">
                                取消
                            </button>
                            <button
                                type="button"
                                onClick={props.onSaveTruthNarrative}
                                disabled={props.isSavingTruthNarrative}
                                className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft"
                            >
                                {props.isSavingTruthNarrative && <Loader2 className="h-4 w-4 animate-spin" />}
                                <span>保存叙事</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {props.editingManualAdjustment && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4 backdrop-blur-sm">
                    <div className="rounded-lg border border-line bg-panel shadow-panel dark:shadow-none w-full max-w-lg animate-in zoom-in duration-200">
                        <div className="flex items-start justify-between gap-4 border-b border-line p-6">
                            <div>
                                <p className="text-xs font-bold uppercase tracking-[0.18em] text-warning">
                                    资金流水
                                </p>
                                <h3 className="mt-1 text-lg font-bold">记录现金调整</h3>
                                <p className="mt-1 text-xs text-ink-muted">
                                    只写入手动调整事件和现金调整流水，不修改先进先出持仓数量或已实现盈亏。
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={props.onCloseManualAdjustment}
                                aria-label="关闭现金调整"
                                title="关闭现金调整"
                                className="rounded-md p-2 transition-colors hover:bg-panel-subtle"
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
                                <label className="mb-1 block text-sm font-medium">调整说明</label>
                                <textarea
                                    value={props.manualAdjustmentForm.note}
                                    onChange={(event) => props.onChangeManualAdjustmentForm({
                                        ...props.manualAdjustmentForm,
                                        note: event.target.value,
                                    })}
                                    className="input min-h-[90px]"
                                    placeholder="例如：券商现金校准、手续费返还或对账调整"
                                />
                            </div>
                            <div className="rounded-lg border border-warning/30 bg-warning/8 p-3 text-xs leading-5 text-warning">
                                正数会增加账户现金，负数会减少账户现金；这不是成交修正，也不会改写任何历史事件。
                            </div>
                        </div>
                        <div className="flex justify-end space-x-3 border-t border-line p-6">
                            <button type="button" onClick={props.onCloseManualAdjustment} className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-panel-subtle px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel">
                                取消
                            </button>
                            <button
                                type="button"
                                onClick={props.onSaveManualAdjustment}
                                disabled={props.isSavingManualAdjustment}
                                className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft"
                            >
                                {props.isSavingManualAdjustment && <Loader2 className="h-4 w-4 animate-spin" />}
                                <span>保存调整</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </>
    )
}
