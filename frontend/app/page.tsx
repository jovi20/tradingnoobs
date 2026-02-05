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
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, PieChart, Pie, Cell, Legend, Sankey } from 'recharts'
import { useRouter } from 'next/navigation'
import { useAuth } from '@/contexts/AuthContext'
import { dashboardAPI, positionsAPI, Position, DashboardStats, AssetAllocation, PositionMover } from '@/lib/api'
import {
    getAssetTypeColor,
    getAssetTypeLabel,
    getAssetTypeHexColor,
    getMarketLabel,
    getRiskLevelInfo,
    AssetCoreType,
    AssetMarket,
    AssetRiskLevel
} from '@/lib/symbolUtils'
import MarketStatus from '@/components/MarketStatus'
import PortfolioSankey from '@/components/PortfolioSankey'
import { useTrendColor } from '@/hooks/useTrendColor'

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

function AllocationPieChart({ data, dimension }: { data: AssetAllocation[], dimension: 'CORE_TYPE' | 'MARKET' | 'RISK' }) {
    const router = useRouter()

    if (!data || data.length === 0) {
        return <div className="h-full flex items-center justify-center text-slate-500 min-h-[300px]">暂无数据</div>
    }

    const chartData = data.map(item => {
        let label = item.name;
        if (dimension === 'CORE_TYPE') label = getAssetTypeLabel(item.name as any);
        else if (dimension === 'MARKET') label = getMarketLabel(item.name as AssetMarket);
        else if (dimension === 'RISK') label = getRiskLevelInfo(item.name as AssetRiskLevel).label;

        return {
            ...item,
            name: label,
            originalName: item.name
        }
    })

    return (
        <div className="h-[300px] w-full mt-4">
            <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                    <Pie
                        data={chartData}
                        cx="50%"
                        cy="50%"
                        innerRadius={60}
                        outerRadius={80}
                        paddingAngle={5}
                        dataKey="value"
                        nameKey="name"
                        onClick={(entry) => {
                            if (entry && entry.originalName) {
                                let queryParam = 'asset_type';
                                if (dimension === 'CORE_TYPE') queryParam = 'core_type';
                                else if (dimension === 'MARKET') queryParam = 'market';
                                else if (dimension === 'RISK') queryParam = 'risk_level';
                                router.push(`/positions?${queryParam}=${entry.originalName}&dimension=${dimension}`)
                            }
                        }}
                        className="cursor-pointer focus:outline-none"
                    >
                        {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={getAssetTypeHexColor(entry.originalName)} />
                        ))}
                    </Pie>
                    <Tooltip
                        formatter={(value: number, name: string, props: any) => `${props.payload.percent}%`}
                    />
                    <Legend />
                </PieChart>
            </ResponsiveContainer>
        </div>
    )
}

