import Link from 'next/link'
import PortfolioSankey from '@/components/PortfolioSankey'
import { MaeMfeScatterPlot } from '@/components/dashboard/MaeMfeScatterPlot'
import PositionCard from '@/components/dashboard/PositionCard'
import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import type { PositionViewModel } from '@/lib/adapters/trading'
import type { DashboardStats } from '@/lib/api'

interface DashboardEvidenceStackProps {
    stats: DashboardStats
    openPositions: PositionViewModel[]
    allPositions: PositionViewModel[]
    isMobileSankey: boolean
}

export function DashboardEvidenceStack({ stats, openPositions, allPositions, isMobileSankey }: DashboardEvidenceStackProps) {
    return (
        <div className="space-y-6">
            {stats.portfolio_flow && stats.portfolio_flow.nodes.length > 0 && (
                <PortfolioSankey data={stats.portfolio_flow} totalAssets={stats.total_assets} isMobile={isMobileSankey} />
            )}
            {allPositions.length > 0 && (
                <Surface className="p-1">
                    <MaeMfeScatterPlot positions={allPositions} />
                </Surface>
            )}
            <Surface className="p-4">
                <SectionHeader
                    eyebrow="未平仓交易"
                    title="持仓中"
                    description="这里只保留宏观预览，逐笔故事继续进入交易详情。"
                    action={openPositions.length > 6 ? (
                        <Link href="/positions" className="text-xs font-semibold text-ink transition-colors hover:text-ink-soft">
                            查看更多
                        </Link>
                    ) : null}
                />
                {openPositions.length === 0 ? (
                    <div className="mt-4">
                        <EmptyStatePanel title="暂无持仓" detail="当前没有打开的交易，看板会优先展示历史结构和风险摘要。" />
                    </div>
                ) : (
                    <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                        {openPositions.slice(0, 6).map((position) => (
                            <PositionCard key={position.id} position={position} />
                        ))}
                    </div>
                )}
            </Surface>
        </div>
    )
}
