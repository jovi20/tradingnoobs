import { lifecycleReadModelPath, type LifecycleReadModel } from '@/lib/readModels'
import { readModelsAPI } from '@/lib/readModelClient'
import { useLifecycleReadModel } from '@/hooks/useLifecycleReadModel'
import { LifecycleThread } from '@/components/lifecycle/LifecycleThread'

const positionPublicId = '01JPOSITIONTASK6000000000'
const lifecyclePath: `/api/v1/read-models/trading-positions/${string}/lifecycle` =
    lifecycleReadModelPath(positionPublicId)

const lifecycle: LifecycleReadModel = {
    meta: {
        as_of: '2026-06-04T10:30:00.000Z',
        freshness: 'FRESH',
        source: 'DERIVED',
        maturity: 'EARLY_SIGNAL',
        value_status: 'FINAL',
        generated_by: 'task6_lifecycle_contract',
        source_refs: [],
    },
    position_public_id: positionPublicId,
    lifecycle_nodes: [],
    ledger_refs: [],
    evidence_items: [],
    narrative_signals: [],
}

async function contractFetch(token: string) {
    const response: LifecycleReadModel = await readModelsAPI.lifecycle(token, positionPublicId)
    return response.position_public_id
}

function ContractLifecycleConsumer({ token }: { token: string | null }) {
    const query = useLifecycleReadModel(token, positionPublicId)
    return (
        <LifecycleThread
            lifecycle={query.data ?? lifecycle}
            isLoading={query.isLoading}
            error={query.error ? query.error.message : null}
            onRefresh={() => query.refetch()}
        />
    )
}

export const task6LifecycleContract = {
    lifecyclePath,
    contractFetch,
    ContractLifecycleConsumer,
}
