import { PageFrame } from '@/components/ui/PageFrame'
import {
    adaptDashboardPageData,
    buildDashboardStatusMetrics,
    getDashboardHistoryDays,
    getDashboardPeriodOptions,
    type DashboardPeriodLabel,
} from '@/lib/adapters/dashboard'
import type { PositionViewModel } from '@/lib/adapters/trading'
import type { DashboardStats } from '@/lib/api'
import { DashboardEvidenceStack } from './DashboardEvidenceStack'
import { DashboardJournalGrid } from './DashboardJournalGrid'
import { DashboardRealizedPnlHero } from './DashboardRealizedPnlHero'
import { DashboardStatusRail } from './DashboardStatusRail'
import { DashboardWorkbenchHeader } from './DashboardWorkbenchHeader'

interface DashboardWorkbenchProps {
    stats: DashboardStats
    pnlHistory: Array<{ date: string; pnl: number; pnl_percent: number }>
    openPositions: PositionViewModel[]
    displayCurrency?: string
    selectedPeriod: DashboardPeriodLabel
    periodReferenceDate: Date
    onChangePeriod: (label: DashboardPeriodLabel, days: number) => void
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
    displayCurrency,
    selectedPeriod,
    periodReferenceDate,
    onChangePeriod,
    trend,
}: DashboardWorkbenchProps) {
    const dashboard = adaptDashboardPageData({ stats, openPositions, pnlHistory, displayCurrency })
    const periodOptions = getDashboardPeriodOptions(periodReferenceDate)
    const statusMetrics = buildDashboardStatusMetrics({
        summary: dashboard.summary,
        currencySymbol: dashboard.currencySymbol,
    })

    return (
        <PageFrame className="space-y-6">
            <DashboardWorkbenchHeader />
            <DashboardStatusRail metrics={statusMetrics} />
            <DashboardRealizedPnlHero
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
            <DashboardJournalGrid accountRows={dashboard.accountRows} summary={dashboard.summary} />
            <DashboardEvidenceStack openPositions={dashboard.openPositions} />
        </PageFrame>
    )
}
