import { MetricTile } from '@/components/ui/MetricTile'
import type { DashboardStatusMetric } from '@/lib/adapters/dashboard'

interface DashboardStatusRailProps {
    metrics: DashboardStatusMetric[]
}

export function DashboardStatusRail({ metrics }: DashboardStatusRailProps) {
    return (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {metrics.map((metric) => (
                <MetricTile
                    key={metric.label}
                    label={metric.label}
                    value={metric.value}
                    detail={metric.detail}
                    tone={metric.tone}
                />
            ))}
        </div>
    )
}
