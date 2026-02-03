'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import {
    Plus,
    TrendingUp,
    TrendingDown,
    Loader2,
    ChevronDown,
    ChevronUp,
    ArrowUpCircle,
    ArrowDownCircle,
    Filter
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { positionsAPI, Position, TradeBatch, accountsAPI, TradingAccount } from '@/lib/api'

export default function PositionsPage() {
    const { token } = useAuth()
    const [positions, setPositions] = useState<Position[]>([])
    const [accounts, setAccounts] = useState<TradingAccount[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState('')

    // Filters
    const [statusFilter, setStatusFilter] = useState<'ALL' | 'OPEN' | 'CLOSED'>('ALL')
    const [accountFilter, setAccountFilter] = useState<number | 'ALL'>('ALL')
    const [assetFilter, setAssetFilter] = useState<'ALL' | 'Stock' | 'Crypto'>('ALL')

    // URL params for linking from dashboard
    const searchParams = useSearchParams()
    const router = useRouter()

    useEffect(() => {
        const type = searchParams.get('asset_type')
        if (type) {
            if (type.toLowerCase() === 'stock') setAssetFilter('Stock')
            else if (type.toLowerCase() === 'crypto') setAssetFilter('Crypto')
        }
    }, [searchParams])

    // Expanded position for batch view
    const [expandedId, setExpandedId] = useState<number | null>(null)

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                // Build API params
                const params: any = {}
                if (statusFilter !== 'ALL') params.status = statusFilter
                if (accountFilter !== 'ALL') params.account_id = accountFilter
                if (assetFilter !== 'ALL') params.asset_type = assetFilter

                const [positionsData, accountsData] = await Promise.all([
                    positionsAPI.list(token, params),
                    accountsAPI.list(token)
                ])
                setPositions(positionsData)
                setAccounts(accountsData)
            } catch (err: any) {
                setError(err.message || '加载失败')
            } finally {
                setIsLoading(false)
            }
        }
        fetchData()
    }, [token, statusFilter, accountFilter, assetFilter])

    // Client-side filtering is no longer needed as we fetch filtered data
    const filteredPositions = positions

    const toggleExpand = async (id: number) => {
        if (expandedId === id) {
            setExpandedId(null)
        } else {
            // Fetch full position with batches if not already loaded
            if (!positions.find(p => p.id === id)?.batches) {
                try {
                    const fullPosition = await positionsAPI.get(token!, id)
                    setPositions(prev => prev.map(p => p.id === id ? fullPosition : p))
                } catch (err) {
                    console.error('Failed to load batches', err)
                }
            }
            setExpandedId(id)
        }
    }

    const getAccountName = (accountId?: number) => {
        if (!accountId) return '-'
        const account = accounts.find(a => a.id === accountId)
        return account?.name || '-'
    }

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
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold">持仓记录</h1>
                <Link href="/positions/new" className="btn btn-primary">
                    <Plus className="w-4 h-4 mr-1" />
                    新增交易
                </Link>
            </div>

            {/* Asset Type Tabs */}
            <div className="border-b border-slate-200 dark:border-slate-700 mb-4">
                <div className="flex space-x-6">
                    {['ALL', 'Stock', 'Crypto'].map((type) => (
                        <button
                            key={type}
                            onClick={() => {
                                setAssetFilter(type as any)
                                // Update URL to reflect current filter state if desired, 
                                // but for now state drive is enough unless deep linking is strictly enforced back to URL
                                const url = new URL(window.location.href)
                                if (type !== 'ALL') url.searchParams.set('asset_type', type)
                                else url.searchParams.delete('asset_type')
                                router.push(`${url.pathname}${url.search}`)
                            }}
                            className={`pb-3 text-sm font-medium border-b-2 transition-colors ${assetFilter === type
                                ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                                : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                                }`}
                        >
                            {type === 'ALL' ? '全部资产' : type === 'Stock' ? '股票 (Stock)' : '加密货币 (Crypto)'}
                        </button>
                    ))}
                </div>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap gap-3 items-center">
                <div className="flex items-center gap-2">
                    <Filter className="w-4 h-4 text-slate-500" />
                    <span className="text-sm text-slate-500">筛选:</span>
                </div>
                <select
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value as 'ALL' | 'OPEN' | 'CLOSED')}
                    className="input text-sm py-1.5 w-auto"
                >
                    <option value="ALL">全部状态</option>
                    <option value="OPEN">持仓中</option>
                    <option value="CLOSED">已平仓</option>
                </select>
                <select
                    value={accountFilter === 'ALL' ? 'ALL' : accountFilter}
                    onChange={(e) => setAccountFilter(e.target.value === 'ALL' ? 'ALL' : parseInt(e.target.value))}
                    className="input text-sm py-1.5 w-auto"
                >
                    <option value="ALL">全部账户</option>
                    {accounts.map(a => (
                        <option key={a.id} value={a.id}>{a.name}</option>
                    ))}
                </select>
            </div>

            {/* Error */}
            {error && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600">
                    {error}
                </div>
            )}

            {/* Position List */}
            {filteredPositions.length === 0 ? (
                <div className="card p-12 text-center">
                    <p className="text-slate-500 mb-4">暂无持仓记录</p>
                    <Link href="/positions/new" className="btn btn-primary inline-flex">
                        <Plus className="w-4 h-4 mr-1" />
                        新增交易
                    </Link>
                </div>
            ) : (
                <div className="space-y-3">
                    {filteredPositions.map(position => (
                        <div key={position.id} className="card overflow-hidden">
                            {/* Position Summary Row */}
                            <div
                                className="p-4 flex items-center justify-between cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
                                onClick={() => toggleExpand(position.id)}
                            >
                                <div className="flex items-center gap-4">
                                    {/* Direction Badge */}
                                    <div className={`p-2 rounded-lg ${position.direction === 'LONG'
                                        ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600'
                                        : 'bg-red-100 dark:bg-red-900/30 text-red-600'
                                        }`}>
                                        {position.direction === 'LONG'
                                            ? <ArrowUpCircle className="w-5 h-5" />
                                            : <ArrowDownCircle className="w-5 h-5" />
                                        }
                                    </div>

                                    {/* Symbol & Account */}
                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold text-lg">{position.symbol}</span>
                                            <span className={`text-xs px-2 py-0.5 rounded-full ${position.status === 'OPEN'
                                                ? 'bg-blue-100 dark:bg-blue-900/30 text-blue-600'
                                                : 'bg-slate-100 dark:bg-slate-700 text-slate-500'
                                                }`}>
                                                {position.status === 'OPEN' ? '持仓中' : '已平仓'}
                                            </span>
                                        </div>
                                        <p className="text-xs text-slate-500">
                                            {getAccountName(position.account_id)} · {position.exchange}
                                        </p>
                                    </div>
                                </div>

                                {/* Stats */}
                                <div className="flex items-center gap-6">
                                    <div className="text-right">
                                        <p className="text-xs text-slate-500">数量</p>
                                        <p className="font-medium">{Number(position.total_quantity).toFixed(4)}</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xs text-slate-500">均价</p>
                                        <p className="font-medium">${Number(position.average_entry_price || 0).toFixed(2)}</p>
                                    </div>
                                    <div className="text-right">
                                        <p className="text-xs text-slate-500">已实现盈亏</p>
                                        <p className={`font-semibold flex items-center justify-end gap-1 ${Number(position.realized_pnl) >= 0 ? 'text-emerald-500' : 'text-red-500'
                                            }`}>
                                            {Number(position.realized_pnl) >= 0 ? <TrendingUp className="w-4 h-4" /> : <TrendingDown className="w-4 h-4" />}
                                            ${Math.abs(Number(position.realized_pnl)).toFixed(2)}
                                        </p>
                                    </div>
                                    <div className="text-slate-400">
                                        {expandedId === position.id ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                                    </div>
                                </div>
                            </div>

                            {/* Expanded Batch List */}
                            {expandedId === position.id && position.batches && (
                                <div className="border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 p-4">
                                    <div className="flex items-center justify-between mb-3">
                                        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">交易批次</h3>
                                        {position.status === 'OPEN' && (
                                            <Link
                                                href={`/positions/${position.id}/add-batch`}
                                                className="text-xs text-indigo-500 hover:text-indigo-600"
                                            >
                                                + 加仓/减仓
                                            </Link>
                                        )}
                                    </div>
                                    <div className="space-y-2">
                                        {position.batches.map((batch: TradeBatch) => (
                                            <div
                                                key={batch.id}
                                                className="flex items-center justify-between p-3 rounded-lg bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700"
                                            >
                                                <div className="flex items-center gap-3">
                                                    <span className={`text-xs font-medium px-2 py-0.5 rounded ${batch.type === 'ENTRY'
                                                        ? 'bg-emerald-100 dark:bg-emerald-900/30 text-emerald-600'
                                                        : 'bg-amber-100 dark:bg-amber-900/30 text-amber-600'
                                                        }`}>
                                                        {batch.type === 'ENTRY' ? '加仓' : '减仓'}
                                                    </span>
                                                    <span className="text-sm text-slate-500">
                                                        {new Date(batch.time).toLocaleString('zh-CN', {
                                                            month: 'short',
                                                            day: 'numeric',
                                                            hour: '2-digit',
                                                            minute: '2-digit'
                                                        })}
                                                    </span>
                                                </div>
                                                <div className="flex items-center gap-4 text-sm">
                                                    <span>${Number(batch.price).toFixed(2)}</span>
                                                    <span className="text-slate-500">x {Number(batch.quantity).toFixed(4)}</span>
                                                    {batch.pnl !== null && batch.pnl !== undefined && (
                                                        <span className={Number(batch.pnl) >= 0 ? 'text-emerald-500' : 'text-red-500'}>
                                                            {Number(batch.pnl) >= 0 ? '+' : ''}{Number(batch.pnl).toFixed(2)}
                                                        </span>
                                                    )}
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                    <div className="mt-3 flex justify-end">
                                        <Link
                                            href={`/positions/${position.id}`}
                                            className="text-sm text-indigo-500 hover:text-indigo-600"
                                        >
                                            查看详情 →
                                        </Link>
                                    </div>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
