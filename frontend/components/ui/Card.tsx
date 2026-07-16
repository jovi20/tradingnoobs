import { forwardRef, type HTMLAttributes } from 'react'

import { cn } from '@/lib/cn'

/**
 * Card — the standard workbench surface. Flat paper: 1px hairline border,
 * near-invisible shadow in light, border-only depth in dark.
 */
export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement> & { inset?: boolean }>(
    ({ className, inset, ...props }, ref) => (
        <div
            ref={ref}
            className={cn(
                'rounded-lg border border-line bg-panel shadow-panel dark:shadow-none',
                inset && 'bg-panel-subtle shadow-none',
                className,
            )}
            {...props}
        />
    ),
)
Card.displayName = 'Card'

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
    return <div className={cn('flex flex-col gap-1 p-5', className)} {...props} />
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
    return <h3 className={cn('text-base font-semibold tracking-tight text-ink', className)} {...props} />
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
    return <p className={cn('text-sm leading-6 text-ink-muted', className)} {...props} />
}

export function CardContent({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
    return <div className={cn('p-5 pt-0', className)} {...props} />
}

export function CardFooter({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
    return <div className={cn('flex items-center gap-3 p-5 pt-0', className)} {...props} />
}
