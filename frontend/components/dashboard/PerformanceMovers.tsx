import { TrendingUp, TrendingDown } from 'lucide-react'
import { useTrendColor } from '@/hooks/useTrendColor'
import { PositionMover } from '@/lib/api'
import { getCurrencySymbol } from '@/lib/symbolUtils'

interface PerformanceMoversProps {
    top: PositionMover[]
    bottom: PositionMover[]
}

export default function PerformanceMovers({ top, bottom }: PerformanceMoversProps) {
    const trendColor = useTrendColor()

    const MoverRow = ({ item, type }: { item: PositionMover, type: 'top' | 'bottom' }) => (
        <div className="flex items-center justify-between py-2 border-b last:border-0 border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${type === 'top' ? trendColor.upBg : trendColor.downBg}`}>
                    {type === 'top' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                </div>
                <div>
                    <h4 className="font-medium text-sm">{item.symbol}</h4>
                    <p className="text-xs text-slate-500">{getCurrencySymbol(item.currency)}{item.current_price?.toFixed(2)}</p>
                </div>
            </div>
            <span className={`font-bold text-sm ${type === 'top' ? trendColor.upColor : trendColor.downColor}`}>
                {type === 'top' ? '+' : ''}{item.change_percent?.toFixed(2)}%
            </span>
        </div>
    )

    return (
        <div className="space-y-6">
            <div>
                <h3 className="text-sm font-medium text-slate-500 mb-3 flex items-center gap-1">
                    <TrendingUp className={`w-4 h-4 ${trendColor.upColor}`} /> 表现最佳
                </h3>
                {top.length > 0 ? (
                    <div className="card p-4">
                        {top.map(item => <MoverRow key={item.id} item={item} type="top" />)}
                    </div>
                ) : <div className="text-sm text-slate-400">暂无数据</div>}
            </div>
            <div>
                <h3 className="text-sm font-medium text-slate-500 mb-3 flex items-center gap-1">
                    <TrendingDown className={`w-4 h-4 ${trendColor.downColor}`} /> 表现最差
                </h3>
                {bottom.length > 0 ? (
                    <div className="card p-4">
                        {bottom.map(item => <MoverRow key={item.id} item={item} type="bottom" />)}
                    </div>
                ) : <div className="text-sm text-slate-400">暂无数据</div>}
            </div>
        </div>
    )
}
