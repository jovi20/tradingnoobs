import { API_BASE } from './api.ts'
import type { InsightArtifactDetail, InsightRun } from './insightArtifacts.ts'

export const insightRunsPath = '/api/v1/insights/runs' as const

export const insightRunDetailPath = (runPublicId: string) =>
    `/api/v1/insights/runs/${runPublicId}` as const

export const insightArtifactDetailPath = (artifactPublicId: string) =>
    `/api/v1/insights/artifacts/${artifactPublicId}` as const

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
    getArtifact: (token: string, artifactPublicId: string) =>
        fetchInsightArtifact<InsightArtifactDetail>(insightArtifactDetailPath(artifactPublicId), token),
}
