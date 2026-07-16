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
        <div className="flex flex-wrap gap-1 rounded-lg border border-line bg-panel-subtle p-1">
            {viewOptions.map((option) => (
                <button
                    key={option.value}
                    type="button"
                    onClick={() => onChange(option.value)}
                    className={`rounded-md px-3.5 py-1.5 text-xs font-semibold transition-colors ${
                        value === option.value
                            ? 'bg-panel text-ink shadow-panel dark:shadow-none dark:border dark:border-line-strong'
                            : 'text-ink-muted hover:text-ink'
                    }`}
                >
                    {option.label}
                </button>
            ))}
        </div>
    )
}
