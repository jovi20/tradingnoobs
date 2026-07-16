import { OPTIONAL_CAPABILITY_IDS } from './generated/release-contract.ts'

export const EFFECTIVE_CAPABILITY_IDS = OPTIONAL_CAPABILITY_IDS

export type EffectiveCapabilityId = (typeof EFFECTIVE_CAPABILITY_IDS)[number]
export type EffectiveCapabilities = Readonly<Record<EffectiveCapabilityId, boolean>>
export type EffectiveCapabilityInput = Partial<Record<EffectiveCapabilityId, unknown>> | null | undefined

export const DISABLED_EFFECTIVE_CAPABILITIES = Object.freeze(Object.fromEntries(
    EFFECTIVE_CAPABILITY_IDS.map((capability) => [capability, false]),
)) as EffectiveCapabilities

export function normalizeEffectiveCapabilities(input: EffectiveCapabilityInput): EffectiveCapabilities {
    if (!input || typeof input !== 'object' || Array.isArray(input)) {
        return DISABLED_EFFECTIVE_CAPABILITIES
    }

    return Object.freeze(Object.fromEntries(
        EFFECTIVE_CAPABILITY_IDS.map((capability) => [
            capability,
            Object.prototype.hasOwnProperty.call(input, capability) && input[capability] === true,
        ]),
    )) as EffectiveCapabilities
}

export function isEffectiveCapabilityEnabled(
    capabilities: EffectiveCapabilities,
    capability: EffectiveCapabilityId,
): boolean {
    return capabilities[capability] === true
}
