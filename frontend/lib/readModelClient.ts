import { API_BASE } from '@/lib/api'
import {
    homeReadModelPath,
    lifecycleReadModelPath,
    type HomeReadModel,
    type LifecycleReadModel,
} from '@/lib/readModels'

async function fetchReadModel<T>(path: string, token: string): Promise<T> {
    const response = await fetch(`${API_BASE}${path}`, {
        headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${token}`,
        },
    })

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Read model request failed' }))
        throw new Error(error.detail || `HTTP ${response.status}`)
    }

    return response.json()
}

export const readModelsAPI = {
    home: (token: string) => fetchReadModel<HomeReadModel>(homeReadModelPath, token),
    lifecycle: (token: string, positionPublicId: string) =>
        fetchReadModel<LifecycleReadModel>(lifecycleReadModelPath(positionPublicId), token),
}
