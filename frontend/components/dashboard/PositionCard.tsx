import Link from 'next/link'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { useTrendColor } from '@/hooks/useTrendColor'
import { PositionViewModel } from '@/lib/adapters/trading'
import { getCurrencySymbol } from '@/lib/symbolUtils'

interface PositionCardProps {
    position: PositionViewModel
}

export default function PositionCard({ position }: PositionCardProps) {
    const trendColor = useTrendColor()
    const pnl = position.status === 'OPEN' ? (Number(position.unrealized_pnl) || 0) : (Number(position.realized_pnl) || 0)
    const isPositive = pnl >= 0
    const cs = getCurrencySymbol(position.asset_metadata?.currency)

    return (
        <Link href={`/positions/${position.routeId}`}>
            <div className="rounded-lg border border-transparent bg-panel p-2 shadow-panel dark:shadow-none transition-colors cursor-pointer hover:border-line">
                <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2">
                        <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${isPositive ? trendColor.upBg : trendColor.downBg}`}>
                            {isPositive ? (
                                <TrendingUp className={`w-4 h-4 ${trendColor.upColor}`} />
                            ) : (
                                <TrendingDown className={`w-4 h-4 ${trendColor.downColor}`} />
                            )}
                        </div>
                        <div className="min-w-0">
                            <h3 className="font-semibold text-sm truncate">{position.symbol}</h3>
                            <p className="text-[10px] text-ink-muted truncate">{position.exchange}</p>
                        </div>
                    </div>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${position.direction === 'LONG' ? 'bg-profit/10 text-profit' : 'bg-loss/10 text-loss'}`}>
                        {position.direction === 'LONG' ? '做多' : '做空'}
                    </span>
                </div>

                <div className="grid grid-cols-2 gap-y-1 gap-x-2 text-xs">
                    <div>
                        <p className="text-ink-muted">均价</p>
                        <p className="font-medium tn-nums">{cs}{Number(position.average_entry_price || 0).toFixed(2)}</p>
                    </div>
                    <div>
                        <p className="text-ink-muted">现价</p>
                        <p className="font-medium tn-nums">{position.current_price ? `${cs}${Number(position.current_price).toFixed(2)}` : '-'}</p>
                    </div>
                    <div>
                        <p className="text-ink-muted">数量</p>
                        <p className="font-medium tn-nums">{Number(position.total_quantity).toLocaleString()}</p>
                    </div>
                    <div>
                        <p className="text-ink-muted">盈亏</p>
                        <p className={`font-bold tn-nums ${isPositive ? trendColor.upColor : trendColor.downColor}`}>
                            {isPositive ? '+' : ''}{cs}{pnl.toFixed(2)}
                        </p>
                    </div>
                </div>
            </div>
        </Link>
    )
}
