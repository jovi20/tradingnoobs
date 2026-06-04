import { useQuery } from '@tanstack/react-query'
import { readModelsAPI } from '@/lib/readModelClient'
import type { HomeReadModel } from '@/lib/readModels'

export function useHomeReadModel(token: string | null) {
    return useQuery<HomeReadModel, Error>({
        queryKey: ['read-models', 'home', token],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            return readModelsAPI.home(token)
        },
        enabled: !!token,
        staleTime: 30 * 1000,
    })
}
