'use client'

import { useRouter } from 'next/navigation'
import { SvgPieChart } from '@/components/charts/renderers/SvgPieChart'
import type { AssetAllocation } from '@/lib/api'
import { getCoreTypeLabel, getMarketLabel, getRiskLevelInfo, getAssetTypeHexColor, AssetMarket, AssetRiskLevel } from '@/lib/symbolUtils'

interface AllocationPieChartProps {
    data: AssetAllocation[]
    dimension: 'CORE_TYPE' | 'MARKET' | 'RISK'
}

export default function AllocationPieChart({ data, dimension }: AllocationPieChartProps) {
    const router = useRouter()

    if (!data || data.length === 0) {
        return <div className="h-full flex items-center justify-center text-ink-muted min-h-[300px]">暂无数据</div>
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

    const navigateToDimension = (entry: { originalName: string }) => {
        let queryParam = 'asset_type';
        if (dimension === 'CORE_TYPE') queryParam = 'core_type';
        else if (dimension === 'MARKET') queryParam = 'market';
        else if (dimension === 'RISK') queryParam = 'risk_level';
        router.push(`/positions?${queryParam}=${entry.originalName}&dimension=${dimension}`)
    }

    return (
        <div className="h-[300px] w-full mt-4">
            <SvgPieChart
                data={chartData}
                getLabel={(entry) => entry.name}
                getValue={(entry) => entry.value}
                getColor={(entry) => getAssetTypeHexColor(entry.originalName)}
                onSliceClick={navigateToDimension}
            />
        </div>
    )
}
