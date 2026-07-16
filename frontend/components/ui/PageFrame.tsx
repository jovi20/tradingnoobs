import type { ReactNode } from 'react'

import { cn } from '@/lib/cn'

interface PageFrameProps {
    children: ReactNode
    className?: string
    density?: 'normal' | 'wide'
}

/**
 * PageFrame — constrains page content width and provides vertical rhythm.
 * The surrounding shell owns page padding; this only sets max-width + spacing.
 */
export function PageFrame({ children, className = '', density = 'wide' }: PageFrameProps) {
    const maxWidth = density === 'wide' ? 'max-w-7xl' : 'max-w-4xl'
    return (
        <div className={cn('mx-auto w-full space-y-6', maxWidth, className)}>
            {children}
        </div>
    )
}
