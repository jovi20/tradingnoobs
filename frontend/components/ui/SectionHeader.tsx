import type { ReactNode } from 'react'

interface SectionHeaderProps {
    title: string
    eyebrow?: string
    description?: string
    action?: ReactNode
}

export function SectionHeader({ title, eyebrow, description, action }: SectionHeaderProps) {
    return (
        <div className="flex items-start justify-between gap-4">
            <div className="min-w-0">
                {eyebrow && (
                    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-400">
                        {eyebrow}
                    </p>
                )}
                <h2 className="mt-1 text-lg font-semibold tracking-tight text-slate-950 dark:text-slate-50">
                    {title}
                </h2>
                {description && (
                    <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                        {description}
                    </p>
                )}
            </div>
            {action && <div className="shrink-0">{action}</div>}
        </div>
    )
}
