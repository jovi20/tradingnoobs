
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
            label: 'Sharpe Ratio',
            value: sharpe !== undefined && sharpe !== null ? sharpe.toFixed(2) : 'N/A',
            desc: 'Risk-adjusted return',
            icon: Activity,
            color: 'text-blue-500',
            bg: 'bg-blue-50 dark:bg-blue-900/20'
        },
        {
            label: 'Sortino Ratio',
            value: sortino !== undefined && sortino !== null ? sortino.toFixed(2) : 'N/A',
            desc: 'Downside risk-adjusted',
            icon: ShieldCheck,
            color: 'text-emerald-500',
            bg: 'bg-emerald-50 dark:bg-emerald-900/20'
        },
        {
            label: 'Calmar Ratio',
            value: calmar !== undefined && calmar !== null ? calmar.toFixed(2) : 'N/A',
            desc: 'Return vs Max Drawdown',
            icon: TrendingUp,
            color: 'text-purple-500',
            bg: 'bg-purple-50 dark:bg-purple-900/20'
        },
        {
            label: 'Max Drawdown',
            value: maxDrawdown !== undefined && maxDrawdown !== null ? `-${(maxDrawdown * 100).toFixed(2)}%` : 'N/A',
            desc: 'Peak to trough decline',
            icon: AlertTriangle,
            color: 'text-amber-500',
            bg: 'bg-amber-50 dark:bg-amber-900/20'
        }
    ]

    return (
        <div className="card p-4 bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700">
            <h3 className="text-sm font-semibold mb-4 text-slate-900 dark:text-white">风险指标</h3>
            <div className="grid grid-cols-2 gap-4">
                {metrics.map((m, idx) => {
                    const Icon = m.icon
                    return (
                        <div key={idx} className="space-y-1">
                            <div className="flex items-center gap-2 text-xs text-slate-500 dark:text-slate-400 mb-1">
                                <Icon className="w-3.5 h-3.5" />
                                <span>{m.label}</span>
                            </div>
                            <div className="text-lg font-semibold text-slate-900 dark:text-white">
                                {m.value}
                            </div>
                            <div className="text-[10px] text-slate-400 dark:text-slate-500">
                                {m.desc}
                            </div>
                        </div>
                    )
                })}
            </div>
        </div>
    )
}
