export type ReleaseProfile = 'JOURNAL_BASELINE' | 'DEVELOPMENT_FULL'

export function resolveReleaseProfile(value: string | null | undefined): ReleaseProfile {
    return value?.trim().toUpperCase() === 'DEVELOPMENT_FULL'
        ? 'DEVELOPMENT_FULL'
        : 'JOURNAL_BASELINE'
}

// JRN-000 launch baseline is intentionally a source-level constant. JRN-001
// will replace it with a deployment ceiling plus a separately guarded rollout.
export const RELEASE_PROFILE: ReleaseProfile = 'JOURNAL_BASELINE'
export const MARKET_RUNTIME_ENABLED = false
export const BROKER_SYNC_RUNTIME_ENABLED = false
