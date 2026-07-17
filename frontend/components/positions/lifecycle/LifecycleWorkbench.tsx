import { PageFrame } from '@/components/ui/PageFrame'
import {
    getLifecycleLegacyPanelState,
    getLifecyclePrimaryActions,
    getLifecycleReversalAction,
    type LifecycleDetailViewModel,
} from '@/lib/adapters/lifecycle'
import {
    getLegacyBatchMutationState,
    getLegacyReviewDisplayState,
    type PositionViewModel,
    type TradeBatchViewModel,
} from '@/lib/adapters/trading'
import { LifecycleActionPanel } from './LifecycleActionPanel'
import { LifecycleEventRail } from './LifecycleEventRail'
import { LifecycleEvidencePanel } from './LifecycleEvidencePanel'
import { LifecycleHero } from './LifecycleHero'
import { LifecycleMigrationPanel } from './LifecycleMigrationPanel'
import { LifecycleWorkbenchHeader } from './LifecycleWorkbenchHeader'

interface LifecycleWorkbenchProps {
    lifecycle: LifecycleDetailViewModel
    legacyPosition: PositionViewModel | null
    sortedBatches: TradeBatchViewModel[]
    isReversing: boolean
    onEditNarrative: () => void
    onReverseLatest: () => void
    onEditMetadata: () => void
    onEditBatch: (batch: TradeBatchViewModel) => void
}

export function LifecycleWorkbench({
    lifecycle,
    legacyPosition,
    sortedBatches,
    isReversing,
    onEditNarrative,
    onReverseLatest,
    onEditMetadata,
    onEditBatch,
}: LifecycleWorkbenchProps) {
    const reversal = getLifecycleReversalAction(lifecycle)
    const actions = getLifecyclePrimaryActions({
        hasEditableNarrativeEvent: Boolean(lifecycle.thesisSourceEventPublicId || lifecycle.nodes[0]?.node_public_id),
        reversal,
    })
    const legacyPanel = getLifecycleLegacyPanelState({
        hasTruthLifecycle: true,
        hasLegacyPosition: Boolean(legacyPosition),
    })
    const legacyBatchMutationState = getLegacyBatchMutationState(Boolean(lifecycle))
    const legacyReviewDisplayState = getLegacyReviewDisplayState(Boolean(lifecycle), Boolean(legacyPosition?.trade_review))

    return (
        <PageFrame className="space-y-6 pb-20 md:pb-6">
            <LifecycleWorkbenchHeader lifecycle={lifecycle} legacyPosition={legacyPosition} />
            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_380px]">
                <div className="space-y-6">
                    <LifecycleHero lifecycle={lifecycle} />
                    <LifecycleActionPanel
                        actions={actions}
                        isReversing={isReversing}
                        onEditNarrative={onEditNarrative}
                        onReverseLatest={onReverseLatest}
                    />
                    <LifecycleEvidencePanel lifecycle={lifecycle} />
                </div>
                <aside className="space-y-6">
                    <LifecycleEventRail lifecycle={lifecycle} />
                </aside>
            </div>
            {legacyPanel.shouldRender && legacyPosition && (
                <LifecycleMigrationPanel
                    position={legacyPosition}
                    hasTruthLifecycle
                    panel={legacyPanel}
                    sortedBatches={sortedBatches}
                    legacyBatchMutationState={legacyBatchMutationState}
                    legacyReviewDisplayState={legacyReviewDisplayState}
                    onEditMetadata={onEditMetadata}
                    onEditBatch={onEditBatch}
                />
            )}
        </PageFrame>
    )
}
