import Link from 'next/link'
import PositionCard from '@/components/dashboard/PositionCard'
import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import type { PositionViewModel } from '@/lib/adapters/trading'

interface DashboardEvidenceStackProps {
    openPositions: PositionViewModel[]
}

export function DashboardEvidenceStack({ openPositions }: DashboardEvidenceStackProps) {
    return (
        <Surface className="p-4">
            <SectionHeader
                eyebrow="未平仓交易"
                title="持仓日志"
                description="保留建仓均价、数量和方向，逐笔事件与复盘内容在交易详情中查看。"
                action={openPositions.length > 6 ? (
                    <Link href="/positions" className="text-xs font-semibold text-ink transition-colors hover:text-ink-soft">
                        查看更多
                    </Link>
                ) : null}
            />
            {openPositions.length === 0 ? (
                <div className="mt-4">
                    <EmptyStatePanel title="暂无未平仓交易" detail="当前日志中没有未平仓记录。" />
                </div>
            ) : (
                <div className="mt-4 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-3">
                    {openPositions.slice(0, 6).map((position) => (
                        <PositionCard key={position.id} position={position} />
                    ))}
                </div>
            )}
        </Surface>
    )
}
