'use client'

import { useState, useEffect } from 'react'
import { useRouter, useParams, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import {
    ArrowLeft,
    Loader2,
    ArrowUpCircle,
    ArrowDownCircle
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { positionsAPI, Position, BatchCreate, marketAPI } from '@/lib/api'
import { buildTruthTradeEventFromBatchForm, getTruthFirstWriteFallbackState } from '@/lib/adapters/trading'
import DateTimePicker from '@/components/DateTimePicker'
import CustomSelect from '@/components/CustomSelect'

export default function AddBatchPage() {
    const { token } = useAuth()
    const router = useRouter()
    const params = useParams()
    const searchParams = useSearchParams()
    const positionId = params.id as string

    const [position, setPosition] = useState<Position | null>(null)
    const [truthPositionPublicId, setTruthPositionPublicId] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState('')

    // Initialize type from query param
    const initType = (searchParams.get('type') === 'EXIT') ? 'EXIT' : 'ENTRY'
    const migrationFallbackRequested = searchParams.get('migrationFallback') === '1'

    // Form state
    const [form, setForm] = useState({
        type: initType as 'ENTRY' | 'EXIT',
        price: '',
        quantity: '',
        time: new Date().toISOString(),
        reason: '',
        emotion: '',
        confidence: undefined as number | undefined
    })

    useEffect(() => {
        const fetchPosition = async () => {
            if (!token) return
            try {
                // 1. Get Position Details
                const data = await positionsAPI.get(token, positionId)
                setPosition(data)
                const truthData = await positionsAPI.getTradingPositionLifecycle(token, positionId).catch(() =>
                    positionsAPI.getTruthLifecycle(token, positionId).catch(() => null)
                )
                setTruthPositionPublicId(truthData?.data?.position_summary?.public_id || null)

                // 2. Try to get current market price to pre-fill
                if (data.status === 'OPEN') {
                    try {
                        const quote = await marketAPI.validateSymbol(token, data.symbol)
                        if (quote.valid && quote.price) {
                            setForm(prev => ({
                                ...prev,
                                price: quote.price ? quote.price.toString() : ''
                            }))
                        }
                    } catch (e) {
                        console.warn('Failed to fetch current price', e)
                    }
                }
            } catch (err: any) {
                setError(err.message || '加载失败')
            } finally {
                setIsLoading(false)
            }
        }
        fetchPosition()
    }, [token, positionId])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!token || !position) return

        setError('')
        setIsSubmitting(true)

        try {
            // Validate exit quantity
            if (form.type === 'EXIT') {
                const qty = parseFloat(form.quantity)
                if (qty > Number(position.total_quantity)) {
                    setError(`平仓数量不能超过当前持仓 (${position.total_quantity})`)
                    setIsSubmitting(false)
                    return
                }
            }

            const batchData: BatchCreate = {
                type: form.type,
                price: parseFloat(form.price),
                quantity: parseFloat(form.quantity),
                time: form.time,
                reason: form.reason || undefined,
                emotion: form.emotion || undefined,
                confidence: form.confidence
            }

            if (truthPositionPublicId) {
                await positionsAPI.createTradingPositionTradeEvent(
                    token,
                    truthPositionPublicId,
                    buildTruthTradeEventFromBatchForm(batchData, position)
                )
                router.push(`/positions/${truthPositionPublicId}`)
            } else {
                const fallbackState = getTruthFirstWriteFallbackState(false, migrationFallbackRequested)
                if (!fallbackState.canWriteLegacyFallback) {
                    setError(fallbackState.reason)
                    return
                }

                await positionsAPI.addBatch(token, positionId, batchData, { migrationFallback: true })
                router.push(`/positions`)
            }
        } catch (err: any) {
            setError(err.message || '操作失败')
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

    if (!position) {
        return (
            <div className="card p-12 text-center">
                <p className="text-slate-500 mb-4">找不到该持仓</p>
                <Link href="/positions" className="btn btn-primary inline-flex">
                    返回列表
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
                <div>
                    <h1 className="text-2xl font-bold">加仓 / 平仓</h1>
                    <p className="text-sm text-slate-500">
                        {position.symbol} · 当前持有 {Number(position.total_quantity).toFixed(4)} 份 @ ${Number(position.average_entry_price || 0).toFixed(2)}
                    </p>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="mb-6 p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600">
                    {error}
                </div>
            )}

            {truthPositionPublicId && (
                <div className="mb-6 rounded-xl border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-900 dark:border-cyan-900 dark:bg-cyan-950/30 dark:text-cyan-200">
                    <p className="font-semibold">Truth write path</p>
                    <p className="mt-1">
                        本次操作会写入 TradingPosition / PositionEvent。legacy batch migration fallback 只在 truth lifecycle 缺失并显式请求时使用。
                    </p>
                </div>
            )}

            {!truthPositionPublicId && (
                <div className="mb-6 rounded-xl border border-amber-200 bg-amber-50 p-4 text-sm text-amber-800 dark:border-amber-800 dark:bg-amber-900/20 dark:text-amber-200">
                    <p className="font-semibold">
                        {getTruthFirstWriteFallbackState(false, migrationFallbackRequested).label}
                    </p>
                    <p className="mt-1">
                        {getTruthFirstWriteFallbackState(false, migrationFallbackRequested).reason}
                    </p>
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
                {/* Batch Type */}
                <div className="card p-6 space-y-4">
                    <label className="block text-sm font-medium mb-2">操作类型 *</label>
                    <div className="grid grid-cols-2 gap-3">
                        <button
                            type="button"
                            onClick={() => setForm({ ...form, type: 'ENTRY' })}
                            className={`p-4 rounded-xl border-2 transition-all flex items-center justify-center gap-2 ${form.type === 'ENTRY'
                                ? 'border-emerald-500 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600'
                                : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                                }`}
                        >
                            <ArrowUpCircle className="w-5 h-5" />
                            <span className="font-medium">加仓</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => setForm({ ...form, type: 'EXIT' })}
                            className={`p-4 rounded-xl border-2 transition-all flex items-center justify-center gap-2 ${form.type === 'EXIT'
                                ? 'border-amber-500 bg-amber-50 dark:bg-amber-900/20 text-amber-600'
                                : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                                }`}
                        >
                            <ArrowDownCircle className="w-5 h-5" />
                            <span className="font-medium">平仓</span>
                        </button>
                    </div>
                </div>

                {/* Details */}
                <div className="card p-6 space-y-4">
                    <h2 className="font-semibold">{form.type === 'ENTRY' ? '加仓' : '平仓'}信息</h2>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">价格 *</label>
                            <input
                                required
                                type="number"
                                step="any"
                                value={form.price}
                                onChange={e => setForm({ ...form, price: e.target.value })}
                                className="input"
                                placeholder="0.00"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">
                                数量 *
                                {form.type === 'EXIT' && (
                                    <span className="text-slate-400 font-normal ml-2">
                                        (最多 {Number(position.total_quantity).toFixed(4)})
                                    </span>
                                )}
                            </label>
                            <input
                                required
                                type="number"
                                step="any"
                                value={form.quantity}
                                onChange={e => setForm({ ...form, quantity: e.target.value })}
                                className="input"
                                placeholder="0"
                                max={form.type === 'EXIT' ? Number(position.total_quantity) : undefined}
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">时间 *</label>
                        <DateTimePicker
                            value={form.time}
                            onChange={(val) => setForm({ ...form, time: val })}
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">理由</label>
                        <textarea
                            value={form.reason}
                            onChange={e => setForm({ ...form, reason: e.target.value })}
                            className="input"
                            rows={3}
                            placeholder={form.type === 'ENTRY' ? '为什么加仓？' : '为什么平仓/止盈/止损？'}
                        />
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">情绪</label>
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
                                value={form.emotion}
                                onChange={val => setForm({ ...form, emotion: val as string })}
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
                                value={form.confidence || ''}
                                onChange={val => setForm({ ...form, confidence: val ? (typeof val === 'string' ? parseInt(val) : val) : undefined })}
                                placeholder="交易信心"
                            />
                        </div>
                    </div>
                </div>

                {/* Submit */}
                <button
                    type="submit"
                    disabled={isSubmitting}
                    className={`w-full btn py-3 ${form.type === 'ENTRY'
                        ? 'bg-emerald-500 hover:bg-emerald-600 text-white'
                        : 'bg-amber-500 hover:bg-amber-600 text-white'
                        }`}
                >
                    {isSubmitting ? (
                        <Loader2 className="w-5 h-5 animate-spin mx-auto" />
                    ) : (
                        form.type === 'ENTRY' ? '确认加仓' : '确认平仓'
                    )}
                </button>
            </form>
        </div>
    )
}
