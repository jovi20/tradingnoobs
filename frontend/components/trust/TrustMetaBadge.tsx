import { AlertTriangle, CheckCircle2, Clock3, RadioTower } from 'lucide-react'
import {
    formatTrustTimestamp,
    trustToneForFreshness,
    type TrustMeta,
    type TrustTone,
} from '@/lib/readModels'

interface TrustMetaBadgeProps {
    meta: TrustMeta
    compact?: boolean
}

const toneStyles: Record<TrustTone, string> = {
    ok: 'border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-500/30 dark:bg-emerald-500/10 dark:text-emerald-200',
    watch: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-500/30 dark:bg-amber-500/10 dark:text-amber-200',
    danger: 'border-red-200 bg-red-50 text-red-800 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200',
    muted: 'border-slate-200 bg-slate-50 text-slate-600 dark:border-slate-700 dark:bg-slate-800/70 dark:text-slate-300',
}

const toneIcons = {
    ok: CheckCircle2,
    watch: Clock3,
    danger: AlertTriangle,
    muted: RadioTower,
}

export function TrustMetaBadge({ meta, compact = false }: TrustMetaBadgeProps) {
    const tone = trustToneForFreshness(meta.freshness)
    const Icon = toneIcons[tone]

    return (
        <span
            className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[11px] font-semibold tracking-[0.16em] ${toneStyles[tone]}`}
            title={`${meta.generated_by} · ${meta.source} · ${meta.value_status}`}
        >
            <Icon className="h-3.5 w-3.5" />
            <span>{meta.freshness}</span>
            {!compact && (
                <>
                    <span className="opacity-40">/</span>
                    <span>{meta.source}</span>
                    <span className="opacity-40">/</span>
                    <span>{formatTrustTimestamp(meta.as_of)}</span>
                </>
            )}
        </span>
    )
}
