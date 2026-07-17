'use client'

import Link from 'next/link'
import {
    Briefcase, Calendar, Clock3, FileText, LayoutDashboard, Layers, Settings,
} from 'lucide-react'

import { cn } from '@/lib/cn'
import { isNavigationItemActive, type NavigationItem } from '@/lib/navigation'

const iconMap = {
    timeline: Clock3,
    dashboard: LayoutDashboard,
    positions: Briefcase,
    strategies: Layers,
    daily: Calendar,
    insights: FileText,
    settings: Settings,
    adminJobs: Settings,
    adminOps: Settings,
} as const

interface MobileBottomNavProps {
    items: NavigationItem[]
    pathname: string
}

export function MobileBottomNav({ items, pathname }: MobileBottomNavProps) {
    // Admin ops surfaces are desktop-first; keep the mobile bar to the product + settings.
    const visible = items.filter((item) => item.section !== 'ops')

    return (
        <nav className="fixed inset-x-0 bottom-0 z-40 border-t border-line bg-canvas/92 pb-safe backdrop-blur-md md:hidden">
            <div
                className="grid gap-0.5 px-1 py-1.5"
                style={{ gridTemplateColumns: `repeat(${Math.max(visible.length, 1)}, minmax(0, 1fr))` }}
            >
                {visible.map((item) => {
                    const Icon = iconMap[item.icon]
                    const active = isNavigationItemActive(item.href, pathname)
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={cn(
                                'flex min-w-0 flex-col items-center gap-1 rounded-md px-1 py-1.5 text-[11px] font-medium transition-colors',
                                active ? 'text-ink' : 'text-ink-faint',
                            )}
                        >
                            <span className={cn(
                                'flex h-8 w-full items-center justify-center rounded-md transition-colors',
                                active && 'bg-panel-subtle',
                            )}>
                                <Icon className="h-[18px] w-[18px]" />
                            </span>
                            <span>{item.label}</span>
                        </Link>
                    )
                })}
            </div>
        </nav>
    )
}
