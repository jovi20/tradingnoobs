import { Clock3, RefreshCcw } from 'lucide-react'

import { formatTrustLabel } from '@/lib/adapters/timeline'
import { StatusPill } from '@/components/ui/StatusPill'
import type { TrustMeta } from '@/lib/read-models'

interface TimelineWorkbenchHeaderProps {
    pageMeta: TrustMeta
    onRefresh: () => void
}

export function TimelineWorkbenchHeader({ pageMeta, onRefresh }: TimelineWorkbenchHeaderProps) {
    const trustLabel = formatTrustLabel(pageMeta)

    return (
        <header className="flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
            <div className="max-w-3xl">
                <div className="inline-flex items-center gap-2 rounded-full bg-slate-950 px-3 py-1.5 text-xs font-semibold text-white dark:bg-white dark:text-slate-950">
                    <Clock3 className="h-3.5 w-3.5" />
                    Timeline-first home
                </div>
                <h1 className="mt-4 text-3xl font-semibold tracking-tight text-slate-950 dark:text-white md:text-4xl">
                    决策时间流
                </h1>
                <p className="mt-3 text-sm leading-6 text-slate-500 dark:text-slate-400 md:text-base">
                    先看最近发生了什么，再处理最值得复盘的偏差、风险和证据。
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-slate-400">
                    <span>as of {new Date(pageMeta.as_of).toLocaleString('zh-CN')}</span>
                    {trustLabel && <StatusPill>{trustLabel}</StatusPill>}
                </div>
            </div>

            <button type="button" onClick={onRefresh} className="btn btn-secondary inline-flex items-center gap-2 self-start md:self-auto">
                <RefreshCcw className="h-4 w-4" />
                刷新
            </button>
        </header>
    )
}
