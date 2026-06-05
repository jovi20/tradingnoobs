import type { DashboardStats } from '../api.ts'
import type { PositionViewModel } from './trading.ts'
import {
    adaptDashboardAllocationChartPayload,
    getDashboardChartPayloadKey,
    type DashboardAllocationDimension,
} from '../chartSchemas.ts'
import { getCurrencySymbol } from '../symbolUtils.ts'

export interface DashboardPeriodMetrics {
    periodPnl: number
    periodValue: number
}

export function calculateDashboardPeriodMetrics(
    pnlHistory: Array<{ pnl: number; pnl_percent: number }>
): DashboardPeriodMetrics {
    if (!pnlHistory || pnlHistory.length === 0) {
        return { periodPnl: 0, periodValue: 0 }
    }

    if (pnlHistory.length === 1) {
        return {
            periodPnl: pnlHistory[0].pnl_percent,
            periodValue: pnlHistory[0].pnl,
        }
    }

    const latest = pnlHistory[pnlHistory.length - 1]
    const start = pnlHistory[0]
    return {
        periodPnl: latest.pnl_percent - start.pnl_percent,
        periodValue: latest.pnl - start.pnl,
    }
}

interface AdaptDashboardPageDataInput {
    stats: DashboardStats
    openPositions: Array<Pick<PositionViewModel, 'id' | 'routeId'>>
    allPositions: PositionViewModel[]
    pnlHistory: Array<{ pnl: number; pnl_percent: number }>
    displayCurrency?: string
}

export function getDashboardAllocationData(
    stats: Pick<DashboardStats, 'core_type_allocation' | 'market_allocation' | 'risk_level_allocation' | 'chart_payloads'>,
    dimension: DashboardAllocationDimension
) {
    const chartView = getDashboardAllocationChart(stats, dimension)
    if (!chartView.isEmpty || stats.chart_payloads?.[getDashboardChartPayloadKey(dimension)]) return chartView.data
    if (dimension === 'MARKET') return stats.market_allocation
    if (dimension === 'RISK') return stats.risk_level_allocation
    return stats.core_type_allocation
}

export function getDashboardAllocationChart(
    stats: Pick<DashboardStats, 'core_type_allocation' | 'market_allocation' | 'risk_level_allocation' | 'chart_payloads'>,
    dimension: DashboardAllocationDimension
) {
    return adaptDashboardAllocationChartPayload(stats.chart_payloads?.[getDashboardChartPayloadKey(dimension)])
}

export function getDashboardMovers(stats: Pick<DashboardStats, 'top_movers' | 'bottom_movers'>) {
    return {
        top: stats.top_movers,
        bottom: stats.bottom_movers,
    }
}

export function adaptDashboardPageData({
    stats,
    openPositions,
    allPositions,
    pnlHistory,
    displayCurrency,
}: AdaptDashboardPageDataInput) {
    return {
        currencySymbol: getCurrencySymbol(displayCurrency),
        totalPnl: stats.total_pnl,
        isPositive: stats.total_pnl >= 0,
        openPositionsCount: openPositions.length,
        openPositions,
        allPositions,
        accountAllocation: stats.account_allocation,
        allocation: {
            coreType: stats.core_type_allocation,
            market: stats.market_allocation,
            risk: stats.risk_level_allocation,
        },
        allocationCharts: {
            coreType: getDashboardAllocationChart(stats, 'CORE_TYPE'),
            market: getDashboardAllocationChart(stats, 'MARKET'),
            risk: getDashboardAllocationChart(stats, 'RISK'),
        },
        movers: getDashboardMovers(stats),
        stats,
        pnlHistory,
        periodMetrics: calculateDashboardPeriodMetrics(pnlHistory),
    }
}
