import { dashboardAPI, positionsAPI } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'

export function useDashboardData(token: string | null, historyDays: number = 7) {
    // 1. Fetch Dashboard Stats
    const statsQuery = useQuery({
        queryKey: ['dashboard', 'stats', token],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            return await dashboardAPI.stats(token)
        },
        enabled: !!token
    })

    // 2. Fetch PnL History (dynamic days)
    const historyQuery = useQuery({
        queryKey: ['dashboard', 'history', token, historyDays],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            return await dashboardAPI.pnlHistory(token, historyDays)
        },
        enabled: !!token
    })

    // 3. Fetch Open Positions
    // 3. Fetch Open Positions
    const positionsQuery = useQuery({
        queryKey: ['dashboard', 'open_positions', token],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            return await positionsAPI.list(token, { status: 'OPEN' })
        },
        enabled: !!token
    })

    // 4. Fetch All Positions (for MAE/MFE Analysis)
    const allPositionsQuery = useQuery({
        queryKey: ['dashboard', 'all_positions', token],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            return await positionsAPI.list(token) // No status filter = all
        },
        enabled: !!token
    })

    // Combined Loading state
    const isLoading = statsQuery.isLoading || historyQuery.isLoading || positionsQuery.isLoading || allPositionsQuery.isLoading
    const error = statsQuery.error || historyQuery.error || positionsQuery.error || allPositionsQuery.error

    // Manual Refresh
    const refresh = async () => {
        await Promise.all([
            statsQuery.refetch(),
            historyQuery.refetch(),
            positionsQuery.refetch(),
            allPositionsQuery.refetch()
        ])
    }

    return {
        stats: statsQuery.data,
        pnlHistory: historyQuery.data || [],
        openPositions: positionsQuery.data || [],
        allPositions: allPositionsQuery.data || [],
        isLoading,
        error: error ? (error as Error).message : null,
        refresh,
        // Expose setters? With React Query, we usually control data via query keys/params.
        // If Dashboard needs to change history period, it should fetch new data, not "set" it manually.
        // However, for compatibility with current Page logic which might manually set history, 
        // we might not expose setPnlHistory. 
        // BUT wait, DashboardPage *does* have period selector logic that calls API directly.
        // We should let DashboardPage handle that specific "selected period" fetching locally, 
        // OR we make this hook accept a `period` argument. 
        // For now, let's keep the API compatible:
        setPnlHistory: () => console.warn("setPnlHistory not supported in React Query mode. Use 'useQuery' with dynamic period instead."),
    }
}
