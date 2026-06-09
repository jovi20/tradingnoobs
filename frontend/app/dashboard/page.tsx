'use client'

import { useState, useSyncExternalStore } from 'react'
import { Loader2 } from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useTrendColor } from '@/hooks/useTrendColor'
import { DashboardWorkbench } from '@/components/dashboard/workbench/DashboardWorkbench'
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
                <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (!stats) return null

    return (
        <div className="pb-20 md:pb-6">
            {error && (
                <div className="mb-4 rounded-xl bg-red-50 p-4 text-sm text-red-600 dark:bg-red-900/20 dark:text-red-400">
                    Error loading dashboard data: {error}
                </div>
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
