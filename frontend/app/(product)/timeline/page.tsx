'use client'

import { useState } from 'react'

import { useAuth } from '@/contexts/AuthContext'
import { useTimelineHomeData } from '@/hooks/useTimelineHomeData'
import type { JournalTimelineView } from '@/lib/read-models'
import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { LoadingState } from '@/components/ui/Spinner'
import { Button } from '@/components/ui/Button'
import { TimelineWorkbench } from '@/components/timeline/workbench/TimelineWorkbench'
import { TimelineZeroState } from '@/components/timeline/TimelineZeroState'

export default function TimelinePage() {
    const { token } = useAuth()
    const [view, setView] = useState<JournalTimelineView>('ALL')
    const { timelineHome, isLoading, error, refresh } = useTimelineHomeData(token, view)

    if (isLoading) {
        return <LoadingState label="正在加载时间线…" />
    }

    if (error) {
        return (
            <EmptyStatePanel
                title="时间线暂时无法加载。"
                detail={error}
                action={<Button variant="secondary" onClick={() => refresh()}>重试</Button>}
            />
        )
    }

    if (!timelineHome) {
        return (
            <EmptyStatePanel
                title="暂时没有可展示的时间线数据。"
                detail="记录交易后，相关生命周期事件会在这里形成时间线。"
            />
        )
    }

    // Zero-data home: guided onboarding + experience preview instead of an empty workbench.
    if (timelineHome.pageState === 'ZERO') {
        return <TimelineZeroState />
    }

    return (
        <TimelineWorkbench
            timelineHome={timelineHome}
            view={view}
            onChangeView={setView}
            onRefresh={refresh}
        />
    )
}
