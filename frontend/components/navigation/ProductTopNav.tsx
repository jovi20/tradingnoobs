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

interface ProductTopNavProps {
    items: NavigationItem[]
    pathname: string
}

export function ProductTopNav({ items, pathname }: ProductTopNavProps) {
    return (
        <div className="hidden items-center gap-1 md:flex">
            {items.map((item) => {
                const Icon = iconMap[item.icon]
                const isActive = isNavigationItemActive(item.href, pathname)
                const isOps = item.section === 'ops'
                return (
                    <Link
                        key={item.href}
                        href={item.href}
                        className={`inline-flex items-center gap-2 rounded-full px-3.5 py-2 text-sm font-medium transition ${
                            isActive
                                ? 'bg-slate-950 text-white shadow-sm dark:bg-white dark:text-slate-950'
                                : isOps
                                    ? 'border border-amber-200 bg-amber-50 text-amber-800 hover:bg-amber-100 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-200'
                                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-950 dark:text-slate-400 dark:hover:bg-slate-800 dark:hover:text-slate-100'
                        }`}
                    >
                        <Icon className="h-4 w-4" />
                        <span>{item.label}</span>
                    </Link>
                )
            })}
        </div>
    )
}
