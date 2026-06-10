'use client'

import { useRouter } from 'next/navigation'
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts'
import type { AssetAllocation } from '@/lib/api'
import { getCoreTypeLabel, getMarketLabel, getRiskLevelInfo, getAssetTypeHexColor, AssetMarket, AssetRiskLevel } from '@/lib/symbolUtils'

interface AllocationPieChartProps {
    data: AssetAllocation[]
    dimension: 'CORE_TYPE' | 'MARKET' | 'RISK'
}

export default function AllocationPieChart({ data, dimension }: AllocationPieChartProps) {
    const router = useRouter()

    if (!data || data.length === 0) {
        return <div className="h-full flex items-center justify-center text-slate-500 min-h-[300px]">暂无数据</div>
    }

    // Cross-dimension label map for keys that appear in all 3 allocation maps
    // but don't belong to any single dimension's enum
    const universalLabels: Record<string, string> = {
        'CASH': '现金',
        'EQUITY': '股票',
        'UNKNOWN': '未分类',
    }

    const chartData = data.map(item => {
        // 1. Check universal labels first (handles CASH, EQUITY, etc. across all dimensions)
        let label = universalLabels[item.name];

        // 2. If not a universal key, use dimension-specific mapping
        if (!label) {
            if (dimension === 'CORE_TYPE') label = getCoreTypeLabel(item.name as any);
            else if (dimension === 'MARKET') label = getMarketLabel(item.name as AssetMarket);
            else if (dimension === 'RISK') label = getRiskLevelInfo(item.name as AssetRiskLevel).label;
            else label = item.name;
        }

        return {
            ...item,
            name: label,
            originalName: item.name
        }
    })

    return (
        <div className="h-[300px] w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                    <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                        nameKey="name"
                        onClick={(entry) => {
                            if (entry && entry.originalName) {
                                let queryParam = 'asset_type';
                                if (dimension === 'CORE_TYPE') queryParam = 'core_type';
                                else if (dimension === 'MARKET') queryParam = 'market';
                                else if (dimension === 'RISK') queryParam = 'risk_level';
                                router.push(`/positions?${queryParam}=${entry.originalName}&dimension=${dimension}`)
                            }
                        }}
                        className="cursor-pointer focus:outline-none"
                    >
                        {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={getAssetTypeHexColor(entry.originalName)} />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(value: number, name: string, props: any) => `${props.payload.percent}%`}
                    />
                    <Legend />
                </PieChart>
            </ResponsiveContainer>
        </div>
    )
}
