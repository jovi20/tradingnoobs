import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

type SurfaceVariant = 'panel' | 'rail' | 'soft' | 'danger' | 'warning'

const variantClasses: Record<SurfaceVariant, string> = {
    panel: 'border-line bg-panel shadow-panel dark:shadow-none',
    rail: 'border-line bg-panel-subtle',
    soft: 'border-line bg-panel-subtle/60',
    danger: 'border-loss/30 bg-loss/8 text-ink-soft',
    warning: 'border-warning/30 bg-warning/8 text-ink-soft',
}

interface SurfaceProps {
    children: ReactNode
    className?: string
    variant?: SurfaceVariant
    as?: 'section' | 'div' | 'aside'
}

export function Surface({ children, className = '', variant = 'panel', as: Component = 'section' }: SurfaceProps) {
    return (
        <Component className={cn('rounded-lg border', variantClasses[variant], className)}>
            {children}
        </Component>
    )
}
