'use client'

import { ThemeProvider } from '@/components/ThemeProvider'
import { AuthProvider } from '@/contexts/AuthContext'
import { EffectiveCapabilitiesProvider } from '@/contexts/EffectiveCapabilitiesContext'
import { TooltipProvider } from '@/components/ui/Tooltip'
import type { EffectiveCapabilityInput } from '@/lib/effective-capabilities'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'

export function Providers({
    children,
    effectiveCapabilities,
}: {
    children: React.ReactNode
    effectiveCapabilities?: EffectiveCapabilityInput
}) {
    const [queryClient] = useState(() => new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 15 * 1000, // 15 seconds
                refetchOnWindowFocus: false, // Optional: prevent refetch on window focus if desired
            },
        },
    }))

    return (
        <EffectiveCapabilitiesProvider effectiveCapabilities={effectiveCapabilities}>
            <QueryClientProvider client={queryClient}>
                <AuthProvider>
                    <ThemeProvider>
                        <TooltipProvider delayDuration={200} skipDelayDuration={300}>
                            {children}
                        </TooltipProvider>
                    </ThemeProvider>
                </AuthProvider>
            </QueryClientProvider>
        </EffectiveCapabilitiesProvider>
    )
}
