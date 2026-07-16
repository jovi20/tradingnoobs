import type { ReactNode } from 'react'

interface EmptyStatePanelProps {
    title: string
    detail?: string
    action?: ReactNode
    icon?: ReactNode
}

export function EmptyStatePanel({ title, detail, action, icon }: EmptyStatePanelProps) {
    return (
        <div className="rounded-lg border border-dashed border-line-strong bg-panel-subtle/50 p-8 text-center">
            {icon && <div className="mb-3 flex justify-center text-ink-faint">{icon}</div>}
            <p className="font-semibold text-ink">{title}</p>
            {detail && <p className="mx-auto mt-2 max-w-md text-sm leading-6 text-ink-muted">{detail}</p>}
            {action && <div className="mt-5">{action}</div>}
        </div>
    )
}
