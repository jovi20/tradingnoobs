'use client'

import { ThemeProvider } from '@/components/ThemeProvider'
import { AuthProvider } from '@/contexts/AuthContext'
import { TooltipProvider } from '@/components/ui/Tooltip'

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { useState } from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
    const [queryClient] = useState(() => new QueryClient({
        defaultOptions: {
            queries: {
                staleTime: 15 * 1000, // 15 seconds
                refetchOnWindowFocus: false, // Optional: prevent refetch on window focus if desired
            },
        },
    }))

    return (
        <QueryClientProvider client={queryClient}>
            <AuthProvider>
                <ThemeProvider>
                    <TooltipProvider delayDuration={200} skipDelayDuration={300}>
                        {children}
                    </TooltipProvider>
                </ThemeProvider>
            </AuthProvider>
        </QueryClientProvider>
    )
}
