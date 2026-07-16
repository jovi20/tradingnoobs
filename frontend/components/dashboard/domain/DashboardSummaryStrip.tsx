import { Activity, BarChart3, Target, Wallet } from 'lucide-react'

import StatCard from '@/components/dashboard/StatCard'

interface DashboardSummaryStripProps {
    totalPnl: number
    isPositive: boolean
    currencySymbol: string
    winRate: number
    avgPnlRatio: number
    openPositions: number
    upColor: string
    downColor: string
}

export function DashboardSummaryStrip({
    totalPnl,
    isPositive,
    currencySymbol,
    winRate,
    avgPnlRatio,
    openPositions,
    upColor,
    downColor,
}: DashboardSummaryStripProps) {
    return (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <StatCard
                title="总盈亏"
                value={`${isPositive ? '+' : ''}${currencySymbol}${totalPnl.toLocaleString()}`}
                icon={Wallet}
                trend={isPositive ? 'up' : 'down'}
                color={isPositive ? upColor : downColor}
            />
            <StatCard
                title="胜率"
                value={`${winRate.toFixed(1)}%`}
                icon={Target}
                color="text-ink"
            />
            <StatCard
                title="盈亏比"
                value={avgPnlRatio.toFixed(2)}
                icon={BarChart3}
                color="text-ink"
            />
            <StatCard
                title="持仓数量"
                value={openPositions.toString()}
                icon={Activity}
                color="text-ink"
            />
        </div>
    )
}
