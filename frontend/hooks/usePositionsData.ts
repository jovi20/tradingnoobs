import { positionsAPI, accountsAPI } from '@/lib/api'
import { adaptPositions, adaptTradingAccounts, PositionViewModel, TradingAccountViewModel } from '@/lib/adapters/trading'
import { useQuery } from '@tanstack/react-query'

interface UsePositionsDataProps {
    token: string | null
    statusFilter: 'ALL' | 'OPEN' | 'CLOSED'
    accountFilter: number | 'ALL'
    dimension: 'CORE_TYPE' | 'MARKET' | 'RISK'
    categoryFilter: string
}

interface UsePositionsDataResult {
    positions: PositionViewModel[]
    accounts: TradingAccountViewModel[]
    isLoading: boolean
    error: string | null
    refresh: () => Promise<void>
}

export function usePositionsData({
    token,
    statusFilter,
    accountFilter,
    dimension,
    categoryFilter
}: UsePositionsDataProps): UsePositionsDataResult {

    // 1. Fetch Positions with Filters
    console.log('usePositionsData hook called', { token: !!token, statusFilter, accountFilter, dimension, categoryFilter })

    const positionsQuery = useQuery({
        queryKey: ['positions', token, statusFilter, accountFilter, dimension, categoryFilter],
        queryFn: async () => {
            if (!token) throw new Error('No token')

            // Build API params
            const params: any = {}
            if (statusFilter !== 'ALL') params.status = statusFilter
            if (accountFilter !== 'ALL') params.account_id = accountFilter

            if (categoryFilter !== 'ALL') {
                if (dimension === 'CORE_TYPE') params.core_type = categoryFilter
                if (dimension === 'MARKET') params.market = categoryFilter
                if (dimension === 'RISK') params.risk_level = categoryFilter
            }

            const positions = await positionsAPI.list(token, params)
            return adaptPositions(positions)
        },
        enabled: !!token,
        placeholderData: (previousData) => previousData // Keep displaying previous data while fetching new filter results
    })

    // 2. Fetch Accounts (for filter dropdown)
    const accountsQuery = useQuery({
        queryKey: ['accounts', token],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            const accounts = await accountsAPI.list(token)
            return adaptTradingAccounts(accounts)
        },
        enabled: !!token
    })

    // Combined State
    const isLoading = positionsQuery.isLoading || accountsQuery.isLoading
    const error = positionsQuery.error || accountsQuery.error

    const refresh = async () => {
        await Promise.all([
            positionsQuery.refetch(),
            accountsQuery.refetch()
        ])
    }

    return {
        positions: positionsQuery.data || [],
        accounts: accountsQuery.data || [],
        isLoading,
        error: error ? (error as Error).message : null,
        refresh
    }
}
