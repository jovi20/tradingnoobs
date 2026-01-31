'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
    Plus,
    TrendingUp,
    TrendingDown,
    Search,
    Loader2
} from 'lucide-react'
import { Trade, tradesAPI } from '@/lib/api'
import { useAuth } from '@/contexts/AuthContext'

function TradeListItem({ trade }: { trade: Trade }) {
    const isOpen = trade.status === 'OPEN'
    const pnl = trade.pnl || 0
    const isPositive = pnl >= 0
    const price = isOpen ? trade.current_price : trade.exit_price

    return (
        <Link href={`/trades/${trade.id}`}>
            <div className="card p-4 hover:scale-[1.01] cursor-pointer">
                <div className="flex items-center justify-between">
                    <div className="flex items-center space-x-4">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${isPositive ? 'bg-emerald-100 dark:bg-emerald-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                            {isPositive ? (
                                <TrendingUp className="w-6 h-6 text-emerald-500" />
                            ) : (
                                <TrendingDown className="w-6 h-6 text-red-500" />
                            )}
                        </div>
                        <div>
                            <div className="flex items-center space-x-2">
                                <h3 className="font-semibold text-lg">{trade.symbol}</h3>
                                <span className={`badge ${isOpen ? 'badge-open' : 'badge-closed'}`}>
                                    {isOpen ? '持仓中' : '已平仓'}
                                </span>
                            </div>
                            <p className="text-sm text-slate-500">
                                {trade.exchange} · {new Date(trade.entry_time).toLocaleDateString('zh-CN')}
                            </p>
                        </div>
                    </div>

                    <div className="text-right">
                        <p className={`text-lg font-bold ${isPositive ? 'pnl-positive' : 'pnl-negative'}`}>
                            {isPositive ? '+' : ''}{pnl.toFixed(2)}
                        </p>
                        <p className={`text-sm ${isPositive ? 'pnl-positive' : 'pnl-negative'}`}>
                            {isPositive ? '+' : ''}{trade.pnl_percent?.toFixed(2)}%
                        </p>
                    </div>
                </div>

                <div className="mt-4 grid grid-cols-3 gap-4 text-sm">
                    <div>
                        <p className="text-slate-500 dark:text-slate-400">成本价</p>
                        <p className="font-medium">${trade.entry_price.toLocaleString()}</p>
                    </div>
                    <div>
                        <p className="text-slate-500 dark:text-slate-400">{isOpen ? '现价' : '卖出价'}</p>
                        <p className="font-medium">${price?.toLocaleString() || '-'}</p>
                    </div>
                    <div>
                        <p className="text-slate-500 dark:text-slate-400">数量</p>
                        <p className="font-medium">{trade.quantity}</p>
                    </div>
                </div>

                {trade.entry_reason && (
                    <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-700">
                        <p className="text-sm text-slate-600 dark:text-slate-400 truncate">
                            📝 {trade.entry_reason}
                        </p>
                    </div>
                )}
            </div>
        </Link>
    )
}

export default function TradesPage() {
    const { token } = useAuth()
    const [trades, setTrades] = useState<Trade[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState('')
    const [filter, setFilter] = useState<'all' | 'open' | 'closed'>('all')
    const [search, setSearch] = useState('')

    useEffect(() => {
        const fetchTrades = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                const data = await tradesAPI.list(token)
                setTrades(data)
            } catch (err: any) {
                setError(err.message || '加载失败')
            } finally {
                setIsLoading(false)
            }
        }
        fetchTrades()
    }, [token])

    const filteredTrades = trades.filter((trade) => {
        if (filter === 'open' && trade.status !== 'OPEN') return false
        if (filter === 'closed' && trade.status !== 'CLOSED') return false
        if (search && !trade.symbol.toLowerCase().includes(search.toLowerCase())) return false
        return true
    })

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        )
    }

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* Header */}
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <h1 className="text-2xl font-bold">交易记录</h1>
                <Link href="/trades/new" className="btn btn-primary flex items-center space-x-2">
                    <Plus className="w-5 h-5" />
                    <span>新增交易</span>
                </Link>
            </div>

            {/* Filters */}
            <div className="flex flex-col sm:flex-row gap-4">
                <div className="relative flex-1">
                    <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                        type="text"
                        value={search}
                        onChange={(e) => setSearch(e.target.value)}
                        className="input pl-12"
                        placeholder="搜索标的..."
                    />
                </div>
                <div className="flex space-x-2">
                    {(['all', 'open', 'closed'] as const).map((f) => (
                        <button
                            key={f}
                            onClick={() => setFilter(f)}
                            className={`px-4 py-2 rounded-xl text-sm font-medium transition-all ${filter === f
                                ? 'bg-primary-500 text-white'
                                : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600'
                                }`}
                        >
                            {f === 'all' ? '全部' : f === 'open' ? '持仓中' : '已平仓'}
                        </button>
                    ))}
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600">
                    {error}
                </div>
            )}

            {/* Trade List */}
            <div className="space-y-4">
                {filteredTrades.length === 0 ? (
                    <div className="card p-12 text-center">
                        <p className="text-slate-500">暂无交易记录</p>
                        <Link href="/trades/new" className="btn btn-primary mt-4 inline-flex items-center space-x-2">
                            <Plus className="w-5 h-5" />
                            <span>创建第一笔交易</span>
                        </Link>
                    </div>
                ) : (
                    filteredTrades.map((trade) => (
                        <TradeListItem key={trade.id} trade={trade} />
                    ))
                )}
            </div>
        </div>
    )
}
