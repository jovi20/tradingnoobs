import { DashboardAllocationPanel } from '@/components/dashboard/domain/DashboardAllocationPanel'
import { DashboardMoversPanel } from '@/components/dashboard/domain/DashboardMoversPanel'
import RiskMetricsCard from '@/components/dashboard/RiskMetricsCard'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import type { DashboardRiskPosture } from '@/lib/adapters/dashboard'
import type { DashboardStats, PositionMover } from '@/lib/api'
import type { DashboardAllocationChartView, DashboardAllocationDimension } from '@/lib/chartSchemas'
import type { AssetAllocation } from '@/lib/api'

interface AccountRow {
    name: string
    broker: string
    valueLabel: string
    percentLabel: string
}

interface DashboardStructureGridProps {
    allocationDimension: DashboardAllocationDimension
    onChangeAllocationDimension: (dimension: DashboardAllocationDimension) => void
    allocationData: AssetAllocation[]
    allocationChart: DashboardAllocationChartView
    accountRows: AccountRow[]
    stats: DashboardStats
    movers: {
        top: PositionMover[]
        bottom: PositionMover[]
    }
    riskPosture: DashboardRiskPosture
}

export function DashboardStructureGrid({
    allocationDimension,
    onChangeAllocationDimension,
    allocationData,
    allocationChart,
    accountRows,
    stats,
    movers,
    riskPosture,
}: DashboardStructureGridProps) {
    return (
        <div className="grid gap-6 xl:grid-cols-[1.25fr_0.9fr]">
            <div className="space-y-6">
                <DashboardAllocationPanel
                    allocationDimension={allocationDimension}
                    onChangeDimension={onChangeAllocationDimension}
                    data={allocationData}
                    chart={allocationChart}
                />
                <Surface className="p-4">
                    <SectionHeader eyebrow="资金归属" title="账户分布" description="账户层面的资金结构，辅助判断集中度。" />
                    <div className="mt-4 space-y-3">
                        {accountRows.map((account) => (
                            <div key={`${account.name}-${account.broker}`} className="flex items-center justify-between gap-4 rounded-lg bg-panel-subtle px-3 py-3 text-sm">
                                <div className="min-w-0">
                                    <p className="truncate font-semibold text-ink">{account.name}</p>
                                    <p className="text-xs text-ink-faint">{account.broker}</p>
                                </div>
                                <div className="shrink-0 text-right">
                                    <p className="font-semibold text-ink tn-nums">{account.valueLabel}</p>
                                    <p className="text-xs text-ink-faint tn-nums">{account.percentLabel}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </Surface>
            </div>
            <div className="space-y-6">
                <Surface variant={riskPosture.tone === 'danger' ? 'danger' : riskPosture.tone === 'warning' ? 'warning' : 'panel'} className="p-4">
                    <SectionHeader eyebrow="组合风险" title={riskPosture.label} description={riskPosture.detail} />
                </Surface>
                <RiskMetricsCard
                    sharpe={stats.sharpe_ratio}
                    sortino={stats.sortino_ratio}
                    calmar={stats.calmar_ratio}
                    maxDrawdown={stats.max_drawdown}
                />
                <DashboardMoversPanel top={movers.top} bottom={movers.bottom} />
            </div>
        </div>
    )
}
