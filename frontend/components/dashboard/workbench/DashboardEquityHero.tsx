import { ChartFrame } from '@/components/charts/ChartFrame'
import { SvgLineChart } from '@/components/charts/renderers/SvgLineChart'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import { shouldRenderEquityLineChart } from '@/lib/adapters/chart-views'
import type { DashboardPeriodLabel, DashboardPeriodMetrics, DashboardPeriodOption } from '@/lib/adapters/dashboard'
import type { ChartSchema, ChartTrustMeta } from '@/lib/charts'

interface DashboardEquityHeroProps {
    periodOptions: DashboardPeriodOption[]
    selectedPeriod: DashboardPeriodLabel
    onSelectPeriod: (label: DashboardPeriodLabel) => void
    periodMetrics: DashboardPeriodMetrics
    pnlHistory: Array<{ date: string; pnl: number; pnl_percent: number; total_equity?: number }>
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
    const equityChartSchema = {
        schema_version: 'chart.v1',
        chart_type: 'line',
        data_path: 'pnlHistory',
        dimensions: [{ field: 'date', label: 'Date' }],
        series: [{ field: 'pnl_percent', label: 'PnL %', color: lineColor }],
    } satisfies ChartSchema
    const equityTrustMeta = {
        freshness: 'DELAYED',
        source: 'LOCAL_DASHBOARD_HISTORY',
        source_refs: ['dashboard:pnlHistory'],
    } satisfies ChartTrustMeta
    const canRenderEquityChart = shouldRenderEquityLineChart(pnlHistory)

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
            <ChartFrame
                eyebrow="Equity"
                title="资金曲线数据"
                description="本阶段仍使用前端本地曲线数据，等待后端 schema-first equity payload。"
                schema={equityChartSchema}
                trustMeta={equityTrustMeta}
                emptyState={{
                    is_empty: !canRenderEquityChart,
                    reason: !canRenderEquityChart ? 'NO_EQUITY_HISTORY' : null,
                    message: !canRenderEquityChart ? '暂无资金曲线数据' : undefined,
                }}
                dataCount={canRenderEquityChart ? pnlHistory.length : 0}
                compact
                className="mt-5"
            >
                {canRenderEquityChart && (
                    <div className="h-[280px] md:h-[340px]">
                        <SvgLineChart
                            data={pnlHistory}
                            getXLabel={(entry) => entry.date}
                            getValue={(entry) => entry.pnl_percent}
                            stroke={lineColor}
                            valueSuffix="%"
                        />
                    </div>
                )}
            </ChartFrame>
        </Surface>
    )
}
