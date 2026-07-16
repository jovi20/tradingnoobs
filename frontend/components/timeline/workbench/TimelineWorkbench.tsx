import { buildTimelineSummaryMetrics } from '@/lib/adapters/timeline-workbench'
import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'
import type { InsightRun } from '@/lib/insightArtifacts'
import type { TimelineView } from '@/lib/read-models'
import { MetricTile } from '@/components/ui/MetricTile'
import { PageFrame } from '@/components/ui/PageFrame'
import { ReviewInboxPanel } from './ReviewInboxPanel'
import { TimelineDecisionRail } from './TimelineDecisionRail'
import { TimelineFeedPanel } from './TimelineFeedPanel'
import { TimelineViewTabs } from './TimelineViewTabs'
import { TimelineWorkbenchHeader } from './TimelineWorkbenchHeader'

interface TimelineWorkbenchProps {
    timelineHome: TimelineHomeViewModel
    view: TimelineView
    onChangeView: (value: TimelineView) => void
    onRefresh: () => void
    insightRuns?: InsightRun[]
    insightRunsLoading: boolean
    insightRunsError: string | null
    onRefreshInsights: () => void
}

export function TimelineWorkbench({
    timelineHome,
    view,
    onChangeView,
    onRefresh,
    insightRuns,
    insightRunsLoading,
    insightRunsError,
    onRefreshInsights,
}: TimelineWorkbenchProps) {
    const metrics = buildTimelineSummaryMetrics(timelineHome.summaryBar)

    return (
        <PageFrame>
            <div className="space-y-6">
                <TimelineWorkbenchHeader pageMeta={timelineHome.pageMeta} onRefresh={onRefresh} />

                <div className="grid gap-3 md:grid-cols-4">
                    {metrics.map((metric) => (
                        <MetricTile
                            key={metric.key}
                            label={metric.label}
                            value={metric.value}
                            detail={metric.detail}
                            tone={metric.tone}
                        />
                    ))}
                </div>

                <TimelineViewTabs value={view} onChange={onChangeView} />

                {timelineHome.reviewInbox.total > 0 && (
                    <div className="lg:hidden">
                        <ReviewInboxPanel reviewInbox={timelineHome.reviewInbox} />
                    </div>
                )}

                <div className="grid gap-5 lg:grid-cols-[minmax(0,1.55fr)_minmax(320px,0.9fr)]">
                    <TimelineFeedPanel timelineHome={timelineHome} />
                    <div className="hidden lg:block">
                        <TimelineDecisionRail
                            timelineHome={timelineHome}
                            insightRuns={insightRuns}
                            insightRunsLoading={insightRunsLoading}
                            insightRunsError={insightRunsError}
                            onRefreshInsights={onRefreshInsights}
                            onSelectView={onChangeView}
                        />
                    </div>
                </div>

                <div className="lg:hidden">
                    <TimelineDecisionRail
                        timelineHome={timelineHome}
                        insightRuns={insightRuns}
                        insightRunsLoading={insightRunsLoading}
                        insightRunsError={insightRunsError}
                        onRefreshInsights={onRefreshInsights}
                        onSelectView={onChangeView}
                        hideReviewInbox={timelineHome.reviewInbox.total > 0}
                    />
                </div>
            </div>
        </PageFrame>
    )
}
