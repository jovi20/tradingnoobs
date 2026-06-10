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
        <div className="flex rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
            {[
                { id: 'CORE_TYPE', label: '类型' },
                { id: 'MARKET', label: '市场' },
                { id: 'RISK', label: '风险' },
            ].map((tab) => (
                <button
                    key={tab.id}
                    type="button"
                    onClick={() => onChangeDimension(tab.id as 'CORE_TYPE' | 'MARKET' | 'RISK')}
                    className={`rounded-md px-2 py-1 text-[10px] font-medium transition-all ${
                        allocationDimension === tab.id
                            ? 'bg-white text-primary-600 shadow-sm dark:bg-slate-700'
                            : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                    }`}
                >
                    {tab.label}
                </button>
            ))}
        </div>
    )

    return (
        <ChartFrame
            eyebrow="Allocation"
            title="资产分布"
            description="schema-first allocation view with local fallback trust when backend chart payloads are absent."
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
