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
    TradingAccount, Strategy, Position, PositionCreate, BatchCreate, SymbolValidation
} from '@/lib/api'
import { detectSymbolType, getAssetTypeColor, getAssetTypeLabel, SymbolDetection } from '@/lib/symbolUtils'
import DateTimePicker from '@/components/DateTimePicker'

export default function NewPositionPage() {
    const { token } = useAuth()
    const router = useRouter()

    const [accounts, setAccounts] = useState<TradingAccount[]>([])
    const [strategies, setStrategies] = useState<Strategy[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState('')

    // Existing position check
    const [existingPosition, setExistingPosition] = useState<Position | null>(null)
    const [showExistingPrompt, setShowExistingPrompt] = useState(false)

    // Symbol validation
    const [symbolValidation, setSymbolValidation] = useState<SymbolValidation | null>(null)
    const [isValidating, setIsValidating] = useState(false)
    const [symbolDetection, setSymbolDetection] = useState<SymbolDetection | null>(null)

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
        entry_confidence: undefined as number | undefined
    })

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return
            try {
                const [accountsData, strategiesData] = await Promise.all([
                    accountsAPI.list(token),
                    strategiesAPI.list(token)
                ])
                setAccounts(accountsData)
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
                    setExistingPosition(existing)
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

    // Validate symbol when it changes
    useEffect(() => {
        // Step 1: Frontend format detection
        const detection = detectSymbolType(form.symbol)
        setSymbolDetection(detection)

        // Step 2: Only call API if format is recognized
        const validateSymbol = async () => {
            if (!token || !form.symbol || form.symbol.length < 2) {
                setSymbolValidation(null)
                return
            }

            // Skip API if format is unknown
            if (detection.type === 'unknown') {
                setSymbolValidation({
                    valid: false,
                    symbol: form.symbol,
                    error: '未知格式，请检查代码'
                })
                return
            }

            setIsValidating(true)
            try {
                // Fix: use detection.symbol instead of undefined detection.normalized
                const result = await marketAPI.validateSymbol(token, detection.symbol)
                setSymbolValidation(result)
            } catch {
                setSymbolValidation({ valid: false, symbol: form.symbol, error: '验证失败' })
            } finally {
                setIsValidating(false)
            }
        }
        const debounce = setTimeout(validateSymbol, 300)
        return () => clearTimeout(debounce)
    }, [token, form.symbol])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!token) return

        setError('')
        setIsSubmitting(true)

        try {
            const data: PositionCreate = {
                account_id: form.account_id,
                symbol: form.symbol.toUpperCase(),
                direction: form.direction,
                strategy_id: form.strategy_id,
                entry_price: parseFloat(form.entry_price),
                quantity: parseFloat(form.quantity),
                entry_time: form.entry_time,
                entry_reason: form.entry_reason || undefined,
                entry_emotion: form.entry_emotion || undefined,
                entry_confidence: form.entry_confidence
            }

            await positionsAPI.create(token, data)
            router.push('/positions')
        } catch (err: any) {
            setError(err.message || '创建失败')
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleAddToExisting = async () => {
        if (!token || !existingPosition) return

        setError('')
        setIsSubmitting(true)

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

            await positionsAPI.addBatch(token, existingPosition.id, batchData)
            router.push(`/positions/${existingPosition.id}`)
        } catch (err: any) {
            setError(err.message || '加仓失败')
        } finally {
            setIsSubmitting(false)
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (accounts.length === 0) {
        return (
            <div className="card p-12 text-center">
                <p className="text-slate-500 mb-4">请先在设置中添加交易账户</p>
                <Link href="/settings" className="btn btn-primary inline-flex">
                    前往设置
                </Link>
            </div>
        )
    }

    return (
        <div className="max-w-2xl mx-auto pb-20 md:pb-6">
            {/* Header */}
            <div className="flex items-center gap-4 mb-6">
                <Link href="/positions" className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800">
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <h1 className="text-2xl font-bold">新增交易</h1>
            </div>

            {/* Error */}
            {error && (
                <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600">
                    {error}
                </div>
            )}

            {/* Existing Position Prompt */}
            {showExistingPrompt && existingPosition && (
                <div className="mb-6 p-4 rounded-xl bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800">
                    <div className="flex items-start gap-3">
                        <AlertCircle className="w-5 h-5 text-amber-500 mt-0.5" />
                        <div className="flex-1">
                            <h3 className="font-medium text-amber-800 dark:text-amber-200">
                                您已有 {existingPosition.symbol} 的持仓
                            </h3>
                            <p className="text-sm text-amber-600 dark:text-amber-300 mt-1">
                                当前持有 {Number(existingPosition.total_quantity).toFixed(4)} 份，
                                均价 ${Number(existingPosition.average_entry_price || 0).toFixed(2)}
                            </p>
                            <div className="flex gap-2 mt-3">
                                <button
                                    type="button"
                                    onClick={handleAddToExisting}
                                    disabled={isSubmitting || !form.entry_price || !form.quantity}
                                    className="btn btn-sm bg-amber-500 hover:bg-amber-600 text-white"
                                >
                                    加仓到此仓位
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setShowExistingPrompt(false)}
                                    className="btn btn-sm btn-outline"
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
                <div className="card p-6 space-y-4">
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">账户 *</label>
                            <select
                                required
                                value={form.account_id}
                                onChange={e => setForm({ ...form, account_id: parseInt(e.target.value) })}
                                className="input"
                            >
                                {accounts.map(a => (
                                    <option key={a.id} value={a.id}>{a.name} ({a.broker})</option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">
                                标的代码 *
                                {symbolDetection && symbolDetection.type !== 'unknown' && (
                                    <span className={`ml-2 px-2 py-0.5 text-xs rounded-full ${getAssetTypeColor(symbolDetection.type)}`}>
                                        {/* Fix 2: Use getAssetTypeLabel or displayName */}
                                        {getAssetTypeLabel(symbolDetection.type)}
                                    </span>
                                )}
                            </label>
                            <div className="relative">
                                <input
                                    required
                                    type="text"
                                    value={form.symbol}
                                    onChange={e => setForm({ ...form, symbol: e.target.value.toUpperCase() })}
                                    className={`input uppercase pr-10 ${symbolValidation?.valid === false ? 'border-red-500' : symbolValidation?.valid ? 'border-emerald-500' : ''}`}
                                    placeholder="AAPL, 600519, BTCUSDT, 00700"
                                />
                                <div className="absolute right-3 top-1/2 -translate-y-1/2">
                                    {isValidating && <Loader2 className="w-4 h-4 animate-spin text-slate-400" />}
                                    {!isValidating && symbolValidation?.valid && (
                                        <span className="text-emerald-500">✓</span>
                                    )}
                                    {!isValidating && symbolValidation?.valid === false && (
                                        <span className="text-red-500">✗</span>
                                    )}
                                </div>
                            </div>
                            {/* Candidates Selection */}
                            {symbolValidation?.candidates && symbolValidation.candidates.length > 0 && (
                                <div className="mt-3">
                                    <p className="text-xs text-slate-500 mb-2">您是不是想找：</p>
                                    <div className="flex flex-wrap gap-2">
                                        {symbolValidation.candidates.map((c, idx) => (
                                            <button
                                                key={idx}
                                                type="button"
                                                onClick={() => setForm({ ...form, symbol: c.symbol })}
                                                className="px-3 py-1.5 rounded-lg text-sm bg-primary-50 dark:bg-primary-900/20 text-primary-600 dark:text-primary-400 hover:bg-primary-100 dark:hover:bg-primary-900/30 transition-colors border border-primary-100 dark:border-primary-800"
                                            >
                                                <span className="font-medium">{c.symbol}</span>
                                                <span className="ml-1.5 text-xs opacity-70">({c.reason})</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Format hint for unknown only if no candidates */}
                            {symbolDetection && symbolDetection.type === 'unknown' && (!symbolValidation?.candidates || symbolValidation.candidates.length === 0) && form.symbol.length > 0 && (
                                <p className="text-xs mt-1 text-amber-600">
                                    格式提示: A股(6位数字) | 港股(5位数字) | 美股(字母) | 加密(XXXUSDT)
                                </p>
                            )}
                            {symbolValidation && (
                                <p className={`text-xs mt-1 ${symbolValidation.valid ? 'text-emerald-600' : 'text-red-500'}`}>
                                    {symbolValidation.valid ? (
                                        <>
                                            <span className="font-semibold">{symbolValidation.name || symbolValidation.symbol}</span>
                                            <span className="mx-2 text-slate-300">|</span>
                                            <span>
                                                {symbolValidation.asset_type === 'A_STOCK' ? '¥' :
                                                    symbolValidation.asset_type === 'HK_STOCK' ? 'HK$' :
                                                        symbolValidation.asset_type === 'US_STOCK' ? '$' : ''}
                                                {symbolValidation.price?.toFixed(2) || '-'}
                                                {symbolValidation.asset_type === 'CRYPTO' ? ' USDT' : ''}
                                            </span>
                                        </>
                                    ) : (
                                        symbolValidation.error
                                    )}
                                </p>
                            )}
                        </div>
                    </div>

                    {/* Direction */}
                    <div>
                        <label className="block text-sm font-medium mb-2">方向 *</label>
                        <div className="grid grid-cols-2 gap-3">
                            <button
                                type="button"
                                onClick={() => setForm({ ...form, direction: 'LONG' })}
                                className={`p-4 rounded-xl border-2 transition-all flex items-center justify-center gap-2 ${form.direction === 'LONG'
                                    ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600'
                                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                                    }`}
                            >
                                <ArrowUpCircle className="w-5 h-5" />
                                <span className="font-medium">做多 (LONG)</span>
                            </button>
                            <button
                                type="button"
                                onClick={() => setForm({ ...form, direction: 'SHORT' })}
                                className={`p-4 rounded-xl border-2 transition-all flex items-center justify-center gap-2 ${form.direction === 'SHORT'
                                    ? 'border-red-500 bg-red-50 dark:bg-red-900/20 text-red-600'
                                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                                    }`}
                            >
                                <ArrowDownCircle className="w-5 h-5" />
                                <span className="font-medium">做空 (SHORT)</span>
                            </button>
                        </div>
                    </div>

                    {/* Strategy */}
                    <div>
                        <label className="block text-sm font-medium mb-2">策略 (可选)</label>
                        <select
                            value={form.strategy_id || ''}
                            onChange={e => setForm({ ...form, strategy_id: e.target.value ? parseInt(e.target.value) : undefined })}
                            className="input"
                        >
                            <option value="">不关联策略</option>
                            {strategies.map(s => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Entry Details */}
                <div className="card p-6 space-y-4">
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
                            <select
                                value={form.entry_emotion}
                                onChange={e => setForm({ ...form, entry_emotion: e.target.value })}
                                className="input"
                            >
                                <option value="">选择情绪</option>
                                <option value="confident">自信 😎</option>
                                <option value="calm">平静 😌</option>
                                <option value="excited">兴奋 🤩</option>
                                <option value="anxious">焦虑 😰</option>
                                <option value="fomo">FOMO 😱</option>
                                <option value="revenge">报复交易 😤</option>
                            </select>
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">信心指数</label>
                            <select
                                value={form.entry_confidence || ''}
                                onChange={e => setForm({ ...form, entry_confidence: e.target.value ? parseInt(e.target.value) : undefined })}
                                className="input"
                            >
                                <option value="">选择信心</option>
                                <option value="1">1 - 很低</option>
                                <option value="2">2 - 较低</option>
                                <option value="3">3 - 一般</option>
                                <option value="4">4 - 较高</option>
                                <option value="5">5 - 非常高</option>
                            </select>
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
        </div>
    )
}
