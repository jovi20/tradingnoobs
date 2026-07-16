'use client'

import { useCallback, useEffect, useState } from 'react'
import { usePathname } from 'next/navigation'

import { useAuth } from '@/contexts/AuthContext'
import { useEffectiveCapabilities } from '@/contexts/EffectiveCapabilitiesContext'
import { getVisibleNavigationItems } from '@/lib/navigation'
import { AppSidebar } from '@/components/navigation/AppSidebar'
import { AppTopBar } from '@/components/navigation/AppTopBar'
import { MobileBottomNav } from '@/components/navigation/MobileBottomNav'
import { CommandPalette } from '@/components/navigation/CommandPalette'

/**
 * Product shell — stable left sidebar (desktop), top bar, mobile bottom nav,
 * and the global ⌘K command palette. Wraps all authenticated product pages.
 */
export function ProductShell({ children }: { children: React.ReactNode }) {
    const pathname = usePathname()
    const { isAuthenticated, user } = useAuth()
    const effectiveCapabilities = useEffectiveCapabilities()
    const [commandOpen, setCommandOpen] = useState(false)

    const openCommand = useCallback(() => setCommandOpen(true), [])

    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'k') {
                e.preventDefault()
                setCommandOpen((v) => !v)
            } else if (e.key === 'Escape') {
                setCommandOpen(false)
            }
        }
        window.addEventListener('keydown', onKey)
        return () => window.removeEventListener('keydown', onKey)
    }, [])

    const items = getVisibleNavigationItems(user?.role, effectiveCapabilities)

    // Unauthenticated users are redirected by AuthContext; render bare to avoid flashing the shell.
    if (!isAuthenticated) {
        return <>{children}</>
    }

    return (
        <div className="min-h-screen bg-canvas">
            <AppSidebar items={items} pathname={pathname} onOpenCommand={openCommand} />
            <div className="md:pl-60">
                <AppTopBar onOpenCommand={openCommand} />
                <main className="mx-auto w-full max-w-7xl px-4 pb-24 pt-6 md:px-6 md:pb-10">
                    {children}
                </main>
            </div>
            <MobileBottomNav items={items} pathname={pathname} />
            <CommandPalette open={commandOpen} onOpenChange={setCommandOpen} />
        </div>
    )
}
