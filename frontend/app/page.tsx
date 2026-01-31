'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
    TrendingUp,
    TrendingDown,
    Target,
    BarChart3,
    Wallet,
    Activity,
    Loader2
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from 'recharts'
import { useAuth } from '@/contexts/AuthContext'
import { dashboardAPI, tradesAPI, Trade, DashboardStats } from '@/lib/api'

function StatCard({
    title,
    value,
    icon: Icon,
    trend,
    color
}: {
    title: string
    value: string
    icon: React.ElementType
    trend?: 'up' | 'down'
    color: string
}) {
    return (
        <div className="card p-6">
            <div className="flex items-center justify-between">
                <div>
                    <p className="text-sm text-slate-500 dark:text-slate-400">{title}</p>
                    <p className={`text-2xl font-bold mt-1 ${color}`}>{value}</p>
                </div>
                <div className={`p-3 rounded-xl ${color.includes('emerald') ? 'bg-emerald-100 dark:bg-emerald-900/30' : color.includes('red') ? 'bg-red-100 dark:bg-red-900/30' : 'bg-slate-100 dark:bg-slate-700'}`}>
                    <Icon className={`w-6 h-6 ${color}`} />
                </div>
            </div>
            {trend && (
                <div className="flex items-center mt-2 text-sm">
                    {trend === 'up' ? (
                        <TrendingUp className="w-4 h-4 text-emerald-500 mr-1" />
                    ) : (
                        <TrendingDown className="w-4 h-4 text-red-500 mr-1" />
                    )}
                    <span className={trend === 'up' ? 'text-emerald-500' : 'text-red-500'}>
                        vs last week
                    </span>
                </div>
            )}
        </div>
    )
}

function TradeCard({ trade }: { trade: Trade }) {
    const isPositive = (trade.pnl || 0) >= 0

    return (
        <Link href={`/trades/${trade.id}`}>
            <div className="card p-4 hover:scale-[1.01] transition-transform cursor-pointer">
                <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${isPositive ? 'bg-emerald-100 dark:bg-emerald-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                            {isPositive ? (
                                <TrendingUp className="w-5 h-5 text-emerald-500" />
                            ) : (
                                <TrendingDown className="w-5 h-5 text-red-500" />
                            )}
                        </div>
                        <div>
                            <h3 className="font-semibold">{trade.symbol}</h3>
                            <p className="text-xs text-slate-500">{trade.exchange}</p>
                        </div>
                    </div>
                    <span className="badge badge-open">持仓中</span>
                </div>

                <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                        <p className="text-slate-500 dark:text-slate-400">成本价</p>
                        <p className="font-medium">${trade.entry_price.toLocaleString()}</p>
                    </div>
                    <div>
                        <p className="text-slate-500 dark:text-slate-400">现价</p>
                        <p className="font-medium">${trade.current_price?.toLocaleString() || '-'}</p>
                    </div>
                    <div>
                        <p className="text-slate-500 dark:text-slate-400">数量</p>
                        <p className="font-medium">{trade.quantity}</p>
                    </div>
                    <div>
                        <p className="text-slate-500 dark:text-slate-400">盈亏</p>
                        <p className={`font-bold ${isPositive ? 'pnl-positive' : 'pnl-negative'}`}>
                            {isPositive ? '+' : ''}{trade.pnl?.toFixed(2)} ({trade.pnl_percent?.toFixed(2)}%)
                        </p>
                    </div>
                </div>

                {trade.entry_reason && (
                    <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                        <p className="text-xs text-slate-500 truncate">📝 {trade.entry_reason}</p>
                    </div>
                )}
            </div>
        </Link>
    )
}

export default function DashboardPage() {
    const { token } = useAuth()
    const [stats, setStats] = useState<DashboardStats | null>(null)
    const [pnlHistory, setPnlHistory] = useState<{ date: string; pnl: number }[]>([])
    const [openTrades, setOpenTrades] = useState<Trade[]>([])
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                const [statsData, historyData, tradesData] = await Promise.all([
                    dashboardAPI.stats(token),
                    dashboardAPI.pnlHistory(token, 30),
                    tradesAPI.list(token, { status: 'OPEN' }),
                ])
                setStats(statsData)
                setPnlHistory(historyData)
                setOpenTrades(tradesData)
            } catch (err) {
                // 如果API失败，使用默认值
                setStats({
                    total_pnl: 0,
                    win_rate: 0,
                    avg_pnl_ratio: 0,
                    total_trades: 0,
                    open_positions: 0,
                    closed_trades: 0,
                })
            } finally {
                setIsLoading(false)
            }
        }
        fetchData()
    }, [token])

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (!stats) return null

    const totalPnl = stats.total_pnl
    const isPositive = totalPnl >= 0

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* Stats Grid */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                <StatCard
                    title="总盈亏"
                    value={`${isPositive ? '+' : ''}$${totalPnl.toLocaleString()}`}
                    icon={Wallet}
                    trend={isPositive ? 'up' : 'down'}
                    color={isPositive ? 'text-emerald-500' : 'text-red-500'}
                />
                <StatCard
                    title="胜率"
                    value={`${stats.win_rate.toFixed(1)}%`}
                    icon={Target}
                    color="text-blue-500"
                />
                <StatCard
                    title="盈亏比"
                    value={stats.avg_pnl_ratio.toFixed(2)}
                    icon={BarChart3}
                    color="text-purple-500"
                />
                <StatCard
                    title="持仓数量"
                    value={stats.open_positions.toString()}
                    icon={Activity}
                    color="text-amber-500"
                />
            </div>

            {/* Chart and Open Positions */}
            <div className="grid lg:grid-cols-3 gap-6">
                {/* P&L Chart */}
                <div className="lg:col-span-2 card p-6">
                    <h2 className="text-lg font-semibold mb-4">累计盈亏曲线</h2>
                    <div className="h-[300px]">
                        {pnlHistory.length > 0 ? (
                            <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={pnlHistory}>
                                    <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                                    <XAxis
                                        dataKey="date"
                                        tick={{ fontSize: 12 }}
                                        tickFormatter={(value) => value.slice(5)}
                                    />
                                    <YAxis
                                        tick={{ fontSize: 12 }}
                                        tickFormatter={(value) => `$${(value / 1000).toFixed(0)}k`}
                                    />
                                    <Tooltip
                                        formatter={(value: number) => [`$${value.toFixed(2)}`, '盈亏']}
                                        labelFormatter={(label) => `日期: ${label}`}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="pnl"
                                        stroke="#22c55e"
                                        strokeWidth={2}
                                        dot={false}
                                    />
                                </LineChart>
                            </ResponsiveContainer>
                        ) : (
                            <div className="h-full flex items-center justify-center text-slate-500">
                                暂无数据
                            </div>
                        )}
                    </div>
                </div>

                {/* Open Positions */}
                <div className="space-y-4">
                    <h2 className="text-lg font-semibold">持仓中</h2>
                    {openTrades.length === 0 ? (
                        <div className="card p-6 text-center text-slate-500">
                            暂无持仓
                        </div>
                    ) : (
                        openTrades.map((trade) => (
                            <TradeCard key={trade.id} trade={trade} />
                        ))
                    )}
                </div>
            </div>
        </div>
    )
}
