import AllocationPieChart from '@/components/dashboard/AllocationPieChart'
import type { AssetAllocation } from '@/lib/api'
import type { DashboardAllocationChartView } from '@/lib/chartSchemas'

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
    return (
        <div className="card p-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2">
                <div>
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-white">资产分布</h3>
                    {chart?.schema && (
                        <p className="mt-1 text-[11px] text-slate-400">
                            {chart.schema.schema_version} · {chart.schema.chart_type}
                            {chart.trustMeta.source ? ` · ${chart.trustMeta.source}` : ''}
                        </p>
                    )}
                </div>
                <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
                    {[
                        { id: 'CORE_TYPE', label: '类型' },
                        { id: 'MARKET', label: '市场' },
                        { id: 'RISK', label: '风险' },
                    ].map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => onChangeDimension(tab.id as 'CORE_TYPE' | 'MARKET' | 'RISK')}
                            className={`px-2 py-1 text-[10px] font-medium rounded-md transition-all ${
                                allocationDimension === tab.id
                                    ? 'bg-white dark:bg-slate-700 text-primary-600 shadow-sm'
                                    : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                        >
                            {tab.label}
                        </button>
                    ))}
                </div>
            </div>
            <AllocationPieChart data={data} dimension={allocationDimension} />
            {chart?.isEmpty && (
                <p className="mt-3 rounded-xl border border-dashed border-slate-200 px-3 py-2 text-xs text-slate-500 dark:border-slate-700">
                    schema empty state: {chart.emptyState.reason ?? 'NO_DATA'}
                </p>
            )}
        </div>
    )
}
