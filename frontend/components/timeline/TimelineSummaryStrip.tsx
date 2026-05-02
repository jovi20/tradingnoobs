import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'

interface TimelineSummaryStripProps {
    summaryBar: TimelineHomeViewModel['summaryBar']
}

export function TimelineSummaryStrip({ summaryBar }: TimelineSummaryStripProps) {
    return (
        <div className="grid gap-4 md:grid-cols-4">
            <div className="card p-4">
                <p className="text-xs uppercase tracking-wide text-slate-400">本周交易数</p>
                <p className="mt-2 text-2xl font-bold">{summaryBar.trade_count}</p>
            </div>
            <div className="card p-4">
                <p className="text-xs uppercase tracking-wide text-slate-400">复盘完成率</p>
                <p className="mt-2 text-2xl font-bold">
                    {summaryBar.review_completion_rate === null
                        ? '-'
                        : `${Math.round(summaryBar.review_completion_rate * 100)}%`}
                </p>
            </div>
            <div className="card p-4">
                <p className="text-xs uppercase tracking-wide text-slate-400">净值变化</p>
                <p className="mt-2 text-2xl font-bold">
                    {summaryBar.net_equity_change === null ? '-' : summaryBar.net_equity_change.toLocaleString()}
                </p>
            </div>
            <div className="card p-4">
                <p className="text-xs uppercase tracking-wide text-slate-400">重点提醒</p>
                <p className="mt-2 text-2xl font-bold">{summaryBar.priority_alert_count}</p>
            </div>
        </div>
    )
}
