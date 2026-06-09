'use client'

import { useState } from 'react'
import { Loader2 } from 'lucide-react'

import { useAuth } from '@/contexts/AuthContext'
import { useInsightRuns } from '@/hooks/useInsightRuns'
import { useTimelineHomeData } from '@/hooks/useTimelineHomeData'
import type { TimelineView } from '@/lib/read-models'
import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { TimelineWorkbench } from '@/components/timeline/workbench/TimelineWorkbench'

export default function TimelinePage() {
    const { token } = useAuth()
    const [view, setView] = useState<TimelineView>('ALL')
    const { timelineHome, isLoading, error, refresh } = useTimelineHomeData(token, view)
    const insightRunsQuery = useInsightRuns(token)

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-slate-500" />
            </div>
        )
    }

    if (error) {
        return (
            <EmptyStatePanel
                title="时间线暂时无法加载。"
                detail={error}
                action={<button type="button" onClick={() => refresh()} className="btn btn-secondary">重试</button>}
            />
        )
    }

    if (!timelineHome) {
        return (
            <EmptyStatePanel
                title="暂时没有可展示的时间线数据。"
                detail="先记录交易或检查同步设置，时间线会在有事件后形成。"
            />
        )
    }

    return (
        <TimelineWorkbench
            timelineHome={timelineHome}
            view={view}
            onChangeView={setView}
            onRefresh={refresh}
            insightRuns={insightRunsQuery.data}
            insightRunsLoading={insightRunsQuery.isLoading}
            insightRunsError={insightRunsQuery.error ? insightRunsQuery.error.message : null}
            onRefreshInsights={() => insightRunsQuery.refetch()}
        />
    )
}
