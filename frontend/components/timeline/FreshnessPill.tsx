import { formatTrustLabel } from '@/lib/adapters/timeline'
import type { TrustMeta } from '@/lib/read-models'

interface FreshnessPillProps {
    trust?: TrustMeta
}

export function FreshnessPill({ trust }: FreshnessPillProps) {
    const label = formatTrustLabel(trust)
    if (!label) return null

    return (
        <span className="inline-flex rounded-full bg-slate-100 px-2.5 py-1 text-[11px] font-medium text-slate-500 dark:bg-slate-800 dark:text-slate-300">
            {label}
        </span>
    )
}
