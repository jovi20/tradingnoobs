'use client'

import { useState, useSyncExternalStore } from 'react'
import { useAuth } from '@/contexts/AuthContext'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useTrendColor } from '@/hooks/useTrendColor'
import { DashboardWorkbench } from '@/components/dashboard/workbench/DashboardWorkbench'
import { LoadingState } from '@/components/ui/Spinner'
import { Callout } from '@/components/ui/Callout'
import type { DashboardPeriodLabel } from '@/lib/adapters/dashboard'

function subscribeToViewport(callback: () => void) {
    window.addEventListener('resize', callback)
    return () => window.removeEventListener('resize', callback)
}

function getSankeyViewportSnapshot() {
    return window.innerWidth < 640
}

function getSankeyServerSnapshot() {
    return false
}

function useIsMobileSankey() {
    return useSyncExternalStore(subscribeToViewport, getSankeyViewportSnapshot, getSankeyServerSnapshot)
}

export default function DashboardPage() {
    const { token, settings } = useAuth()
    const trendColor = useTrendColor()
    const [selectedPeriod, setSelectedPeriod] = useState<DashboardPeriodLabel>('1周')
    const [historyDays, setHistoryDays] = useState<number>(7)
    const isMobileSankey = useIsMobileSankey()
    const { stats, pnlHistory, openPositions, allPositions, isLoading, error } = useDashboardData(token, historyDays)

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <LoadingState label="正在加载看板…" />
            </div>
        )
    }

    if (!stats) return null

    return (
        <div>
            {error && (
                <Callout kind="error" className="mb-4">
                    看板数据加载失败：{error}
                </Callout>
            )}
            <DashboardWorkbench
                stats={stats}
                pnlHistory={pnlHistory}
                openPositions={openPositions}
                allPositions={allPositions}
                displayCurrency={settings?.display_currency}
                selectedPeriod={selectedPeriod}
                onChangePeriod={(label, days) => {
                    setSelectedPeriod(label)
                    setHistoryDays(days)
                }}
                isMobileSankey={isMobileSankey}
                trend={{
                    upClassName: trendColor.upColor,
                    downClassName: trendColor.downColor,
                    lineColor: trendColor.upHex,
                }}
            />
        </div>
    )
}
