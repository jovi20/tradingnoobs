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
import { AlertTriangle } from 'lucide-react'
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
            {stats.accounting_degraded && (
                <div
                    role="alert"
                    className="flex items-start gap-3 border-y border-warning/30 bg-warning/8 px-4 py-3 text-warning"
                >
                    <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                    <div>
                        <p className="text-sm font-semibold">部分账户待完成账务对账</p>
                        <p className="mt-1 text-xs">
                            汇总余额仅包含账务健康的账户；待对账账户保留只读记录。
                        </p>
                    </div>
                </div>
            )}
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
