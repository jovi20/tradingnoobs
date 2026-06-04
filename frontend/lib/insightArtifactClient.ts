import { API_BASE } from '@/lib/api'
import type { InsightRun } from '@/lib/insightArtifacts'

export const insightRunsPath = '/api/v1/insights/runs' as const

export const insightRunDetailPath = (runPublicId: string) =>
    `/api/v1/insights/runs/${runPublicId}` as const

async function fetchInsightArtifact<T>(path: string, token: string): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
    })

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Insight artifact request failed' }))
        throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
}

export const insightArtifactsAPI = {
    listRuns: (token: string) => fetchInsightArtifact<InsightRun[]>(insightRunsPath, token),
    getRun: (token: string, runPublicId: string) =>
        fetchInsightArtifact<InsightRun>(insightRunDetailPath(runPublicId), token),
}
