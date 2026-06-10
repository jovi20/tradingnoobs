'use client'

import { Bar, BarChart, CartesianGrid, Cell, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

import { ChartFrame } from '@/components/charts/ChartFrame'
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
                <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={view.data}>
                        <CartesianGrid strokeDasharray="3 3" opacity={0.1} />
                        <XAxis dataKey="name" fontSize={11} />
                        <YAxis fontSize={11} />
                        <Tooltip contentStyle={{ backgroundColor: '#1e293b', border: 'none', borderRadius: '8px', color: '#fff', fontSize: '12px' }} />
                        <Bar dataKey="pnl" name="平均盈亏" radius={[4, 4, 0, 0]}>
                            {view.data.map((entry) => (
                                <Cell key={entry.name} fill={entry.pnl >= 0 ? '#34d399' : '#f87171'} />
                            ))}
                        </Bar>
                    </BarChart>
                </ResponsiveContainer>
            </div>
        </ChartFrame>
    )
}
