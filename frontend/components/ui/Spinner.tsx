import { Loader2 } from 'lucide-react'

import { cn } from '@/lib/cn'

export function Spinner({ className }: { className?: string }) {
    return <Loader2 className={cn('h-5 w-5 animate-spin text-ink-muted', className)} />
}

/** Centered full-panel loading state with an optional label. */
export function LoadingState({ label, className }: { label?: string; className?: string }) {
    return (
        <div className={cn('flex flex-col items-center justify-center gap-3 py-20 text-ink-muted', className)}>
            <Spinner className="h-7 w-7" />
            {label && <p className="text-sm">{label}</p>}
        </div>
    )
}
