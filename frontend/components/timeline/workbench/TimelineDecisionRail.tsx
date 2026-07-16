import { EvidenceLinkedInsightSidecar } from '@/components/insights/EvidenceLinkedInsightSidecar'
import { TimelineContextRail } from '@/components/timeline/TimelineContextRail'
import type { InsightRun } from '@/lib/insightArtifacts'
import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'
import type { TimelineView } from '@/lib/read-models'
import { ReviewInboxPanel } from './ReviewInboxPanel'

interface TimelineDecisionRailProps {
    timelineHome: TimelineHomeViewModel
    insightRuns?: InsightRun[]
    insightRunsLoading: boolean
    insightRunsError: string | null
    onRefreshInsights: () => void
    onSelectView: (value: TimelineView) => void
    hideReviewInbox?: boolean
}

export function TimelineDecisionRail({
    timelineHome,
    insightRuns,
    insightRunsLoading,
    insightRunsError,
    onRefreshInsights,
    onSelectView,
    hideReviewInbox = false,
}: TimelineDecisionRailProps) {
    return (
        <aside className="space-y-4">
            {!hideReviewInbox && <ReviewInboxPanel reviewInbox={timelineHome.reviewInbox} />}
            <EvidenceLinkedInsightSidecar
                runs={insightRuns}
                isLoading={insightRunsLoading}
                error={insightRunsError}
                title="时间线 AI 洞察"
                onRefresh={onRefreshInsights}
            />
            <TimelineContextRail
                contextRail={timelineHome.contextRail}
                onSelectView={(value) => onSelectView(value as TimelineView)}
            />
        </aside>
    )
}
