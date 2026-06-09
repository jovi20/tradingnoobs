import type { TimelineView } from '@/lib/read-models'

const viewOptions: Array<{ value: TimelineView; label: string }> = [
    { value: 'ALL', label: '全部' },
    { value: 'TRADING', label: '交易' },
    { value: 'REVIEW', label: '复盘' },
    { value: 'AI', label: 'AI' },
    { value: 'EXCEPTION', label: '异常' },
]

interface TimelineViewTabsProps {
    value: TimelineView
    onChange: (value: TimelineView) => void
}

export function TimelineViewTabs({ value, onChange }: TimelineViewTabsProps) {
    return (
        <div className="flex flex-wrap gap-2 rounded-2xl border border-slate-200 bg-white/70 p-2 dark:border-slate-800 dark:bg-slate-900/70">
            {viewOptions.map((option) => (
                <button
                    key={option.value}
                    type="button"
                    onClick={() => onChange(option.value)}
                    className={`rounded-xl px-3 py-2 text-xs font-semibold transition ${
                        value === option.value
                            ? 'bg-slate-950 text-white shadow-sm dark:bg-white dark:text-slate-950'
                            : 'text-slate-500 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100'
                    }`}
                >
                    {option.label}
                </button>
            ))}
        </div>
    )
}
