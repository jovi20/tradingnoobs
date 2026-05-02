'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams } from 'next/navigation'
import Link from 'next/link'
import {
    ArrowLeft,
    Loader2,
    TrendingUp,
    TrendingDown,
    ArrowUpCircle,
    ArrowDownCircle,
    Plus,
    Trash2,
    Edit3,
    Calendar,
    DollarSign,
    Target,
    MessageSquare,
    Award
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { positionsAPI } from '@/lib/api'
import { adaptPosition, PositionViewModel, TradeBatchViewModel } from '@/lib/adapters/trading'
import { adaptLifecycleDetail, LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'
import { TruthLifecycleDetail } from '@/components/positions/domain/TruthLifecycleDetail'

import {
    getCoreTypeLabel,
    getMarketLabel,
    getRiskLevelInfo,
    AssetCoreType,
    AssetMarket,
    AssetRiskLevel,
    ALL_ASSET_CORE_TYPES,
    ALL_ASSET_MARKETS,
    ALL_ASSET_RISK_LEVELS,
    getCurrencySymbol
} from '@/lib/symbolUtils'
import CustomSelect from '@/components/CustomSelect'
import DateTimePicker from '@/components/DateTimePicker'

export default function PositionDetailPage() {
    const { token } = useAuth()
    const router = useRouter()
    const params = useParams()
    const positionId = params.id as string

    const [position, setPosition] = useState<PositionViewModel | null>(null)
    const [truthLifecycle, setTruthLifecycle] = useState<LifecycleDetailViewModel | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState('')
    const [isDeleting, setIsDeleting] = useState(false)

    // Batch Edit State
    const [editingBatch, setEditingBatch] = useState<TradeBatchViewModel | null>(null)
    const [isSavingBatch, setIsSavingBatch] = useState(false)
    const [editForm, setEditForm] = useState({
        price: 0,
        quantity: 0,
        time: '',
        reason: '',
        confidence: 3
    })

    // Metadata Edit State
    const [editingMetadata, setEditingMetadata] = useState(false)
    const [isSavingMetadata, setIsSavingMetadata] = useState(false)
    const [hasAttemptedSave, setHasAttemptedSave] = useState(false) // New: Fix potential infinite loop or double submission
    const [metadataForm, setMetadataForm] = useState({
        core_type: 'STOCK',
        market: 'US',
        sector: '',
        risk_level: 'MODERATE',
        instrument: 'Spot'
    })

    // Extremes Edit State
    const [editingExtremes, setEditingExtremes] = useState(false)
    const [isSavingExtremes, setIsSavingExtremes] = useState(false)
    const [isAnalyzing, setIsAnalyzing] = useState(false)
    const [extremesForm, setExtremesForm] = useState({
        max_price: 0,
        min_price: 0
    })

    useEffect(() => {
        const fetchPosition = async () => {
            if (!token || !positionId) return
            try {
                const directTruthData = await positionsAPI.getTradingPositionLifecycle(token, positionId).catch(() => null)
                if (directTruthData) {
                    setTruthLifecycle(adaptLifecycleDetail(directTruthData))
                    const legacyData = await positionsAPI.get(token, positionId).catch(() => null)
                    setPosition(legacyData ? adaptPosition(legacyData) : null)
                    setError('')
                    return
                }

                const data = await positionsAPI.get(token, positionId)
                const truthData = await positionsAPI.getTruthLifecycle(token, positionId).catch(() => null)
                setPosition(adaptPosition(data))
                setTruthLifecycle(truthData ? adaptLifecycleDetail(truthData) : null)
                setError('')
            } catch (err: any) {
                setError(err.message || '加载失败')
            } finally {
                setIsLoading(false)
            }
        }
        fetchPosition()
    }, [token, positionId])

    const handleDelete = async () => {
        if (!token || !position) return
        if (!window.confirm('确定要删除这个交易记录吗？所有相关的交易批次也会被删除。')) return

        setIsDeleting(true)
        try {
            await positionsAPI.delete(token, position.routeId)
            router.push('/positions')
        } catch (err: any) {
            setError(err.message || '删除失败')
            setIsDeleting(false)
        }
    }

    const openEditModal = (batch: TradeBatchViewModel) => {
        setEditingBatch(batch)
        setEditForm({
            price: Number(batch.price),
            quantity: Number(batch.quantity),
            time: new Date(batch.time).toISOString(), // Use full ISO for DateTimePicker
            reason: batch.reason || '',
            confidence: batch.confidence || 3
        })
    }

    const handleUpdateBatch = async () => {
        if (!token || !editingBatch || !position) return
        setIsSavingBatch(true)
        try {
            await positionsAPI.updateBatch(token, editingBatch.routeId, {
                price: editForm.price,
                quantity: editForm.quantity,
                time: new Date(editForm.time).toISOString(),
                reason: editForm.reason,
                confidence: editForm.confidence
            })
            // Refresh position data
            const [updated, truthData] = await Promise.all([
                positionsAPI.get(token, position.routeId),
                positionsAPI.getTruthLifecycle(token, position.routeId).catch(() => null),
            ])
            setPosition(adaptPosition(updated))
            setTruthLifecycle(truthData ? adaptLifecycleDetail(truthData) : null)
            setEditingBatch(null)
        } catch (err: any) {
            alert(err.message || '更新失败')
        } finally {
            setIsSavingBatch(false)
        }
    }

    const openMetadataModal = () => {
        if (!position?.asset_metadata) return
        setMetadataForm({
            core_type: position.asset_metadata.core_type || 'STOCK',
            market: position.asset_metadata.market || 'US',
            sector: position.asset_metadata.sector || '',
            risk_level: position.asset_metadata.risk_level || 'MODERATE',
            instrument: position.asset_metadata.instrument || 'Spot'
        })
        setEditingMetadata(true)
    }

    const handleUpdateMetadata = async () => {
        if (!token || !position) return

        setIsSavingMetadata(true)
        try {
            // Using a specialized endpoint or general update endpoint
            // Currently using generic update which might need to handle nested metadata
            // Assuming backend supports accepting flat metadata fields in PositionUpdate or we need to call a metadata endpoint
            // BUT implementation plan says: Enhance `update_position` to allow updating `asset_metadata`.
            // So we pass metadata in the body.

            await positionsAPI.update(token, position.routeId, {
                asset_metadata: {
                    core_type: metadataForm.core_type,
                    market: metadataForm.market,
                    sector: metadataForm.sector,
                    risk_level: metadataForm.risk_level,
                    instrument: metadataForm.instrument
                }
            })

            const [updated, truthData] = await Promise.all([
                positionsAPI.get(token, position.routeId),
                positionsAPI.getTruthLifecycle(token, position.routeId).catch(() => null),
            ])
            setPosition(adaptPosition(updated))
            setTruthLifecycle(truthData ? adaptLifecycleDetail(truthData) : null)
            setEditingMetadata(false)
        } catch (err: any) {
            alert(err.message || '更新失败')
        } finally {
            setIsSavingMetadata(false)
        }
    }

    const handleAnalyze = async () => {
        if (!token || !position) return
        setIsAnalyzing(true)
        try {
            const [updated, truthData] = await Promise.all([
                positionsAPI.analyze(token, position.routeId),
                positionsAPI.getTruthLifecycle(token, position.routeId).catch(() => null),
            ])
            setPosition(adaptPosition(updated))
            setTruthLifecycle(truthData ? adaptLifecycleDetail(truthData) : null)
        } catch (err: any) {
            alert(err.message || '分析失败')
        } finally {
            setIsAnalyzing(false)
        }
    }

    const handleUpdateExtremes = async () => {
        if (!token || !position) return
        setIsSavingExtremes(true)
        try {
            await positionsAPI.update(token, position.routeId, {
                max_price_during_hold: extremesForm.max_price,
                min_price_during_hold: extremesForm.min_price
            })
            const [updated, truthData] = await Promise.all([
                positionsAPI.get(token, position.routeId),
                positionsAPI.getTruthLifecycle(token, position.routeId).catch(() => null),
            ])
            setPosition(adaptPosition(updated))
            setTruthLifecycle(truthData ? adaptLifecycleDetail(truthData) : null)
            setEditingExtremes(false)
        } catch (err: any) {
            alert(err.message || '更新失败')
        } finally {
            setIsSavingExtremes(false)
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (error || (!position && !truthLifecycle)) {
        return (
            <div className="card p-8 text-center">
                <p className="text-red-500 mb-4">{error || '持仓不存在'}</p>
                <Link href="/positions" className="btn btn-secondary">
                    返回列表
                </Link>
            </div>
        )
    }

    const displayTitle = truthLifecycle?.assetSymbol || position?.symbol || ''
    const displayStatus = truthLifecycle?.positionStatus || position?.status || 'CLOSED'
    const displaySide = truthLifecycle?.side || position?.direction || 'LONG'
    const displaySubtitle = truthLifecycle
        ? `${truthLifecycle.instrumentLabel} · ${truthLifecycle.accountLabel}`
        : `${position?.exchange} · ${displaySide === 'LONG' ? '做多' : '做空'}`
    const realizedPnl = truthLifecycle?.realizedPnlNet ?? position?.realized_pnl ?? 0
    const isPositive = Number(realizedPnl) >= 0
    const isOpen = displayStatus === 'OPEN'

    // Sort batches by time
    const sortedBatches = [...(position?.batches || [])].sort(
        (a, b) => new Date(a.time).getTime() - new Date(b.time).getTime()
    )

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* Header */}
            <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0 flex-1">
                    <Link
                        href="/positions"
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800 shrink-0"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div className="min-w-0">
                        <h1 className="text-xl md:text-2xl font-bold flex items-center gap-2">
                            <span className="truncate">{displayTitle}</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${isOpen
                                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                                }`}>
                                {isOpen ? '持仓中' : '已平仓'}
                            </span>
                        </h1>
                        <p className="text-sm text-slate-500 truncate">
                            {displaySubtitle}
                        </p>
                    </div>
                </div>
                <div className="flex gap-2 shrink-0">
                    {position && isOpen && (
                        <Link
                            href={`/positions/${position.routeId}/add-batch`}
                            className="btn btn-primary flex items-center gap-1 px-3 md:px-4"
                        >
                            <Plus className="w-4 h-4" />
                            <span className="hidden sm:inline">加/平仓</span>
                        </Link>
                    )}
                    <button
                        onClick={handleDelete}
                        disabled={isDeleting || !position}
                        className="btn btn-danger flex items-center gap-1 px-3 md:px-4"
                    >
                        {isDeleting ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Trash2 className="w-4 h-4" />
                        )}
                        <span className="hidden sm:inline">删除</span>
                    </button>
                </div>
            </div>

            {truthLifecycle && (
                <TruthLifecycleDetail lifecycle={truthLifecycle} />
            )}

            {!position && truthLifecycle && (
                <div className="card border-emerald-200 bg-emerald-50 p-5 text-sm text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-200">
                    当前详情由 TradingPosition truth read model 直接驱动。旧 Position 编辑控件未显示，避免把新真相路径重新绑回 legacy DTO。
                </div>
            )}

            {position && (
                <>

            {/* Summary Card */}
            <div className="card overflow-hidden">
                <div className="grid grid-cols-2 lg:grid-cols-5 gap-0 divide-x divide-y lg:divide-y-0 divide-slate-100 dark:divide-slate-700">
                    <div className="p-4 lg:p-6">
                        <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider font-semibold">持仓数量</p>
                        <p className="text-xl font-bold">{Number(position.total_quantity).toLocaleString()}</p>
                    </div>
                    <div className="p-4 lg:p-6">
                        <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider font-semibold">均价 / 当前价</p>
                        <p className="text-xl font-bold">
                            {getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.average_entry_price || 0).toFixed(2)}
                            {position.current_price && (
                                <span className="text-sm font-normal ml-2 text-slate-400">
                                    → {getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.current_price).toFixed(2)}
                                </span>
                            )}
                        </p>
                    </div>
                    <div className="p-4 lg:p-6">
                        <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider font-semibold">已实现盈亏</p>
                        <p className={`text-xl font-bold ${isPositive ? 'pnl-positive' : 'pnl-negative'}`}>
                            {isPositive ? '+' : ''}{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.realized_pnl).toFixed(2)}
                        </p>
                    </div>
                    {position.status === 'OPEN' && (
                        <div className="p-4 lg:p-6 bg-slate-50/50 dark:bg-slate-800/30">
                            <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider font-semibold">未实现盈亏</p>
                            <p className={`text-xl font-bold ${(position.unrealized_pnl || 0) >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                {(position.unrealized_pnl || 0) >= 0 ? '+' : ''}{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.unrealized_pnl || 0).toFixed(2)}
                            </p>
                        </div>
                    )}
                    <div className="p-4 lg:p-6">
                        <p className="text-xs text-slate-500 mb-1 uppercase tracking-wider font-semibold">开仓日期</p>
                        <p className="text-lg font-medium">
                            {new Date(position.opened_at).toLocaleDateString('zh-CN')}
                        </p>
                    </div>
                </div>
            </div>

            {/* Metadata Card */}
            {position.asset_metadata && (
                <div className="card p-5 relative group">
                    <button
                        onClick={openMetadataModal}
                        className="absolute top-4 right-4 p-2 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-500 transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                        title="编辑属性"
                    >
                        <Edit3 className="w-4 h-4" />
                    </button>

                    <h2 className="text-sm font-bold text-slate-400 mb-4 uppercase tracking-wider flex items-center">
                        <Target className="w-4 h-4 mr-2" />
                        资产属性
                    </h2>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                        <div>
                            <p className="text-xs text-slate-500 mb-1">资产类型</p>
                            <p className="font-semibold flex items-center">
                                {getCoreTypeLabel(position.asset_metadata.core_type as AssetCoreType)}
                                <span className="mx-1 text-slate-300">/</span>
                                <span className="text-sm font-normal text-slate-600 dark:text-slate-400">{position.asset_metadata.instrument}</span>
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-slate-500 mb-1">交易市场</p>
                            <p className="font-semibold flex items-center">
                                {getMarketLabel(position.asset_metadata.market as AssetMarket)}
                                <span className="ml-2 text-xs bg-slate-100 dark:bg-slate-800 px-1.5 py-0.5 rounded text-slate-500">
                                    {position.asset_metadata.currency}
                                </span>
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-slate-500 mb-1">所属板块</p>
                            <p className="font-semibold">{position.asset_metadata.sector || '未分类'}</p>
                        </div>
                        <div>
                            <p className="text-xs text-slate-500 mb-1">风险评级</p>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getRiskLevelInfo(position.asset_metadata.risk_level as AssetRiskLevel).color}`}>
                                {getRiskLevelInfo(position.asset_metadata.risk_level as AssetRiskLevel).label}
                            </span>
                        </div>
                    </div>
                </div>
            )}

            {/* Price Extremes & MAE/MFE Card */}
            <div className="card p-5 relative group">
                <button
                    onClick={() => {
                        setExtremesForm({
                            max_price: Number(position.max_price_during_hold || 0),
                            min_price: Number(position.min_price_during_hold || 0)
                        })
                        setEditingExtremes(true)
                    }}
                    className="absolute top-4 right-14 p-2 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-500 transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                    title="手动修改极值"
                >
                    <Edit3 className="w-4 h-4" />
                </button>
                <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                    <button
                        onClick={handleAnalyze}
                        disabled={isAnalyzing}
                        className="p-2 rounded-lg bg-indigo-50 hover:bg-indigo-100 dark:bg-indigo-900/30 dark:hover:bg-indigo-900/50 text-indigo-600 dark:text-indigo-400"
                        title="自动分析 (从历史数据)"
                    >
                        {isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <TrendingUp className="w-4 h-4" />}
                    </button>
                </div>

                <h2 className="text-sm font-bold text-slate-400 mb-4 uppercase tracking-wider flex items-center">
                    <TrendingUp className="w-4 h-4 mr-2" />
                    价格极值 (MAE/MFE)
                </h2>

                <div className="grid grid-cols-2 gap-6">
                    <div>
                        <p className="text-xs text-slate-500 mb-1">持仓期最高 (Max Price)</p>
                        <p className="font-semibold text-lg flex items-center">
                            {position.max_price_during_hold ? (
                                <span>{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.max_price_during_hold).toFixed(2)}</span>
                            ) : (
                                <span className="text-slate-300">-</span>
                            )}
                        </p>
                        {position.average_entry_price && position.max_price_during_hold && (
                            <p className={`text-xs mt-1 ${position.direction === 'LONG' ? 'text-emerald-500' : 'text-red-500'}`}>
                                {position.direction === 'LONG' ? 'MFE' : 'MAE'}: {((Number(position.max_price_during_hold) - Number(position.average_entry_price)) / Number(position.average_entry_price) * 100).toFixed(2)}%
                            </p>
                        )}
                    </div>
                    <div>
                        <p className="text-xs text-slate-500 mb-1">持仓期最低 (Min Price)</p>
                        <p className="font-semibold text-lg flex items-center">
                            {position.min_price_during_hold ? (
                                <span>{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.min_price_during_hold).toFixed(2)}</span>
                            ) : (
                                <span className="text-slate-300">-</span>
                            )}
                        </p>
                        {position.average_entry_price && position.min_price_during_hold && (
                            <p className={`text-xs mt-1 ${position.direction === 'LONG' ? 'text-red-500' : 'text-emerald-500'}`}>
                                {position.direction === 'LONG' ? 'MAE' : 'MFE'}: {((Number(position.min_price_during_hold) - Number(position.average_entry_price)) / Number(position.average_entry_price) * 100).toFixed(2)}%
                            </p>
                        )}
                    </div>
                </div>
            </div>

            {/* Phase 1: Plan Drift Analysis Card */}
            {position.drift_analysis?.has_planned_data && (
                <div className="card p-5">
                    <h2 className="text-sm font-bold text-slate-400 mb-4 uppercase tracking-wider flex items-center">
                        📊 计划执行对比
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {/* Planned Entry */}
                        <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                            <p className="text-xs text-slate-500 mb-1">计划入场价</p>
                            <p className="font-semibold">{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.planned_entry_price || 0).toFixed(2)}</p>
                        </div>
                        {/* Actual Entry */}
                        <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                            <p className="text-xs text-slate-500 mb-1">实际入场价</p>
                            <p className="font-semibold">{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.average_entry_price || 0).toFixed(2)}</p>
                        </div>
                        {/* Entry Drift */}
                        <div className={`p-3 rounded-lg ${position.drift_analysis.execution_quality === 'excellent' ? 'bg-emerald-50 dark:bg-emerald-900/20' :
                            position.drift_analysis.execution_quality === 'good' ? 'bg-blue-50 dark:bg-blue-900/20' :
                                position.drift_analysis.execution_quality === 'fair' ? 'bg-amber-50 dark:bg-amber-900/20' :
                                    'bg-red-50 dark:bg-red-900/20'
                            }`}>
                            <p className="text-xs text-slate-500 mb-1">入场偏移</p>
                            <p className={`font-semibold ${Math.abs(position.drift_analysis.entry_drift_pct || 0) <= 2 ? 'text-emerald-600' :
                                Math.abs(position.drift_analysis.entry_drift_pct || 0) <= 5 ? 'text-amber-600' : 'text-red-600'
                                }`}>
                                {(position.drift_analysis.entry_drift_pct || 0) > 0 ? '+' : ''}{position.drift_analysis.entry_drift_pct}%
                                <span className="text-xs ml-1 text-slate-500">
                                    ({position.drift_analysis.entry_drift_direction === 'above' ? '高于计划' :
                                        position.drift_analysis.entry_drift_direction === 'below' ? '低于计划' : '命中'})
                                </span>
                            </p>
                        </div>
                        {/* Execution Quality */}
                        <div className="p-3 bg-slate-50 dark:bg-slate-800/50 rounded-lg">
                            <p className="text-xs text-slate-500 mb-1">执行质量</p>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${position.drift_analysis.execution_quality === 'excellent' ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400' :
                                position.drift_analysis.execution_quality === 'good' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                                    position.drift_analysis.execution_quality === 'fair' ? 'bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400' :
                                        'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                }`}>
                                {position.drift_analysis.execution_quality === 'excellent' ? '优秀 ⭐' :
                                    position.drift_analysis.execution_quality === 'good' ? '良好' :
                                        position.drift_analysis.execution_quality === 'fair' ? '一般' : '需改进'}
                            </span>
                        </div>
                    </div>
                    {/* Risk Info */}
                    {position.planned_stop_loss && (
                        <div className="mt-4 pt-4 border-t border-slate-100 dark:border-slate-700 flex items-center gap-4">
                            <div>
                                <span className="text-xs text-slate-500">计划止损: </span>
                                <span className="font-medium">{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.planned_stop_loss).toFixed(2)}</span>
                            </div>
                            {position.drift_analysis.stop_loss_risk_pct && (
                                <div>
                                    <span className="text-xs text-slate-500">风险占比: </span>
                                    <span className={`font-medium ${position.drift_analysis.stop_loss_risk_pct > 5 ? 'text-red-600' : 'text-slate-700 dark:text-slate-300'}`}>
                                        {position.drift_analysis.stop_loss_risk_pct}%
                                    </span>
                                </div>
                            )}
                        </div>
                    )}
                </div>
            )}

            {/* Phase 1: Checklist Responses Card */}
            {position.checklist_responses && Object.keys(position.checklist_responses).length > 0 && (
                <div className="card p-5">
                    <h2 className="text-sm font-bold text-slate-400 mb-4 uppercase tracking-wider flex items-center">
                        ✅ 交易前检查清单
                        {position.checklist_completed_at && (
                            <span className="ml-2 text-xs font-normal text-slate-500">
                                (完成于 {new Date(position.checklist_completed_at).toLocaleString('zh-CN')})
                            </span>
                        )}
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                        {Object.entries(position.checklist_responses).map(([id, checked]) => (
                            <div
                                key={id}
                                className={`flex items-center gap-2 p-2 rounded-lg ${checked ? 'bg-emerald-50 dark:bg-emerald-900/20' : 'bg-red-50 dark:bg-red-900/20'
                                    }`}
                            >
                                <span className={checked ? 'text-emerald-500' : 'text-red-500'}>
                                    {checked ? '✓' : '✗'}
                                </span>
                                <span className="text-sm">检查项 #{id}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Trade Batches */}
            <div className="card">
                <div className="p-6 border-b border-slate-100 dark:border-slate-700">
                    <h2 className="text-lg font-semibold flex items-center space-x-2">
                        <Calendar className="w-5 h-5 text-slate-400" />
                        <span>交易记录</span>
                        <span className="text-sm text-slate-400 font-normal">({sortedBatches.length}笔)</span>
                    </h2>
                </div>
                <div className="divide-y divide-slate-100 dark:divide-slate-700">
                    {sortedBatches.map((batch) => (
                        <div key={batch.id} className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-3">
                                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${batch.type === 'ENTRY'
                                        ? 'bg-emerald-100 dark:bg-emerald-900/30'
                                        : 'bg-red-100 dark:bg-red-900/30'
                                        }`}>
                                        {batch.type === 'ENTRY' ? (
                                            <ArrowUpCircle className="w-5 h-5 text-emerald-500" />
                                        ) : (
                                            <ArrowDownCircle className="w-5 h-5 text-red-500" />
                                        )}
                                    </div>
                                    <div>
                                        <p className="font-medium">
                                            {batch.type === 'ENTRY' ? '加仓' : '平仓'}
                                            <span className="ml-2 text-slate-500">
                                                {Number(batch.quantity).toLocaleString()} @ {getCurrencySymbol(position.asset_metadata?.currency)}{Number(batch.price).toFixed(2)}
                                            </span>
                                        </p>
                                        <p className="text-sm text-slate-500">
                                            {new Date(batch.time).toLocaleString('zh-CN')}
                                        </p>
                                    </div>
                                </div>
                                <div className="text-right flex items-center space-x-4">
                                    <div className="hidden md:block">
                                        {batch.type === 'EXIT' && batch.pnl !== null && (
                                            <p className={`font-bold ${Number(batch.pnl) >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                                {Number(batch.pnl) >= 0 ? '+' : ''}{getCurrencySymbol(position.asset_metadata?.currency)}{Number(batch.pnl).toFixed(2)}
                                            </p>
                                        )}
                                        {batch.confidence && (
                                            <div className="flex items-center justify-end space-x-1 text-sm text-slate-400">
                                                <Target className="w-3 h-3" />
                                                <span>信心度 {batch.confidence}/5</span>
                                            </div>
                                        )}
                                    </div>
                                    <button
                                        onClick={() => openEditModal(batch)}
                                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700 text-slate-400 hover:text-primary-500 transition-colors"
                                    >
                                        <Edit3 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                            {batch.reason && (
                                <div className="mt-2 pl-13 text-sm text-slate-600 dark:text-slate-400">
                                    <MessageSquare className="w-3 h-3 inline mr-1" />
                                    {batch.reason}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Review Section */}
            {position.trade_review && (
                <div className="card p-6">
                    <h2 className="text-lg font-semibold mb-4 flex items-center space-x-2">
                        <Edit3 className="w-5 h-5 text-slate-400" />
                        <span>交易复盘</span>
                    </h2>
                    <p className="text-slate-600 dark:text-slate-400 whitespace-pre-wrap">
                        {position.trade_review}
                    </p>
                </div>
            )}

            {/* Lessons */}
            {position.lessons && position.lessons.length > 0 && (
                <div className="card p-6">
                    <h2 className="text-lg font-semibold mb-4 flex items-center space-x-2">
                        <Award className="w-5 h-5 text-slate-400" />
                        <span>经验教训</span>
                    </h2>
                    <div className="flex flex-wrap gap-2">
                        {position.lessons.map((lesson, idx) => (
                            <span
                                key={idx}
                                className="px-3 py-1 rounded-full bg-amber-100 text-amber-700 dark:bg-amber-900/30 dark:text-amber-400 text-sm"
                            >
                                {lesson}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Edit Batch Modal */}
            {editingBatch && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
                    <div className="card w-full max-w-md shadow-2xl animate-in zoom-in duration-200">
                        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                            <h3 className="text-lg font-bold">修改交易记录</h3>
                            <button
                                onClick={() => setEditingBatch(null)}
                                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                            >
                                <Plus className="w-5 h-5 rotate-45" />
                            </button>
                        </div>
                        <div className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">成交价格</label>
                                <input
                                    type="number"
                                    step="any"
                                    value={editForm.price}
                                    onChange={e => setEditForm({ ...editForm, price: parseFloat(e.target.value) })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">成交数量</label>
                                <input
                                    type="number"
                                    step="any"
                                    value={editForm.quantity}
                                    onChange={e => setEditForm({ ...editForm, quantity: parseFloat(e.target.value) })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">成交时间</label>
                                <DateTimePicker
                                    value={editForm.time}
                                    onChange={(val) => setEditForm({ ...editForm, time: val })}
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">交易理由</label>
                                <textarea
                                    value={editForm.reason}
                                    onChange={e => setEditForm({ ...editForm, reason: e.target.value })}
                                    className="input min-h-[80px]"
                                    placeholder="为什么要修改这笔交易？"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">信心度 (1-5)</label>
                                <input
                                    type="range"
                                    min="1"
                                    max="5"
                                    value={editForm.confidence}
                                    onChange={e => setEditForm({ ...editForm, confidence: parseInt(e.target.value) })}
                                    className="w-full h-2 bg-slate-200 rounded-lg appearance-none cursor-pointer accent-primary-500"
                                />
                                <div className="flex justify-between text-xs text-slate-400 mt-1">
                                    <span>纠结</span>
                                    <span>平常</span>
                                    <span>极度自信</span>
                                </div>
                            </div>
                        </div>
                        <div className="p-6 border-t border-slate-100 dark:border-slate-800 flex justify-end space-x-3">
                            <button
                                onClick={() => setEditingBatch(null)}
                                className="btn btn-secondary"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleUpdateBatch}
                                disabled={isSavingBatch}
                                className="btn btn-primary flex items-center space-x-2"
                            >
                                {isSavingBatch && <Loader2 className="w-4 h-4 animate-spin" />}
                                <span>保存修改</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* Edit Metadata Modal */}
            {editingMetadata && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
                    <div className="card w-full max-w-lg shadow-2xl animate-in zoom-in duration-200">
                        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                            <h3 className="text-lg font-bold">编辑资产属性</h3>
                            <button
                                onClick={() => setEditingMetadata(false)}
                                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                            >
                                <Plus className="w-5 h-5 rotate-45" />
                            </button>
                        </div>
                        <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">底层资产</label>
                                <select
                                    value={metadataForm.core_type}
                                    onChange={e => setMetadataForm({ ...metadataForm, core_type: e.target.value })}
                                    className="input"
                                >
                                    {ALL_ASSET_CORE_TYPES.map(type => (
                                        <option key={type} value={type}>
                                            {getCoreTypeLabel(type)} ({type})
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">交易工具</label>
                                <input
                                    type="text"
                                    value={metadataForm.instrument}
                                    onChange={e => setMetadataForm({ ...metadataForm, instrument: e.target.value })}
                                    className="input"
                                    placeholder="e.g. Spot, ETF, Future"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">所属市场</label>
                                <select
                                    value={metadataForm.market}
                                    onChange={e => setMetadataForm({ ...metadataForm, market: e.target.value })}
                                    className="input"
                                >
                                    {ALL_ASSET_MARKETS.map(market => (
                                        <option key={market} value={market}>
                                            {getMarketLabel(market)} ({market as string})
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">风险评级</label>
                                <select
                                    value={metadataForm.risk_level}
                                    onChange={e => setMetadataForm({ ...metadataForm, risk_level: e.target.value })}
                                    className="input"
                                >
                                    {ALL_ASSET_RISK_LEVELS.map(level => (
                                        <option key={level} value={level}>
                                            {getRiskLevelInfo(level).label} ({level})
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div className="md:col-span-2">
                                <label className="block text-sm font-medium mb-1">行业 / 板块</label>
                                <input
                                    type="text"
                                    value={metadataForm.sector}
                                    onChange={e => setMetadataForm({ ...metadataForm, sector: e.target.value })}
                                    className="input"
                                    placeholder="e.g. 科技, 医疗, 消费..."
                                />
                            </div>
                        </div>
                        <div className="p-6 border-t border-slate-100 dark:border-slate-800 flex justify-end space-x-3">
                            <button
                                onClick={() => setEditingMetadata(false)}
                                className="btn btn-secondary"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleUpdateMetadata}
                                disabled={isSavingMetadata}
                                className="btn btn-primary flex items-center space-x-2"
                            >
                                {isSavingMetadata && <Loader2 className="w-4 h-4 animate-spin" />}
                                <span>保存属性</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
            {/* Edit Extremes Modal */}
            {editingExtremes && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm">
                    <div className="card w-full max-w-sm shadow-2xl animate-in zoom-in duration-200">
                        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex items-center justify-between">
                            <h3 className="text-lg font-bold">编辑价格极值</h3>
                            <button
                                onClick={() => setEditingExtremes(false)}
                                className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors"
                            >
                                <Plus className="w-5 h-5 rotate-45" />
                            </button>
                        </div>
                        <div className="p-6 space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-1">持仓期最高价</label>
                                <input
                                    type="number"
                                    step="any"
                                    value={extremesForm.max_price}
                                    onChange={e => setExtremesForm({ ...extremesForm, max_price: parseFloat(e.target.value) })}
                                    className="input"
                                />
                            </div>
                            <div>
                                <label className="block text-sm font-medium mb-1">持仓期最低价</label>
                                <input
                                    type="number"
                                    step="any"
                                    value={extremesForm.min_price}
                                    onChange={e => setExtremesForm({ ...extremesForm, min_price: parseFloat(e.target.value) })}
                                    className="input"
                                />
                            </div>
                        </div>
                        <div className="p-6 border-t border-slate-100 dark:border-slate-800 flex justify-end space-x-3">
                            <button
                                onClick={() => setEditingExtremes(false)}
                                className="btn btn-secondary"
                            >
                                取消
                            </button>
                            <button
                                onClick={handleUpdateExtremes}
                                disabled={isSavingExtremes}
                                className="btn btn-primary flex items-center space-x-2"
                            >
                                {isSavingExtremes && <Loader2 className="w-4 h-4 animate-spin" />}
                                <span>保存</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
                </>
            )}
        </div>
    )
}
