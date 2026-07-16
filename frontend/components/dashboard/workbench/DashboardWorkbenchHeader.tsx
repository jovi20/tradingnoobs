import Link from 'next/link'
import { BarChart3, Calendar, FileText, TrendingUp } from 'lucide-react'
import MarketStatus from '@/components/MarketStatus'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { StatusPill } from '@/components/ui/StatusPill'
import type { DashboardRiskPosture } from '@/lib/adapters/dashboard'

const quickLinks = [
    { href: '/positions/new', label: '新增交易', icon: TrendingUp },
    { href: '/strategies', label: '策略', icon: BarChart3 },
    { href: '/daily', label: '日历', icon: Calendar },
    { href: '/insights', label: '洞察', icon: FileText },
]

interface DashboardWorkbenchHeaderProps {
    riskPosture: DashboardRiskPosture
}

export function DashboardWorkbenchHeader({ riskPosture }: DashboardWorkbenchHeaderProps) {
    return (
        <div className="grid gap-4 lg:grid-cols-[1fr_auto] lg:items-start">
            <SectionHeader
                eyebrow="组合概览"
                title="整体状态怎么样"
                description="看板汇总组合健康度、资产结构、风险和数据新鲜度；最近事件继续在时间线中处理。"
                action={<StatusPill tone={riskPosture.tone}>{riskPosture.label}</StatusPill>}
            />
            <div className="flex flex-col gap-3 lg:items-end">
                <div className="flex max-w-full gap-2 overflow-x-auto pb-1">
                    {quickLinks.map((item) => {
                        const Icon = item.icon
                        return (
                            <Link
                                key={item.href}
                                href={item.href}
                                className="inline-flex shrink-0 items-center gap-2 rounded-full border border-line bg-panel px-3 py-2 text-xs font-semibold text-ink-soft transition-colors hover:border-line-strong hover:bg-panel-subtle"
                            >
                                <Icon className="h-3.5 w-3.5" />
                                {item.label}
                            </Link>
                        )
                    })}
                </div>
                <MarketStatus />
            </div>
        </div>
    )
}
