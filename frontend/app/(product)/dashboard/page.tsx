'use client'

import { useState } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useTrendColor } from '@/hooks/useTrendColor'
import { DashboardWorkbench } from '@/components/dashboard/workbench/DashboardWorkbench'
import { LoadingState } from '@/components/ui/Spinner'
import { Callout } from '@/components/ui/Callout'
import type { DashboardPeriodLabel } from '@/lib/adapters/dashboard'

export default function DashboardPage() {
    const { token, settings } = useAuth()
    const trendColor = useTrendColor()
    const [selectedPeriod, setSelectedPeriod] = useState<DashboardPeriodLabel>('1周')
    const [historyDays, setHistoryDays] = useState<number>(7)
    const [periodReferenceDate] = useState(() => new Date())
    const { stats, pnlHistory, openPositions, isLoading, error } = useDashboardData(token, historyDays)

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <LoadingState label="正在加载日志看板…" />
            </div>
        )
    }

    if (error && !stats) {
        return (
            <Callout kind="error">
                日志看板数据加载失败：{error}
            </Callout>
        )
    }

    if (!stats) return null

    return (
        <div>
            {error && (
                <Callout kind="error" className="mb-4">
                    日志看板数据加载失败：{error}
                </Callout>
            )}
            <DashboardWorkbench
                stats={stats}
                pnlHistory={pnlHistory}
                openPositions={openPositions}
                displayCurrency={settings?.display_currency}
                selectedPeriod={selectedPeriod}
                periodReferenceDate={periodReferenceDate}
                onChangePeriod={(label, days) => {
                    setSelectedPeriod(label)
                    setHistoryDays(days)
                }}
                trend={{
                    upClassName: trendColor.upColor,
                    downClassName: trendColor.downColor,
                    lineColor: stats.realized_pnl >= 0 ? trendColor.upHex : trendColor.downHex,
                }}
            />
        </div>
    )
}
