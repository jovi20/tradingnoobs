import type { DashboardStats } from '../api.ts'
import type { PositionViewModel } from './trading.ts'
import {
    adaptDashboardAllocationChartPayload,
    buildDashboardAllocationFallbackChart,
    getDashboardChartPayloadKey,
    type DashboardAllocationDimension,
} from '../charts.ts'
import { getCurrencySymbol } from '../symbolUtils.ts'

export type DashboardPeriodLabel = '1周' | '本月' | '1月' | '3月' | '本年' | '1年' | '全部'
export type DashboardTone = 'neutral' | 'positive' | 'negative' | 'warning' | 'danger'
export type DashboardMobileSection = 'header' | 'status' | 'equity' | 'risk' | 'structure' | 'movers' | 'positions' | 'evidence'

export interface DashboardPeriodOption {
    label: DashboardPeriodLabel
    days: number
}

export interface DashboardStatusMetric {
    label: string
    value: string
    detail: string
    tone: DashboardTone
}

export interface DashboardRiskPosture {
    label: string
    detail: string
    tone: DashboardTone
}

export interface DashboardPeriodMetrics {
    periodPnl: number
    periodValue: number
}

export interface DashboardPnlHistoryPoint {
    date: string
    pnl: number
    pnl_percent: number
}

const fixedDashboardPeriodOptions: Array<DashboardPeriodOption> = [
    { label: '1周', days: 7 },
    { label: '1月', days: 30 },
    { label: '3月', days: 90 },
    { label: '1年', days: 365 },
    { label: '全部', days: 9999 },
]

function clampDashboardDays(days: number) {
    return Math.max(1, Math.ceil(days))
}

function getDaysElapsedSince(startDate: Date, now: Date) {
    const millisecondsPerDay = 1000 * 60 * 60 * 24
    const currentDay = Date.UTC(now.getUTCFullYear(), now.getUTCMonth(), now.getUTCDate())
    return clampDashboardDays((currentDay - startDate.getTime()) / millisecondsPerDay + 1)
}

function formatSignedCurrency(value: number, currencySymbol: string) {
    const prefix = value >= 0 ? '+' : '-'
    return `${prefix}${currencySymbol}${Math.abs(value).toLocaleString(undefined, { maximumFractionDigits: 0 })}`
}

function formatPercentValue(value: number) {
    return `${value.toFixed(1)}%`
}

function formatDrawdown(maxDrawdown?: number) {
    if (maxDrawdown === undefined || maxDrawdown === null) return 'N/A'
    return `-${(maxDrawdown * 100).toFixed(1)}%`
}

export function getDashboardHistoryDays(label: DashboardPeriodLabel, now: Date = new Date()) {
    if (label === '本月') return clampDashboardDays(now.getUTCDate())
    if (label === '本年') return getDaysElapsedSince(new Date(Date.UTC(now.getUTCFullYear(), 0, 1)), now)
    return fixedDashboardPeriodOptions.find((option) => option.label === label)?.days ?? 7
}

export function getDashboardPeriodOptions(now: Date = new Date()): Array<DashboardPeriodOption> {
    return [
        { label: '1周', days: getDashboardHistoryDays('1周', now) },
        { label: '本月', days: getDashboardHistoryDays('本月', now) },
        { label: '1月', days: getDashboardHistoryDays('1月', now) },
        { label: '3月', days: getDashboardHistoryDays('3月', now) },
        { label: '本年', days: getDashboardHistoryDays('本年', now) },
        { label: '1年', days: getDashboardHistoryDays('1年', now) },
        { label: '全部', days: getDashboardHistoryDays('全部', now) },
    ]
}

export function getDashboardRiskPosture(
    stats: Pick<DashboardStats, 'max_drawdown' | 'sharpe_ratio' | 'risk_summary'>
): DashboardRiskPosture {
    const riskAlerts = stats.risk_summary?.alerts ?? []
    const criticalAlert = riskAlerts.find((alert) => alert.severity === 'CRITICAL')
    if (criticalAlert) {
        return { label: '风险预警', detail: criticalAlert.summary, tone: 'danger' }
    }
    const warningAlert = riskAlerts.find((alert) => alert.severity === 'WARNING')
    if (warningAlert) {
        return { label: '需要处理', detail: warningAlert.summary, tone: 'warning' }
    }

    const drawdown = stats.max_drawdown ?? 0
    const hasSharpe = typeof stats.sharpe_ratio === 'number'
    const sharpe = stats.sharpe_ratio ?? 0

    if (drawdown >= 0.25 || (hasSharpe && sharpe < 0.5)) {
        return { label: '风险偏高', detail: '回撤或风险调整收益已经进入警戒区', tone: 'danger' }
    }

    if (drawdown >= 0.12 || (hasSharpe && sharpe < 1)) {
        return { label: '需要观察', detail: '组合仍可运行，但风险质量需要复盘', tone: 'warning' }
    }

    return { label: '状态健康', detail: '回撤和风险调整收益保持在可接受区间', tone: 'positive' }
}

