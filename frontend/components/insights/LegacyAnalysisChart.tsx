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
            eyebrow="Legacy analysis"
            title="数据可视化"
            description="旧版 AI analysis response 被转换为统一 chart.v1 视图。"
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
