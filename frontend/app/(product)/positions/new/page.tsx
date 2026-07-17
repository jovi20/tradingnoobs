'use client'

import { useState, useEffect, useMemo } from 'react'
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
    positionsAPI, accountsAPI, strategiesAPI,
    Strategy, PositionCreate, PositionOpenIdentity, BatchCreate,
    ReleaseAssetType, ReleaseCurrency, ReleaseInstrumentType, ReleaseMarket
} from '@/lib/api'
import {
    adaptPosition,
    adaptTradingAccounts,
    buildTruthTradeEventFromBatchForm,
    getTruthFirstWriteFallbackState,
    normalizeReleasePositionIdentityInput,
    PositionViewModel,
    ReleasePositionIdentityField,
    TradingAccountViewModel
} from '@/lib/adapters/trading'
import DateTimePicker from '@/components/DateTimePicker'
import CustomSelect from '@/components/CustomSelect'

import { Info } from 'lucide-react'
import ChecklistModal from '@/components/ChecklistModal'

interface PositionIdentityInput {
    account_id: number
    symbol: string
    exchange_code: string
    direction: 'LONG' | 'SHORT'
    asset_type: ReleaseAssetType | ''
    metadata: {
        market: ReleaseMarket | ''
        currency: ReleaseCurrency
        instrument: ReleaseInstrumentType
    }
}

type NewPositionFormState = Omit<PositionIdentityInput, 'metadata'> & {
    strategy_id?: number
    entry_price: string
    quantity: string
    entry_time: string
    entry_reason: string
    entry_emotion: string
    entry_confidence?: number
    planned_entry_price: string
    planned_stop_loss: string
    checklist_responses: Record<string, boolean>
    metadata: PositionIdentityInput['metadata'] & {
        core_type: ReleaseAssetType | ''
    }
}

type NormalizedNewPositionFormState = Omit<NewPositionFormState, 'asset_type' | 'metadata'> & {
    asset_type: ReleaseAssetType
    metadata: {
        core_type: ReleaseAssetType
        market: ReleaseMarket
        currency: ReleaseCurrency
        instrument: ReleaseInstrumentType
    }
}

const IDENTITY_FIELD_LABELS: Record<ReleasePositionIdentityField, string> = {
    symbol: '标的代码',
    exchange_code: '交易所代码',
    asset_type: '资产类型',
    market: '市场',
    instrument_type: '工具类型',
    quote_currency: '计价货币',
}

function getReleaseAssetTypeSelection(value: unknown): ReleaseAssetType | '' {
    return value === 'STOCK' || value === 'FUND' || value === 'CRYPTO' ? value : ''
}

function getReleaseMarketSelection(value: unknown): ReleaseMarket | '' {
    return value === 'US' || value === 'CRYPTO' ? value : ''
}

function parsePositionIdentity(form: PositionIdentityInput) {
    return normalizeReleasePositionIdentityInput({
        symbol: form.symbol,
        exchange_code: form.exchange_code,
        asset_type: form.asset_type,
        market: form.metadata.market,
        instrument_type: form.metadata.instrument,
        quote_currency: form.metadata.currency,
    })
}

function getIdentityValidationError(form: PositionIdentityInput): string | null {
    const result = parsePositionIdentity(form)
    if (result.ok) return null
    if (result.reason === 'INVALID_COMBINATION') {
        return '股票和基金仅支持 US 市场，加密资产仅支持 CRYPTO 市场'
    }
    if (result.reason === 'REQUIRED') {
        if (result.field === 'symbol') return '请输入标的代码'
        if (result.field === 'exchange_code') return '请输入交易所代码'
        return `请选择${IDENTITY_FIELD_LABELS[result.field]}`
    }
    if (result.reason === 'NON_ASCII') {
        return `${IDENTITY_FIELD_LABELS[result.field]}仅支持 ASCII 字符`
    }
    return `${IDENTITY_FIELD_LABELS[result.field]}格式不符合当前发布合同`
}

function normalizeIdentityForm(form: NewPositionFormState): NormalizedNewPositionFormState | null {
    const result = parsePositionIdentity(form)
    if (!result.ok) return null
    return {
        ...form,
        symbol: result.identity.symbol,
        exchange_code: result.identity.exchange_code,
        asset_type: result.identity.asset_type,
        metadata: {
            core_type: result.identity.asset_type,
            market: result.identity.market,
            currency: result.identity.quote_currency,
            instrument: result.identity.instrument_type,
        },
    }
}

