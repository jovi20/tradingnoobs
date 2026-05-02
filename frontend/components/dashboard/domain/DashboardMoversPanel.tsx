import PerformanceMovers from '@/components/dashboard/PerformanceMovers'
import type { PositionMover } from '@/lib/api'

interface DashboardMoversPanelProps {
    top: PositionMover[]
    bottom: PositionMover[]
}

export function DashboardMoversPanel({ top, bottom }: DashboardMoversPanelProps) {
    return (
        <div className="card p-4">
            <h2 className="text-sm font-semibold mb-4 text-slate-900 dark:text-white">历史表现</h2>
            <PerformanceMovers top={top} bottom={bottom} />
        </div>
    )
}
