'use client'

import { ChartFrame } from '@/components/charts/ChartFrame'
import { SvgBarChart } from '@/components/charts/renderers/SvgBarChart'
import { adaptLegacyAnalysisChart } from '@/lib/adapters/insight-charts'
import type { AnalysisResponse } from '@/lib/api'

interface LegacyAnalysisChartProps {
    result: AnalysisResponse | null | undefined
    compact?: boolean
}

export function LegacyAnalysisChart({ result, compact = false }: LegacyAnalysisChartProps) {
    const view = adaptLegacyAnalysisChart(result)

    return (
        <ChartFrame
            eyebrow="旧版分析"
            title="数据可视化"
            description="旧版 AI 分析结果已转换为统一图表视图，仅供迁移期读取。"
            schema={view.schema}
            trustMeta={view.trustMeta}
            emptyState={view.emptyState}
            dataCount={view.data.length}
            compact={compact}
        >
            <div className={compact ? 'h-56 w-full' : 'h-64 w-full'}>
                <SvgBarChart
                    data={view.data}
                    getLabel={(entry) => entry.name}
                    getValue={(entry) => entry.pnl}
                    getColor={(entry) => (entry.pnl >= 0 ? '#34d399' : '#f87171')}
                    valueLabel="平均盈亏"
                />
            </div>
        </ChartFrame>
    )
}
