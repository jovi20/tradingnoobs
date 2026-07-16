import { useState } from 'react'
import { X, CheckCircle, AlertTriangle, ShieldCheck } from 'lucide-react'
import { ChecklistItem } from '@/lib/api'

interface ChecklistModalProps {
    isOpen: boolean
    onClose: () => void
    onConfirm: (responses: Record<string, boolean>) => void
    checklistItems: ChecklistItem[]
    strategyName: string
    isSubmitting: boolean
}

export default function ChecklistModal({
    isOpen,
    onClose,
    onConfirm,
    checklistItems,
    strategyName,
    isSubmitting
}: ChecklistModalProps) {
    const [responses, setResponses] = useState<Record<string, boolean>>({})

    if (!isOpen) return null

    const requiredItems = checklistItems.filter(item => item.required)
    const allRequiredChecked = requiredItems.every(item => responses[String(item.id)])
    const totalChecked = Object.values(responses).filter(Boolean).length
    const progress = Math.round((totalChecked / checklistItems.length) * 100)

    const handleToggle = (id: number) => {
        setResponses(prev => ({
            ...prev,
            [String(id)]: !prev[String(id)]
        }))
    }

    const handleCheckAll = () => {
        const newResponses: Record<string, boolean> = {}
        checklistItems.forEach(item => {
            newResponses[String(item.id)] = true
        })
        setResponses(newResponses)
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 animate-in fade-in duration-200">
            <div className="bg-panel w-full max-w-lg rounded-lg overflow-hidden border border-line animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="bg-panel-subtle p-6 border-b border-line flex items-start justify-between">
                    <div>
                        <h2 className="text-xl font-bold flex items-center gap-2 text-ink">
                            <ShieldCheck className="w-6 h-6 text-profit" />
                            交易前核查
                        </h2>
                        <p className="text-sm text-ink-muted mt-1">
                            执行策略 <span className="font-semibold text-profit">{strategyName}</span> 的纪律检查
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 -mr-2 text-ink-faint hover:text-ink-soft hover:bg-panel-subtle rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 max-h-[60vh] overflow-y-auto">
                    {/* Progress Bar */}
                    <div className="mb-6 relative h-2 bg-panel-subtle rounded-full overflow-hidden">
                        <div
                            className={`absolute top-0 left-0 h-full transition-all duration-500 ease-out ${allRequiredChecked ? 'bg-profit' : 'bg-warning'}`}
                            style={{ width: `${progress}%` }}
                        />
                    </div>

                    <div className="space-y-3">
                        {checklistItems.map((item) => (
                            <label
                                key={item.id}
                                className={`flex items-start gap-3 p-4 rounded-md cursor-pointer border-2 transition-colors duration-200 ${responses[String(item.id)]
                                    ? 'border-profit bg-profit/10'
                                    : 'border-line hover:border-line-strong bg-panel'
                                    }`}
                            >
                                <div className={`mt-0.5 w-5 h-5 rounded border flex items-center justify-center transition-colors ${responses[String(item.id)]
                                    ? 'bg-profit border-profit'
                                    : 'border-line-strong'
                                    }`}>
                                    {responses[String(item.id)] && <CheckCircle className="w-3.5 h-3.5 text-white" />}
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <span className={`font-medium ${responses[String(item.id)] ? 'text-profit' : 'text-ink-soft'}`}>
                                            {item.label}
                                        </span>
                                        {item.required && (
                                            <span className="text-[10px] font-bold px-1.5 py-0.5 bg-loss/10 text-loss rounded uppercase tracking-wider">
                                                Required
                                            </span>
                                        )}
                                        {item.category && (
                                            <span className="text-[10px] px-1.5 py-0.5 bg-panel-subtle text-ink-muted rounded uppercase tracking-wider">
                                                {item.category === 'entry' ? '入场' : item.category === 'risk' ? '风控' : item.category === 'exit' ? '出场' : '其他'}
                                            </span>
                                        )}
                                    </div>
                                </div>
                                <input
                                    type="checkbox"
                                    className="hidden"
                                    checked={responses[String(item.id)] || false}
                                    onChange={() => handleToggle(item.id)}
                                />
                            </label>
                        ))}
                    </div>

                    {!allRequiredChecked && requiredItems.length > 0 && (
                        <div className="mt-4 flex items-center gap-2 text-sm text-warning p-3 bg-warning/12 rounded-lg">
                            <AlertTriangle className="w-4 h-4" />
                            <span>请勾选所有必填项以继续</span>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 bg-panel-subtle border-t border-line flex items-center justify-between gap-4">
                    <button
                        type="button"
                        onClick={handleCheckAll}
                        className="text-sm font-medium text-ink-muted hover:text-ink-soft underline decoration-line-strong underline-offset-4"
                    >
                        一键全部确认
                    </button>
                    <div className="flex gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 rounded-md text-ink-soft hover:bg-panel-subtle font-medium transition-colors"
                        >
                            取消
                        </button>
                        <button
                            type="button"
                            onClick={() => onConfirm(responses)}
                            disabled={!allRequiredChecked || isSubmitting}
                            className={`px-6 py-2 rounded-md font-bold text-white transition-colors flex items-center gap-2 ${allRequiredChecked && !isSubmitting
                                ? 'bg-profit hover:opacity-90'
                                : 'bg-panel-subtle text-ink-faint cursor-not-allowed'
                                }`}
                        >
                            {isSubmitting ? '提交中...' : '确认并开仓'}
                            {allRequiredChecked && !isSubmitting && <CheckCircle className="w-4 h-4" />}
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}
