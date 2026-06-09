import type { WorkbenchTone } from '@/lib/adapters/timeline-workbench'

const toneClasses: Record<WorkbenchTone, string> = {
    neutral: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    positive: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    negative: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300',
    warning: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
    danger: 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300',
    entry: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300',
    exit: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300',
    review: 'bg-sky-50 text-sky-700 dark:bg-sky-950/40 dark:text-sky-300',
    ai: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
}

interface StatusPillProps {
    children: string
    tone?: WorkbenchTone
    className?: string
}

export function StatusPill({ children, tone = 'neutral', className = '' }: StatusPillProps) {
    return (
        <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold ${toneClasses[tone]} ${className}`}>
            {children}
        </span>
    )
}
