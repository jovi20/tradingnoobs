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
    ArrowRight,
    Filter
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { positionsAPI, Position, TradeBatch, accountsAPI, TradingAccount } from '@/lib/api'
import { useTrendColor } from '@/hooks/useTrendColor'
import CustomSelect from '@/components/CustomSelect'
import {
    getMarketLabel, getRiskLevelInfo, getCoreTypeLabel,
    AssetMarket, AssetRiskLevel
} from '@/lib/symbolUtils'

export default function PositionsPage() {
    const { token } = useAuth()
    const trendColor = useTrendColor()
    const [positions, setPositions] = useState<Position[]>([])
    const [accounts, setAccounts] = useState<TradingAccount[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState('')

    // Filters
    const [statusFilter, setStatusFilter] = useState<'ALL' | 'OPEN' | 'CLOSED'>('ALL')
    const [accountFilter, setAccountFilter] = useState<number | 'ALL'>('ALL')

    // Multi-dimensional filters
    const [dimension, setDimension] = useState<'CORE_TYPE' | 'MARKET' | 'RISK' | 'ASSET_TYPE'>('ASSET_TYPE')
    const [categoryFilter, setCategoryFilter] = useState<string>('ALL')

    // URL params for linking from dashboard
    const searchParams = useSearchParams()
    const router = useRouter()

    useEffect(() => {
        const type = searchParams.get('asset_type')
        const core = searchParams.get('core_type')
        const mkt = searchParams.get('market')
        const risk = searchParams.get('risk_level')
        const dim = searchParams.get('dimension')

        if (dim) setDimension(dim as any)

        if (type) {
            setDimension('ASSET_TYPE')
            setCategoryFilter(type)
        } else if (core) {
            setDimension('CORE_TYPE')
            setCategoryFilter(core)
        } else if (mkt) {
            setDimension('MARKET')
            setCategoryFilter(mkt)
        } else if (risk) {
            setDimension('RISK')
            setCategoryFilter(risk)
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

                if (categoryFilter !== 'ALL') {
                    if (dimension === 'ASSET_TYPE') params.asset_type = categoryFilter
                    if (dimension === 'CORE_TYPE') params.core_type = categoryFilter
                    if (dimension === 'MARKET') params.market = categoryFilter
                    if (dimension === 'RISK') params.risk_level = categoryFilter
                }

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
    }, [token, statusFilter, accountFilter, dimension, categoryFilter])

    const filteredPositions = positions

    const toggleExpand = async (id: number, e: React.MouseEvent) => {
        // Stop propagation to prevent row click from triggering twice if button is clicked
        e.stopPropagation()

        if (expandedId === id) {
            setExpandedId(null)
        } else {
            setExpandedId(id)
        }
    }

    const getAccountName = (accountId?: number) => {
        if (!accountId) return '-'
        const account = accounts.find(a => a.id === accountId)
        return account?.name || '-'
    }

    // Helper to get categories for current dimension
    const getCategories = () => {
        switch (dimension) {
            case 'ASSET_TYPE':
                return ['ALL', 'EQUITY', 'ETF_EQUITY', 'ETF_BOND', 'ETF_COMMODITY', 'CRYPTO', 'FOREX']
            case 'CORE_TYPE':
                return ['ALL', 'STOCK', 'FUND', 'BOND', 'COMMODITY', 'FX', 'CRYPTO']
            case 'MARKET':
                return ['ALL', 'US', 'HK', 'A_SHARE', 'CN_OTC', 'FOREX', 'CRYPTO', 'UK']
            case 'RISK':
                return ['ALL', 'CONSERVATIVE', 'MODERATE', 'GROWTH', 'AGGRESSIVE', 'HEDGE']
            default:
                return ['ALL']
        }
    }

    const getCategoryLabel = (cat: string) => {
        if (cat === 'ALL') return '全部'
        switch (dimension) {
            case 'ASSET_TYPE':
                switch (cat) {
                    case 'EQUITY': return '股票'
                    case 'ETF_EQUITY': return '股票ETF'
                    case 'ETF_BOND': return '债券ETF'
                    case 'ETF_COMMODITY': return '商品ETF'
                    case 'CRYPTO': return '加密货币'
                    case 'FOREX': return '外汇'
                    default: return cat
                }
            case 'CORE_TYPE':
                return getCoreTypeLabel(cat as any)
            case 'MARKET':
                return getMarketLabel(cat as any)
            case 'RISK':
                return getRiskLevelInfo(cat as any).label
            default:
                return cat
        }
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
                <Link href="/positions/new" className="btn btn-primary flex items-center">
                    <Plus className="w-4 h-4 mr-1" />
                    新增交易
                </Link>
            </div>

            {/* Dimension Selector */}
            <div className="flex items-center gap-1 p-1 bg-slate-100 dark:bg-slate-800 rounded-xl w-fit">
                {[
                    { id: 'ASSET_TYPE', label: '主要类型' },
                    { id: 'CORE_TYPE', label: '底层类别' },
                    { id: 'MARKET', label: '交易市场' },
                    { id: 'RISK', label: '风险等级' },
                ].map(dim => (
                    <button
                        key={dim.id}
                        onClick={() => {
                            setDimension(dim.id as any)
                            setCategoryFilter('ALL')
                            // Clear URL params
                            router.push('/positions')
                        }}
                        className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-all ${dimension === dim.id
                            ? 'bg-white dark:bg-slate-700 text-slate-900 dark:text-white shadow-sm'
                            : 'text-slate-500 hover:text-slate-700 dark:hover:text-slate-300'
                            }`}
                    >
                        {dim.label}
                    </button>
                ))}
            </div>

            {/* Top Bar with Tabs and Compact Filters */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-200 dark:border-slate-700 pb-0.5">
                {/* Dynamic Tabs */}
                <div className="overflow-x-auto scrollbar-hide">
                    <div className="flex space-x-6 min-w-max">
                        {getCategories().map((cat) => (
                            <button
                                key={cat}
                                onClick={() => {
                                    setCategoryFilter(cat)
                                    const url = new URL(window.location.href)
                                    // Clear other dimension params
                                    url.searchParams.delete('asset_type')
                                    url.searchParams.delete('core_type')
                                    url.searchParams.delete('market')
                                    url.searchParams.delete('risk_level')

                                    if (cat !== 'ALL') {
                                        const param = dimension === 'ASSET_TYPE' ? 'asset_type' :
                                            dimension === 'CORE_TYPE' ? 'core_type' :
                                                dimension === 'MARKET' ? 'market' : 'risk_level'
                                        url.searchParams.set(param, cat)
                                        url.searchParams.set('dimension', dimension)
                                    } else {
                                        url.searchParams.delete('dimension')
                                    }
                                    router.push(`${url.pathname}${url.search}`)
                                }}
                                className={`pb-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap min-w-max px-2 ${categoryFilter === cat
                                    ? 'border-slate-900 text-slate-900 dark:border-white dark:text-white'
                                    : 'border-transparent text-slate-500 hover:text-slate-700 hover:border-slate-300'
                                    }`}
                            >
                                {getCategoryLabel(cat)}
                            </button>
                        ))}
                    </div>
                </div>

                {/* Compact Filters */}
                <div className="flex items-center gap-2 pb-3 md:pb-0">
                    <CustomSelect
                        className="w-32"
                        options={[
                            { value: 'ALL', label: '全部状态' },
                            { value: 'OPEN', label: '持仓中' },
                            { value: 'CLOSED', label: '已平仓' }
                        ]}
                        value={statusFilter}
                        onChange={setStatusFilter}
                    />
                    <CustomSelect
                        className="w-40"
                        options={[
                            { value: 'ALL', label: '全部账户' },
                            ...accounts.map(a => ({ value: a.id, label: a.name }))
                        ]}
                        value={accountFilter}
                        onChange={setAccountFilter}
                    />
                </div>
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
                    <Link href="/positions/new" className="btn btn-primary inline-flex items-center">
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
                                className="p-4 flex flex-col md:flex-row md:items-center justify-between cursor-pointer hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors gap-4"
                                onClick={(e) => toggleExpand(position.id, e)}
                            >
                                <div className="flex items-center gap-4">
                                    <div className={`p-2 rounded-lg ${position.direction === 'LONG'
                                        ? trendColor.upBg
                                        : trendColor.downBg
                                        }`}>
                                        {position.direction === 'LONG'
                                            ? <ArrowUpCircle className="w-5 h-5" />
                                            : <ArrowDownCircle className="w-5 h-5" />
                                        }
                                    </div>

                                    <div>
                                        <div className="flex items-center gap-2">
                                            <span className="font-semibold text-lg">{position.symbol}</span>
                                            <span className={`text-xs px-2 py-0.5 rounded-full ${position.status === 'OPEN'
                                                ? 'bg-slate-100 dark:bg-slate-700 text-slate-900 dark:text-white font-medium border border-slate-200 dark:border-slate-600'
                                                : 'bg-slate-50 dark:bg-slate-800 text-slate-500 border border-transparent'
                                                }`}>
                                                {position.status === 'OPEN' ? '持仓中' : '已平仓'}
                                            </span>
                                        </div>
                                        <p className="text-xs text-slate-500">
                                            {getAccountName(position.account_id)} · {position.exchange}
                                        </p>

                                        {/* Rich Metadata Badges */}
                                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                                            {position.asset_metadata?.market && (
                                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 border border-slate-200 dark:border-slate-700">
                                                    {getMarketLabel(position.asset_metadata.market as AssetMarket)}
                                                </span>
                                            )}
                                            {position.asset_metadata?.sector && (
                                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-800/50">
                                                    {position.asset_metadata.sector}
                                                </span>
                                            )}
                                            {position.asset_metadata?.risk_level && (
                                                <span className={`text-[10px] px-1.5 py-0.5 rounded border ${getRiskLevelInfo(position.asset_metadata.risk_level as AssetRiskLevel).color}`}>
                                                    {getRiskLevelInfo(position.asset_metadata.risk_level as AssetRiskLevel).label}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between md:justify-end gap-2 md:gap-6 w-full md:w-auto mt-2 md:mt-0 pt-2 md:pt-0 border-t md:border-t-0 border-slate-100 dark:border-slate-800 md:border-none">
                                    <div className="text-center md:text-right flex-1 md:flex-none">
                                        <p className="text-xs text-slate-500">数量</p>
                                        <p className="font-medium text-sm md:text-base">
                                            {(() => {
                                                const qty = Number(position.total_quantity)
                                                if (position.asset_type === 'CRYPTO' || position.asset_type === 'FOREX') {
                                                    return qty.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 6 })
                                                }
                                                return qty.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })
                                            })()}
                                        </p>
                                    </div>
                                    <div className="text-center md:text-right flex-1 md:flex-none">
                                        <p className="text-xs text-slate-500">均价</p>
                                        <p className="font-medium text-sm md:text-base">${Number(position.average_entry_price || 0).toFixed(2)}</p>
                                    </div>
                                    <div className="text-center md:text-right flex-1 md:flex-none">
                                        <p className="text-xs text-slate-500">{position.status === 'OPEN' ? '现价' : '出场'}</p>
                                        <p className="font-medium text-sm md:text-base">
                                            {position.current_price
                                                ? `$${Number(position.current_price).toFixed(2)}`
                                                : '-'}
                                        </p>
                                    </div>
                                    <div className="text-right flex-1 md:flex-none">
                                        <p className="text-xs text-slate-500">{position.status === 'OPEN' ? '持仓盈亏' : '已实现盈亏'}</p>
                                        <p className={`font-semibold text-sm md:text-base flex items-center justify-end gap-1 ${(position.status === 'OPEN' ? Number(position.unrealized_pnl || 0) : Number(position.realized_pnl)) >= 0
                                            ? 'text-emerald-500'
                                            : 'text-red-500'
                                            }`}>
                                            {(position.status === 'OPEN' ? Number(position.unrealized_pnl || 0) : Number(position.realized_pnl)) >= 0
                                                ? <TrendingUp className="w-3 h-3 md:w-4 md:h-4" />
                                                : <TrendingDown className="w-3 h-3 md:w-4 md:h-4" />
                                            }
                                            ${Math.abs(position.status === 'OPEN' ? Number(position.unrealized_pnl || 0) : Number(position.realized_pnl)).toFixed(2)}
                                        </p>
                                    </div>
                                    <div className="text-slate-400 pl-2">
                                        <button
                                            type="button"
                                            className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-700 transition"
                                        >
                                            {expandedId === position.id ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {expandedId === position.id && position.batches && (
                                <div className="border-t border-slate-100 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50 p-4">
                                    <div className="flex items-center justify-between mb-3">
                                        <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">交易批次</h3>
                                        <div className="flex items-center gap-2">
                                            <Link
                                                href={`/positions/${position.id}/add-batch?type=ENTRY`}
                                                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-900/20 text-xs font-medium text-emerald-600 dark:text-emerald-400 hover:bg-emerald-100 dark:hover:bg-emerald-900/30 transition-all shadow-sm active:scale-95"
                                            >
                                                <ArrowUpCircle className="w-3.5 h-3.5" />
                                                <span>加仓</span>
                                            </Link>
                                            <Link
                                                href={`/positions/${position.id}/add-batch?type=EXIT`}
                                                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-900/20 text-xs font-medium text-amber-600 dark:text-amber-400 hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-all shadow-sm active:scale-95"
                                            >
                                                <ArrowDownCircle className="w-3.5 h-3.5" />
                                                <span>减仓</span>
                                            </Link>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        {position.batches.map((batch: TradeBatch) => (
                                            <div
                                                key={batch.id}
                                                className="p-3 rounded-lg bg-white dark:bg-slate-800 border border-slate-100 dark:border-slate-700 hover:shadow-sm transition-shadow"
                                            >
                                                <div className="flex items-center justify-between mb-2">
                                                    <div className="flex items-center gap-3">
                                                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${batch.type === 'ENTRY'
                                                            ? trendColor.upBg
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
                                                        <span className="font-mono">${Number(batch.price).toFixed(2)}</span>
                                                        <span className="text-slate-500">x {(() => {
                                                            const bQty = Number(batch.quantity)
                                                            if (position.asset_type === 'CRYPTO' || position.asset_type === 'FOREX') {
                                                                return bQty.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 6 })
                                                            }
                                                            return bQty.toLocaleString(undefined, { minimumFractionDigits: 0, maximumFractionDigits: 2 })
                                                        })()}</span>
                                                        {batch.pnl !== null && batch.pnl !== undefined && (
                                                            <span className={`font-medium ${Number(batch.pnl) >= 0 ? trendColor.upColor : trendColor.downColor}`}>
                                                                {Number(batch.pnl) >= 0 ? '+' : ''}{Number(batch.pnl).toFixed(2)}
                                                            </span>
                                                        )}
                                                    </div>
                                                </div>

                                                {/* Emotion & Reason Row */}
                                                {(batch.emotion || batch.reason || batch.confidence) && (
                                                    <div className="flex flex-wrap items-start gap-3 pt-2 border-t border-slate-100 dark:border-slate-700/50 mt-2 text-xs">
                                                        {batch.emotion && (
                                                            <span className="px-1.5 py-0.5 rounded bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 border border-purple-100 dark:border-purple-800/50">
                                                                Mood: {batch.emotion}
                                                            </span>
                                                        )}
                                                        {batch.confidence && (
                                                            <span className="px-1.5 py-0.5 rounded bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 border border-blue-100 dark:border-blue-800/50">
                                                                Conf: {batch.confidence}/5
                                                            </span>
                                                        )}
                                                        {batch.reason && (
                                                            <span className="text-slate-600 dark:text-slate-400 flex-1 leading-relaxed">
                                                                {batch.reason}
                                                            </span>
                                                        )}
                                                    </div>
                                                )}
                                            </div>
                                        ))}
                                    </div>
                                    <div className="mt-4 flex justify-end">
                                        <Link
                                            href={`/positions/${position.id}`}
                                            className="flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-900 dark:bg-white text-white dark:text-slate-900 text-xs font-semibold hover:opacity-90 transition-all active:scale-95 shadow-md shadow-slate-200 dark:shadow-none"
                                        >
                                            <span>查看详情</span>
                                            <ArrowRight className="w-3.5 h-3.5" />
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
