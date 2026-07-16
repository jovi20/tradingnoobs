export type ReleaseProfile = 'JOURNAL_BASELINE' | 'DEVELOPMENT_FULL'

export {
    AI_INSIGHTS_RUNTIME_ENABLED,
    BROKER_SYNC_RUNTIME_ENABLED,
    MARKET_RUNTIME_ENABLED,
    OPEN_REGISTRATION_RUNTIME_ENABLED,
    PDF_EXPORT_RUNTIME_ENABLED,
    RELEASE_BASE_CURRENCY,
    RELEASE_CONTRACT_ID,
    RELEASE_POSITION_MODE,
    RISK_CARDS_RUNTIME_ENABLED,
} from './generated/release-contract.ts'

export function resolveReleaseProfile(value: string | null | undefined): ReleaseProfile {
    return value?.trim().toUpperCase() === 'DEVELOPMENT_FULL'
        ? 'DEVELOPMENT_FULL'
        : 'JOURNAL_BASELINE'
}

// The journal client is built against the frozen Beta ceiling. Optional UI is
// absent from this artifact; runtime flags can only narrow a deployment build.
export const RELEASE_PROFILE: ReleaseProfile = 'JOURNAL_BASELINE'
