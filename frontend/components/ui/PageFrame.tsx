import type { ReactNode } from 'react'

interface PageFrameProps {
    children: ReactNode
    className?: string
    density?: 'normal' | 'wide'
}

export function PageFrame({ children, className = '', density = 'wide' }: PageFrameProps) {
    const maxWidth = density === 'wide' ? 'max-w-7xl' : 'max-w-5xl'
    return (
        <div className={`mx-auto w-full ${maxWidth} space-y-6 pb-24 md:pb-8 ${className}`}>
            {children}
        </div>
    )
}
