'use client'

import Link from 'next/link'
import {
    Briefcase,
    Calendar,
    Clock3,
    FileText,
    LayoutDashboard,
    Layers,
    Settings,
    ShieldCheck,
} from 'lucide-react'

import { isNavigationItemActive, type NavigationItem } from '@/lib/navigation'

const iconMap = {
    timeline: Clock3,
    dashboard: LayoutDashboard,
    positions: Briefcase,
    strategies: Layers,
    daily: Calendar,
    insights: FileText,
    settings: Settings,
    adminJobs: ShieldCheck,
}

interface MobileBottomNavProps {
    items: NavigationItem[]
    pathname: string
}

export function MobileBottomNav({ items, pathname }: MobileBottomNavProps) {
    return (
        <div className="fixed bottom-0 left-0 right-0 z-50 border-t border-slate-200 bg-white/95 pb-safe backdrop-blur-xl dark:border-slate-800 dark:bg-slate-950/95 md:hidden">
            <div className="flex gap-1 overflow-x-auto px-2 py-2">
                {items.map((item) => {
                    const Icon = iconMap[item.icon]
                    const isActive = isNavigationItemActive(item.href, pathname)
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className={`flex min-w-[4.65rem] flex-col items-center rounded-2xl px-2 py-2 text-[11px] font-medium transition ${
                                isActive
                                    ? 'bg-slate-950 text-white dark:bg-white dark:text-slate-950'
                                    : item.section === 'ops'
                                        ? 'text-amber-700 dark:text-amber-300'
                                        : 'text-slate-500 dark:text-slate-400'
                            }`}
                        >
                            <Icon className="h-5 w-5" />
                            <span className="mt-1">{item.label}</span>
                        </Link>
                    )
                })}
            </div>
        </div>
    )
}
