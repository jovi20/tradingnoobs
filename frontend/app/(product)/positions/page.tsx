'use client'

import { useState, useEffect, useMemo } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
    Plus,
    TrendingUp,
    TrendingDown,
    Loader2,
    ChevronDown,
    ChevronUp,
    ArrowUpCircle,
    ArrowDownCircle,
    ArrowRight
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { TradeBatch } from '@/lib/api'
import { PositionViewModel } from '@/lib/adapters/trading'
import { useTrendColor } from '@/hooks/useTrendColor'
import CustomSelect from '@/components/CustomSelect'
import {
    getMarketLabel, getCoreTypeLabel,
    AssetMarket,
    ALL_ASSET_CORE_TYPES, ALL_ASSET_MARKETS,
    getCurrencySymbol
} from '@/lib/symbolUtils'
import { usePositionsData } from '@/hooks/usePositionsData'

type PositionDimension = 'CORE_TYPE' | 'MARKET'

interface SearchParamReader {
    get(name: string): string | null
}

interface PositionUrlFilters {
    dimension: PositionDimension
    categoryFilter: string
}

const DEFAULT_POSITION_URL_FILTERS: PositionUrlFilters = {
    dimension: 'CORE_TYPE',
    categoryFilter: 'ALL',
}

function isPositionDimension(value: string | null): value is PositionDimension {
    return value === 'CORE_TYPE' || value === 'MARKET'
}

function readPositionUrlFilters(searchParams: SearchParamReader): PositionUrlFilters | null {
    const core = searchParams.get('core_type')
    const market = searchParams.get('market')
    const dimension = searchParams.get('dimension')

    if (core) return { dimension: 'CORE_TYPE', categoryFilter: core }
    if (market) return { dimension: 'MARKET', categoryFilter: market }
    if (isPositionDimension(dimension)) return { dimension, categoryFilter: 'ALL' }
    return null
}

