import { TrendingUp, TrendingDown } from 'lucide-react'
import { useTrendColor } from '@/hooks/useTrendColor'

interface StatCardProps {
    title: string
    value: string
    icon: React.ElementType
    trend?: 'up' | 'down'
    color: string
}

export default function StatCard({
    title,
    value,
    icon: Icon,
    trend,
    color
}: StatCardProps) {
    const trendColor = useTrendColor()

    const getBgClass = (colorClass: string) => {
        if (colorClass.includes('emerald')) return 'bg-emerald-100 dark:bg-emerald-900/30'
        if (colorClass.includes('red')) return 'bg-red-100 dark:bg-red-900/30'
        if (colorClass.includes('blue')) return 'bg-blue-100 dark:bg-blue-900/30'
        if (colorClass.includes('purple')) return 'bg-purple-100 dark:bg-purple-900/30'
        if (colorClass.includes('amber')) return 'bg-amber-100 dark:bg-amber-900/30'
        return 'bg-slate-100 dark:bg-slate-700'
    }

    return (
        <div className="card p-3 md:p-6">
            <div className="flex items-start justify-between">
                <div className="min-w-0 flex-1">
                    <p className="text-xs md:text-sm text-slate-500 dark:text-slate-400">{title}</p>
                    <p className={`text-lg md:text-2xl font-bold mt-1 truncate ${color}`} title={value}>{value}</p>
                </div>
                <div className={`p-2 md:p-3 rounded-xl ml-2 shrink-0 ${getBgClass(color)}`}>
                    <Icon className={`w-5 h-5 md:w-6 md:h-6 ${color}`} />
                </div>
            </div>
            {trend && (
                <div className="flex items-center mt-2 text-sm">
                    {trend === 'up' ? (
                        <TrendingUp className={`w-4 h-4 mr-1 ${trendColor.upColor}`} />
                    ) : (
                        <TrendingDown className={`w-4 h-4 mr-1 ${trendColor.downColor}`} />
                    )}
                    <span className={trend === 'up' ? trendColor.upColor : trendColor.downColor}>
                        vs last week
                    </span>
                </div>
            )}
        </div>
    )
}
