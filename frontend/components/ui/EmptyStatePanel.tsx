import type { ReactNode } from 'react'

interface EmptyStatePanelProps {
    title: string
    detail?: string
    action?: ReactNode
}

export function EmptyStatePanel({ title, detail, action }: EmptyStatePanelProps) {
    return (
        <div className="rounded-2xl border border-dashed border-slate-300 bg-slate-50/70 p-8 text-center dark:border-slate-700 dark:bg-slate-900/50">
            <p className="font-semibold text-slate-900 dark:text-slate-100">{title}</p>
            {detail && <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">{detail}</p>}
            {action && <div className="mt-5">{action}</div>}
        </div>
    )
}
