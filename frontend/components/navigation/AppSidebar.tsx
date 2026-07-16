'use client'

import Link from 'next/link'
import Image from 'next/image'
import {
    Briefcase, Calendar, Clock3, FileText, Gauge, LayoutDashboard, Layers, ListChecks, Settings, Search,
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
    adminJobs: ListChecks,
    adminOps: Gauge,
} as const

interface AppSidebarProps {
    items: NavigationItem[]
    pathname: string
    onOpenCommand: () => void
}

export function AppSidebar({ items, pathname, onOpenCommand }: AppSidebarProps) {
    const productItems = items.filter((i) => i.section === 'product')
    const opsItems = items.filter((i) => i.section === 'ops')
    const settingsItems = items.filter((i) => i.section === 'settings')

    return (
        <aside className="fixed inset-y-0 left-0 z-40 hidden w-60 flex-col border-r border-line bg-panel md:flex">
            {/* Brand */}
            <div className="flex h-16 items-center gap-2.5 px-5">
                <span className="relative flex h-8 w-8 items-center justify-center overflow-hidden rounded-md bg-ink p-1.5">
                    <Image src="/logo.png" alt="Trading Noobs" width={24} height={24} className="h-full w-full object-contain" priority />
                </span>
                <span className="flex flex-col leading-tight">
                    <span className="text-sm font-semibold tracking-tight text-ink">Trading Noobs</span>
                    <span className="text-[10px] font-medium text-ink-faint">决策复盘工作台</span>
                </span>
            </div>

            {/* Command trigger */}
            <div className="px-3 pb-2">
                <button
                    onClick={onOpenCommand}
                    className="flex w-full items-center gap-2 rounded-md border border-line bg-panel-subtle px-3 py-2 text-sm text-ink-faint transition-colors hover:border-line-strong hover:text-ink-muted"
                >
                    <Search className="h-4 w-4" />
                    <span className="flex-1 text-left">快速跳转…</span>
                    <kbd className="rounded border border-line bg-panel px-1.5 py-0.5 text-[10px] font-medium">⌘K</kbd>
                </button>
            </div>

            {/* Product nav */}
            <nav className="flex-1 space-y-0.5 overflow-y-auto px-3 py-2">
                {productItems.map((item) => (
                    <SidebarLink key={item.href} item={item} pathname={pathname} />
                ))}
                {opsItems.length > 0 && (
                    <div className="mt-4 border-t border-line pt-3">
                        <p className="mb-1 px-3 text-[10px] font-semibold text-ink-faint">管理</p>
                        {opsItems.map((item) => (
                            <SidebarLink key={item.href} item={item} pathname={pathname} />
                        ))}
                    </div>
                )}
            </nav>

            {/* Settings pinned bottom */}
            <div className="space-y-0.5 border-t border-line px-3 py-3">
                {settingsItems.map((item) => (
                    <SidebarLink key={item.href} item={item} pathname={pathname} />
                ))}
            </div>
        </aside>
    )
}

function SidebarLink({ item, pathname }: { item: NavigationItem; pathname: string }) {
    const Icon = iconMap[item.icon]
    const active = isNavigationItemActive(item.href, pathname)
    return (
        <Link
            href={item.href}
            className={cn(
                'flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                active ? 'bg-panel-subtle text-ink' : 'text-ink-muted hover:bg-panel-subtle/60 hover:text-ink',
            )}
        >
            <Icon className={cn('h-[18px] w-[18px]', active ? 'text-ink' : 'text-ink-faint')} />
            <span>{item.label}</span>
        </Link>
    )
}