export default function PositionsPage() {
    const { token } = useAuth()
    const trendColor = useTrendColor()
    const searchParams = useSearchParams()
    const router = useRouter()
    const initialUrlFilters = readPositionUrlFilters(searchParams) ?? DEFAULT_POSITION_URL_FILTERS

    // Filters
    const [statusFilter, setStatusFilter] = useState<'ALL' | 'OPEN' | 'CLOSED'>('ALL')
    const [accountFilter, setAccountFilter] = useState<number | 'ALL'>('ALL')

    // Multi-dimensional filters
    const [dimension, setDimension] = useState<PositionDimension>(initialUrlFilters.dimension)
    const [categoryFilter, setCategoryFilter] = useState<string>(initialUrlFilters.categoryFilter)
    const [currentTime, setCurrentTime] = useState<number | null>(null)

    // URL params for linking from dashboard
    useEffect(() => {
        const nextFilters = readPositionUrlFilters(searchParams)
        if (!nextFilters) return

        const syncTimer = window.setTimeout(() => {
            setDimension(nextFilters.dimension)
            setCategoryFilter(nextFilters.categoryFilter)
        }, 0)
        return () => window.clearTimeout(syncTimer)
    }, [searchParams])

    useEffect(() => {
        const updateCurrentTime = () => setCurrentTime(Date.now())
        const startTimer = window.setTimeout(updateCurrentTime, 0)
        const intervalTimer = window.setInterval(updateCurrentTime, 60000)

        return () => {
            window.clearTimeout(startTimer)
            window.clearInterval(intervalTimer)
        }
    }, [])

    // Use custom hook for data fetching
    const { positions, accounts, isLoading, error } = usePositionsData({
        token,
        statusFilter,
        accountFilter,
        dimension,
        categoryFilter
    })

    // Expanded position for batch view
    const [expandedId, setExpandedId] = useState<number | null>(null)

    const filteredPositions = useMemo(() => {
        return positions
    }, [positions])

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

    const formatHoldingTime = (position: PositionViewModel, now: number | null) => {
        const start = new Date(position.opened_at).getTime()
        const end = position.status === 'CLOSED' && position.closed_at
            ? new Date(position.closed_at).getTime()
            : now
        if (end === null) return '-'

        const diffMs = end - start
        if (diffMs < 0) return '-'

        const minutes = Math.floor(diffMs / 60000)
        const hours = Math.floor(diffMs / 3600000)
        const days = Math.floor(diffMs / 86400000)
        const months = Math.floor(days / 30)
        const remainDays = days % 30

        if (minutes < 60) return `${minutes}分钟`
        if (hours < 24) return `${hours}小时`
        if (days < 30) return `${days}天`
        return remainDays > 0 ? `${months}个月${remainDays}天` : `${months}个月`
    }

    // Helper to get categories for current dimension
    const getCategories = () => {
        switch (dimension) {
            case 'CORE_TYPE':
                return ['ALL', ...ALL_ASSET_CORE_TYPES]
            case 'MARKET':
                return ['ALL', ...ALL_ASSET_MARKETS]
            default:
                return ['ALL']
        }
    }

    const getCategoryLabel = (cat: string) => {
        if (cat === 'ALL') return '全部'
        switch (dimension) {
            case 'CORE_TYPE':
                return getCoreTypeLabel(cat as any)
            case 'MARKET':
                return getMarketLabel(cat as any)
            default:
                return cat
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-ink-muted" />
            </div>
        )
    }

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold">交易记录</h1>
                <div className="flex gap-2">
                    <Link href="/positions/new" className="btn btn-primary flex items-center">
                        <Plus className="w-4 h-4 mr-1" />
                        新增交易
                    </Link>
                </div>
            </div>

            {/* Dimension Selector */}
            <div className="flex items-center gap-1 p-1 bg-panel-subtle rounded-md w-fit">
                {[
                    { id: 'CORE_TYPE', label: '底层类别' },
                    { id: 'MARKET', label: '交易市场' },
                ].map(dim => (
                    <button
                        key={dim.id}
                        onClick={() => {
                            setDimension(dim.id as any)
                            setCategoryFilter('ALL')
                            // Clear URL params
                            router.push('/positions')
                        }}
                        className={`px-4 py-1.5 rounded-lg text-xs font-semibold transition-colors ${dimension === dim.id
                            ? 'bg-panel text-ink shadow-sm'
                            : 'text-ink-muted hover:text-ink'
                            }`}
                    >
                        {dim.label}
                    </button>
                ))}
            </div>

            {/* Top Bar with Tabs and Compact Filters */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-line pb-0.5">
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

                                    if (cat !== 'ALL') {
                                        const param = dimension === 'CORE_TYPE' ? 'core_type' : 'market'
                                        url.searchParams.set(param, cat)
                                        url.searchParams.set('dimension', dimension)
                                    } else {
                                        url.searchParams.delete('dimension')
                                    }
                                    router.push(`${url.pathname}${url.search}`)
                                }}
                                className={`pb-3 text-sm font-medium border-b-2 transition-colors whitespace-nowrap min-w-max px-2 ${categoryFilter === cat
                                    ? 'border-ink text-ink'
                                    : 'border-transparent text-ink-muted hover:text-ink-soft hover:border-line-strong'
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
                <div className="p-4 rounded-md bg-loss/8 dark:bg-loss/8 text-loss">
                    {error}
                </div>
            )}

            {/* Position List */}
            {filteredPositions.length === 0 ? (
                <div className="card p-12 text-center">
                    <p className="text-ink-muted mb-4">暂无交易记录</p>
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
                                className="p-4 flex flex-col md:flex-row md:items-center justify-between cursor-pointer hover:bg-panel-subtle/50 transition-colors gap-4"
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
                                                ? 'bg-panel-subtle text-ink font-medium border border-line-strong'
                                                : 'bg-panel-subtle text-ink-muted border border-transparent'
                                                }`}>
                                                {position.status === 'OPEN' ? '持仓中' : '已平仓'}
                                            </span>
                                        </div>
                                        <p className="text-xs text-ink-muted">
                                            {getAccountName(position.account_id)} · {position.exchange}
                                        </p>

                                        {/* Rich Metadata Badges */}
                                        <div className="flex flex-wrap gap-1.5 mt-1.5">
                                            {position.asset_metadata?.market && (
                                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-panel-subtle text-ink-muted border border-line">
                                                    {getMarketLabel(position.asset_metadata.market as AssetMarket)}
                                                </span>
                                            )}
                                            {position.asset_metadata?.sector && (
                                                <span className="text-[10px] px-1.5 py-0.5 rounded bg-ai/8 dark:bg-ai/8 text-ai dark:text-ai border border-ai/30 dark:border-ai/30/50">
                                                    {position.asset_metadata.sector}
                                                </span>
                                            )}
                                        </div>
                                    </div>
                                </div>

                                <div className="flex items-center justify-between md:justify-end gap-2 md:gap-6 w-full md:w-auto mt-2 md:mt-0 pt-2 md:pt-0 border-t md:border-t-0 border-line md:border-none">
                                    <div className="text-center md:text-right flex-1 md:flex-none">
                                        <p className="text-xs text-ink-muted">持仓时间</p>
                                        <p className="font-medium text-sm md:text-base text-ink-soft">
                                            {formatHoldingTime(position, currentTime)}
                                        </p>
                                    </div>
                                    <div className="text-center md:text-right flex-1 md:flex-none">
                                        <p className="text-xs text-ink-muted">数量</p>
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
                                        <p className="text-xs text-ink-muted">均价</p>
                                        <p className="font-medium text-sm md:text-base">{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.average_entry_price || 0).toFixed(2)}</p>
                                    </div>
                                    <div className="text-right flex-1 md:flex-none">
                                        <p className="text-xs text-ink-muted">已实现盈亏</p>
                                        <p className={`font-semibold text-sm md:text-base flex items-center justify-end gap-1 ${Number(position.realized_pnl || 0) >= 0
                                            ? 'text-profit'
                                            : 'text-loss'
                                            }`}>
                                            {Number(position.realized_pnl || 0) >= 0
                                                ? <TrendingUp className="w-3 h-3 md:w-4 md:h-4" />
                                                : <TrendingDown className="w-3 h-3 md:w-4 md:h-4" />
                                            }
                                            {getCurrencySymbol(position.asset_metadata?.currency)}{Math.abs(Number(position.realized_pnl || 0)).toFixed(2)}
                                        </p>
                                    </div>
                                    <div className="text-ink-faint pl-2">
                                        <button
                                            type="button"
                                            onClick={(e) => toggleExpand(position.id, e)}
                                            aria-expanded={expandedId === position.id}
                                            aria-controls={`position-batches-${position.id}`}
                                            aria-label={`${expandedId === position.id ? '收起' : '展开'} ${position.symbol} 的旧版批次记录`}
                                            title={`${expandedId === position.id ? '收起' : '展开'} ${position.symbol} 的旧版批次记录`}
                                            className="p-1 rounded hover:bg-panel-subtle transition"
                                        >
                                            {expandedId === position.id ? <ChevronUp className="w-5 h-5" /> : <ChevronDown className="w-5 h-5" />}
                                        </button>
                                    </div>
                                </div>
                            </div>

                            {expandedId === position.id && position.batches && (
                                <div id={`position-batches-${position.id}`} className="border-t border-line bg-panel-subtle/50 p-4">
                                    <div className="flex items-start justify-between gap-4 mb-3">
                                        <div>
                                            <h3 className="text-sm font-semibold text-ink-soft">旧版批次记录</h3>
                                            <p className="mt-1 text-xs text-ink-muted">
                                                仅供迁移和排查使用；日常加仓、减仓和平仓均写入审计事件。
                                            </p>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <Link
                                                href={`/positions/${position.routeId}/add-batch?type=ENTRY`}
                                                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-profit/30 dark:border-profit/30 bg-profit/8 dark:bg-profit/8 text-xs font-medium text-profit dark:text-profit hover:bg-profit/8 dark:hover:bg-profit/8 transition-colors shadow-sm"
                                            >
                                                <ArrowUpCircle className="w-3.5 h-3.5" />
                                                <span>记录加仓</span>
                                            </Link>
                                            <Link
                                                href={`/positions/${position.routeId}/add-batch?type=EXIT`}
                                                className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-warning/30 dark:border-warning/30 bg-warning/8 dark:bg-warning/8 text-xs font-medium text-warning dark:text-warning hover:bg-warning/8 dark:hover:bg-warning/8 transition-colors shadow-sm"
                                            >
                                                <ArrowDownCircle className="w-3.5 h-3.5" />
                                                <span>记录减仓或平仓</span>
                                            </Link>
                                        </div>
                                    </div>
                                    <div className="space-y-2">
                                        {position.batches.map((batch: TradeBatch) => (
                                            <div
                                                key={batch.id}
                                                className="p-3 rounded-lg bg-panel border border-line hover:shadow-sm transition-shadow"
                                            >
                                                <div className="flex items-center justify-between mb-2">
                                                    <div className="flex items-center gap-3">
                                                        <span className={`text-xs font-medium px-2 py-0.5 rounded ${batch.type === 'ENTRY'
                                                            ? trendColor.upBg
                                                            : 'bg-warning/8 text-warning'
                                                            }`}>
                                                            {batch.type === 'ENTRY' ? '加仓' : '平仓'}
                                                        </span>
                                                        <span className="text-sm text-ink-muted">
                                                            {new Date(batch.time).toLocaleString('zh-CN', {
                                                                month: 'short',
                                                                day: 'numeric',
                                                                hour: '2-digit',
                                                                minute: '2-digit'
                                                            })}
                                                        </span>
                                                    </div>
                                                    <div className="flex items-center gap-4 text-sm">
                                                        <span className="font-mono">{getCurrencySymbol(position.asset_metadata?.currency)}{Number(batch.price).toFixed(2)}</span>
                                                        <span className="text-ink-muted">x {(() => {
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
                                                    <div className="flex flex-wrap items-start gap-3 pt-2 border-t border-line/50 mt-2 text-xs">
                                                        {batch.emotion && (
                                                            <span className="px-1.5 py-0.5 rounded bg-purple-50 dark:bg-purple-900/20 text-purple-600 dark:text-purple-400 border border-purple-100 dark:border-purple-800/50">
                                                                情绪：{batch.emotion}
                                                            </span>
                                                        )}
                                                        {batch.confidence && (
                                                            <span className="px-1.5 py-0.5 rounded bg-ai/8 dark:bg-ai/8 text-ai dark:text-ai border border-ai/30 dark:border-ai/30/50">
                                                                信心度：{batch.confidence}/5
                                                            </span>
                                                        )}
                                                        {batch.reason && (
                                                            <span className="text-ink-muted flex-1 leading-relaxed">
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
                                            href={`/positions/${position.routeId}`}
                                            className="flex items-center gap-1.5 px-4 py-2 rounded-md bg-ink dark:bg-panel text-white dark:text-ink text-xs font-semibold hover:opacity-90 transition-colors"
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
