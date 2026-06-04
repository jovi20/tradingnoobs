'use client'

import { TimelineHome } from '@/components/home/TimelineHome'
import { useAuth } from '@/contexts/AuthContext'
import { useHomeReadModel } from '@/hooks/useHomeReadModel'
import { useInsightRuns } from '@/hooks/useInsightRuns'

export default function HomePage() {
    const { token } = useAuth()
    const homeQuery = useHomeReadModel(token)
    const insightRunsQuery = useInsightRuns(token)

    return (
        <TimelineHome
            home={homeQuery.data}
            isLoading={homeQuery.isLoading}
            error={homeQuery.error ? homeQuery.error.message : null}
            insightRuns={insightRunsQuery.data}
            isInsightLoading={insightRunsQuery.isLoading}
            insightError={insightRunsQuery.error ? insightRunsQuery.error.message : null}
            onRefresh={() => homeQuery.refetch()}
            onInsightRefresh={() => insightRunsQuery.refetch()}
        />
    )
}
