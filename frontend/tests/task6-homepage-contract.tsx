import { buildMockHomeReadModel, type HomeReadModel } from '@/lib/readModels'
import { readModelsAPI } from '@/lib/readModelClient'
import { useHomeReadModel } from '@/hooks/useHomeReadModel'
import { TimelineHome } from '@/components/home/TimelineHome'

const home: HomeReadModel = buildMockHomeReadModel({
    nowIso: '2026-06-04T10:00:00.000Z',
})

async function contractFetch(token: string) {
    const response: HomeReadModel = await readModelsAPI.home(token)
    return response.meta.freshness
}

function ContractHookConsumer({ token }: { token: string | null }) {
    const query = useHomeReadModel(token)
    return (
        <TimelineHome
            home={query.data ?? home}
            isLoading={query.isLoading}
            error={query.error ? query.error.message : null}
            onRefresh={() => query.refetch()}
        />
    )
}

export const task6HomepageContract = {
    contractFetch,
    ContractHookConsumer,
}
