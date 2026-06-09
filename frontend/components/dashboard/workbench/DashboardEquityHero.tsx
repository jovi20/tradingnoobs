import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import type { DashboardPeriodLabel, DashboardPeriodMetrics, DashboardPeriodOption } from '@/lib/adapters/dashboard'

interface DashboardEquityHeroProps {
    periodOptions: DashboardPeriodOption[]
    selectedPeriod: DashboardPeriodLabel
    onSelectPeriod: (label: DashboardPeriodLabel) => void
    periodMetrics: DashboardPeriodMetrics
    pnlHistory: Array<{ date: string; pnl: number; pnl_percent: number }>
    currencySymbol: string
    upClassName: string
    downClassName: string
    lineColor: string
}

export function DashboardEquityHero({
    periodOptions,
    selectedPeriod,
    onSelectPeriod,
    periodMetrics,
    pnlHistory,
    currencySymbol,
    upClassName,
    downClassName,
    lineColor,
}: DashboardEquityHeroProps) {
    const trendClassName = periodMetrics.periodPnl >= 0 ? upClassName : downClassName
    const periodValueClassName = periodMetrics.periodValue >= 0 ? upClassName : downClassName

    return (
        <Surface className="overflow-hidden p-4 md:p-6">
            <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-start">
                <SectionHeader
                    eyebrow="Equity / Drawdown"
                    title="资金曲线"
                    description="主图回答当前阶段收益方向，风险解释放在右侧 rail。"
                />
                <div className="flex flex-wrap gap-1">
                    {periodOptions.map((option) => (
                        <button
                            key={option.label}
                            type="button"
                            onClick={() => onSelectPeriod(option.label)}
                            className={`rounded-full px-3 py-1.5 text-xs font-semibold transition-colors ${
                                selectedPeriod === option.label
                                    ? 'bg-slate-950 text-white dark:bg-slate-100 dark:text-slate-950'
                                    : 'bg-slate-100 text-slate-500 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                            }`}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            </div>
            <div className="mt-4 flex flex-wrap items-end gap-2">
                <p className={`text-3xl font-semibold tracking-tight ${trendClassName}`}>
                    {periodMetrics.periodPnl >= 0 ? '+' : ''}{periodMetrics.periodPnl.toFixed(2)}%
                </p>
                <p className={`pb-1 text-sm font-semibold ${periodValueClassName}`}>
                    ({periodMetrics.periodValue >= 0 ? '+' : ''}{currencySymbol}{Math.abs(periodMetrics.periodValue).toLocaleString()})
                </p>
                <p className="pb-1 text-xs text-slate-400">{selectedPeriod}阶段盈亏</p>
            </div>
            <div className="mt-5 h-[280px] md:h-[340px]">
                {pnlHistory.length > 0 ? (
                    <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={pnlHistory}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                            <XAxis dataKey="date" tick={{ fontSize: 12 }} tickFormatter={(value) => String(value).slice(5)} />
                            <YAxis tick={{ fontSize: 12 }} tickFormatter={(value) => `${value}%`} />
                            <Tooltip formatter={(value: number) => [`${value.toFixed(2)}%`, '盈亏率']} labelFormatter={(label) => `日期: ${label}`} />
                            <Line type="monotone" dataKey="pnl_percent" stroke={lineColor} strokeWidth={2.5} dot={false} />
                        </LineChart>
                    </ResponsiveContainer>
                ) : (
                    <div className="flex h-full items-center justify-center rounded-2xl border border-dashed border-slate-200 text-sm text-slate-500 dark:border-slate-800">
                        暂无资金曲线数据
                    </div>
                )}
            </div>
        </Surface>
    )
}
