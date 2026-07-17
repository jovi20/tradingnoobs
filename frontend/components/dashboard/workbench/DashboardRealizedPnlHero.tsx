import { ChartFrame } from '@/components/charts/ChartFrame'
import { SvgLineChart } from '@/components/charts/renderers/SvgLineChart'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import type { DashboardPeriodLabel, DashboardPeriodMetrics, DashboardPeriodOption } from '@/lib/adapters/dashboard'
import type { ChartSchema, ChartTrustMeta } from '@/lib/charts'

interface DashboardRealizedPnlHeroProps {
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

export function DashboardRealizedPnlHero({
    periodOptions,
    selectedPeriod,
    onSelectPeriod,
    periodMetrics,
    pnlHistory,
    currencySymbol,
    upClassName,
    downClassName,
    lineColor,
}: DashboardRealizedPnlHeroProps) {
    const valueClassName = periodMetrics.periodValue >= 0 ? upClassName : downClassName
    const referenceClassName = periodMetrics.periodPnl >= 0 ? upClassName : downClassName
    const hasRealizedHistory = pnlHistory.some((point) => point.pnl !== 0 || point.pnl_percent !== 0)
    const realizedChartSchema = {
        schema_version: 'chart.v1',
        chart_type: 'line',
        data_path: 'pnlHistory',
        dimensions: [{ field: 'date', label: 'Date' }],
        series: [{ field: 'pnl_percent', label: 'Realized PnL / initial principal (%)', color: lineColor }],
    } satisfies ChartSchema
    const realizedTrustMeta = {
        freshness: 'FRESH',
        source: 'JOURNAL_REALIZED_HISTORY',
        source_refs: ['dashboard:pnl-history'],
    } satisfies ChartTrustMeta

    return (
        <Surface className="overflow-hidden p-4 md:p-6">
            <div className="grid gap-4 md:grid-cols-[1fr_auto] md:items-start">
                <SectionHeader
                    eyebrow="已实现结果"
                    title="累计已实现盈亏"
                    description="按日志中的减仓和平仓事实累计；百分比以账户初始本金为分母，仅作已实现收益参考。"
                />
                <div className="grid w-full grid-cols-4 gap-1 rounded-lg bg-panel-subtle p-1 md:flex md:w-auto md:max-w-full md:overflow-x-auto">
                    {periodOptions.map((option) => (
                        <button
                            key={option.label}
                            type="button"
                            onClick={() => onSelectPeriod(option.label)}
                            className={`min-w-0 rounded-md px-2 py-1.5 text-xs font-semibold transition-colors md:shrink-0 md:px-3 ${
                                selectedPeriod === option.label
                                    ? 'bg-ink text-canvas'
                                    : 'text-ink-muted hover:bg-panel hover:text-ink'
                            }`}
                        >
                            {option.label}
                        </button>
                    ))}
                </div>
            </div>
            <div className="mt-4 flex flex-wrap items-end gap-2">
                <p className={`text-3xl font-semibold tn-nums ${valueClassName}`}>
                    {periodMetrics.periodValue >= 0 ? '+' : '-'}{currencySymbol}{Math.abs(periodMetrics.periodValue).toLocaleString()}
                </p>
                <p className={`pb-1 text-sm font-semibold tn-nums ${referenceClassName}`}>
                    {periodMetrics.periodPnl >= 0 ? '+' : ''}{periodMetrics.periodPnl.toFixed(2)}%
                </p>
                <p className="pb-1 text-xs text-ink-faint">{selectedPeriod}已实现收益参考</p>
            </div>
            <ChartFrame
                eyebrow="已实现收益参考"
                title="累计已实现盈亏曲线"
                description="每个日期点表示所选区间内截至当日的累计已实现结果。"
                schema={realizedChartSchema}
                trustMeta={realizedTrustMeta}
                emptyState={{
                    is_empty: !hasRealizedHistory,
                    reason: !hasRealizedHistory ? 'NO_REALIZED_PNL_HISTORY' : null,
                    message: !hasRealizedHistory ? '所选区间暂无已实现盈亏记录。' : undefined,
                }}
                dataCount={hasRealizedHistory ? pnlHistory.length : 0}
                compact
                className="mt-5"
            >
                {hasRealizedHistory && (
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
