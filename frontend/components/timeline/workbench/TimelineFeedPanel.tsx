import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import { getTimelineEmptyState } from '@/lib/adapters/timeline'
import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'
import { TimelineEventCardV2 } from './TimelineEventCardV2'

interface TimelineFeedPanelProps {
    timelineHome: TimelineHomeViewModel
}

export function TimelineFeedPanel({ timelineHome }: TimelineFeedPanelProps) {
    const emptyState = getTimelineEmptyState(timelineHome.pageState)

    return (
        <Surface className="p-4 md:p-5">
            <SectionHeader
                eyebrow="事件流"
                title="主时间线"
                description="按天分组，优先展示交易、复盘、AI 证据和异常。"
            />

            {timelineHome.timeline.groups.length === 0 ? (
                <div className="mt-5">
                    <EmptyStatePanel title={emptyState.title} detail={emptyState.detail} />
                </div>
            ) : (
                <div className="mt-5 space-y-6">
                    {timelineHome.timeline.groups.map((group) => (
                        <div key={group.group_key} className="space-y-3">
                            <div className="flex items-center gap-3">
                                <span className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-faint">
                                    {group.group_label}
                                </span>
                                <div className="h-px flex-1 bg-line" />
                            </div>
                            {group.items.map((event) => (
                                <TimelineEventCardV2 key={event.event_public_id} event={event} />
                            ))}
                        </div>
                    ))}
                </div>
            )}
        </Surface>
    )
}
