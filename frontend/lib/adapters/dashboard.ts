import type { DashboardStats } from '../api.ts'
import type { PositionViewModel } from './trading.ts'
import { getCurrencySymbol } from '../symbolUtils.ts'

export type DashboardPeriodLabel = '1周' | '本月' | '1月' | '3月' | '本年' | '1年' | '全部'
export type DashboardTone = 'neutral' | 'positive' | 'negative'

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

export interface DashboardPeriodMetrics {
    periodPnl: number
    periodValue: number
}

export interface DashboardPnlHistoryPoint {
    date: string
    pnl: number
    pnl_percent: number
}

export interface DashboardJournalSummary {
    journalBalance: number
    realizedPnl: number
    winRate: number
    avgPnlRatio: number
    totalTrades: number
    openPositions: number
    closedTrades: number
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

export function buildDashboardStatusMetrics({
    summary,
    currencySymbol,
}: {
    summary: DashboardJournalSummary
    currencySymbol: string
}): DashboardStatusMetric[] {
    return [
        {
            label: '累计已实现盈亏',
            value: formatSignedCurrency(summary.realizedPnl, currencySymbol),
            detail: `日志余额 ${currencySymbol}${summary.journalBalance.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
            tone: summary.realizedPnl >= 0 ? 'positive' : 'negative',
        },
        {
            label: '已实现胜率',
            value: formatPercentValue(summary.winRate),
            detail: `已实现盈亏比 ${summary.avgPnlRatio.toFixed(2)}`,
            tone: 'neutral',
        },
        {
            label: '交易日志',
            value: `${summary.totalTrades}`,
            detail: `已平仓 ${summary.closedTrades} 笔`,
            tone: 'neutral',
        },
        {
            label: '未平仓记录',
            value: `${summary.openPositions}`,
            detail: '按建仓事实展示',
            tone: 'neutral',
        },
    ]
}

export function formatDashboardAccountRows(
    accountBalances: DashboardStats['account_balances'],
    currencySymbol: string
) {
    return accountBalances.map((account) => ({
        name: account.name,
        broker: account.broker,
        balanceLabel: `${currencySymbol}${account.journal_balance.toLocaleString(undefined, { maximumFractionDigits: 0 })}`,
        journalBalanceTrusted: account.journal_balance_trusted,
        accountingHealth: account.accounting_health,
    }))
}

export function calculateDashboardPeriodMetrics(
    pnlHistory: Array<Pick<DashboardPnlHistoryPoint, 'pnl' | 'pnl_percent'>>
): DashboardPeriodMetrics {
    const latest = pnlHistory.at(-1)
    if (!latest) return { periodPnl: 0, periodValue: 0 }

    // The endpoint resets its cumulative total at the requested window start.
    return {
        periodPnl: latest.pnl_percent,
        periodValue: latest.pnl,
    }
}

interface AdaptDashboardPageDataInput {
    stats: DashboardStats
    openPositions: PositionViewModel[]
    pnlHistory: DashboardPnlHistoryPoint[]
    displayCurrency?: string
}

export function adaptDashboardPageData({
    stats,
    openPositions,
    pnlHistory,
    displayCurrency,
}: AdaptDashboardPageDataInput) {
    const currencySymbol = getCurrencySymbol(displayCurrency)
    const summary: DashboardJournalSummary = {
        journalBalance: stats.journal_balance,
        realizedPnl: stats.realized_pnl,
        winRate: stats.win_rate,
        avgPnlRatio: stats.avg_pnl_ratio,
        totalTrades: stats.total_trades,
        openPositions: stats.open_positions,
        closedTrades: stats.closed_trades,
    }

    return {
        currencySymbol,
        summary,
        openPositions,
        accountRows: formatDashboardAccountRows(stats.account_balances, currencySymbol),
        pnlHistory,
        periodMetrics: calculateDashboardPeriodMetrics(pnlHistory),
    }
}
