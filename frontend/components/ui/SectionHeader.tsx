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
                    <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-faint">
                        {eyebrow}
                    </p>
                )}
                <h2 className="mt-1 text-lg font-semibold tracking-tight text-ink">
                    {title}
                </h2>
                {description && (
                    <p className="mt-1 text-sm leading-6 text-ink-muted">
                        {description}
                    </p>
                )}
            </div>
            {action && <div className="shrink-0">{action}</div>}
        </div>
    )
}