function PerformanceMovers({ top, bottom }: { top: PositionMover[], bottom: PositionMover[] }) {
    const trendColor = useTrendColor()

    const MoverRow = ({ item, type }: { item: PositionMover, type: 'top' | 'bottom' }) => (
        <div className="flex items-center justify-between py-2 border-b last:border-0 border-slate-100 dark:border-slate-800">
            <div className="flex items-center gap-2">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${type === 'top' ? trendColor.upBg : trendColor.downBg}`}>
                    {type === 'top' ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                </div>
                <div>
                    <h4 className="font-medium text-sm">{item.symbol}</h4>
                    <p className="text-xs text-slate-500">${item.current_price?.toFixed(2)}</p>
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

function PositionCard({ position }: { position: Position }) {
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

export default function DashboardPage() {
    const { token } = useAuth()
    const trendColor = useTrendColor()
    const [stats, setStats] = useState<DashboardStats | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [allocationDimension, setAllocationDimension] = useState<'CORE_TYPE' | 'MARKET' | 'RISK'>('CORE_TYPE')
    const [pnlHistory, setPnlHistory] = useState<{ date: string; pnl: number; pnl_percent: number }[]>([])
    const [openPositions, setOpenPositions] = useState<Position[]>([])
    const [periodPnl, setPeriodPnl] = useState<number>(0)
    const [periodValue, setPeriodValue] = useState<number>(0)
    const [selectedPeriod, setSelectedPeriod] = useState<string>('1周')
    const [isMobile, setIsMobile] = useState(false)

    useEffect(() => {
        const handleResize = () => {
            setIsMobile(window.innerWidth < 640)
        }
        handleResize()
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [])

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                const [statsData, historyData, positionsData] = await Promise.all([
                    dashboardAPI.stats(token),
                    dashboardAPI.pnlHistory(token, 7),
                    positionsAPI.list(token, { status: 'OPEN' }),
                ])
                setStats(statsData)
                setPnlHistory(historyData)
                setOpenPositions(positionsData)
            } catch (err) {
                setStats({
                    total_assets: 0,
                    total_pnl: 0,
                    win_rate: 0,
                    avg_pnl_ratio: 0,
                    total_trades: 0,
                    open_positions: 0,
                    closed_trades: 0,
                    asset_allocation: [],
                    core_type_allocation: [],
                    market_allocation: [],
                    risk_level_allocation: [],
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

    useEffect(() => {
        if (pnlHistory.length > 1) {
            const latest = pnlHistory[pnlHistory.length - 1]
            const start = pnlHistory[0]
            setPeriodPnl(latest.pnl_percent - start.pnl_percent)
            setPeriodValue(latest.pnl - start.pnl)
        } else if (pnlHistory.length === 1) {
            setPeriodPnl(pnlHistory[0].pnl_percent)
            setPeriodValue(pnlHistory[0].pnl)
        } else {
            setPeriodPnl(0)
            setPeriodValue(0)
        }
    }, [pnlHistory])

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
                <div className="grid grid-cols-2 md:flex gap-3 md:gap-4 w-full md:w-auto">
                    <Link href="/positions/new" className="flex items-center gap-2 px-3 md:px-4 py-2.5 md:py-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-100 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500 transition-colors group">
                        <div className="p-1.5 md:p-2 bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white rounded-lg group-hover:bg-slate-200 dark:group-hover:bg-slate-600 transition-colors shrink-0">
                            <TrendingUp className="w-4 h-4 md:w-5 md:h-5" />
                        </div>
                        <span className="font-medium text-xs md:text-sm whitespace-nowrap">新增交易</span>
                    </Link>
                    <Link href="/strategies" className="flex items-center gap-2 px-3 md:px-4 py-2.5 md:py-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-100 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500 transition-colors group">
                        <div className="p-1.5 md:p-2 bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white rounded-lg group-hover:bg-slate-200 dark:group-hover:bg-slate-600 transition-colors shrink-0">
                            <BarChart3 className="w-4 h-4 md:w-5 md:h-5" />
                        </div>
                        <span className="font-medium text-xs md:text-sm whitespace-nowrap">新增策略</span>
                    </Link>
                    <Link href="/settings" className="flex items-center gap-2 px-3 md:px-4 py-2.5 md:py-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-100 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500 transition-colors group">
                        <div className="p-1.5 md:p-2 bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white rounded-lg group-hover:bg-slate-200 dark:group-hover:bg-slate-600 transition-colors shrink-0">
                            <Wallet className="w-4 h-4 md:w-5 md:h-5" />
                        </div>
                        <span className="font-medium text-xs md:text-sm whitespace-nowrap">新增账户</span>
                    </Link>
                    <Link href="/daily" className="flex items-center gap-2 px-3 md:px-4 py-2.5 md:py-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-100 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500 transition-colors group">
                        <div className="p-1.5 md:p-2 bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white rounded-lg group-hover:bg-slate-200 dark:group-hover:bg-slate-600 transition-colors shrink-0">
                            <Calendar className="w-4 h-4 md:w-5 md:h-5" />
                        </div>
                        <span className="font-medium text-xs md:text-sm whitespace-nowrap">交易日历</span>
                    </Link>
                    <Link href="/insights" className="flex items-center gap-2 px-3 md:px-4 py-2.5 md:py-3 bg-white dark:bg-slate-800 rounded-xl shadow-sm border border-slate-100 dark:border-slate-700 hover:border-slate-400 dark:hover:border-slate-500 transition-colors group">
                        <div className="p-1.5 md:p-2 bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white rounded-lg group-hover:bg-slate-200 dark:group-hover:bg-slate-600 transition-colors shrink-0">
                            <FileText className="w-4 h-4 md:w-5 md:h-5" />
                        </div>
                        <span className="font-medium text-xs md:text-sm whitespace-nowrap">AI 洞察</span>
                    </Link>
                </div>

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
                    color={isPositive ? trendColor.upColor : trendColor.downColor}
                />
                <StatCard
                    title="胜率"
                    value={`${stats.win_rate.toFixed(1)}%`}
                    icon={Target}
                    color="text-slate-900 dark:text-white"
                />
                <StatCard
                    title="盈亏比"
                    value={stats.avg_pnl_ratio.toFixed(2)}
                    icon={BarChart3}
                    color="text-slate-900 dark:text-white"
                />
                <StatCard
                    title="持仓数量"
                    value={stats.open_positions.toString()}
                    icon={Activity}
                    color="text-slate-900 dark:text-white"
                />
            </div>

            {/* Main Content Layout - Optimized for Mobile order and Desktop no-gap */}
            <div className="flex flex-col lg:grid lg:grid-cols-3 gap-6 lg:items-start">

                {/* Wrapper 1: Chart & Positions (Desktop Column 1&2) */}
                <div className="contents lg:block lg:col-span-2 space-y-6">
                    {/* Funds Flow (Sankey) - Now Top of Left Column */}
                    {stats.portfolio_flow && stats.portfolio_flow.nodes.length > 0 && (
                        <PortfolioSankey
                            data={stats.portfolio_flow}
                            totalAssets={stats.total_assets}
                            isMobile={isMobile}
                        />
                    )}

                    {/* P&L Chart */}
                    <div className="card p-4 md:p-6 order-1">
                        <div className="flex items-start justify-between mb-4 relative z-10">
                            <div>
                                <h2 className="text-lg font-semibold text-slate-900 dark:text-white">盈亏曲线</h2>
                                <div className="flex items-baseline gap-2 mt-1">
                                    <p className={`text-2xl font-bold ${periodPnl >= 0 ? trendColor.upColor : trendColor.downColor}`}>
                                        {periodPnl >= 0 ? '+' : ''}{periodPnl.toFixed(2)}%
                                    </p>
                                    <p className={`text-sm font-medium ${periodValue >= 0 ? trendColor.upColor : trendColor.downColor} opacity-80`}>
                                        ({periodValue >= 0 ? '+' : ''}${Math.abs(periodValue).toLocaleString()})
                                    </p>
                                </div>
                                <p className="text-xs text-slate-500 mt-0.5">{selectedPeriod}阶段盈亏 (Relative Change)</p>
                            </div>
                            <div className="flex flex-wrap gap-1">
                                {[
                                    { label: '1周', days: 7 },
                                    { label: '本月', days: -1 },
                                    { label: '1月', days: 30 },
                                    { label: '3月', days: 90 },
                                    { label: '本年', days: -2 },
                                    { label: '1年', days: 365 },
                                    { label: '全部', days: 9999 },
                                ].map((option) => (
                                    <button
                                        key={option.label}
                                        onClick={async () => {
                                            if (!token) return
                                            try {
                                                setSelectedPeriod(option.label)
                                                let days = option.days
                                                if (days === -1) {
                                                    const now = new Date()
                                                    days = now.getDate()
                                                } else if (days === -2) {
                                                    const now = new Date()
                                                    const startOfYear = new Date(now.getFullYear(), 0, 1)
                                                    days = Math.ceil((now.getTime() - startOfYear.getTime()) / (1000 * 60 * 60 * 24))
                                                }
                                                // Ensure days is at least 1
                                                if (days < 1) days = 1

                                                const data = await dashboardAPI.pnlHistory(token, days)
                                                setPnlHistory(data)
                                            } catch (err) {
                                                console.error('Failed to fetch PnL history:', err)
                                            }
                                        }}
                                        className={`px-2 py-1 text-xs rounded-md transition-colors ${selectedPeriod === option.label
                                            ? 'bg-primary-600 text-white shadow-sm'
                                            : 'text-slate-500 hover:bg-primary-100 dark:hover:bg-primary-900/30 hover:text-primary-600'
                                            }`}
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
                                            stroke={trendColor.upHex}
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

                    {/* Open Positions - Positioned under Chart on Desktop but at the bottom on Mobile */}
                    <div className="space-y-4 order-4">
                        <div className="flex items-center justify-between">
                            <h2 className="text-lg font-semibold flex items-center gap-2">
                                持仓中
                                <span className="bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 text-xs px-2 py-0.5 rounded-full">{openPositions.length}</span>
                            </h2>
                            {openPositions.length > 6 && (
                                <Link href="/positions" className="text-xs text-primary-600 hover:text-primary-700 font-medium flex items-center gap-1">
                                    查看更多 <span className="text-[10px] bg-primary-50 dark:bg-primary-900/20 px-1.5 py-0.5 rounded-full">+{openPositions.length - 6}</span>
                                </Link>
                            )}
                        </div>
                        {openPositions.length === 0 ? (
                            <div className="card p-6 text-center text-slate-500">
                                暂无持仓
                            </div>
                        ) : (
                            <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-3">
                                {openPositions.slice(0, 6).map((position) => (
                                    <PositionCard key={position.id} position={position} />
                                ))}
                            </div>
                        )}
                    </div>
                </div>

                {/* Wrapper 2: Sidebar (Desktop Column 3) */}
                <div className="contents lg:block lg:col-span-1 space-y-6">
                    {/* Asset Allocation Pie Chart */}
                    <div className="card p-4">
                        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 mb-2">
                            <h3 className="text-sm font-semibold text-slate-900 dark:text-white">资产分布</h3>
                            <div className="flex bg-slate-100 dark:bg-slate-800 p-1 rounded-lg">
                                {[
                                    { id: 'CORE_TYPE', label: '类型' },
                                    { id: 'MARKET', label: '市场' },
                                    { id: 'RISK', label: '风险' },
                                ].map((tab) => (
                                    <button
                                        key={tab.id}
                                        onClick={() => setAllocationDimension(tab.id as any)}
                                        className={`px-2 py-1 text-[10px] font-medium rounded-md transition-all ${allocationDimension === tab.id
                                            ? 'bg-white dark:bg-slate-700 text-primary-600 shadow-sm'
                                            : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                                            }`}
                                    >
                                        {tab.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <AllocationPieChart
                            data={
                                allocationDimension === 'MARKET' ? stats.market_allocation :
                                    allocationDimension === 'RISK' ? stats.risk_level_allocation :
                                        stats.core_type_allocation
                            }
                            dimension={allocationDimension}
                        />
                    </div>

                    {/* Account Allocation List */}
                    <div className="card p-4">
                        <h3 className="text-sm font-semibold mb-4 text-slate-900 dark:text-white">账户分布</h3>
                        <div className="space-y-4">
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

                    {/* Historical Performance (Movers) - Moved to Sidebar */}
                    <div className="card p-4">
                        <h2 className="text-sm font-semibold mb-4 text-slate-900 dark:text-white">历史表现</h2>
                        <PerformanceMovers top={stats.top_movers} bottom={stats.bottom_movers} />
                    </div>
                </div>

            </div>
        </div>
    )
}
