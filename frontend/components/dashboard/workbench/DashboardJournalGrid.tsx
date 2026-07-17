import { EmptyStatePanel } from '@/components/ui/EmptyStatePanel'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { Surface } from '@/components/ui/Surface'
import type { DashboardJournalSummary } from '@/lib/adapters/dashboard'

interface AccountRow {
    name: string
    broker: string
    balanceLabel: string
}

interface DashboardJournalGridProps {
    accountRows: AccountRow[]
    summary: DashboardJournalSummary
}

const journalCountRows: Array<{
    label: string
    key: 'totalTrades' | 'closedTrades' | 'openPositions'
}> = [
    { label: '全部交易', key: 'totalTrades' },
    { label: '已平仓', key: 'closedTrades' },
    { label: '未平仓', key: 'openPositions' },
]

export function DashboardJournalGrid({ accountRows, summary }: DashboardJournalGridProps) {
    return (
        <div className="grid gap-6 xl:grid-cols-[1.25fr_0.75fr]">
            <Surface className="p-4">
                <SectionHeader
                    eyebrow="账户账本"
                    title="各账户日志余额"
                    description="按账户初始余额与已记录账本流水汇总，不包含持仓估值。"
                />
                {accountRows.length === 0 ? (
                    <div className="mt-4">
                        <EmptyStatePanel title="暂无账户日志余额" detail="创建账户并记录初始余额或资金流水后，这里会按账户汇总。" />
                    </div>
                ) : (
                    <div className="mt-4 divide-y divide-line">
                        {accountRows.map((account) => (
                            <div key={`${account.name}-${account.broker}`} className="flex items-center justify-between gap-4 py-3 text-sm">
                                <div className="min-w-0">
                                    <p className="truncate font-semibold text-ink">{account.name}</p>
                                    <p className="text-xs text-ink-faint">{account.broker}</p>
                                </div>
                                <div className="shrink-0 text-right">
                                    <p className="font-semibold text-ink tn-nums">{account.balanceLabel}</p>
                                    <p className="text-xs text-ink-faint">日志余额</p>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </Surface>
            <Surface className="p-4">
                <SectionHeader
                    eyebrow="日志完整度"
                    title="交易记录统计"
                    description="按交易日志当前状态计数。"
                />
                <div className="mt-4 divide-y divide-line">
                    {journalCountRows.map((row) => (
                        <div key={row.key} className="flex items-center justify-between py-3 text-sm">
                            <span className="text-ink-muted">{row.label}</span>
                            <span className="font-semibold text-ink tn-nums">{summary[row.key]}</span>
                        </div>
                    ))}
                </div>
            </Surface>
        </div>
    )
}
