'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
    Activity,
    BarChart3,
    Calendar,
    FileText,
    Loader2,
    Plus,
    Target,
    Wallet,
} from 'lucide-react'
import PortfolioSankey from '@/components/PortfolioSankey'
import MarketStatus from '@/components/MarketStatus'
import AllocationPieChart from '@/components/dashboard/AllocationPieChart'
import PerformanceMovers from '@/components/dashboard/PerformanceMovers'
import RiskMetricsCard from '@/components/dashboard/RiskMetricsCard'
import StatCard from '@/components/dashboard/StatCard'
import { MaeMfeScatterPlot } from '@/components/dashboard/MaeMfeScatterPlot'
import { useAuth } from '@/contexts/AuthContext'
import { useDashboardData } from '@/hooks/useDashboardData'
import { useTrendColor } from '@/hooks/useTrendColor'
import { getCurrencySymbol } from '@/lib/symbolUtils'

export function DashboardMacroView() {
    const { token, settings } = useAuth()
    const trendColor = useTrendColor()
    const [historyDays] = useState(30)
    const [allocationDimension, setAllocationDimension] = useState<'CORE_TYPE' | 'MARKET' | 'RISK'>('CORE_TYPE')
    const [isMobile, setIsMobile] = useState(false)
    const { stats, pnlHistory, openPositions, allPositions, isLoading, error, refresh } = useDashboardData(token, historyDays)

    useEffect(() => {
        const handleResize = () => setIsMobile(window.innerWidth < 640)
        handleResize()
        window.addEventListener('resize', handleResize)
        return () => window.removeEventListener('resize', handleResize)
    }, [])

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (!stats) {
        return (
            <div className="card p-8 text-center">
                <p className="text-slate-500 dark:text-slate-400">Dashboard 数据暂不可用。</p>
            </div>
        )
    }

    const cs = getCurrencySymbol(settings?.display_currency)
    const totalPnl = Number(stats.total_pnl || 0)
    const isPositive = totalPnl >= 0
    const allocationData = allocationDimension === 'CORE_TYPE'
        ? stats.core_type_allocation
        : allocationDimension === 'MARKET'
            ? stats.market_allocation
            : stats.risk_level_allocation

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            <section className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-white/80 p-5 shadow-xl shadow-slate-200/50 backdrop-blur dark:border-slate-800 dark:bg-slate-950/70 dark:shadow-slate-950/40">
                <div className="pointer-events-none absolute right-[-8rem] top-[-8rem] h-64 w-64 rounded-full bg-slate-200/60 blur-3xl dark:bg-slate-700/30" />
                <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
                    <div>
                        <p className="text-xs font-black uppercase tracking-[0.3em] text-slate-500">Macro Dashboard</p>
                        <h1 className="mt-3 text-3xl font-black tracking-[-0.04em] text-slate-950 dark:text-white md:text-5xl">
                            宏观看板，不再抢占首页。
                        </h1>
                        <p className="mt-3 max-w-2xl text-sm leading-7 text-slate-600 dark:text-slate-300">
                            这里保留资产、风险、表现和资金流的全局分析。默认入口已经回到时间线与 Review Inbox。
                        </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link href="/positions/new" className="btn btn-primary inline-flex items-center gap-2">
                            <Plus className="h-4 w-4" />
                            新增交易
                        </Link>
                        <button onClick={() => refresh()} className="btn btn-secondary inline-flex items-center gap-2">
                            <Activity className="h-4 w-4" />
                            刷新
                        </button>
                    </div>
                </div>
            </section>

            {error && (
                <div className="rounded-2xl border border-red-200 bg-red-50 p-4 text-sm text-red-700 dark:border-red-500/30 dark:bg-red-500/10 dark:text-red-200">
                    Error loading dashboard data: {error}
                </div>
            )}

            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                <div className="grid grid-cols-2 gap-3 md:flex">
                    <Link href="/" className="btn btn-outline inline-flex items-center justify-center gap-2">
                        <Activity className="h-4 w-4" />
                        回到时间线
                    </Link>
                    <Link href="/daily" className="btn btn-outline inline-flex items-center justify-center gap-2">
                        <Calendar className="h-4 w-4" />
                        交易日历
                    </Link>
                    <Link href="/insights" className="btn btn-outline inline-flex items-center justify-center gap-2">
                        <FileText className="h-4 w-4" />
                        复盘洞察
                    </Link>
                </div>
                <MarketStatus />
            </div>

            <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
                <StatCard
                    title="总盈亏"
                    value={`${isPositive ? '+' : ''}${cs}${totalPnl.toLocaleString()}`}
                    icon={Wallet}
                    trend={isPositive ? 'up' : 'down'}
                    color={isPositive ? trendColor.upColor : trendColor.downColor}
                />
                <StatCard
                    title="胜率"
                    value={`${Number(stats.win_rate || 0).toFixed(1)}%`}
                    icon={Target}
                    color="text-slate-900 dark:text-white"
                />
                <StatCard
                    title="盈亏比"
                    value={Number(stats.avg_pnl_ratio || 0).toFixed(2)}
                    icon={BarChart3}
                    color="text-slate-900 dark:text-white"
                />
                <StatCard
                    title="持仓数量"
                    value={Number(stats.open_positions || 0).toString()}
                    icon={Activity}
                    color="text-slate-900 dark:text-white"
                />
            </div>

            <div className="grid gap-6 xl:grid-cols-[minmax(0,1fr)_360px]">
                <main className="space-y-6">
                    {stats.portfolio_flow && stats.portfolio_flow.nodes.length > 0 && (
                        <PortfolioSankey data={stats.portfolio_flow} totalAssets={stats.total_assets} isMobile={isMobile} />
                    )}

                    <section className="card p-5">
                        <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                            <div>
                                <p className="text-xs font-black uppercase tracking-[0.24em] text-slate-500">Allocation</p>
                                <h2 className="text-lg font-bold text-slate-950 dark:text-white">资产配置视角</h2>
                            </div>
                            <div className="flex rounded-xl bg-slate-100 p-1 dark:bg-slate-800">
                                {[
                                    { id: 'CORE_TYPE', label: '类别' },
                                    { id: 'MARKET', label: '市场' },
                                    { id: 'RISK', label: '风险' },
                                ].map((item) => (
                                    <button
                                        key={item.id}
                                        onClick={() => setAllocationDimension(item.id as 'CORE_TYPE' | 'MARKET' | 'RISK')}
                                        className={`rounded-lg px-3 py-1.5 text-xs font-bold transition ${allocationDimension === item.id
                                            ? 'bg-white text-slate-950 shadow-sm dark:bg-slate-700 dark:text-white'
                                            : 'text-slate-500 hover:text-slate-800 dark:hover:text-slate-200'
                                            }`}
                                    >
                                        {item.label}
                                    </button>
                                ))}
                            </div>
                        </div>
                        <AllocationPieChart data={allocationData} dimension={allocationDimension} />
                    </section>

                    <RiskMetricsCard
                        sharpe={stats.sharpe_ratio}
                        sortino={stats.sortino_ratio}
                        calmar={stats.calmar_ratio}
                        maxDrawdown={stats.max_drawdown}
                    />
                </main>

                <aside className="space-y-6">
                    <PerformanceMovers top={stats.top_movers} bottom={stats.bottom_movers} />
                    <MaeMfeScatterPlot positions={allPositions} />
                    <section className="card p-5">
                        <p className="text-xs font-black uppercase tracking-[0.24em] text-slate-500">Open Positions</p>
                        <p className="mt-2 text-3xl font-black text-slate-950 dark:text-white">{openPositions.length}</p>
                        <p className="mt-2 text-sm leading-6 text-slate-500 dark:text-slate-400">
                            这里保留宏观数量视角；具体复盘动作回到首页 Review Inbox。
                        </p>
                    </section>
                </aside>
            </div>
        </div>
    )
}
