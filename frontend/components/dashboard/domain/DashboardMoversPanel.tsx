import PerformanceMovers from '@/components/dashboard/PerformanceMovers'
import type { PositionMover } from '@/lib/api'

interface DashboardMoversPanelProps {
    top: PositionMover[]
    bottom: PositionMover[]
}

export function DashboardMoversPanel({ top, bottom }: DashboardMoversPanelProps) {
    return (
        <div className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
            <h2 className="text-sm font-semibold mb-4 text-ink">历史表现</h2>
            <PerformanceMovers top={top} bottom={bottom} />
        </div>
    )
}