export function buildDashboardStatusMetrics({
    stats,
    currencySymbol,
}: {
    stats: Pick<DashboardStats, 'total_pnl' | 'win_rate' | 'avg_pnl_ratio' | 'open_positions' | 'max_drawdown' | 'total_assets'>
    currencySymbol: string
}): DashboardStatusMetric[] {
    const riskPosture = getDashboardRiskPosture({ max_drawdown: stats.max_drawdown, sharpe_ratio: undefined })
    return [
        {
            label: '总盈亏',
            value: formatSignedCurrency(stats.total_pnl, currencySymbol),
            detail: `资产 ${currencySymbol}${stats.total_assets.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
            tone: stats.total_pnl >= 0 ? 'positive' : 'negative',
        },
        {
            label: '胜率质量',
            value: formatPercentValue(stats.win_rate),
            detail: `盈亏比 ${stats.avg_pnl_ratio.toFixed(2)}`,
            tone: stats.win_rate >= 50 && stats.avg_pnl_ratio >= 1 ? 'positive' : 'warning',
        },
        {
            label: '最大回撤',
            value: formatDrawdown(stats.max_drawdown),
            detail: riskPosture.label,
            tone: riskPosture.tone,
        },
        {
            label: '持仓暴露',
            value: `${stats.open_positions}`,
            detail: '当前打开的交易对象',
            tone: stats.open_positions > 0 ? 'neutral' : 'warning',
        },
    ]
}

export function formatDashboardAccountRows(
    accountAllocation: DashboardStats['account_allocation'],
    currencySymbol: string
) {
    return accountAllocation.map((account) => ({
        name: account.name,
        broker: account.broker,
        valueLabel: `${currencySymbol}${account.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        percentLabel: `${account.percent.toFixed(1)}%`,
    }))
}

export function getDashboardMobileSectionOrder(hasPositions: boolean, hasEvidence: boolean): DashboardMobileSection[] {
    return [
        'header',
        'status',
        'equity',
        'risk',
        'structure',
        'movers',
        ...(hasPositions ? ['positions' as const] : []),
        ...(hasEvidence ? ['evidence' as const] : []),
    ]
}

export function calculateDashboardPeriodMetrics(
    pnlHistory: Array<Pick<DashboardPnlHistoryPoint, 'pnl' | 'pnl_percent'>>
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
    openPositions: PositionViewModel[]
    allPositions: PositionViewModel[]
    pnlHistory: DashboardPnlHistoryPoint[]
    displayCurrency?: string
}

export function getDashboardAllocationData(
    stats: Pick<DashboardStats, 'core_type_allocation' | 'market_allocation' | 'risk_level_allocation' | 'chart_payloads'>,
    dimension: DashboardAllocationDimension
) {
    return getDashboardAllocationChart(stats, dimension).data
}

export function getDashboardAllocationChart(
    stats: Pick<DashboardStats, 'core_type_allocation' | 'market_allocation' | 'risk_level_allocation' | 'chart_payloads'>,
    dimension: DashboardAllocationDimension
) {
    const schemaPayload = stats.chart_payloads?.[getDashboardChartPayloadKey(dimension)]
    if (schemaPayload) return adaptDashboardAllocationChartPayload(schemaPayload)

    if (dimension === 'MARKET') return buildDashboardAllocationFallbackChart(stats.market_allocation ?? [], dimension)
    if (dimension === 'RISK') return buildDashboardAllocationFallbackChart(stats.risk_level_allocation ?? [], dimension)
    return buildDashboardAllocationFallbackChart(stats.core_type_allocation ?? [], dimension)
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
        riskAlerts: stats.risk_summary?.alerts ?? [],
    }
}
