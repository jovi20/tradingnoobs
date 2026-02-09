import Link from 'next/link'
import { TrendingUp, TrendingDown } from 'lucide-react'
import { useTrendColor } from '@/hooks/useTrendColor'
import { Position } from '@/lib/api'

interface PositionCardProps {
    position: Position
}

export default function PositionCard({ position }: PositionCardProps) {
    const trendColor = useTrendColor()
    const pnl = position.status === 'OPEN' ? (Number(position.unrealized_pnl) || 0) : (Number(position.realized_pnl) || 0)
    const isPositive = pnl >= 0

    return (
        <Link href={`/positions/${position.id}`}>
            <div className="card p-2 hover:scale-[1.01] transition-transform cursor-pointer border-transparent hover:border-slate-200 dark:hover:border-slate-700">
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
                            <p className="text-[10px] text-slate-500 truncate">{position.exchange}</p>
                        </div>
                    </div>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${position.direction === 'LONG' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'}`}>
                        {position.direction === 'LONG' ? '做多' : '做空'}
                    </span>
                </div>

                <div className="grid grid-cols-2 gap-y-1 gap-x-2 text-xs">
                    <div>
                        <p className="text-slate-500 dark:text-slate-400">均价</p>
                        <p className="font-medium">${Number(position.average_entry_price || 0).toFixed(2)}</p>
                    </div>
                    <div>
                        <p className="text-slate-500 dark:text-slate-400">现价</p>
                        <p className="font-medium">{position.current_price ? `$${Number(position.current_price).toFixed(2)}` : '-'}</p>
                    </div>
                    <div>
                        <p className="text-slate-500 dark:text-slate-400">数量</p>
                        <p className="font-medium">{Number(position.total_quantity).toLocaleString()}</p>
                    </div>
                    <div>
                        <p className="text-slate-500 dark:text-slate-400">盈亏</p>
                        <p className={`font-bold ${isPositive ? trendColor.upColor : trendColor.downColor}`}>
                            {isPositive ? '+' : ''}${pnl.toFixed(2)}
                        </p>
                    </div>
                </div>
            </div>
        </Link>
    )
}
