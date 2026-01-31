'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import {
    ArrowLeft,
    Save,
    TrendingUp,
    DollarSign,
    Calendar,
    FileText,
    Heart,
    Target,
    Loader2
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { tradesAPI, strategiesAPI, Strategy } from '@/lib/api'

interface TradeForm {
    symbol: string
    exchange: 'IBKR' | 'Binance'
    entry_price: string
    quantity: string
    entry_time: string
    entry_reason: string
    entry_emotion: string
    entry_confidence: number
    strategy_id: string
}

const emotions = ['平静', '兴奋', '紧张', '谨慎', '贪婪', '恐惧', '犹豫', '自信']

export default function NewTradePage() {
    const router = useRouter()
    const { token } = useAuth()
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState('')
    const [strategies, setStrategies] = useState<Strategy[]>([])
    const [form, setForm] = useState<TradeForm>({
        symbol: '',
        exchange: 'IBKR',
        entry_price: '',
        quantity: '',
        entry_time: new Date().toISOString().slice(0, 16),
        entry_reason: '',
        entry_emotion: '平静',
        entry_confidence: 3,
        strategy_id: '',
    })

    // 加载策略列表
    useEffect(() => {
        const fetchStrategies = async () => {
            if (!token) return
            try {
                const data = await strategiesAPI.list(token)
                setStrategies(data)
            } catch (err) {
                // 忽略错误，策略列表非必需
            }
        }
        fetchStrategies()
    }, [token])

    const updateForm = (key: keyof TradeForm, value: string | number) => {
        setForm((prev) => ({ ...prev, [key]: value }))
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!token) return

        setError('')
        setIsSubmitting(true)

        try {
            await tradesAPI.create(token, {
                symbol: form.symbol,
                exchange: form.exchange,
                entry_price: parseFloat(form.entry_price),
                quantity: parseFloat(form.quantity),
                entry_time: form.entry_time,
                entry_reason: form.entry_reason || undefined,
                entry_emotion: form.entry_emotion || undefined,
                entry_confidence: form.entry_confidence,
                strategy_id: form.strategy_id ? parseInt(form.strategy_id) : undefined,
            })
            router.push('/trades')
        } catch (err: any) {
            setError(err.message || '创建交易失败')
        } finally {
            setIsSubmitting(false)
        }
    }

    return (
        <div className="max-w-2xl mx-auto space-y-6 pb-20 md:pb-6">
            {/* Header */}
            <div className="flex items-center space-x-4">
                <Link
                    href="/trades"
                    className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                >
                    <ArrowLeft className="w-5 h-5" />
                </Link>
                <h1 className="text-2xl font-bold">新增交易</h1>
            </div>

            {/* Error */}
            {error && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600">
                    {error}
                </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-6">
                {/* Basic Info */}
                <div className="card p-6 space-y-4">
                    <div className="flex items-center space-x-2 mb-2">
                        <TrendingUp className="w-5 h-5 text-primary-500" />
                        <h2 className="font-semibold">基本信息</h2>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2 sm:col-span-1">
                            <label className="block text-sm font-medium mb-2">交易标的 *</label>
                            <input
                                type="text"
                                required
                                value={form.symbol}
                                onChange={(e) => updateForm('symbol', e.target.value.toUpperCase())}
                                className="input"
                                placeholder="AAPL, BTC/USDT..."
                            />
                        </div>
                        <div className="col-span-2 sm:col-span-1">
                            <label className="block text-sm font-medium mb-2">交易所 *</label>
                            <select
                                value={form.exchange}
                                onChange={(e) => updateForm('exchange', e.target.value)}
                                className="input"
                            >
                                <option value="IBKR">IBKR 盈透证券</option>
                                <option value="Binance">Binance 币安</option>
                            </select>
                        </div>
                    </div>

                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">
                                <DollarSign className="w-4 h-4 inline mr-1" />
                                入场价格 *
                            </label>
                            <input
                                type="number"
                                required
                                step="any"
                                value={form.entry_price}
                                onChange={(e) => updateForm('entry_price', e.target.value)}
                                className="input"
                                placeholder="0.00"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">数量 *</label>
                            <input
                                type="number"
                                required
                                step="any"
                                value={form.quantity}
                                onChange={(e) => updateForm('quantity', e.target.value)}
                                className="input"
                                placeholder="0"
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">
                            <Calendar className="w-4 h-4 inline mr-1" />
                            入场时间 *
                        </label>
                        <input
                            type="datetime-local"
                            required
                            value={form.entry_time}
                            onChange={(e) => updateForm('entry_time', e.target.value)}
                            className="input"
                        />
                    </div>
                </div>

                {/* Trading Decision */}
                <div className="card p-6 space-y-4">
                    <div className="flex items-center space-x-2 mb-2">
                        <FileText className="w-5 h-5 text-indigo-500" />
                        <h2 className="font-semibold">交易决策</h2>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">入场理由</label>
                        <textarea
                            value={form.entry_reason}
                            onChange={(e) => updateForm('entry_reason', e.target.value)}
                            className="input min-h-[100px]"
                            placeholder="描述你的入场逻辑，例如：突破前高，量能放大..."
                        />
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">关联策略</label>
                        <select
                            value={form.strategy_id}
                            onChange={(e) => updateForm('strategy_id', e.target.value)}
                            className="input"
                        >
                            <option value="">无</option>
                            {strategies.map((s) => (
                                <option key={s.id} value={s.id}>{s.name}</option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* Psychology */}
                <div className="card p-6 space-y-4">
                    <div className="flex items-center space-x-2 mb-2">
                        <Heart className="w-5 h-5 text-rose-500" />
                        <h2 className="font-semibold">心理状态</h2>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">入场时情绪</label>
                        <div className="flex flex-wrap gap-2">
                            {emotions.map((emotion) => (
                                <button
                                    key={emotion}
                                    type="button"
                                    onClick={() => updateForm('entry_emotion', emotion)}
                                    className={`px-3 py-1.5 rounded-full text-sm transition-all ${form.entry_emotion === emotion
                                            ? 'bg-primary-500 text-white'
                                            : 'bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600'
                                        }`}
                                >
                                    {emotion}
                                </button>
                            ))}
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium mb-2">
                            <Target className="w-4 h-4 inline mr-1" />
                            信心程度
                        </label>
                        <div className="flex items-center space-x-4">
                            <input
                                type="range"
                                min="1"
                                max="5"
                                value={form.entry_confidence}
                                onChange={(e) => updateForm('entry_confidence', Number(e.target.value))}
                                className="flex-1"
                            />
                            <span className="w-8 text-center font-semibold text-primary-500">
                                {form.entry_confidence}
                            </span>
                        </div>
                        <div className="flex justify-between text-xs text-slate-500 mt-1">
                            <span>不确定</span>
                            <span>非常自信</span>
                        </div>
                    </div>
                </div>

                {/* Submit */}
                <button
                    type="submit"
                    disabled={isSubmitting}
                    className="w-full btn btn-primary py-3 flex items-center justify-center space-x-2"
                >
                    {isSubmitting ? (
                        <Loader2 className="w-5 h-5 animate-spin" />
                    ) : (
                        <Save className="w-5 h-5" />
                    )}
                    <span>{isSubmitting ? '保存中...' : '保存交易'}</span>
                </button>
            </form>
        </div>
    )
}
