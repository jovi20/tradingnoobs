import Link from 'next/link'
import { ArrowLeft, Plus } from 'lucide-react'

import { StatusPill } from '@/components/ui/StatusPill'
import { getLifecycleReviewTone, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'
import type { PositionViewModel } from '@/lib/adapters/trading'

interface LifecycleWorkbenchHeaderProps {
    lifecycle: LifecycleDetailViewModel
    legacyPosition: PositionViewModel | null
}

export function LifecycleWorkbenchHeader({ lifecycle, legacyPosition }: LifecycleWorkbenchHeaderProps) {
    const reviewTone = getLifecycleReviewTone(lifecycle.reviewStatus)
    const isOpen = lifecycle.positionStatus === 'OPEN'
    const positionStatusLabel = isOpen ? '持仓中' : '已平仓'
    const addBatchHref = isOpen && legacyPosition
        ? `/positions/${legacyPosition.routeId}/add-batch`
        : null
    const subtitle = Array.from(new Set([
        lifecycle.assetSymbol,
        lifecycle.instrumentLabel,
        lifecycle.accountLabel,
        lifecycle.side === 'LONG' ? '做多' : '做空',
    ].filter(Boolean))).join(' · ')

    return (
        <header className="flex flex-col gap-4 md:flex-row md:items-start md:justify-between">
            <div className="flex min-w-0 items-start gap-3">
                <Link
                    href="/positions"
                    aria-label="返回交易记录"
                    title="返回交易记录"
                    className="rounded-md border border-line bg-panel p-2 text-ink-muted transition-colors hover:bg-panel-subtle"
                >
                    <ArrowLeft className="h-5 w-5" />
                </Link>
                <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                        <p className="text-xs font-bold uppercase tracking-[0.22em] text-ai">交易生命周期</p>
                        <StatusPill tone={isOpen ? 'review' : 'neutral'}>{positionStatusLabel}</StatusPill>
                        {reviewTone.label !== positionStatusLabel && (
                            <StatusPill tone={reviewTone.tone}>{reviewTone.label}</StatusPill>
                        )}
                    </div>
                    <h1 className="mt-2 truncate text-3xl font-black tracking-tight text-ink md:text-5xl">
                        {lifecycle.positionTitle}
                    </h1>
                    <p className="mt-2 text-sm text-ink-muted">
                        {subtitle}
                    </p>
                </div>
            </div>
            <div className="flex flex-col items-stretch gap-2 sm:flex-row sm:items-center">
                {addBatchHref && (
                    <Link
                        href={addBatchHref}
                        className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft"
                    >
                        <Plus className="h-4 w-4" />
                        加/平仓
                    </Link>
                )}
                <div className="rounded-lg border border-line bg-panel px-4 py-3 text-xs text-ink-muted">
                    <p className="font-semibold uppercase tracking-[0.18em]">数据截至</p>
                    <p className="mt-1 tn-nums">{new Date(lifecycle.trust.as_of).toLocaleString('zh-CN')}</p>
                </div>
            </div>
        </header>
    )
}
