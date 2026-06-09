import type { ReactNode } from 'react'

type SurfaceVariant = 'panel' | 'rail' | 'soft' | 'danger' | 'warning'

const variantClasses: Record<SurfaceVariant, string> = {
    panel: 'border-slate-200/80 bg-white/90 shadow-sm shadow-slate-200/70 dark:border-slate-800 dark:bg-slate-900/80 dark:shadow-slate-950/40',
    rail: 'border-slate-200 bg-slate-50/90 dark:border-slate-800 dark:bg-slate-900/60',
    soft: 'border-slate-200/70 bg-slate-100/70 dark:border-slate-800 dark:bg-slate-800/60',
    danger: 'border-red-200 bg-red-50 text-red-800 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-200',
    warning: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-200',
}

interface SurfaceProps {
    children: ReactNode
    className?: string
    variant?: SurfaceVariant
    as?: 'section' | 'div' | 'aside'
}

export function Surface({ children, className = '', variant = 'panel', as: Component = 'section' }: SurfaceProps) {
    return (
        <Component className={`rounded-[1.35rem] border ${variantClasses[variant]} ${className}`}>
            {children}
        </Component>
    )
}
