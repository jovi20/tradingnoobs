'use client'

import { useRouter } from 'next/navigation'
import { PieChart, Pie, Cell, Legend, Tooltip, ResponsiveContainer } from 'recharts'
import { AssetAllocation } from '@/lib/api'
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

    const chartData = data.map(item => {
        let label = item.name;
        if (dimension === 'CORE_TYPE') label = getCoreTypeLabel(item.name as any);
        else if (dimension === 'MARKET') label = getMarketLabel(item.name as AssetMarket);
        else if (dimension === 'RISK') label = getRiskLevelInfo(item.name as AssetRiskLevel).label;

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
