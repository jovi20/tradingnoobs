import { useQuery } from '@tanstack/react-query'

import { insightArtifactsAPI } from '@/lib/insightArtifactClient'
import type { InsightArtifactDetail } from '@/lib/insightArtifacts'

export function useInsightArtifact(token: string | null, artifactPublicId: string | null) {
    return useQuery<InsightArtifactDetail, Error>({
        queryKey: ['insights', 'artifacts', artifactPublicId, token],
        queryFn: async () => {
            if (!token) throw new Error('No token')
            if (!artifactPublicId) throw new Error('No artifact id')
            return insightArtifactsAPI.getArtifact(token, artifactPublicId)
        },
        enabled: !!token && !!artifactPublicId,
        staleTime: 30 * 1000,
    })
}
