import type { HTMLAttributes } from 'react'

import { cn } from '@/lib/cn'
import { toneSoft, type Tone } from './tone'

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
    tone?: Tone
    variant?: 'soft' | 'outline'
    dot?: boolean
}

export function Badge({ className, tone = 'neutral', variant = 'soft', dot, children, ...props }: BadgeProps) {
    return (
        <span
            className={cn(
                'inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-[11px] font-semibold',
                variant === 'soft' ? toneSoft[tone] : 'border border-line text-ink-muted',
                className,
            )}
            {...props}
        >
            {dot && <span className={cn('h-1.5 w-1.5 rounded-full', toneSoft[tone].split(' ').find((c) => c.startsWith('text-'))?.replace('text-', 'bg-'))} />}
            {children}
        </span>
    )
}
