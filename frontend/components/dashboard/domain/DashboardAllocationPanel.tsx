import AllocationPieChart from '@/components/dashboard/AllocationPieChart'
import { ChartFrame } from '@/components/charts/ChartFrame'
import type { AssetAllocation } from '@/lib/api'
import type { DashboardAllocationChartView } from '@/lib/charts'

interface DashboardAllocationPanelProps {
    allocationDimension: 'CORE_TYPE' | 'MARKET' | 'RISK'
    onChangeDimension: (value: 'CORE_TYPE' | 'MARKET' | 'RISK') => void
    data: AssetAllocation[]
    chart?: DashboardAllocationChartView
}

export function DashboardAllocationPanel({
    allocationDimension,
    onChangeDimension,
    data,
    chart,
}: DashboardAllocationPanelProps) {
    const dimensionTabs = (
        <div className="flex rounded-lg bg-panel-subtle p-1">
            {[
                { id: 'CORE_TYPE', label: '类型' },
                { id: 'MARKET', label: '市场' },
                { id: 'RISK', label: '风险' },
            ].map((tab) => (
                <button
                    key={tab.id}
                    type="button"
                    onClick={() => onChangeDimension(tab.id as 'CORE_TYPE' | 'MARKET' | 'RISK')}
                    className={`rounded-md px-2 py-1 text-[10px] font-medium transition-colors ${
                        allocationDimension === tab.id
                            ? 'bg-panel text-ink shadow-panel'
                            : 'text-ink-muted hover:text-ink-soft'
                    }`}
                >
                    {tab.label}
                </button>
            ))}
        </div>
    )

    return (
        <ChartFrame
            eyebrow="资产结构"
            title="资产分布"
            description="按类型、市场或风险维度查看资产集中度。"
            schema={chart?.schema}
            trustMeta={chart?.trustMeta}
            emptyState={chart?.emptyState}
            dataCount={data.length}
            compact
            action={dimensionTabs}
        >
            <AllocationPieChart data={data} dimension={allocationDimension} />
        </ChartFrame>
    )
}
