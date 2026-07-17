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
import { positionsAPI, Position, BatchCreate } from '@/lib/api'
import { buildTruthTradeEventFromBatchForm } from '@/lib/adapters/trading'
import { adaptLifecycleDetail, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'
import { getCurrencySymbol } from '@/lib/symbolUtils'
import DateTimePicker from '@/components/DateTimePicker'
import CustomSelect from '@/components/CustomSelect'

const TRUTH_LIFECYCLE_REQUIRED_LABEL = '审计生命周期不可用'
const TRUTH_LIFECYCLE_REQUIRED_REASON = '普通加仓和平仓必须写入审计生命周期；旧版批次写入已从产品入口关闭。'

export default function AddBatchPage() {
    const { token } = useAuth()
    const router = useRouter()
    const params = useParams()
    const searchParams = useSearchParams()
    const positionId = params.id as string

    const [position, setPosition] = useState<Position | null>(null)
    const [truthLifecycle, setTruthLifecycle] = useState<LifecycleDetailViewModel | null>(null)
    const [truthPositionPublicId, setTruthPositionPublicId] = useState<string | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState('')

    // Initialize type from query param
    const initType = (searchParams.get('type') === 'EXIT') ? 'EXIT' : 'ENTRY'
    const currentOpenQuantity = truthLifecycle?.openQuantity ?? Number(position?.total_quantity || 0)
    const currentAverageOpenPrice = truthLifecycle?.averageOpenPrice ?? Number(position?.average_entry_price || 0)
    const currencySymbol = getCurrencySymbol(truthLifecycle?.baseCurrency || position?.asset_metadata?.currency)

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
                const data = await positionsAPI.get(token, positionId)
                setPosition(data)
                const truthData = await positionsAPI.getTruthLifecycle(token, data.public_id).catch(() =>
                    data.truth_position_public_id
                        ? positionsAPI.getTradingPositionLifecycle(token, data.truth_position_public_id).catch(() => null)
                        : null
                )
                const lifecycle = truthData ? adaptLifecycleDetail(truthData) : null
                setTruthLifecycle(lifecycle)
                setTruthPositionPublicId(lifecycle?.truthPositionPublicId || null)
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
                if (qty > currentOpenQuantity) {
                    setError(`平仓数量不能超过当前持仓 (${currentOpenQuantity})`)
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
                    buildTruthTradeEventFromBatchForm(batchData, {
                        total_quantity: currentOpenQuantity,
                        asset_metadata: position.asset_metadata,
                    })
                )
                router.push(`/positions/${position.public_id}`)
            } else {
                setError(TRUTH_LIFECYCLE_REQUIRED_REASON)
                return
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
                <Loader2 className="w-8 h-8 animate-spin text-ink-muted" />
            </div>
        )
    }

    if (!position) {
        return (
            <div className="rounded-lg border border-line bg-panel p-12 text-center shadow-panel dark:shadow-none">
                <p className="text-ink-muted mb-4">找不到该持仓</p>
                <Link href="/positions" className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft">
                    返回列表
                </Link>
            </div>
        )
    }

    return (
        <div className="max-w-2xl mx-auto pb-20 md:pb-6">
            {/* Header */}
            <div className="flex items-center gap-4 mb-6">
                <Link
                    href={`/positions/${position.public_id}`}
                    aria-label="返回持仓详情"
                    title="返回持仓详情"
                    className="p-2 rounded-lg hover:bg-panel-subtle"
                >
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <div>
                    <h1 className="text-2xl font-bold">加仓 / 平仓</h1>
                    <p className="text-sm text-ink-muted">
                        {position.symbol} · 当前持有 {currentOpenQuantity.toFixed(4)} 份 @ {currencySymbol}{currentAverageOpenPrice.toFixed(2)}
                    </p>
                </div>
            </div>

            {/* Error */}
            {error && (
                <div className="mb-6 p-4 rounded-md bg-loss/8 dark:bg-loss/8 text-loss">
                    {error}
                </div>
            )}

            {truthPositionPublicId && (
                <div className="mb-6 rounded-md border border-cyan-200 bg-cyan-50 p-4 text-sm text-cyan-900 dark:border-cyan-900 dark:bg-cyan-950/30 dark:text-cyan-200">
                    <p className="font-semibold">审计事件写入</p>
                    <p className="mt-1">
                        本次操作只会写入权威审计生命周期，不会写入旧版批次记录。
                    </p>
                </div>
            )}

            {!truthPositionPublicId && (
                <div className="mb-6 rounded-md border border-warning/30 bg-warning/8 p-4 text-sm text-warning dark:border-warning/30 dark:bg-warning/8 dark:text-warning">
                    <p className="font-semibold">
                        {TRUTH_LIFECYCLE_REQUIRED_LABEL}
                    </p>
                    <p className="mt-1">
                        {TRUTH_LIFECYCLE_REQUIRED_REASON}
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
                            className={`p-4 rounded-md border-2 transition-all flex items-center justify-center gap-2 ${form.type === 'ENTRY'
                                ? 'border-profit/30 bg-profit/8 dark:bg-profit/8 text-profit'
                                : 'border-line hover:border-line-strong'
                                }`}
                        >
                            <ArrowUpCircle className="w-5 h-5" />
                            <span className="font-medium">加仓</span>
                        </button>
                        <button
                            type="button"
                            onClick={() => setForm({ ...form, type: 'EXIT' })}
                            className={`p-4 rounded-md border-2 transition-all flex items-center justify-center gap-2 ${form.type === 'EXIT'
                                ? 'border-warning/30 bg-warning/8 dark:bg-warning/8 text-warning'
                                : 'border-line hover:border-line-strong'
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
                                    <span className="text-ink-faint font-normal ml-2">
                                        (最多 {currentOpenQuantity.toFixed(4)})
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
                                max={form.type === 'EXIT' ? currentOpenQuantity : undefined}
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
                    disabled={isSubmitting || !truthPositionPublicId}
                    className={`w-full btn py-3 ${form.type === 'ENTRY'
                        ? 'bg-profit text-white hover:opacity-90'
                        : 'bg-warning text-white hover:opacity-90'
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
