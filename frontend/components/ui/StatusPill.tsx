import { cn } from '@/lib/cn'
import { toneSoft, type Tone } from './tone'

interface StatusPillProps {
    children: string
    tone?: Tone
    className?: string
}

export function StatusPill({ children, tone = 'neutral', className = '' }: StatusPillProps) {
    return (
        <span className={cn('inline-flex items-center rounded-full px-2.5 py-1 text-[11px] font-semibold', toneSoft[tone], className)}>
            {children}
        </span>
    )
}
