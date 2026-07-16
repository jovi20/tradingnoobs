'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
    ArrowLeft,
    Loader2,
    ArrowUpCircle,
    ArrowDownCircle,
    AlertCircle
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import {
    positionsAPI, accountsAPI, strategiesAPI, marketAPI,
    Strategy, PositionCreate, BatchCreate, SymbolValidation, ChecklistItem
} from '@/lib/api'
import {
    adaptPosition,
    adaptTradingAccounts,
    buildTruthTradeEventFromBatchForm,
    getTruthFirstWriteFallbackState,
    PositionViewModel,
    TradingAccountViewModel
} from '@/lib/adapters/trading'
import {
    buildMarketDataStatus,
    type MarketFreshnessTone
} from '@/lib/adapters/market-data'
import { MARKET_RUNTIME_ENABLED } from '@/lib/release-profile'
import {
    detectSymbolType, getAssetTypeColor, getAssetTypeLabel,
    getCoreTypeLabel, getMarketLabel, getRiskLevelInfo,
    AssetCoreType, AssetMarket, AssetCurrency, AssetRiskLevel
} from '@/lib/symbolUtils'
import DateTimePicker from '@/components/DateTimePicker'
import CustomSelect from '@/components/CustomSelect'

import { Info } from 'lucide-react'
import ChecklistModal from '@/components/ChecklistModal'

const marketStatusToneClasses: Record<MarketFreshnessTone, string> = {
    positive: 'border-profit/30 bg-profit/10 text-profit',
    neutral: 'border-line bg-panel-subtle text-ink-soft',
    warning: 'border-warning/30 bg-warning/12 text-warning',
    danger: 'border-loss/30 bg-loss/10 text-loss',
}

