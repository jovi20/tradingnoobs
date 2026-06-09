import type { WorkbenchTone } from '@/lib/adapters/timeline-workbench'

const toneClasses: Record<WorkbenchTone, string> = {
    neutral: 'text-slate-900 dark:text-slate-100',
    positive: 'text-emerald-700 dark:text-emerald-300',
    negative: 'text-red-700 dark:text-red-300',
    warning: 'text-amber-700 dark:text-amber-300',
    danger: 'text-red-700 dark:text-red-300',
    entry: 'text-emerald-700 dark:text-emerald-300',
    exit: 'text-amber-700 dark:text-amber-300',
    review: 'text-sky-700 dark:text-sky-300',
    ai: 'text-slate-700 dark:text-slate-200',
}

interface MetricTileProps {
    label: string
    value: string
    detail: string
    tone?: WorkbenchTone
}

export function MetricTile({ label, value, detail, tone = 'neutral' }: MetricTileProps) {
    return (
        <div className="rounded-2xl border border-slate-200/80 bg-white/80 p-4 dark:border-slate-800 dark:bg-slate-900/70">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">{label}</p>
            <p className={`mt-2 text-2xl font-semibold tracking-tight ${toneClasses[tone]}`}>{value}</p>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{detail}</p>
        </div>
    )
}
