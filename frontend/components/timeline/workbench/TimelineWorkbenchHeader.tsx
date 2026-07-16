import { Clock3, RefreshCcw } from 'lucide-react'

import { formatTrustLabel } from '@/lib/adapters/timeline'
import { StatusPill } from '@/components/ui/StatusPill'
import { Button } from '@/components/ui/Button'
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
                <div className="inline-flex items-center gap-2 rounded-full bg-ink px-3 py-1.5 text-xs font-semibold text-canvas">
                    <Clock3 className="h-3.5 w-3.5" />
                    时间线首页
                </div>
                <h1 className="tn-display mt-4 text-3xl font-semibold tracking-tight text-ink md:text-[2.5rem] md:leading-tight">
                    决策时间流
                </h1>
                <p className="mt-2 text-sm leading-6 text-ink-muted md:text-base">
                    先看最近发生了什么，再处理最值得复盘的偏差、风险和证据。
                </p>
                <div className="mt-3 flex flex-wrap items-center gap-2 text-xs text-ink-faint">
                    <span className="tn-nums">数据截至 {new Date(pageMeta.as_of).toLocaleString('zh-CN')}</span>
                    {trustLabel && <StatusPill>{trustLabel}</StatusPill>}
                </div>
            </div>

            <Button variant="secondary" onClick={onRefresh} className="self-start md:self-auto">
                <RefreshCcw className="h-4 w-4" />
                刷新
            </Button>
        </header>
    )
}
