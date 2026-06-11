import { useState } from 'react'
import { PageFrame } from '@/components/ui/PageFrame'
import {
    adaptDashboardPageData,
    buildDashboardStatusMetrics,
    formatDashboardAccountRows,
    getDashboardAllocationChart,
    getDashboardAllocationData,
    getDashboardHistoryDays,
    getDashboardPeriodOptions,
    getDashboardRiskPosture,
    type DashboardPeriodLabel,
} from '@/lib/adapters/dashboard'
import type { PositionViewModel } from '@/lib/adapters/trading'
import type { DashboardStats } from '@/lib/api'
import type { DashboardAllocationDimension } from '@/lib/chartSchemas'
import { DashboardEquityHero } from './DashboardEquityHero'
import { DashboardEvidenceStack } from './DashboardEvidenceStack'
import { DashboardRiskRail } from './DashboardRiskRail'
import { DashboardStatusRail } from './DashboardStatusRail'
import { DashboardStructureGrid } from './DashboardStructureGrid'
import { DashboardWorkbenchHeader } from './DashboardWorkbenchHeader'

interface DashboardWorkbenchProps {
    stats: DashboardStats
    pnlHistory: Array<{ date: string; pnl: number; pnl_percent: number }>
    openPositions: PositionViewModel[]
    allPositions: PositionViewModel[]
    displayCurrency?: string
    selectedPeriod: DashboardPeriodLabel
    onChangePeriod: (label: DashboardPeriodLabel, days: number) => void
    isMobileSankey: boolean
    trend: {
        upClassName: string
        downClassName: string
        lineColor: string
    }
}

export function DashboardWorkbench({
    stats,
    pnlHistory,
    openPositions,
    allPositions,
    displayCurrency,
    selectedPeriod,
    onChangePeriod,
    isMobileSankey,
    trend,
}: DashboardWorkbenchProps) {
    const [allocationDimension, setAllocationDimension] = useState<DashboardAllocationDimension>('CORE_TYPE')
    const [periodReferenceDate] = useState(() => new Date())
    const dashboard = adaptDashboardPageData({ stats, openPositions, allPositions, pnlHistory, displayCurrency })
    const riskPosture = getDashboardRiskPosture(stats)
    const periodOptions = getDashboardPeriodOptions(periodReferenceDate)
    const statusMetrics = buildDashboardStatusMetrics({ stats, currencySymbol: dashboard.currencySymbol })
    const accountRows = formatDashboardAccountRows(dashboard.accountAllocation, dashboard.currencySymbol)

    return (
        <PageFrame className="space-y-6">
            <DashboardWorkbenchHeader riskPosture={riskPosture} />
            <DashboardStatusRail metrics={statusMetrics} />
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
                <DashboardEquityHero
                    periodOptions={periodOptions}
                    selectedPeriod={selectedPeriod}
                    onSelectPeriod={(label) => onChangePeriod(label, getDashboardHistoryDays(label, periodReferenceDate))}
                    periodMetrics={dashboard.periodMetrics}
                    pnlHistory={dashboard.pnlHistory}
                    currencySymbol={dashboard.currencySymbol}
                    upClassName={trend.upClassName}
                    downClassName={trend.downClassName}
                    lineColor={trend.lineColor}
                />
                <DashboardRiskRail
                    riskPosture={riskPosture}
                    openPositionsCount={dashboard.openPositionsCount}
                    hasPnlHistory={dashboard.pnlHistory.length > 0}
                    riskAlerts={dashboard.riskAlerts}
                />
            </div>
            <DashboardStructureGrid
                allocationDimension={allocationDimension}
                onChangeAllocationDimension={setAllocationDimension}
                allocationData={getDashboardAllocationData(stats, allocationDimension)}
                allocationChart={getDashboardAllocationChart(stats, allocationDimension)}
                accountRows={accountRows}
                stats={stats}
                movers={dashboard.movers}
                riskPosture={riskPosture}
            />
            <DashboardEvidenceStack
                stats={stats}
                openPositions={dashboard.openPositions}
                allPositions={dashboard.allPositions}
                isMobileSankey={isMobileSankey}
            />
        </PageFrame>
    )
}
