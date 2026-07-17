import { dashboardAPI, positionsAPI, type DashboardStats } from '@/lib/api'
import { adaptPositions, type PositionViewModel } from '@/lib/adapters/trading'
import { useQuery } from '@tanstack/react-query'

export function useDashboardData(token: string | null, historyDays: number = 7) {
    const statsQuery = useQuery<DashboardStats>({
        queryKey: ['dashboard', 'stats', token],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            return dashboardAPI.stats(token)
        },
        enabled: !!token,
    })

    const historyQuery = useQuery({
        queryKey: ['dashboard', 'history', token, historyDays],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            return dashboardAPI.pnlHistory(token, historyDays)
        },
        enabled: !!token,
    })

    const positionsQuery = useQuery({
        queryKey: ['dashboard', 'open_positions', token],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            const positions = await positionsAPI.list(token, { status: 'OPEN' })
            return adaptPositions(positions)
        },
        enabled: !!token,
    })

    const isLoading = statsQuery.isLoading || historyQuery.isLoading || positionsQuery.isLoading
    const error = statsQuery.error || historyQuery.error || positionsQuery.error

    return {
        stats: statsQuery.data,
        pnlHistory: historyQuery.data || [],
        openPositions: (positionsQuery.data || []) as PositionViewModel[],
        isLoading,
        error: error ? (error as Error).message : null,
        refresh: async () => {
            await Promise.all([
                statsQuery.refetch(),
                historyQuery.refetch(),
                positionsQuery.refetch(),
            ])
        },
    }
}
