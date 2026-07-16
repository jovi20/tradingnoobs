import { AlertTriangle, CircleAlert, Info, Clock } from 'lucide-react'
import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

type CalloutKind = 'info' | 'warning' | 'error' | 'stale' | 'ai'

const kindConfig: Record<CalloutKind, { wrap: string; icon: typeof Info; iconClass: string }> = {
    info: { wrap: 'border-line bg-panel-subtle text-ink-soft', icon: Info, iconClass: 'text-ink-muted' },
    warning: { wrap: 'border-warning/30 bg-warning/8 text-ink-soft', icon: AlertTriangle, iconClass: 'text-warning' },
    error: { wrap: 'border-loss/30 bg-loss/8 text-ink-soft', icon: CircleAlert, iconClass: 'text-loss' },
    stale: { wrap: 'border-warning/25 bg-warning/6 text-ink-soft', icon: Clock, iconClass: 'text-warning' },
    ai: { wrap: 'border-ai/25 bg-ai/8 text-ink-soft', icon: Info, iconClass: 'text-ai' },
}

interface CalloutProps {
    kind?: CalloutKind
    title?: string
    children?: ReactNode
    action?: ReactNode
    icon?: ReactNode
    className?: string
}

/**
 * Callout / Banner — the unified surface for stale-data, error, and warning
 * states across the product. One component, consistent voice.
 */
export function Callout({ kind = 'info', title, children, action, icon, className }: CalloutProps) {
    const config = kindConfig[kind]
    const Icon = config.icon
    return (
        <div className={cn('flex items-start gap-3 rounded-md border px-4 py-3', config.wrap, className)}>
            <span className={cn('mt-0.5 shrink-0', config.iconClass)}>
                {icon ?? <Icon className="h-4 w-4" />}
            </span>
            <div className="min-w-0 flex-1">
                {title && <p className="text-sm font-semibold text-ink">{title}</p>}
                {children && <div className={cn('text-sm leading-6 text-ink-muted', title && 'mt-0.5')}>{children}</div>}
            </div>
            {action && <div className="shrink-0">{action}</div>}
        </div>
    )
}
