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
import { tradesAPI, strategiesAPI, accountsAPI, Strategy, TradingAccount } from '@/lib/api'
import DateTimePicker from '@/components/DateTimePicker'

interface TradeForm {
    symbol: string
    account_id: string // Start as string for select input
    status: 'OPEN' | 'CLOSED'
    entry_price: string
    quantity: string
    entry_time: string
    entry_reason: string
    entry_emotion: string
    entry_confidence: number
    strategy_id: string
    // 平仓信息（当 status=CLOSED 时使用）
    exit_price: string
    exit_time: string
}

const emotions = ['平静', '兴奋', '紧张', '谨慎', '贪婪', '恐惧', '犹豫', '自信']

export default function NewTradePage() {
    const router = useRouter()
    const { token } = useAuth()
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [error, setError] = useState('')
    const [strategies, setStrategies] = useState<Strategy[]>([])
    const [accounts, setAccounts] = useState<TradingAccount[]>([])
    const [form, setForm] = useState<TradeForm>({
        symbol: '',
        account_id: '',
        status: 'OPEN',
        entry_price: '',
        quantity: '',
        entry_time: new Date().toISOString().slice(0, 16),
        entry_reason: '',
        entry_emotion: '平静',
        entry_confidence: 3,
        strategy_id: '',
        exit_price: '',
        exit_time: new Date().toISOString().slice(0, 16),
    })

    // 加载策略和账户列表
    useEffect(() => {
        const fetchData = async () => {
            if (!token) return
            try {
                const [strategiesData, accountsData] = await Promise.all([
                    strategiesAPI.list(token),
                    accountsAPI.list(token)
                ])
                setStrategies(strategiesData)
                setAccounts(accountsData)

                // 默认选中第一个账户
                if (accountsData.length > 0) {
                    setForm(prev => ({ ...prev, account_id: accountsData[0].id.toString() }))
                }
            } catch (err) {
                // 忽略错误
            }
        }
        fetchData()
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
                account_id: parseInt(form.account_id),
                status: form.status,
                entry_price: parseFloat(form.entry_price),
                quantity: parseFloat(form.quantity),
                entry_time: form.entry_time,
                entry_reason: form.entry_reason || undefined,
                entry_emotion: form.entry_emotion || undefined,
                entry_confidence: form.entry_confidence,
                strategy_id: form.strategy_id ? parseInt(form.strategy_id) : undefined,
                // 平仓信息（仅当已平仓时）
                exit_price: form.status === 'CLOSED' ? parseFloat(form.exit_price) : undefined,
                exit_time: form.status === 'CLOSED' ? form.exit_time : undefined,
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
                            <label className="block text-sm font-medium mb-2">交易账户 *</label>
                            <select
                                required
                                value={form.account_id}
                                onChange={(e) => updateForm('account_id', e.target.value)}
                                className="input"
                            >
                                <option value="" disabled>选择账户</option>
                                {accounts.map((account) => (
                                    <option key={account.id} value={account.id}>
                                        {account.name} ({account.broker})
                                    </option>
                                ))}
                            </select>
                            {accounts.length === 0 && (
                                <p className="text-xs text-amber-500 mt-1">
                                    暂无可用账户，请先在设置中添加
                                </p>
                            )}
                        </div>
                    </div>

                    {/* 交易状态选择 */}
                    <div>
                        <label className="block text-sm font-medium mb-2">交易状态 *</label>
                        <div className="flex gap-4">
                            <button
                                type="button"
                                onClick={() => updateForm('status', 'OPEN')}
                                className={`flex-1 py-3 px-4 rounded-xl border-2 transition-all ${form.status === 'OPEN'
                                    ? 'border-blue-500 bg-blue-50 dark:bg-blue-900/20 text-blue-600'
                                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                                    }`}
                            >
                                <div className="font-medium">🔵 持仓中</div>
                                <div className="text-xs text-slate-500 mt-1">记录开仓，稍后平仓</div>
                            </button>
                            <button
                                type="button"
                                onClick={() => updateForm('status', 'CLOSED')}
                                className={`flex-1 py-3 px-4 rounded-xl border-2 transition-all ${form.status === 'CLOSED'
                                    ? 'border-green-500 bg-green-50 dark:bg-green-900/20 text-green-600'
                                    : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                                    }`}
                            >
                                <div className="font-medium">✅ 已平仓</div>
                                <div className="text-xs text-slate-500 mt-1">记录完整交易</div>
                            </button>
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
                        <DateTimePicker
                            label="入场时间"
                            required
                            value={form.entry_time}
                            onChange={(val) => updateForm('entry_time', val)}
                        />
                    </div>

                    {/* 平仓信息 - 仅在已平仓时显示 */}
                    {form.status === 'CLOSED' && (
                        <div className="p-4 rounded-xl bg-green-50 dark:bg-green-900/10 border border-green-200 dark:border-green-800 space-y-4">
                            <div className="text-sm font-medium text-green-700 dark:text-green-400">
                                📊 平仓信息
                            </div>
                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <label className="block text-sm font-medium mb-2">
                                        <DollarSign className="w-4 h-4 inline mr-1" />
                                        平仓价格 *
                                    </label>
                                    <input
                                        type="number"
                                        required={form.status === 'CLOSED'}
                                        step="any"
                                        value={form.exit_price}
                                        onChange={(e) => updateForm('exit_price', e.target.value)}
                                        className="input"
                                        placeholder="0.00"
                                    />
                                </div>
                                <div>
                                    <DateTimePicker
                                        label="出场时间"
                                        required={form.status === 'CLOSED'}
                                        value={form.exit_time}
                                        onChange={(val) => updateForm('exit_time', val)}
                                    />
                                </div>
                            </div>
                        </div>
                    )}
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
