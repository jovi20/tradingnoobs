import { useState, useEffect } from 'react'
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

    // Reset responses when modal opens
    useEffect(() => {
        if (isOpen) {
            setResponses({})
        }
    }, [isOpen])

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
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden border border-slate-200 dark:border-slate-800 animate-in zoom-in-95 duration-200">
                {/* Header */}
                <div className="bg-slate-50 dark:bg-slate-800/50 p-6 border-b border-slate-100 dark:border-slate-800 flex items-start justify-between">
                    <div>
                        <h2 className="text-xl font-bold flex items-center gap-2 text-slate-900 dark:text-slate-100">
                            <ShieldCheck className="w-6 h-6 text-emerald-500" />
                            交易前核查
                        </h2>
                        <p className="text-sm text-slate-500 mt-1">
                            执行策略 <span className="font-semibold text-emerald-600 dark:text-emerald-400">{strategyName}</span> 的纪律检查
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 -mr-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Body */}
                <div className="p-6 max-h-[60vh] overflow-y-auto">
                    {/* Progress Bar */}
                    <div className="mb-6 relative h-2 bg-slate-100 dark:bg-slate-800 rounded-full overflow-hidden">
                        <div
                            className={`absolute top-0 left-0 h-full transition-all duration-500 ease-out ${allRequiredChecked ? 'bg-emerald-500' : 'bg-amber-500'}`}
                            style={{ width: `${progress}%` }}
                        />
                    </div>

                    <div className="space-y-3">
                        {checklistItems.map((item) => (
                            <label
                                key={item.id}
                                className={`flex items-start gap-3 p-4 rounded-xl cursor-pointer border-2 transition-all duration-200 ${responses[String(item.id)]
                                    ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20'
                                    : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 bg-white dark:bg-slate-900'
                                    }`}
                            >
                                <div className={`mt-0.5 w-5 h-5 rounded border flex items-center justify-center transition-colors ${responses[String(item.id)]
                                    ? 'bg-emerald-500 border-emerald-500'
                                    : 'border-slate-300 dark:border-slate-600'
                                    }`}>
                                    {responses[String(item.id)] && <CheckCircle className="w-3.5 h-3.5 text-white" />}
                                </div>
                                <div className="flex-1">
                                    <div className="flex items-center gap-2">
                                        <span className={`font-medium ${responses[String(item.id)] ? 'text-emerald-900 dark:text-emerald-100' : 'text-slate-700 dark:text-slate-300'}`}>
                                            {item.label}
                                        </span>
                                        {item.required && (
                                            <span className="text-[10px] font-bold px-1.5 py-0.5 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded uppercase tracking-wider">
                                                Required
                                            </span>
                                        )}
                                        {item.category && (
                                            <span className="text-[10px] px-1.5 py-0.5 bg-slate-100 dark:bg-slate-800 text-slate-500 rounded uppercase tracking-wider">
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
                        <div className="mt-4 flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400 p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                            <AlertTriangle className="w-4 h-4" />
                            <span>请勾选所有必填项以继续</span>
                        </div>
                    )}
                </div>

                {/* Footer */}
                <div className="p-6 bg-slate-50 dark:bg-slate-800/50 border-t border-slate-100 dark:border-slate-800 flex items-center justify-between gap-4">
                    <button
                        type="button"
                        onClick={handleCheckAll}
                        className="text-sm font-medium text-slate-500 hover:text-slate-800 dark:hover:text-slate-200 underline decoration-slate-300 underline-offset-4"
                    >
                        一键全部确认
                    </button>
                    <div className="flex gap-3">
                        <button
                            type="button"
                            onClick={onClose}
                            className="px-4 py-2 rounded-xl text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700 font-medium transition-colors"
                        >
                            取消
                        </button>
                        <button
                            type="button"
                            onClick={() => onConfirm(responses)}
                            disabled={!allRequiredChecked || isSubmitting}
                            className={`px-6 py-2 rounded-xl font-bold text-white shadow-lg transition-all transform active:scale-95 flex items-center gap-2 ${allRequiredChecked && !isSubmitting
                                ? 'bg-emerald-500 hover:bg-emerald-600 shadow-emerald-500/30'
                                : 'bg-slate-300 dark:bg-slate-700 cursor-not-allowed shadow-none'
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
