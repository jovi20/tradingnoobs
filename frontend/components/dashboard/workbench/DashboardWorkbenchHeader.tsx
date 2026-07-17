'use client'

import Link from 'next/link'
import { BarChart3, Calendar, List, Plus } from 'lucide-react'
import { SectionHeader } from '@/components/ui/SectionHeader'

const quickLinks = [
    { href: '/positions/new', label: '新增交易', icon: Plus },
    { href: '/positions', label: '交易记录', icon: List },
    { href: '/strategies', label: '策略', icon: BarChart3 },
    { href: '/daily', label: '日历', icon: Calendar },
]

export function DashboardWorkbenchHeader() {
    return (
        <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-start">
            <SectionHeader
                eyebrow="交易日志"
                title="日志概览"
                description="已实现结果、账户日志余额和未平仓交易记录。"
            />
            <div className="flex max-w-full gap-2 overflow-x-auto pb-1">
                {quickLinks.map((item) => {
                    const Icon = item.icon
                    return (
                        <Link
                            key={item.href}
                            href={item.href}
                            className="inline-flex shrink-0 items-center gap-2 rounded-md border border-line bg-panel px-3 py-2 text-xs font-semibold text-ink-soft transition-colors hover:border-line-strong hover:bg-panel-subtle"
                        >
                            <Icon className="h-3.5 w-3.5" />
                            {item.label}
                        </Link>
                    )
                })}
            </div>
        </div>
    )
}
