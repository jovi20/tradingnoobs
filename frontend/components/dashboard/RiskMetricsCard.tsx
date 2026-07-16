
import { AlertTriangle, TrendingUp, ShieldCheck, Activity } from 'lucide-react'

interface RiskMetricsCardProps {
    sharpe?: number
    sortino?: number
    calmar?: number
    maxDrawdown?: number
}

export default function RiskMetricsCard({ sharpe, sortino, calmar, maxDrawdown }: RiskMetricsCardProps) {
    const metrics = [
        {
            label: '夏普比率',
            value: sharpe !== undefined && sharpe !== null ? sharpe.toFixed(2) : '暂无',
            desc: '风险调整后收益',
            icon: Activity,
            color: 'text-ai',
            bg: 'bg-ai/10'
        },
        {
            label: '索提诺比率',
            value: sortino !== undefined && sortino !== null ? sortino.toFixed(2) : '暂无',
            desc: '下行风险调整后收益',
            icon: ShieldCheck,
            color: 'text-profit',
            bg: 'bg-profit/10'
        },
        {
            label: '卡玛比率',
            value: calmar !== undefined && calmar !== null ? calmar.toFixed(2) : '暂无',
            desc: '收益与最大回撤之比',
            icon: TrendingUp,
            color: 'text-ai',
            bg: 'bg-ai/10'
        },
        {
            label: '最大回撤',
            value: maxDrawdown !== undefined && maxDrawdown !== null ? `-${(maxDrawdown * 100).toFixed(2)}%` : '暂无',
            desc: '净值从高点到低点的最大跌幅',
            icon: AlertTriangle,
            color: 'text-warning',
            bg: 'bg-warning/12'
        }
    ]

    return (
        <div className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
            <h3 className="text-sm font-semibold mb-4 text-ink">风险指标</h3>
            <div className="grid grid-cols-2 gap-4">
                {metrics.map((m, idx) => {
                    const Icon = m.icon
                    return (
                        <div key={idx} className="space-y-1">
                            <div className="flex items-center gap-2 text-xs text-ink-muted mb-1">
                                <Icon className="w-3.5 h-3.5" />
                                <span>{m.label}</span>
                            </div>
                            <div className="text-lg font-semibold text-ink tn-nums">
                                {m.value}
                            </div>
                            <div className="text-[10px] text-ink-faint">
                                {m.desc}
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