export default function NewPositionPage() {
    const { token } = useAuth()
    const router = useRouter()

    const [accounts, setAccounts] = useState<TradingAccountViewModel[]>([])
    const [strategies, setStrategies] = useState<Strategy[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState('')

    // Existing position check
    const [existingPosition, setExistingPosition] = useState<PositionViewModel | null>(null)
    const [showExistingPrompt, setShowExistingPrompt] = useState(false)

    // Symbol validation
    const [symbolValidation, setSymbolValidation] = useState<SymbolValidation | null>(null)
    const [isValidating, setIsValidating] = useState(false)

    // Form state
    const [form, setForm] = useState({
        account_id: 0,
        symbol: '',
        direction: 'LONG' as 'LONG' | 'SHORT',
        strategy_id: undefined as number | undefined,
        entry_price: '',
        quantity: '',
        entry_time: new Date().toISOString(),
        entry_reason: '',
        entry_emotion: '',
        entry_confidence: undefined as number | undefined,
        asset_type: '',
        // Phase 1: Plan Drift Detection
        planned_entry_price: '' as string,
        planned_stop_loss: '' as string,
        // Phase 1: Checklist Responses
        checklist_responses: {} as Record<string, boolean>,
        metadata: {
            name: '',
            core_type: '' as AssetCoreType | '',
            market: '' as AssetMarket | '',
            currency: '' as AssetCurrency | '',
            sector: '',
            risk_level: '' as AssetRiskLevel | '',
            instrument: ''
        }
    })
    const symbolDetection = detectSymbolType(form.symbol)
    const activeSymbolValidation = symbolValidation?.symbol === form.symbol.trim().toUpperCase()
        ? symbolValidation
        : null
    const marketDataStatus = activeSymbolValidation?.valid && (
        activeSymbolValidation.provider
        || activeSymbolValidation.freshness
        || activeSymbolValidation.degraded
        || activeSymbolValidation.as_of
    )
        ? buildMarketDataStatus(activeSymbolValidation)
        : null

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return
            try {
                const [accountsData, strategiesData] = await Promise.all([
                    accountsAPI.list(token),
                    strategiesAPI.list(token)
                ])
                setAccounts(adaptTradingAccounts(accountsData))
                setStrategies(strategiesData.filter((s: Strategy) => s.status === 'ACTIVE'))
                if (accountsData.length > 0) {
                    setForm(prev => ({ ...prev, account_id: accountsData[0].id }))
                }
            } catch (err: any) {
                setError(err.message || '加载失败')
            } finally {
                setIsLoading(false)
            }
        }
        fetchData()
    }, [token])

    // Modal State
    const [showChecklistModal, setShowChecklistModal] = useState(false)

    const [isAddingBatch, setIsAddingBatch] = useState(false)

    // Check for existing position when symbol or account changes
    useEffect(() => {
        const checkExisting = async () => {
            if (!token || !form.symbol || !form.account_id) {
                setExistingPosition(null)
                setShowExistingPrompt(false)
                return
            }
            try {
                const existing = await positionsAPI.checkOpen(token, form.symbol, form.account_id)
                if (existing) {
                    setExistingPosition(adaptPosition(existing))
                    setShowExistingPrompt(true)
                } else {
                    setExistingPosition(null)
                    setShowExistingPrompt(false)
                }
            } catch {
                // Ignore errors, just don't show prompt
            }
        }
        const debounce = setTimeout(checkExisting, 500)
        return () => clearTimeout(debounce)
    }, [token, form.symbol, form.account_id])

    // Simplified symbol behavior: No auto-validation on typing
    useEffect(() => {
        if (!MARKET_RUNTIME_ENABLED) {
            return
        }
        if (!form.symbol) {
            const clearTimer = window.setTimeout(() => {
                setSymbolValidation(null)
            }, 0)
            return () => window.clearTimeout(clearTimer)
        }

        // Debounce validation
        let cancelled = false
        const timeoutId = window.setTimeout(async () => {
            if (!token) return
            const detection = detectSymbolType(form.symbol)
            setIsValidating(true)
            try {
                // Determine exchange hint based on detection
                let exchangeHint = undefined
                if (detection.type === 'CRYPTO') exchangeHint = 'BINANCE'
                if (detection.type === 'HK_STOCK') exchangeHint = 'HKEX'
                if (detection.type === 'A_STOCK') exchangeHint = 'A_SHARE'

                const res = await marketAPI.validateSymbol(token, form.symbol, exchangeHint)
                if (cancelled) return
                setSymbolValidation(res)

                if (res.valid && res.metadata) {
                    // Auto-fill form if metadata found
                    setForm(prev => ({
                        ...prev,
                        asset_type: res.asset_type || prev.asset_type,
                        entry_price: (prev.entry_price && prev.entry_price !== '0') ? prev.entry_price : (res.price != null ? res.price.toString() : ''),
                        metadata: {
                            ...prev.metadata,
                            name: res.name || res.metadata.name || prev.metadata.name,
                            core_type: (res.metadata.core_type as any) || prev.metadata.core_type,
                            market: (res.metadata.market as any) || prev.metadata.market,
                            currency: (res.metadata.currency as any) || prev.metadata.currency,
                            sector: res.metadata.sector || prev.metadata.sector,
                            risk_level: (res.metadata.risk_level as any) || prev.metadata.risk_level,
                            instrument: res.metadata.instrument || prev.metadata.instrument
                        }
                    }))
                }
            } catch (err) {
                console.warn("Validation failed", err)
            } finally {
                if (!cancelled) setIsValidating(false)
            }
        }, 800)

        return () => {
            cancelled = true
            window.clearTimeout(timeoutId)
        }
    }, [form.symbol, token])

    const submitPosition = async (finalForm: typeof form) => {
        if (!token) return
        setError('')
        setIsSubmitting(true)

        try {
            const data: PositionCreate = {
                account_id: finalForm.account_id,
                symbol: finalForm.symbol.toUpperCase(),
                direction: finalForm.direction,
                strategy_id: finalForm.strategy_id,
                entry_price: parseFloat(finalForm.entry_price),
                quantity: parseFloat(finalForm.quantity),
                entry_time: finalForm.entry_time,
                entry_reason: finalForm.entry_reason || undefined,
                entry_emotion: finalForm.entry_emotion || undefined,
                entry_confidence: finalForm.entry_confidence,
                asset_type: finalForm.asset_type || undefined,
                // Phase 1: Plan Drift Detection
                planned_entry_price: finalForm.planned_entry_price ? parseFloat(finalForm.planned_entry_price) : undefined,
                planned_stop_loss: finalForm.planned_stop_loss ? parseFloat(finalForm.planned_stop_loss) : undefined,
                // Phase 1: Checklist Responses
                checklist_responses: Object.keys(finalForm.checklist_responses).length > 0 ? finalForm.checklist_responses : undefined,
                asset_metadata: {
                    name: finalForm.metadata.name || finalForm.symbol,
                    core_type: finalForm.metadata.core_type || undefined,
                    market: finalForm.metadata.market || undefined,
                    currency: finalForm.metadata.currency || undefined,
                    sector: finalForm.metadata.sector || undefined,
                    risk_level: finalForm.metadata.risk_level || undefined,
                    instrument: finalForm.metadata.instrument || undefined
                }
            }

            const createdPosition = await positionsAPI.create(token, data)
            if (createdPosition.truth_position_public_id) {
                router.push(`/positions/${createdPosition.public_id}`)
            } else {
                router.push('/positions')
            }
        } catch (err: any) {
            setError(err.message || '创建失败')
            setIsSubmitting(false)
        }
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!token) return

        if (!form.entry_price || !form.quantity) {
            setError('请输入价格和数量')
            return
        }

        // Check if strategy has checklist items
        if (form.strategy_id) {
            const selectedStrategy = strategies.find(s => s.id === form.strategy_id)
            if (selectedStrategy && selectedStrategy.checklist_items && selectedStrategy.checklist_items.length > 0) {
                setShowChecklistModal(true)
                return
            }
        }

        // Directly submit if no checklist
        submitPosition(form)
    }

    const handleChecklistConfirm = (responses: Record<string, boolean>) => {
        const updatedForm = { ...form, checklist_responses: responses }
        setForm(updatedForm)
        submitPosition(updatedForm)
    }

    const handleAddToExisting = async () => {
        if (!token || !existingPosition) return

        if (!form.entry_price || !form.quantity) {
            setError('请输入加仓的价格和数量')
            // Scroll to fields
            document.querySelector('.input[type="number"]')?.scrollIntoView({ behavior: 'smooth' })
            return
        }

        setError('')
        setIsAddingBatch(true)

        try {
            const batchData: BatchCreate = {
                type: 'ENTRY',
                price: parseFloat(form.entry_price),
                quantity: parseFloat(form.quantity),
                time: form.entry_time,
                reason: form.entry_reason || undefined,
                emotion: form.entry_emotion || undefined,
                confidence: form.entry_confidence
            }

            const truthData = await positionsAPI.getTruthLifecycle(token, existingPosition.routeId).catch(() =>
                existingPosition.truth_position_public_id
                    ? positionsAPI.getTradingPositionLifecycle(token, existingPosition.truth_position_public_id).catch(() => null)
                    : null
            )
            const truthPositionPublicId = truthData?.data?.position_summary?.public_id

            if (truthPositionPublicId) {
                await positionsAPI.createTradingPositionTradeEvent(
                    token,
                    truthPositionPublicId,
                    buildTruthTradeEventFromBatchForm(batchData, existingPosition)
                )
                router.push(`/positions/${existingPosition.routeId}`)
            } else {
                const fallbackState = getTruthFirstWriteFallbackState(false, false)
                if (!fallbackState.canWriteLegacyFallback) {
                    setError(fallbackState.reason)
                    return
                }

                await positionsAPI.addBatch(token, existingPosition.routeId, batchData, { migrationFallback: true })
                router.push(`/positions/${existingPosition.routeId}`)
            }
        } catch (err: any) {
            setError(err.message || '加仓失败')
        } finally {
            setIsAddingBatch(false)
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-ink-muted" />
            </div>
        )
    }

    if (accounts.length === 0) {
        return (
            <div className="card p-12 text-center">
                <p className="text-ink-muted mb-4">请先在设置中添加交易账户</p>
                <Link href="/settings" className="btn btn-primary inline-flex items-center justify-center">
                    前往设置
                </Link>
            </div>
        )
    }

    return (
        <div className="max-w-2xl mx-auto pb-20 md:pb-6">
            {/* Header */}
            <div className="flex items-center gap-4 mb-6">
                <Link
                    href="/positions"
                    aria-label="返回交易记录"
                    title="返回交易记录"
                    className="p-2 rounded-lg hover:bg-panel-subtle"
                >
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <h1 className="text-2xl font-bold">新增交易</h1>
            </div>

            {/* Error */}
            {error && (
                <div className="mb-6 p-4 rounded-md bg-loss/8 dark:bg-loss/8 text-loss animate-in fade-in slide-in-from-top-2">
                    {error}
                </div>
            )}

            {/* Existing Position Prompt */}
            {showExistingPrompt && existingPosition && (
                <div className="mb-6 p-4 rounded-md bg-warning/8 dark:bg-warning/8 border border-warning/30 dark:border-warning/30 animate-in zoom-in-95 duration-300">
                    <div className="flex items-start gap-4">
                        <div className="p-2 rounded-lg bg-warning/8">
                            <AlertCircle className="w-6 h-6 text-warning dark:text-warning" />
                        </div>
                        <div className="flex-1">
                            <h3 className="font-semibold text-lg text-warning dark:text-warning">
                                检测到已有 {existingPosition.symbol} 持仓
                            </h3>
                            <p className="text-sm text-warning/80 dark:text-warning/80 mt-1">
                                您当前持有 <span className="font-bold">{Number(existingPosition.total_quantity).toFixed(4)}</span> 份，
                                均价 <span className="font-bold">${Number(existingPosition.average_entry_price || 0).toFixed(2)}</span>
                            </p>
                            <div className="flex gap-3 mt-4">
                                <button
                                    type="button"
                                    onClick={handleAddToExisting}
                                    disabled={isAddingBatch}
                                    className="btn flex-1 bg-warning text-white hover:opacity-90"
                                >
                                    {isAddingBatch ? <Loader2 className="w-4 h-4 animate-spin mx-auto" /> : '加仓到此仓位'}
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setShowExistingPrompt(false)}
                                    className="btn flex-1 btn-outline border-warning/30 dark:border-warning/30 text-warning dark:text-warning hover:bg-warning/8 dark:hover:bg-warning/8"
                                >
                                    开新仓位
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
                {/* Account & Symbol */}
                <div className="card p-6 space-y-4 relative z-20">
                    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                        <div>
                            <label className="block text-sm font-medium mb-2">账户 *</label>
                            <CustomSelect
                                options={accounts.map(a => ({ value: a.id, label: `${a.name} · ${a.broker}` }))}
                                value={form.account_id}
                                onChange={val => setForm({ ...form, account_id: typeof val === 'string' ? parseInt(val) : val })}
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">
                                标的代码 *
                                {(activeSymbolValidation?.asset_type || (symbolDetection && symbolDetection.type !== 'UNKNOWN')) && (
                                    <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${getAssetTypeColor((activeSymbolValidation?.asset_type as any) || symbolDetection?.type)}`}>
                                        {getAssetTypeLabel((activeSymbolValidation?.asset_type as any) || symbolDetection?.type)}
                                    </span>
                                )}
                            </label>
                            <div className="relative">
                                <input
                                    required
                                    type="text"
                                    value={form.symbol}
                                    onChange={e => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
                                    className="input uppercase"
                                    placeholder="AAPL, 600519, BTCUSDT, 00700"
                                />
                            </div>

                            {/* Format hint for unknown only */}
                            {symbolDetection && symbolDetection.type === 'UNKNOWN' && form.symbol.length > 0 && (
                                <p className="text-xs mt-1 text-warning">
                                    格式提示: A股(6位数字) | 港股(5位数字) | 美股(字母) | 加密(XXXUSDT)
                                </p>
                            )}
                        </div>
                    </div>

                    {isValidating && form.symbol && (
                        <div role="status" aria-live="polite" className="flex items-center gap-2 text-xs text-ink-muted">
                            <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" />
                            正在验证标的并获取行情
                        </div>
                    )}

                    {marketDataStatus && (
                        <div
                            role="status"
                            aria-live="polite"
                            className={`rounded-md border px-3 py-2 text-xs ${marketStatusToneClasses[marketDataStatus.tone]}`}
                        >
                            <div className="flex flex-wrap items-center gap-x-4 gap-y-1">
                                <span className="font-semibold">行情来源：{marketDataStatus.providerLabel}</span>
                                <span>新鲜度：{marketDataStatus.freshnessLabel}</span>
                                {marketDataStatus.asOf && (
                                    <span className="tn-nums">数据截至：{new Date(marketDataStatus.asOf).toLocaleString('zh-CN')}</span>
                                )}
                            </div>
                            {marketDataStatus.degradedReason && (
                                <p className="mt-1 leading-5">{marketDataStatus.degradedReason}</p>
                            )}
                        </div>
                    )}

                    {/* Direction */}
                    <div>
                        <label className="block text-sm font-medium mb-2">方向 *</label>
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                type="button"
                                onClick={() => setForm({ ...form, direction: 'LONG' })}
                                className={`p-4 rounded-md border-2 transition-all flex items-center justify-center gap-2 ${form.direction === 'LONG'
                                    ? 'border-profit/30 bg-profit/8 dark:bg-profit/8 text-profit'
                                    : 'border-line hover:border-line-strong'
                                    }`}
                            >
                                <ArrowUpCircle className="w-5 h-5" />
                                <span className="font-medium">做多</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setForm({ ...form, direction: 'SHORT' })}
                                className={`p-4 rounded-md border-2 transition-all flex items-center justify-center gap-2 ${form.direction === 'SHORT'
                                    ? 'border-loss/30 bg-loss/8 dark:bg-loss/8 text-loss'
                                    : 'border-line hover:border-line-strong'
                                    }`}
                            >
                                <ArrowDownCircle className="w-5 h-5" />
                                <span className="font-medium">做空</span>
                            </button>
                        </div>
                    </div>

                    {/* Strategy & Multi-dimensional Attributes */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">策略（可选）</label>
                            <CustomSelect
                                options={[
                                    { value: '', label: '不关联策略' },
                                    ...strategies.map(s => ({ value: s.id, label: s.name }))
                                ]}
                                value={form.strategy_id || ''}
                                onChange={val => {
                                    const strategyId = val ? (typeof val === 'string' ? parseInt(val) : val) : undefined
                                    // Reset checklist responses when strategy changes
                                    setForm({ ...form, strategy_id: strategyId, checklist_responses: {} })
                                }}
                                placeholder="选择交易策略"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">标的名称</label>
                            <input
                                type="text"
                                value={form.metadata.name}
                                onChange={e => setForm({ ...form, metadata: { ...form.metadata, name: e.target.value } })}
                                className="input"
                                placeholder="标的名称"
                            />
                        </div>
                    </div>

                    {/* Metadata Detail Section */}
                    <div className="pt-4 border-t border-line">
                        <div className="flex items-center gap-2 mb-4 text-ink-muted">
                            <Info className="w-4 h-4" />
                            <span className="text-xs font-semibold uppercase tracking-wider">资产多维属性（自动识别）</span>
                        </div>

                        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                            <div>
                                <label className="block text-[10px] uppercase font-bold text-ink-faint mb-1">核心类型</label>
                                <CustomSelect
                                    size="sm"
                                    options={[
                                        { value: 'STOCK', label: '股票 (STOCK)' },
                                        { value: 'BOND', label: '债券 (BOND)' },
                                        { value: 'FUND', label: '基金 (FUND)' },
                                        { value: 'COMMODITY', label: '大宗商品 (COMM)' },
                                        { value: 'FX', label: '外汇 (FX)' },
                                        { value: 'DERIVATIVE', label: '衍生品 (DERIV)' },
                                        { value: 'CRYPTO', label: '加密资产' },
                                    ]}
                                    value={form.metadata.core_type}
                                    onChange={val => setForm({ ...form, metadata: { ...form.metadata, core_type: val as any }, asset_type: val as string })}
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] uppercase font-bold text-ink-faint mb-1">市场</label>
                                <CustomSelect
                                    size="sm"
                                    options={[
                                        { value: 'US', label: '美股 (US)' },
                                        { value: 'HK', label: '港股 (HK)' },
                                        { value: 'A_SHARE', label: 'A股 (A_SHARE)' },
                                        { value: 'CN_OTC', label: '中国场外 (OTC)' },
                                        { value: 'FOREX', label: '外汇市场 (FX)' },
                                        { value: 'COMMODITY_FUT', label: '商品期货 (FUT)' },
                                        { value: 'UK', label: '英股 (UK)' },
                                        { value: 'CRYPTO', label: '加密资产' },
                                    ]}
                                    value={form.metadata.market}
                                    onChange={val => setForm({ ...form, metadata: { ...form.metadata, market: val as any } })}
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] uppercase font-bold text-ink-faint mb-1">计价货币</label>
                                <CustomSelect
                                    size="sm"
                                    options={[
                                        { value: 'USD', label: '美元 (USD)' },
                                        { value: 'HKD', label: '港币 (HKD)' },
                                        { value: 'CNY', label: '人民币 (CNY)' },
                                        { value: 'EUR', label: '欧元 (EUR)' },
                                        { value: 'GBP', label: '英镑 (GBP)' },
                                    ]}
                                    value={form.metadata.currency}
                                    onChange={val => setForm({ ...form, metadata: { ...form.metadata, currency: val as any } })}
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] uppercase font-bold text-ink-faint mb-1">风险等级</label>
                                <CustomSelect
                                    size="sm"
                                    options={[
                                        { value: 'CONSERVATIVE', label: '保守 (CONSERV)' },
                                        { value: 'MODERATE', label: '稳健 (MODERATE)' },
                                        { value: 'GROWTH', label: '成长 (GROWTH)' },
                                        { value: 'AGGRESSIVE', label: '激进 (AGGR)' },
                                        { value: 'HEDGE', label: '避险 (HEDGE)' },
                                    ]}
                                    value={form.metadata.risk_level}
                                    onChange={val => setForm({ ...form, metadata: { ...form.metadata, risk_level: val as any } })}
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] uppercase font-bold text-ink-faint mb-1">行业/主题</label>
                                <input
                                    type="text"
                                    value={form.metadata.sector}
                                    onChange={e => setForm({ ...form, metadata: { ...form.metadata, sector: e.target.value } })}
                                    className="input py-1 text-sm h-9"
                                    placeholder="例如：科技、AI"
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] uppercase font-bold text-ink-faint mb-1">工具类型</label>
                                <input
                                    type="text"
                                    value={form.metadata.instrument}
                                    onChange={e => setForm({ ...form, metadata: { ...form.metadata, instrument: e.target.value } })}
                                    className="input py-1 text-sm h-9"
                                    placeholder="例如：现货、ETF、期货"
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Inline Checklist Removed - Replaced by Modal */}

                {/* Entry Details */}
                <div className="card p-6 space-y-4 relative z-10">
                    <h2 className="font-semibold">入场信息</h2>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">入场价格 *</label>
                            <input
                                required
                                type="number"
                                step="any"
                                value={form.entry_price}
                                onChange={e => setForm({ ...form, entry_price: e.target.value })}
                                className="input"
                                placeholder="0.00"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">数量 *</label>
                            <input
                                required
                                type="number"
                                step="any"
                                value={form.quantity}
                                onChange={e => setForm({ ...form, quantity: e.target.value })}
                                className="input"
                                placeholder="0"
                            />
                        </div>
                    </div>

                    {/* Phase 1: Plan Drift Detection - Plan Prices */}
                    <div className="border-t border-line pt-4">
                        <div className="flex items-center gap-2 mb-3 text-ink-muted">
                            <Info className="w-4 h-4" />
                            <span className="text-xs font-semibold uppercase tracking-wider">计划价格（可选）</span>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-xs text-ink-muted mb-1">计划入场价</label>
                                <input
                                    type="number"
                                    step="any"
                                    value={form.planned_entry_price}
                                    onChange={e => setForm({ ...form, planned_entry_price: e.target.value })}
                                    className="input py-1 text-sm h-9"
                                    placeholder="计划入场价格"
                                />
                            </div>
                            <div>
                                <label className="block text-xs text-ink-muted mb-1">计划止损价</label>
                                <input
                                    type="number"
                                    step="any"
                                    value={form.planned_stop_loss}
                                    onChange={e => setForm({ ...form, planned_stop_loss: e.target.value })}
                                    className="input py-1 text-sm h-9"
                                    placeholder="计划止损价格"
                                />
                            </div>
                        </div>
                        <p className="text-xs text-ink-faint mt-2">用于交易后对比计划与实际执行的偏移</p>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">入场时间 *</label>
                        <DateTimePicker
                            value={form.entry_time}
                            onChange={(val) => setForm({ ...form, entry_time: val })}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">入场理由</label>
                        <textarea
                            value={form.entry_reason}
                            onChange={e => setForm({ ...form, entry_reason: e.target.value })}
                            className="input"
                            rows={3}
                            placeholder="为什么选择在这个时机入场？"
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">入场情绪</label>
                            <CustomSelect
                                options={[
                                    { value: '', label: '选择情绪' },
                                    { value: 'confident', label: '自信 😎' },
                                    { value: 'calm', label: '平静 😌' },
                                    { value: 'excited', label: '兴奋 🤩' },
                                    { value: 'anxious', label: '焦虑 😰' },
                                    { value: 'fomo', label: 'FOMO 😱' },
                                    { value: 'revenge', label: '报复交易 😤' },
                                ]}
                                value={form.entry_emotion}
                                onChange={val => setForm({ ...form, entry_emotion: val })}
                                placeholder="当前情绪"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">信心指数</label>
                            <CustomSelect
                                options={[
                                    { value: '', label: '选择信心' },
                                    { value: 1, label: '1 - 很低' },
                                    { value: 2, label: '2 - 较低' },
                                    { value: 3, label: '3 - 一般' },
                                    { value: 4, label: '4 - 较高' },
                                    { value: 5, label: '5 - 非常高' },
                                ]}
                                value={form.entry_confidence || ''}
                                onChange={val => setForm({ ...form, entry_confidence: val ? (typeof val === 'string' ? parseInt(val) : val) : undefined })}
                                placeholder="交易信心"
                            />
                        </div>
                    </div>
                </div>

                {/* Submit */}
                <button
                    type="submit"
                    disabled={isSubmitting || (showExistingPrompt && !!existingPosition)}
                    className="w-full btn btn-primary py-3"
                >
                    {isSubmitting ? (
                        <Loader2 className="w-5 h-5 animate-spin mx-auto" />
                    ) : (
                        '创建交易'
                    )}
                </button>
            </form>

            {/* Checklist Modal */}
            {
                form.strategy_id && (() => {
                    const selectedStrategy = strategies.find(s => s.id === form.strategy_id)
                    if (!selectedStrategy || !selectedStrategy.checklist_items || selectedStrategy.checklist_items.length === 0) return null
                    if (!showChecklistModal) return null

                    return (
                        <ChecklistModal
                            isOpen={showChecklistModal}
                            onClose={() => {
                                setShowChecklistModal(false)
                                setIsSubmitting(false)
                            }}
                            onConfirm={handleChecklistConfirm}
                            checklistItems={selectedStrategy.checklist_items}
                            strategyName={selectedStrategy.name}
                            isSubmitting={isSubmitting}
                        />
                    )
                })()
            }
        </div >
    )
}
