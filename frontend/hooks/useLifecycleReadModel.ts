import { useQuery } from '@tanstack/react-query'
import { readModelsAPI } from '@/lib/readModelClient'
import type { LifecycleReadModel } from '@/lib/readModels'

export function useLifecycleReadModel(token: string | null, positionPublicId: string | null) {
    return useQuery<LifecycleReadModel, Error>({
        queryKey: ['read-models', 'lifecycle', positionPublicId, token],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            if (!positionPublicId) throw new Error('No position public id')
            return readModelsAPI.lifecycle(token, positionPublicId)
        },
        enabled: !!token && !!positionPublicId,
        staleTime: 30 * 1000,
    })
}
