'use client'

import { createContext, useContext, useMemo } from 'react'

import {
    DISABLED_EFFECTIVE_CAPABILITIES,
    normalizeEffectiveCapabilities,
    type EffectiveCapabilities,
    type EffectiveCapabilityInput,
} from '@/lib/effective-capabilities'

const EffectiveCapabilitiesContext = createContext<EffectiveCapabilities>(DISABLED_EFFECTIVE_CAPABILITIES)

export function EffectiveCapabilitiesProvider({
    children,
    effectiveCapabilities,
}: {
    children: React.ReactNode
    effectiveCapabilities?: EffectiveCapabilityInput
}) {
    const value = useMemo(
        () => normalizeEffectiveCapabilities(effectiveCapabilities),
        [effectiveCapabilities],
    )

    return (
        <EffectiveCapabilitiesContext.Provider value={value}>
            {children}
        </EffectiveCapabilitiesContext.Provider>
    )
}

export function useEffectiveCapabilities(): EffectiveCapabilities {
    return useContext(EffectiveCapabilitiesContext)
}
