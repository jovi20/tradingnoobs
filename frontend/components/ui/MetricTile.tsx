import { cn } from '@/lib/cn'
import { toneText, type Tone } from './tone'

interface MetricTileProps {
    label: string
    value: string
    detail: string
    tone?: Tone
}

export function MetricTile({ label, value, detail, tone = 'neutral' }: MetricTileProps) {
    return (
        <div className="rounded-md border border-line bg-panel p-4 shadow-panel dark:shadow-none">
            <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-faint">{label}</p>
            <p className={cn('mt-2 text-2xl font-semibold tracking-tight tn-nums', toneText[tone])}>{value}</p>
            <p className="mt-1 text-xs text-ink-muted">{detail}</p>
        </div>
    )
}
