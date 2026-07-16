import type { HTMLAttributes } from 'react'

import { cn } from '@/lib/cn'

/** Skeleton — neutral shimmer placeholder for loading states. */
export function Skeleton({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
    return (
        <div
            className={cn('animate-pulse rounded-md bg-panel-subtle', className)}
            {...props}
        />
    )
}

/** A stack of skeleton lines — common in card/list loading states. */
export function SkeletonText({ lines = 3, className }: { lines?: number; className?: string }) {
    return (
        <div className={cn('space-y-2', className)}>
            {Array.from({ length: lines }).map((_, i) => (
                <Skeleton
                    key={i}
                    className={cn('h-3.5', i === lines - 1 ? 'w-2/3' : 'w-full')}
                />
            ))}
        </div>
    )
}
