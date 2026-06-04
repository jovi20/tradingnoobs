import {
    buildMockHomeReadModel,
    homeReadModelPath,
    trustToneForFreshness,
    type HomeReadModel,
    type TrustTone,
} from '@/lib/readModels'
import { TimelineEventCard } from '@/components/read-models/TimelineEventCard'
import { ReviewInboxPanel } from '@/components/read-models/ReviewInboxPanel'
import { TrustMetaBadge } from '@/components/trust/TrustMetaBadge'

const home: HomeReadModel = buildMockHomeReadModel({
    nowIso: '2026-06-04T09:30:00.000Z',
})

const homePath: '/api/v1/read-models/home' = homeReadModelPath
const tone: TrustTone = trustToneForFreshness(home.meta.freshness)

export const task4ReadModelContract = (
    <section data-home-path={homePath} data-tone={tone}>
        <TrustMetaBadge meta={home.meta} />
        <ReviewInboxPanel items={home.review_inbox} />
        <TimelineEventCard event={home.timeline_events[0]} />
    </section>
)
