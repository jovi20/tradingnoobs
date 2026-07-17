import { TimelineContextRail } from '@/components/timeline/TimelineContextRail'
import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'
import type { JournalTimelineView } from '@/lib/read-models'
import { ReviewInboxPanel } from './ReviewInboxPanel'

interface TimelineDecisionRailProps {
    timelineHome: TimelineHomeViewModel
    onSelectView: (value: JournalTimelineView) => void
    hideReviewInbox?: boolean
}

export function TimelineDecisionRail({
    timelineHome,
    onSelectView,
    hideReviewInbox = false,
}: TimelineDecisionRailProps) {
    return (
        <aside className="space-y-4">
            {!hideReviewInbox && <ReviewInboxPanel reviewInbox={timelineHome.reviewInbox} />}
            <TimelineContextRail
                contextRail={timelineHome.contextRail}
                onSelectView={(value) => onSelectView(value as JournalTimelineView)}
            />
        </aside>
    )
}
