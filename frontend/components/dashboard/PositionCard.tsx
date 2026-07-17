import Link from 'next/link'
import { BookOpen } from 'lucide-react'
import type { PositionViewModel } from '@/lib/adapters/trading'
import { getCurrencySymbol } from '@/lib/symbolUtils'

interface PositionCardProps {
    position: PositionViewModel
}

function formatEntryPrice(position: PositionViewModel) {
    if (position.average_entry_price === undefined || position.average_entry_price === null) return '-'
    const currencySymbol = getCurrencySymbol(position.asset_metadata?.currency)
    return `${currencySymbol}${Number(position.average_entry_price).toFixed(2)}`
}

export default function PositionCard({ position }: PositionCardProps) {
    return (
        <Link
            href={`/positions/${position.routeId}`}
            className="block rounded-lg border border-line bg-panel p-3 shadow-panel transition-colors hover:border-line-strong dark:shadow-none"
        >
            <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex min-w-0 items-center gap-2">
                    <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-panel-subtle text-ink-muted">
                        <BookOpen className="h-4 w-4" />
                    </div>
                    <div className="min-w-0">
                        <h3 className="truncate text-sm font-semibold text-ink">{position.symbol}</h3>
                        <p className="truncate text-[10px] text-ink-muted">{position.exchange}</p>
                    </div>
                </div>
                <span className={`shrink-0 rounded px-1.5 py-0.5 text-[10px] font-medium ${position.direction === 'LONG' ? 'bg-profit/10 text-profit' : 'bg-loss/10 text-loss'}`}>
                    {position.direction === 'LONG' ? '做多' : '做空'}
                </span>
            </div>
            <div className="grid grid-cols-2 gap-x-3 text-xs">
                <div>
                    <p className="text-ink-muted">建仓均价</p>
                    <p className="mt-1 font-medium text-ink tn-nums">{formatEntryPrice(position)}</p>
                </div>
                <div>
                    <p className="text-ink-muted">当前数量</p>
                    <p className="mt-1 font-medium text-ink tn-nums">{Number(position.total_quantity).toLocaleString()}</p>
                </div>
            </div>
        </Link>
    )
}