function buildOpenIdentity(form: PositionIdentityInput): PositionOpenIdentity | null {
    const result = parsePositionIdentity(form)
    if (!result.ok) return null
    return {
        account_id: form.account_id,
        direction: form.direction,
        ...result.identity,
    }
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

    // Form state
    const [form, setForm] = useState<NewPositionFormState>({
        account_id: 0,
        symbol: '',
        exchange_code: '',
        direction: 'LONG',
        strategy_id: undefined,
        entry_price: '',
        quantity: '',
        entry_time: new Date().toISOString(),
        entry_reason: '',
        entry_emotion: '',
        entry_confidence: undefined,
        asset_type: '',
        // Phase 1: Plan Drift Detection
        planned_entry_price: '',
        planned_stop_loss: '',
        // Phase 1: Checklist Responses
        checklist_responses: {},
        metadata: {
            core_type: '',
            market: '',
            currency: 'USD',
            instrument: 'SPOT'
        }
    })
    const identitySnapshot = useMemo<PositionIdentityInput>(() => ({
        account_id: form.account_id,
        symbol: form.symbol,
        exchange_code: form.exchange_code,
        direction: form.direction,
        asset_type: form.asset_type,
        metadata: {
            market: form.metadata.market,
            currency: form.metadata.currency,
            instrument: form.metadata.instrument,
        },
    }), [
        form.account_id,
        form.symbol,
        form.exchange_code,
        form.direction,
        form.asset_type,
        form.metadata.market,
        form.metadata.currency,
        form.metadata.instrument,
    ])

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

    // Check for an existing lifecycle only when the complete identity is valid.
    useEffect(() => {
        let cancelled = false
        const clearExisting = () => {
            if (cancelled) return
            setExistingPosition(null)
            setShowExistingPrompt(false)
        }
        const checkExisting = async () => {
            const openIdentity = buildOpenIdentity(identitySnapshot)
            if (
                !token
                || !identitySnapshot.account_id
                || getIdentityValidationError(identitySnapshot)
                || !openIdentity
            ) {
                clearExisting()
                return
            }
            try {
                const existing = await positionsAPI.checkOpen(
                    token,
                    openIdentity,
                )
                if (cancelled) return
                if (existing) {
                    setExistingPosition(adaptPosition(existing))
                    setShowExistingPrompt(true)
                } else {
                    clearExisting()
                }
            } catch {
                clearExisting()
            }
        }
        const debounce = setTimeout(checkExisting, 500)
        return () => {
            cancelled = true
            clearTimeout(debounce)
        }
    }, [token, identitySnapshot])

    const prepareForSubmission = (candidate: NewPositionFormState): NormalizedNewPositionFormState | null => {
        if (!candidate.entry_price || !candidate.quantity) {
            setError('请输入价格和数量')
            return null
        }
        const identityError = getIdentityValidationError(candidate)
        if (identityError) {
            setError(identityError)
            return null
        }
        const normalizedForm = normalizeIdentityForm(candidate)
        if (!normalizedForm) {
            setError('标的身份不符合当前发布合同')
            return null
        }
        return normalizedForm
    }

    const submitPosition = async (candidate: NewPositionFormState) => {
        if (!token) return
        const finalForm = prepareForSubmission(candidate)
        if (!finalForm) return
        setError('')
        setIsSubmitting(true)

        try {
            const data: PositionCreate = {
                account_id: finalForm.account_id,
                symbol: finalForm.symbol,
                exchange_code: finalForm.exchange_code,
                direction: finalForm.direction,
                strategy_id: finalForm.strategy_id,
                entry_price: parseFloat(finalForm.entry_price),
                quantity: parseFloat(finalForm.quantity),
                entry_time: finalForm.entry_time,
                entry_reason: finalForm.entry_reason || undefined,
                entry_emotion: finalForm.entry_emotion || undefined,
                entry_confidence: finalForm.entry_confidence,
                asset_type: finalForm.asset_type,
                // Phase 1: Plan Drift Detection
                planned_entry_price: finalForm.planned_entry_price ? parseFloat(finalForm.planned_entry_price) : undefined,
                planned_stop_loss: finalForm.planned_stop_loss ? parseFloat(finalForm.planned_stop_loss) : undefined,
                // Phase 1: Checklist Responses
                checklist_responses: Object.keys(finalForm.checklist_responses).length > 0 ? finalForm.checklist_responses : undefined,
                asset_metadata: {
                    core_type: finalForm.metadata.core_type,
                    market: finalForm.metadata.market,
                    currency: finalForm.metadata.currency,
                    instrument: 'SPOT'
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

        const normalizedForm = prepareForSubmission(form)
        if (!normalizedForm) return
        setForm(normalizedForm)

        // Check if strategy has checklist items
        if (form.strategy_id) {
            const selectedStrategy = strategies.find(s => s.id === form.strategy_id)
            if (selectedStrategy && selectedStrategy.checklist_items && selectedStrategy.checklist_items.length > 0) {
                setShowChecklistModal(true)
                return
            }
        }

        // Directly submit if no checklist
        submitPosition(normalizedForm)
    }

    const handleChecklistConfirm = (responses: Record<string, boolean>) => {
        const updatedForm = { ...form, checklist_responses: responses }
        setForm(updatedForm)
        setShowChecklistModal(false)
        submitPosition(updatedForm)
    }

    const handleAddToExisting = async () => {
        if (!token || !existingPosition) return

        const normalizedForm = prepareForSubmission(form)
        if (!normalizedForm) return

        setError('')
        setIsAddingBatch(true)

        try {
            const openIdentity = buildOpenIdentity(normalizedForm)
            if (!openIdentity) {
                setError('标的身份不符合当前发布合同')
                return
            }
            const confirmed = await positionsAPI.checkOpen(
                token,
                openIdentity,
            )
            if (!confirmed || confirmed.public_id !== existingPosition.public_id) {
                setExistingPosition(null)
                setShowExistingPrompt(false)
                setError('已有仓位已变化，请重新确认标的身份')
                return
            }
            const targetPosition = adaptPosition(confirmed)
            const batchData: BatchCreate = {
                type: 'ENTRY',
                price: parseFloat(normalizedForm.entry_price),
                quantity: parseFloat(normalizedForm.quantity),
                time: normalizedForm.entry_time,
                reason: normalizedForm.entry_reason || undefined,
                emotion: normalizedForm.entry_emotion || undefined,
                confidence: normalizedForm.entry_confidence
            }

            const truthData = await positionsAPI.getTruthLifecycle(token, targetPosition.routeId).catch(() =>
                targetPosition.truth_position_public_id
                    ? positionsAPI.getTradingPositionLifecycle(token, targetPosition.truth_position_public_id).catch(() => null)
                    : null
            )
            const truthPositionPublicId = truthData?.data?.position_summary?.public_id

            if (truthPositionPublicId) {
                await positionsAPI.createTradingPositionTradeEvent(
                    token,
                    truthPositionPublicId,
                    buildTruthTradeEventFromBatchForm(batchData, targetPosition)
                )
                router.push(`/positions/${targetPosition.routeId}`)
            } else {
                const fallbackState = getTruthFirstWriteFallbackState(false, false)
                if (!fallbackState.canWriteLegacyFallback) {
                    setError(fallbackState.reason)
                    return
                }

                await positionsAPI.addBatch(token, targetPosition.routeId, batchData, { migrationFallback: true })
                router.push(`/positions/${targetPosition.routeId}`)
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
                                <Link
                                    href={`/positions/${existingPosition.routeId}`}
                                    className="btn flex-1 btn-outline border-warning/30 dark:border-warning/30 text-warning dark:text-warning hover:bg-warning/8 dark:hover:bg-warning/8"
                                >
                                    查看已有仓位
                                </Link>
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
                            <label className="block text-sm font-medium mb-2">标的代码 *</label>
                            <div className="relative">
                                <input
                                    required
                                    type="text"
                                    value={form.symbol}
                                    onChange={e => setForm({ ...form, symbol: e.target.value })}
                                    className="input uppercase"
                                    placeholder="AAPL, SPY, BTC/USD"
                                />
                            </div>
                        </div>
                    </div>

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
                    <div>
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
                    </div>

                    {/* Metadata Detail Section */}
                    <div className="pt-4 border-t border-line">
                        <div className="flex items-center gap-2 mb-4 text-ink-muted">
                            <Info className="w-4 h-4" />
                            <span className="text-xs font-semibold uppercase tracking-wider">标的身份</span>
                        </div>

                        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
                            <div>
                                <label className="block text-[10px] uppercase font-bold text-ink-faint mb-1">核心类型</label>
                                <CustomSelect
                                    size="sm"
                                    options={[
                                        { value: 'STOCK', label: '股票 (STOCK)' },
                                        { value: 'FUND', label: '基金 (FUND)' },
                                        { value: 'CRYPTO', label: '加密资产 (CRYPTO)' },
                                    ]}
                                    value={form.metadata.core_type}
                                    onChange={val => {
                                        const assetType = getReleaseAssetTypeSelection(val)
                                        setForm({
                                            ...form,
                                            asset_type: assetType,
                                            metadata: { ...form.metadata, core_type: assetType },
                                        })
                                    }}
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] uppercase font-bold text-ink-faint mb-1">市场</label>
                                <CustomSelect
                                    size="sm"
                                    options={[
                                        { value: 'US', label: '美股 (US)' },
                                        { value: 'CRYPTO', label: '加密市场 (CRYPTO)' },
                                    ]}
                                    value={form.metadata.market}
                                    onChange={val => setForm({
                                        ...form,
                                        metadata: { ...form.metadata, market: getReleaseMarketSelection(val) },
                                    })}
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] uppercase font-bold text-ink-faint mb-1">交易所代码 *</label>
                                <input
                                    required
                                    type="text"
                                    maxLength={32}
                                    value={form.exchange_code}
                                    onChange={e => setForm({ ...form, exchange_code: e.target.value })}
                                    className="input py-1 text-sm h-9 uppercase"
                                    placeholder="NASDAQ, NYSE, ARCA, COINBASE"
                                    autoCapitalize="characters"
                                    spellCheck={false}
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] uppercase font-bold text-ink-faint mb-1">计价货币</label>
                                <CustomSelect
                                    size="sm"
                                    options={[
                                        { value: 'USD', label: '美元 (USD)' },
                                    ]}
                                    value="USD"
                                    onChange={() => undefined}
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] uppercase font-bold text-ink-faint mb-1">工具类型</label>
                                <CustomSelect
                                    size="sm"
                                    options={[
                                        { value: 'SPOT', label: '现货 (SPOT)' },
                                    ]}
                                    value="SPOT"
                                    onChange={() => undefined}
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
                    disabled={isSubmitting || !!existingPosition}
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
