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
    Award,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { positionsAPI } from '@/lib/api'
import {
    adaptPosition,
    getLegacyBatchMutationState,
    getLegacyPositionDeleteState,
    getLegacyReviewDisplayState,
    PositionViewModel,
    TradeBatchViewModel
} from '@/lib/adapters/trading'
import {
    adaptLifecycleDetail,
    getLifecycleNarrativeDraft,
    getLifecycleReversalAction,
    type LifecycleDetailViewModel,
    type LifecycleNarrativeDraft,
} from '@/lib/adapters/lifecycle'
import { LifecycleModals } from '@/components/positions/lifecycle/LifecycleModals'
import { LifecycleWorkbench } from '@/components/positions/lifecycle/LifecycleWorkbench'

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

const emptyTruthNarrativeForm: LifecycleNarrativeDraft = {
    eventPublicId: '',
    reason: '',
    emotion: '',
    confidence: 3,
    thesis: '',
    invalidationRule: '',
    plannedExitRule: '',
    sizingRationale: '',
    note: '',
    checklistSnapshot: {},
}

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
    const [editingTruthNarrative, setEditingTruthNarrative] = useState(false)
    const [isSavingTruthNarrative, setIsSavingTruthNarrative] = useState(false)
    const [isReversingTruthEvent, setIsReversingTruthEvent] = useState(false)
    const [truthNarrativeForm, setTruthNarrativeForm] = useState<LifecycleNarrativeDraft>(emptyTruthNarrativeForm)
    const [editingManualAdjustment, setEditingManualAdjustment] = useState(false)
    const [isSavingManualAdjustment, setIsSavingManualAdjustment] = useState(false)
    const [manualAdjustmentForm, setManualAdjustmentForm] = useState({
        amount: 0,
        currency: 'USD',
        occurred_at: new Date().toISOString(),
        note: '',
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
                    if (legacyData && legacyData.public_id !== positionId) {
                        router.replace(`/positions/${legacyData.public_id}`)
                    }
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
    }, [token, positionId, router])

    const handleDelete = async () => {
        if (!token || !position) return
        if (truthLifecycle) {
            setError(legacyDeleteState.reason)
            return
        }
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

    const openTruthNarrativeModal = () => {
        if (!truthLifecycle) return
        const draft = getLifecycleNarrativeDraft(truthLifecycle)
        if (!draft.eventPublicId) {
            alert('当前生命周期没有可编辑的持仓事件标识。')
            return
        }
        setTruthNarrativeForm(draft)
        setEditingTruthNarrative(true)
    }

    const handleUpdateTruthNarrative = async () => {
        if (!token || !truthLifecycle || !truthNarrativeForm.eventPublicId) return
        setIsSavingTruthNarrative(true)
        try {
            const updatedLifecycle = await positionsAPI.updateTradingPositionEventNarrative(
                token,
                truthLifecycle.truthPositionPublicId,
                truthNarrativeForm.eventPublicId,
                {
                    reason: truthNarrativeForm.reason,
                    emotion: truthNarrativeForm.emotion,
                    confidence: truthNarrativeForm.confidence,
                    thesis: truthNarrativeForm.thesis,
                    invalidation_rule: truthNarrativeForm.invalidationRule,
                    planned_exit_rule: truthNarrativeForm.plannedExitRule,
                    sizing_rationale: truthNarrativeForm.sizingRationale,
                    checklist_snapshot: truthNarrativeForm.checklistSnapshot,
                    note: truthNarrativeForm.note,
                }
            )
            setTruthLifecycle(adaptLifecycleDetail(updatedLifecycle))
            setEditingTruthNarrative(false)
        } catch (err: any) {
            alert(err.message || '保存交易叙事失败')
        } finally {
            setIsSavingTruthNarrative(false)
        }
    }

    const handleReverseLatestTruthEvent = async () => {
        if (!token || !truthLifecycle) return
        const reversalAction = getLifecycleReversalAction(truthLifecycle)
        if (!reversalAction.canReverse || !reversalAction.eventPublicId) {
            setError(reversalAction.reason)
            return
        }
        if (!window.confirm(`确定要撤销最新 ${reversalAction.nodeType} truth event 吗？系统会追加 REVERSAL 节点，而不是静默删除历史事件。`)) return

        setIsReversingTruthEvent(true)
        try {
            const updatedLifecycle = await positionsAPI.reverseTradingPositionTradeEvent(
                token,
                truthLifecycle.truthPositionPublicId,
                reversalAction.eventPublicId,
                {
                    occurred_at: new Date().toISOString(),
                    note: `从持仓详情撤销 ${reversalAction.nodeType} 事件`,
                }
            )
            setTruthLifecycle(adaptLifecycleDetail(updatedLifecycle))
            setError('')
        } catch (err: any) {
            alert(err.message || '撤销审计事件失败')
        } finally {
            setIsReversingTruthEvent(false)
        }
    }

    const openManualAdjustmentModal = () => {
        if (!truthLifecycle) return
        setManualAdjustmentForm({
            amount: 0,
            currency: position?.asset_metadata?.currency || truthLifecycle.cashEffects[0]?.currency || 'USD',
            occurred_at: new Date().toISOString(),
            note: '',
        })
        setEditingManualAdjustment(true)
    }

    const handleCreateManualAdjustment = async () => {
        if (!token || !truthLifecycle) return
        if (!Number.isFinite(manualAdjustmentForm.amount) || manualAdjustmentForm.amount === 0) {
            alert('现金调整金额不能为 0。')
            return
        }

        setIsSavingManualAdjustment(true)
        try {
            const updatedLifecycle = await positionsAPI.createTradingPositionManualAdjustment(
                token,
                truthLifecycle.truthPositionPublicId,
                {
                    amount: manualAdjustmentForm.amount,
                    currency: manualAdjustmentForm.currency,
                    occurred_at: manualAdjustmentForm.occurred_at,
                    note: manualAdjustmentForm.note,
                }
            )
            setTruthLifecycle(adaptLifecycleDetail(updatedLifecycle))
            setEditingManualAdjustment(false)
            setError('')
        } catch (err: any) {
            alert(err.message || '记录现金调整失败')
        } finally {
            setIsSavingManualAdjustment(false)
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-ink-muted" />
            </div>
        )
    }

    if (error || (!position && !truthLifecycle)) {
        return (
            <div className="card p-8 text-center">
                <p className="text-loss mb-4">{error || '持仓不存在'}</p>
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
    const legacyBatchMutationState = getLegacyBatchMutationState(Boolean(truthLifecycle))
    const legacyDeleteState = getLegacyPositionDeleteState(Boolean(truthLifecycle))
    const legacyReviewDisplayState = getLegacyReviewDisplayState(Boolean(truthLifecycle), Boolean(position?.trade_review))

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* Legacy fallback header. The truth workbench owns its canonical page header. */}
            {!truthLifecycle && (
            <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-3 min-w-0 flex-1">
                    <Link
                        href="/positions"
                        aria-label="返回交易记录"
                        title="返回交易记录"
                        className="p-2 rounded-lg hover:bg-panel-subtle shrink-0"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div className="min-w-0">
                        <h1 className="text-xl md:text-2xl font-bold flex items-center gap-2">
                            <span className="truncate">{displayTitle}</span>
                            <span className={`text-xs px-2 py-0.5 rounded-full shrink-0 ${isOpen
                                ? 'bg-ai/8 text-ai dark:bg-ai/8 dark:text-ai'
                                : 'bg-panel-subtle text-ink-soft'
                                }`}>
                                {isOpen ? '持仓中' : '已平仓'}
                            </span>
                        </h1>
                        <p className="text-sm text-ink-muted truncate">
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
                        disabled={isDeleting || !position || !legacyDeleteState.canDelete}
                        title={legacyDeleteState.reason}
                        className="btn btn-danger flex items-center gap-1 px-3 md:px-4 disabled:cursor-not-allowed disabled:opacity-60"
                    >
                        {isDeleting ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Trash2 className="w-4 h-4" />
                        )}
                        <span className="hidden sm:inline">{legacyDeleteState.label}</span>
                    </button>
                </div>
            </div>
            )}

            {truthLifecycle && (
                <LifecycleWorkbench
                    lifecycle={truthLifecycle}
                    legacyPosition={position}
                    sortedBatches={sortedBatches}
                    isAnalyzing={isAnalyzing}
                    isReversing={isReversingTruthEvent}
                    onEditNarrative={openTruthNarrativeModal}
                    onReverseLatest={handleReverseLatestTruthEvent}
                    onManualAdjustment={openManualAdjustmentModal}
                    onEditMetadata={openMetadataModal}
                    onEditExtremes={() => {
                        if (!position) return
                        setExtremesForm({
                            max_price: Number(position.max_price_during_hold || 0),
                            min_price: Number(position.min_price_during_hold || 0),
                        })
                        setEditingExtremes(true)
                    }}
                    onAnalyze={handleAnalyze}
                    onEditBatch={openEditModal}
                />
            )}

            {!position && truthLifecycle && (
                <div className="card border-profit/30 bg-profit/8 p-5 text-sm text-profit dark:border-profit/30 dark:text-profit">
                    当前详情由审计生命周期直接提供。旧版持仓编辑控件已隐藏，避免误改迁移数据。
                </div>
            )}

            {position && !truthLifecycle && (
                <>
                    <div className="card border-warning/30 bg-warning/8 p-5 text-sm text-warning dark:border-warning/30 dark:text-warning">
                        审计生命周期暂不可用，当前仅展示旧版持仓和批次数据。
                    </div>

            {/* Summary Card */}
            <div className="card overflow-hidden">
                <div className="grid grid-cols-2 lg:grid-cols-5 gap-0 divide-x divide-y lg:divide-y-0 divide-line">
                    <div className="p-4 lg:p-6">
                        <p className="text-xs text-ink-muted mb-1 uppercase tracking-wider font-semibold">持仓数量</p>
                        <p className="text-xl font-bold">{Number(position.total_quantity).toLocaleString()}</p>
                    </div>
                    <div className="p-4 lg:p-6">
                        <p className="text-xs text-ink-muted mb-1 uppercase tracking-wider font-semibold">均价 / 当前价</p>
                        <p className="text-xl font-bold">
                            {getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.average_entry_price || 0).toFixed(2)}
                            {position.current_price && (
                                <span className="text-sm font-normal ml-2 text-ink-faint">
                                    → {getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.current_price).toFixed(2)}
                                </span>
                            )}
                        </p>
                    </div>
                    <div className="p-4 lg:p-6">
                        <p className="text-xs text-ink-muted mb-1 uppercase tracking-wider font-semibold">已实现盈亏</p>
                        <p className={`text-xl font-bold ${isPositive ? 'pnl-positive' : 'pnl-negative'}`}>
                            {isPositive ? '+' : ''}{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.realized_pnl).toFixed(2)}
                        </p>
                    </div>
                    {position.status === 'OPEN' && (
                        <div className="p-4 lg:p-6 bg-panel-subtle/50">
                            <p className="text-xs text-ink-muted mb-1 uppercase tracking-wider font-semibold">未实现盈亏</p>
                            <p className={`text-xl font-bold ${(position.unrealized_pnl || 0) >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                {(position.unrealized_pnl || 0) >= 0 ? '+' : ''}{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.unrealized_pnl || 0).toFixed(2)}
                            </p>
                        </div>
                    )}
                    <div className="p-4 lg:p-6">
                        <p className="text-xs text-ink-muted mb-1 uppercase tracking-wider font-semibold">开仓日期</p>
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
                        aria-label="编辑资产属性"
                        className="absolute top-4 right-4 p-2 rounded-lg bg-panel hover:bg-panel-subtle text-ink-muted transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                        title="编辑属性"
                    >
                        <Edit3 className="w-4 h-4" />
                    </button>

                    <h2 className="text-sm font-bold text-ink-faint mb-4 uppercase tracking-wider flex items-center">
                        <Target className="w-4 h-4 mr-2" />
                        资产属性
                    </h2>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                        <div>
                            <p className="text-xs text-ink-muted mb-1">资产类型</p>
                            <p className="font-semibold flex items-center">
                                {getCoreTypeLabel(position.asset_metadata.core_type as AssetCoreType)}
                                {position.asset_metadata.instrument && (
                                    <>
                                        <span className="mx-1 text-line-strong">/</span>
                                        <span className="text-sm font-normal text-ink-muted">{position.asset_metadata.instrument}</span>
                                    </>
                                )}
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-ink-muted mb-1">交易市场</p>
                            <p className="font-semibold flex items-center">
                                {getMarketLabel(position.asset_metadata.market as AssetMarket)}
                                <span className="ml-2 text-xs bg-panel-subtle px-1.5 py-0.5 rounded text-ink-muted">
                                    {position.asset_metadata.currency}
                                </span>
                            </p>
                        </div>
                        <div>
                            <p className="text-xs text-ink-muted mb-1">所属板块</p>
                            <p className="font-semibold">{position.asset_metadata.sector || '未分类'}</p>
                        </div>
                        <div>
                            <p className="text-xs text-ink-muted mb-1">风险评级</p>
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
                    aria-label="手动修改价格极值"
                    className="absolute top-4 right-14 p-2 rounded-lg bg-panel hover:bg-panel-subtle text-ink-muted transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                    title="手动修改极值"
                >
                    <Edit3 className="w-4 h-4" />
                </button>
                <div className="absolute top-4 right-4 opacity-0 group-hover:opacity-100 focus-within:opacity-100 transition-opacity">
                    <button
                        onClick={handleAnalyze}
                        disabled={isAnalyzing}
                        aria-label={isAnalyzing ? '正在分析历史价格' : '分析历史价格'}
                        className="p-2 rounded-lg bg-ai/8 hover:bg-ai/8 dark:hover:bg-ai/8 text-ai dark:text-ai"
                        title="自动分析 (从历史数据)"
                    >
                        {isAnalyzing ? <Loader2 className="w-4 h-4 animate-spin" /> : <TrendingUp className="w-4 h-4" />}
                    </button>
                </div>

                <h2 className="text-sm font-bold text-ink-faint mb-4 uppercase tracking-wider flex items-center">
                    <TrendingUp className="w-4 h-4 mr-2" />
                    价格极值 (MAE/MFE)
                </h2>

                <div className="grid grid-cols-2 gap-6">
                    <div>
                        <p className="text-xs text-ink-muted mb-1">持仓期最高价</p>
                        <p className="font-semibold text-lg flex items-center">
                            {position.max_price_during_hold ? (
                                <span>{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.max_price_during_hold).toFixed(2)}</span>
                            ) : (
                                <span className="text-line-strong">-</span>
                            )}
                        </p>
                        {position.average_entry_price && position.max_price_during_hold && (
                            <p className={`text-xs mt-1 ${position.direction === 'LONG' ? 'text-profit' : 'text-loss'}`}>
                                {position.direction === 'LONG' ? 'MFE' : 'MAE'}: {((Number(position.max_price_during_hold) - Number(position.average_entry_price)) / Number(position.average_entry_price) * 100).toFixed(2)}%
                            </p>
                        )}
                    </div>
                    <div>
                        <p className="text-xs text-ink-muted mb-1">持仓期最低价</p>
                        <p className="font-semibold text-lg flex items-center">
                            {position.min_price_during_hold ? (
                                <span>{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.min_price_during_hold).toFixed(2)}</span>
                            ) : (
                                <span className="text-line-strong">-</span>
                            )}
                        </p>
                        {position.average_entry_price && position.min_price_during_hold && (
                            <p className={`text-xs mt-1 ${position.direction === 'LONG' ? 'text-loss' : 'text-profit'}`}>
                                {position.direction === 'LONG' ? 'MAE' : 'MFE'}: {((Number(position.min_price_during_hold) - Number(position.average_entry_price)) / Number(position.average_entry_price) * 100).toFixed(2)}%
                            </p>
                        )}
                    </div>
                </div>
            </div>

            {/* Phase 1: Plan Drift Analysis Card */}
            {position.drift_analysis?.has_planned_data && (
                <div className="card p-5">
                    <h2 className="text-sm font-bold text-ink-faint mb-4 uppercase tracking-wider flex items-center">
                        📊 计划执行对比
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        {/* Planned Entry */}
                        <div className="p-3 bg-panel-subtle rounded-lg">
                            <p className="text-xs text-ink-muted mb-1">计划入场价</p>
                            <p className="font-semibold">{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.planned_entry_price || 0).toFixed(2)}</p>
                        </div>
                        {/* Actual Entry */}
                        <div className="p-3 bg-panel-subtle rounded-lg">
                            <p className="text-xs text-ink-muted mb-1">实际入场价</p>
                            <p className="font-semibold">{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.average_entry_price || 0).toFixed(2)}</p>
                        </div>
                        {/* Entry Drift */}
                        <div className={`p-3 rounded-lg ${position.drift_analysis.execution_quality === 'excellent' ? 'bg-profit/8 dark:bg-profit/8' :
                            position.drift_analysis.execution_quality === 'good' ? 'bg-ai/8 dark:bg-ai/8' :
                                position.drift_analysis.execution_quality === 'fair' ? 'bg-warning/8 dark:bg-warning/8' :
                                    'bg-loss/8 dark:bg-loss/8'
                            }`}>
                            <p className="text-xs text-ink-muted mb-1">入场偏移</p>
                            <p className={`font-semibold ${Math.abs(position.drift_analysis.entry_drift_pct || 0) <= 2 ? 'text-profit' :
                                Math.abs(position.drift_analysis.entry_drift_pct || 0) <= 5 ? 'text-warning' : 'text-loss'
                                }`}>
                                {(position.drift_analysis.entry_drift_pct || 0) > 0 ? '+' : ''}{position.drift_analysis.entry_drift_pct}%
                                <span className="text-xs ml-1 text-ink-muted">
                                    ({position.drift_analysis.entry_drift_direction === 'above' ? '高于计划' :
                                        position.drift_analysis.entry_drift_direction === 'below' ? '低于计划' : '命中'})
                                </span>
                            </p>
                        </div>
                        {/* Execution Quality */}
                        <div className="p-3 bg-panel-subtle rounded-lg">
                            <p className="text-xs text-ink-muted mb-1">执行质量</p>
                            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${position.drift_analysis.execution_quality === 'excellent' ? 'bg-profit/8 text-profit dark:bg-profit/8 dark:text-profit' :
                                position.drift_analysis.execution_quality === 'good' ? 'bg-ai/8 text-ai dark:bg-ai/8 dark:text-ai' :
                                    position.drift_analysis.execution_quality === 'fair' ? 'bg-warning/8 text-warning dark:bg-warning/8 dark:text-warning' :
                                        'bg-loss/8 text-loss dark:bg-loss/8 dark:text-loss'
                                }`}>
                                {position.drift_analysis.execution_quality === 'excellent' ? '优秀 ⭐' :
                                    position.drift_analysis.execution_quality === 'good' ? '良好' :
                                        position.drift_analysis.execution_quality === 'fair' ? '一般' : '需改进'}
                            </span>
                        </div>
                    </div>
                    {/* Risk Info */}
                    {position.planned_stop_loss && (
                        <div className="mt-4 pt-4 border-t border-line flex items-center gap-4">
                            <div>
                                <span className="text-xs text-ink-muted">计划止损: </span>
                                <span className="font-medium">{getCurrencySymbol(position.asset_metadata?.currency)}{Number(position.planned_stop_loss).toFixed(2)}</span>
                            </div>
                            {position.drift_analysis.stop_loss_risk_pct && (
                                <div>
                                    <span className="text-xs text-ink-muted">风险占比: </span>
                                    <span className={`font-medium ${position.drift_analysis.stop_loss_risk_pct > 5 ? 'text-loss' : 'text-ink-soft'}`}>
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
                    <h2 className="text-sm font-bold text-ink-faint mb-4 uppercase tracking-wider flex items-center">
                        ✅ 交易前检查清单
                        {position.checklist_completed_at && (
                            <span className="ml-2 text-xs font-normal text-ink-muted">
                                (完成于 {new Date(position.checklist_completed_at).toLocaleString('zh-CN')})
                            </span>
                        )}
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                        {Object.entries(position.checklist_responses).map(([id, checked]) => (
                            <div
                                key={id}
                                className={`flex items-center gap-2 p-2 rounded-lg ${checked ? 'bg-profit/8 dark:bg-profit/8' : 'bg-loss/8 dark:bg-loss/8'
                                    }`}
                            >
                                <span className={checked ? 'text-profit' : 'text-loss'}>
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
                <div className="p-6 border-b border-line">
                    <h2 className="text-lg font-semibold flex items-center space-x-2">
                        <Calendar className="w-5 h-5 text-ink-faint" />
                        <span>交易记录</span>
                        <span className="text-sm text-ink-faint font-normal">({sortedBatches.length}笔)</span>
                    </h2>
                </div>
                <div className="divide-y divide-line">
                    {sortedBatches.map((batch) => (
                        <div key={batch.id} className="p-4 hover:bg-panel-subtle/50">
                            <div className="flex items-center justify-between">
                                <div className="flex items-center space-x-3">
                                    <div className={`w-10 h-10 rounded-md flex items-center justify-center ${batch.type === 'ENTRY'
                                        ? 'bg-profit/8'
                                        : 'bg-loss/8'
                                        }`}>
                                        {batch.type === 'ENTRY' ? (
                                            <ArrowUpCircle className="w-5 h-5 text-profit" />
                                        ) : (
                                            <ArrowDownCircle className="w-5 h-5 text-loss" />
                                        )}
                                    </div>
                                    <div>
                                        <p className="font-medium">
                                            {batch.type === 'ENTRY' ? '加仓' : '平仓'}
                                            <span className="ml-2 text-ink-muted">
                                                {Number(batch.quantity).toLocaleString()} @ {getCurrencySymbol(position.asset_metadata?.currency)}{Number(batch.price).toFixed(2)}
                                            </span>
                                        </p>
                                        <p className="text-sm text-ink-muted">
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
                                            <div className="flex items-center justify-end space-x-1 text-sm text-ink-faint">
                                                <Target className="w-3 h-3" />
                                                <span>信心度 {batch.confidence}/5</span>
                                            </div>
                                        )}
                                    </div>
                                    {legacyBatchMutationState.canMutate ? (
                                        <button
                                            onClick={() => openEditModal(batch)}
                                            aria-label={`编辑${batch.type === 'ENTRY' ? '加仓' : '平仓'}记录`}
                                            title={legacyBatchMutationState.reason}
                                            className="p-2 rounded-lg hover:bg-panel-subtle text-ink-faint hover:text-ink-muted transition-colors"
                                        >
                                            <Edit3 className="w-4 h-4" />
                                        </button>
                                    ) : (
                                        <span
                                            title={legacyBatchMutationState.reason}
                                            className="rounded-full border border-warning/30 bg-warning/8 px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.14em] text-warning dark:border-warning/30 dark:text-warning"
                                        >
                                            {legacyBatchMutationState.label}
                                        </span>
                                    )}
                                </div>
                            </div>
                            {batch.reason && (
                                <div className="mt-2 pl-13 text-sm text-ink-muted">
                                    <MessageSquare className="w-3 h-3 inline mr-1" />
                                    {batch.reason}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {/* Review Section */}
            {legacyReviewDisplayState.shouldDisplay && position.trade_review && (
                <div className="card p-6">
                    <h2 className="text-lg font-semibold mb-4 flex items-center space-x-2">
                        <Edit3 className="w-5 h-5 text-ink-faint" />
                        <span>{legacyReviewDisplayState.label}</span>
                        {legacyReviewDisplayState.isMigrationOnly && (
                            <span className="rounded-full border border-warning/30 bg-warning/8 px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.14em] text-warning dark:border-warning/30 dark:text-warning">
                                仅迁移
                            </span>
                        )}
                    </h2>
                    <p className="mb-4 rounded-md border border-line bg-panel-subtle px-3 py-2 text-xs text-ink-muted">
                        {legacyReviewDisplayState.reason}
                    </p>
                    <p className="text-ink-muted whitespace-pre-wrap">
                        {position.trade_review}
                    </p>
                </div>
            )}

            {/* Lessons */}
            {position.lessons && position.lessons.length > 0 && (
                <div className="card p-6">
                    <h2 className="text-lg font-semibold mb-4 flex items-center space-x-2">
                        <Award className="w-5 h-5 text-ink-faint" />
                        <span>经验教训</span>
                    </h2>
                    <div className="flex flex-wrap gap-2">
                        {position.lessons.map((lesson, idx) => (
                            <span
                                key={idx}
                                className="px-3 py-1 rounded-full bg-warning/8 text-warning dark:bg-warning/8 dark:text-warning text-sm"
                            >
                                {lesson}
                            </span>
                        ))}
                    </div>
                </div>
            )}

            {/* Edit Batch Modal */}
            {editingBatch && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm">
                    <div className="card w-full max-w-md shadow-2xl animate-in zoom-in duration-200">
                        <div className="p-6 border-b border-line flex items-center justify-between">
                            <h3 className="text-lg font-bold">修改交易记录</h3>
                            <button
                                type="button"
                                onClick={() => setEditingBatch(null)}
                                aria-label="关闭修改交易记录对话框"
                                title="关闭修改交易记录对话框"
                                className="p-2 hover:bg-panel-subtle rounded-lg transition-colors"
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
                                <label className="block text-sm font-medium mb-1">信心度（1-5）</label>
                                <input
                                    type="range"
                                    min="1"
                                    max="5"
                                    value={editForm.confidence}
                                    onChange={e => setEditForm({ ...editForm, confidence: parseInt(e.target.value) })}
                                    className="w-full h-2 bg-panel-subtle rounded-lg appearance-none cursor-pointer accent-ink"
                                />
                                <div className="flex justify-between text-xs text-ink-faint mt-1">
                                    <span>纠结</span>
                                    <span>平常</span>
                                    <span>极度自信</span>
                                </div>
                            </div>
                        </div>
                        <div className="p-6 border-t border-line flex justify-end space-x-3">
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
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm">
                    <div className="card w-full max-w-lg shadow-2xl animate-in zoom-in duration-200">
                        <div className="p-6 border-b border-line flex items-center justify-between">
                            <h3 className="text-lg font-bold">编辑资产属性</h3>
                            <button
                                type="button"
                                onClick={() => setEditingMetadata(false)}
                                aria-label="关闭编辑资产属性对话框"
                                title="关闭编辑资产属性对话框"
                                className="p-2 hover:bg-panel-subtle rounded-lg transition-colors"
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
                                    placeholder="例如：现货、ETF、期货"
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
                                    placeholder="例如：科技、医疗、消费"
                                />
                            </div>
                        </div>
                        <div className="p-6 border-t border-line flex justify-end space-x-3">
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
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-ink/50 backdrop-blur-sm">
                    <div className="card w-full max-w-sm shadow-2xl animate-in zoom-in duration-200">
                        <div className="p-6 border-b border-line flex items-center justify-between">
                            <h3 className="text-lg font-bold">编辑价格极值</h3>
                            <button
                                type="button"
                                onClick={() => setEditingExtremes(false)}
                                aria-label="关闭编辑价格极值对话框"
                                title="关闭编辑价格极值对话框"
                                className="p-2 hover:bg-panel-subtle rounded-lg transition-colors"
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
                        <div className="p-6 border-t border-line flex justify-end space-x-3">
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
            <LifecycleModals
                editingTruthNarrative={editingTruthNarrative}
                isSavingTruthNarrative={isSavingTruthNarrative}
                truthNarrativeForm={truthNarrativeForm}
                onChangeTruthNarrativeForm={setTruthNarrativeForm}
                onCloseTruthNarrative={() => setEditingTruthNarrative(false)}
                onSaveTruthNarrative={handleUpdateTruthNarrative}
                editingManualAdjustment={editingManualAdjustment}
                isSavingManualAdjustment={isSavingManualAdjustment}
                manualAdjustmentForm={manualAdjustmentForm}
                onChangeManualAdjustmentForm={setManualAdjustmentForm}
                onCloseManualAdjustment={() => setEditingManualAdjustment(false)}
                onSaveManualAdjustment={handleCreateManualAdjustment}
            />
        </div>
    )
}
