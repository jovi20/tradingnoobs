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
    Loader2,
    Calendar,
    FileText
} from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell, Legend } from 'recharts'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { dashboardAPI, tradesAPI, Trade, DashboardStats, AssetAllocation, PositionMover } from '@/lib/api'
import { getAssetTypeColor } from '@/lib/symbolUtils'
import MarketStatus from '@/components/MarketStatus'

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
        <div className="card p-4 md:p-6">
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

const COLORS = ['#3b82f6', '#f59e0b', '#10b981', '#6366f1', '#ec4899'];

function AllocationPieChart({ data }: { data: AssetAllocation[] }) {
    const router = useRouter()

    if (!data || data.length === 0) {
        return <div className="h-full flex items-center justify-center text-slate-500">暂无数据</div>
    }

    return (
        <div className="h-[300px] w-full">
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                    <Pie
                        data={data}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                        onClick={(data) => {
                            if (data && data.name) {
                                router.push(`/positions?asset_type=${data.name}`)
                            }
                        }}
                        className="cursor-pointer focus:outline-none"
                    >
                        {data.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(value: number) => `$${value.toLocaleString()}`}
                    />
                    <Legend />
                </PieChart>
            </ResponsiveContainer>
        </div>
    )
}

function PerformanceMovers({ top, bottom }: { top: PositionMover[], bottom: PositionMover[] }) {
    const MoverRow = ({ item, type }: { item: PositionMover, type: 'top' | 'bottom' }) => (
        <div className="flex items-center justify-between py-2 border-b last:border-0 border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${type === 'top' ? 'bg-emerald-100 text-emerald-600' : 'bg-red-100 text-red-600'}`}>
                    {type === 'top' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                </div>
                <div>
                    <h4 className="font-medium text-sm">{item.symbol}</h4>
                    <p className="text-xs text-slate-500">${item.current_price?.toFixed(2)}</p>
                </div>
            </div>
            <span className={`font-bold text-sm ${type === 'top' ? 'text-emerald-500' : 'text-red-500'}`}>
                {type === 'top' ? '+' : ''}{item.change_percent?.toFixed(2)}%
            </span>
        </div>
    )

    return (
        <div className="space-y-6">
            <div>
                <h3 className="text-sm font-medium text-slate-500 mb-3 flex items-center gap-1">
                    <TrendingUp className="w-4 h-4 text-emerald-500" /> 表现最佳
                </h3>
                {top.length > 0 ? (
                    <div className="card p-4">
                        {top.map(item => <MoverRow key={item.id} item={item} type="top" />)}
                    </div>
                ) : <div className="text-sm text-slate-400">暂无数据</div>}
            </div>
            <div>
                <h3 className="text-sm font-medium text-slate-500 mb-3 flex items-center gap-1">
                    <TrendingDown className="w-4 h-4 text-red-500" /> 表现最差
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

function TradeCard({ trade }: { trade: Trade }) {
    const isPositive = (trade.pnl || 0) >= 0

    return (
        <Link href={`/positions/${trade.id}`}>
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
    const [pnlHistory, setPnlHistory] = useState<{ date: string; pnl: number; pnl_percent: number }[]>([])
    const [openTrades, setOpenTrades] = useState<Trade[]>([])
    const [isLoading, setIsLoading] = useState(true)

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                const [statsData, historyData, tradesData] = await Promise.all([
                    dashboardAPI.stats(token),
                    dashboardAPI.pnlHistory(token, 7),
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
                    asset_allocation: [],
                    account_allocation: [],
                    top_movers: [],
                    bottom_movers: [],
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
            {/* Quick Actions & Market Status */}
            <div className="flex flex-col md:flex-row items-center justify-between gap-4 pb-2">
                {/* Left: Quick Actions */}
                <div className="flex gap-4 overflow-x-auto w-full md:w-auto pb-1 no-scrollbar">
                    <Link href="/positions/new" className="flex items-center gap-2 px-4 py-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-100 dark:border-slate-700 hover:border-primary-500 transition-colors min-w-max">
                        <div className="p-2 bg-primary-50 dark:bg-primary-900/20 text-primary-600 rounded-lg">
                            <TrendingUp className="w-5 h-5" />
                        </div>
                        <span className="font-medium">新增交易</span>
                    </Link>
                    <Link href="/strategies" className="flex items-center gap-2 px-4 py-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-100 dark:border-slate-700 hover:border-primary-500 transition-colors min-w-max">
                        <div className="p-2 bg-purple-50 dark:bg-purple-900/20 text-purple-600 rounded-lg">
                            <BarChart3 className="w-5 h-5" />
                        </div>
                        <span className="font-medium">新增策略</span>
                    </Link>
                    <Link href="/settings" className="flex items-center gap-2 px-4 py-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-100 dark:border-slate-700 hover:border-primary-500 transition-colors min-w-max">
                        <div className="p-2 bg-amber-50 dark:bg-amber-900/20 text-amber-600 rounded-lg">
                            <Wallet className="w-5 h-5" />
                        </div>
                        <span className="font-medium">新增账户</span>
                    </Link>
                    <Link href="/daily" className="flex items-center gap-2 px-4 py-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-100 dark:border-slate-700 hover:border-primary-500 transition-colors min-w-max">
                        <div className="p-2 bg-blue-50 dark:bg-blue-900/20 text-blue-600 rounded-lg">
                            <Calendar className="w-5 h-5" />
                        </div>
                        <span className="font-medium">交易日历</span>
                    </Link>
                    <Link href="/reports" className="flex items-center gap-2 px-4 py-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-100 dark:border-slate-700 hover:border-primary-500 transition-colors min-w-max">
                        <div className="p-2 bg-teal-50 dark:bg-teal-900/20 text-teal-600 rounded-lg">
                            <FileText className="w-5 h-5" />
                        </div>
                        <span className="font-medium">查看周报</span>
                    </Link>
                </div>

                {/* Right: Market Status */}
                <div className="w-full md:w-auto flex justify-start md:justify-end overflow-hidden">
                    <MarketStatus />
                </div>
            </div>

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

            {/* Allocation and Movers */}
            <div className="grid lg:grid-cols-3 gap-6">
                {/* Asset Allocation Pie Chart & Accounts */}
                <div className="card p-4 md:p-6 lg:col-span-2 flex flex-col md:flex-row gap-8">
                    <div className="flex-1 min-w-0">
                        <h2 className="text-lg font-semibold mb-4">资产分布</h2>
                        <AllocationPieChart data={stats.asset_allocation} />
                    </div>

                    {/* Account Allocation List */}
                    {stats.account_allocation && stats.account_allocation.length > 0 && (
                        <div className="flex-1 min-w-0 border-t md:border-t-0 md:border-l border-slate-100 dark:border-slate-700 pt-6 md:pt-0 md:pl-8 flex flex-col">
                            <h3 className="text-sm font-medium text-slate-500 mb-4">账户分布 (Top 5)</h3>
                            <div className="space-y-3">
                                {stats.account_allocation.map((acc, idx) => (
                                    <div key={idx} className="flex items-center justify-between text-sm">
                                        <div className="flex items-center gap-3">
                                            <div className="w-2 h-2 rounded-full bg-slate-200 dark:bg-slate-700 shrink-0"></div>
                                            <div className="truncate">
                                                <span className="font-medium block truncate max-w-[120px]">{acc.name}</span>
                                                <span className="text-xs text-slate-400 block">{acc.broker}</span>
                                            </div>
                                        </div>
                                        <div className="text-right shrink-0">
                                            <span className="block font-medium">${acc.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                                            <span className="text-xs text-slate-400">{acc.percent}%</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>

                {/* Movers */}
                <div className="card p-4 md:p-6 lg:col-span-1">
                    <h2 className="text-lg font-semibold mb-4">历史表现</h2>
                    <PerformanceMovers top={stats.top_movers} bottom={stats.bottom_movers} />
                </div>
            </div>

            {/* Chart and Open Positions */}
            <div className="grid lg:grid-cols-3 gap-6">
                {/* P&L Chart */}
                <div className="lg:col-span-2 card p-4 md:p-6">
                    <div className="flex items-center justify-between mb-4">
                        <h2 className="text-lg font-semibold">盈亏曲线</h2>
                        <div className="flex flex-wrap gap-1">
                            {[
                                { label: '1周', days: 7 },
                                { label: '本月', days: -1 },  // MTD
                                { label: '1月', days: 30 },
                                { label: '3月', days: 90 },
                                { label: '本年', days: -2 },  // YTD
                                { label: '1年', days: 365 },
                                { label: '全部', days: 9999 },
                            ].map((option) => (
                                <button
                                    key={option.label}
                                    onClick={async () => {
                                        if (!token) return
                                        let days = option.days
                                        if (days === -1) {
                                            // MTD: 本月迄今
                                            const now = new Date()
                                            days = now.getDate()
                                        } else if (days === -2) {
                                            // YTD: 本年迄今
                                            const now = new Date()
                                            const startOfYear = new Date(now.getFullYear(), 0, 1)
                                            days = Math.ceil((now.getTime() - startOfYear.getTime()) / (1000 * 60 * 60 * 24))
                                        }
                                        const data = await dashboardAPI.pnlHistory(token, days)
                                        setPnlHistory(data)
                                    }}
                                    className="px-2 py-1 text-xs rounded-md hover:bg-primary-100 dark:hover:bg-primary-900/30 hover:text-primary-600 transition-colors"
                                >
                                    {option.label}
                                </button>
                            ))}
                        </div>
                    </div>
                    <div className="h-[250px] md:h-[300px]">
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
                                        tickFormatter={(value) => `${value}%`}
                                    />
                                    <Tooltip
                                        formatter={(value: number) => [`${value.toFixed(2)}%`, '盈亏率']}
                                        labelFormatter={(label) => `日期: ${label}`}
                                    />
                                    <Line
                                        type="monotone"
                                        dataKey="pnl_percent"
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
                    <div className="flex items-center justify-between">
                        <h2 className="text-lg font-semibold">
                            持仓中
                            <span className="ml-2 text-sm font-normal text-slate-500">{openTrades.length}</span>
                        </h2>
                        {openTrades.length > 5 && (
                            <Link href="/positions" className="text-sm text-primary-600 hover:text-primary-700 font-medium">
                                查看更多 →
                            </Link>
                        )}
                    </div>
                    {openTrades.length === 0 ? (
                        <div className="card p-6 text-center text-slate-500">
                            暂无持仓
                        </div>
                    ) : (
                        openTrades.slice(0, 5).map((trade) => (
                            <TradeCard key={trade.id} trade={trade} />
                        ))
                    )}
                </div>
            </div>
        </div>
    )
}
