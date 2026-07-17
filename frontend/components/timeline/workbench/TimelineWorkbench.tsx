import { buildTimelineSummaryMetrics } from '@/lib/adapters/timeline-workbench'
import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'
import type { JournalTimelineView } from '@/lib/read-models'
import { MetricTile } from '@/components/ui/MetricTile'
import { PageFrame } from '@/components/ui/PageFrame'
import { ReviewInboxPanel } from './ReviewInboxPanel'
import { TimelineDecisionRail } from './TimelineDecisionRail'
import { TimelineFeedPanel } from './TimelineFeedPanel'
import { TimelineViewTabs } from './TimelineViewTabs'
import { TimelineWorkbenchHeader } from './TimelineWorkbenchHeader'

interface TimelineWorkbenchProps {
    timelineHome: TimelineHomeViewModel
    view: JournalTimelineView
    onChangeView: (value: JournalTimelineView) => void
    onRefresh: () => void
}

export function TimelineWorkbench({
    timelineHome,
    view,
    onChangeView,
    onRefresh,
}: TimelineWorkbenchProps) {
    const metrics = buildTimelineSummaryMetrics(timelineHome.summaryBar)

    return (
        <PageFrame>
            <div className="space-y-6">
                <TimelineWorkbenchHeader pageMeta={timelineHome.pageMeta} onRefresh={onRefresh} />

                <div className="grid gap-3 md:grid-cols-3">
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
                            onSelectView={onChangeView}
                        />
                    </div>
                </div>

                <div className="lg:hidden">
                    <TimelineDecisionRail
                        timelineHome={timelineHome}
                        onSelectView={onChangeView}
                        hideReviewInbox={timelineHome.reviewInbox.total > 0}
                    />
                </div>
            </div>
        </PageFrame>
    )
}
