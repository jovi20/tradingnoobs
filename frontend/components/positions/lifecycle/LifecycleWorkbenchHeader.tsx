import Link from 'next/link'
import { ArrowLeft } from 'lucide-react'

import { StatusPill } from '@/components/ui/StatusPill'
import { getLifecycleReviewTone, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'

interface LifecycleWorkbenchHeaderProps {
    lifecycle: LifecycleDetailViewModel
}

export function LifecycleWorkbenchHeader({ lifecycle }: LifecycleWorkbenchHeaderProps) {
    const reviewTone = getLifecycleReviewTone(lifecycle.reviewStatus)
    const isOpen = lifecycle.positionStatus === 'OPEN'

    return (
        <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="flex min-w-0 items-start gap-3">
                <Link href="/positions" className="rounded-xl border border-slate-200 bg-white p-2 text-slate-500 transition-colors hover:bg-slate-50 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-300 dark:hover:bg-slate-800">
                    <ArrowLeft className="h-5 w-5" />
                </Link>
                <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                        <p className="text-xs font-bold uppercase tracking-[0.22em] text-cyan-700 dark:text-cyan-300">Lifecycle Command Center</p>
                        <StatusPill tone={isOpen ? 'review' : 'neutral'}>{isOpen ? 'Open Position' : 'Closed Position'}</StatusPill>
                        <StatusPill tone={reviewTone.tone}>{reviewTone.label}</StatusPill>
                    </div>
                    <h1 className="mt-2 truncate text-3xl font-black tracking-tight text-slate-950 dark:text-white md:text-5xl">
                        {lifecycle.positionTitle}
                    </h1>
                    <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
                        {lifecycle.assetSymbol} · {lifecycle.instrumentLabel} · {lifecycle.accountLabel} · {lifecycle.side}
                    </p>
                </div>
            </div>
            <div className="rounded-2xl border border-slate-200 bg-white/80 px-4 py-3 text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900/70 dark:text-slate-400">
                <p className="font-semibold uppercase tracking-[0.18em]">as of</p>
                <p className="mt-1">{new Date(lifecycle.trust.as_of).toLocaleString('zh-CN')}</p>
            </div>
        </header>
    )
}
