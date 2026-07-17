import { useQuery } from '@tanstack/react-query'

import { timelineAPI } from '@/lib/api'
import { adaptTimelineHome, TimelineHomeViewModel } from '@/lib/adapters/timeline'
import type { JournalTimelineView } from '@/lib/read-models'

export function useTimelineHomeData(token: string | null, view: JournalTimelineView = 'ALL') {
    const timelineQuery = useQuery({
        queryKey: ['timeline', 'home', token, view],
        queryFn: async (): Promise<TimelineHomeViewModel> => {
            if (!token) throw new Error('No token')
            const response = await timelineAPI.home(token, { view })
            return adaptTimelineHome(response)
        },
        enabled: !!token,
        placeholderData: (previousData) => previousData,
    })

    return {
        timelineHome: timelineQuery.data,
        isLoading: timelineQuery.isLoading,
        error: timelineQuery.error ? (timelineQuery.error as Error).message : null,
        refresh: timelineQuery.refetch,
    }
}
