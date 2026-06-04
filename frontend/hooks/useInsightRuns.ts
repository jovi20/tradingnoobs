import { useQuery } from '@tanstack/react-query'
import { insightArtifactsAPI } from '@/lib/insightArtifactClient'
import type { InsightRun } from '@/lib/insightArtifacts'

export function useInsightRuns(token: string | null) {
    return useQuery<InsightRun[], Error>({
        queryKey: ['insights', 'runs', token],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            return insightArtifactsAPI.listRuns(token)
        },
        enabled: !!token,
        staleTime: 30 * 1000,
    })
}
