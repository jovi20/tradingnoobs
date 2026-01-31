'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
    ArrowLeft,
    TrendingUp,
    TrendingDown,
    Edit2,
    Trash2,
    DollarSign,
    Calendar,
    FileText,
    Heart,
    Target,
    Camera,
    X,
    Check,
    AlertTriangle,
    Loader2
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { Trade, tradesAPI } from '@/lib/api'

const emotions = ['平静', '兴奋', '紧张', '谨慎', '贪婪', '恐惧', '犹豫', '自信', '满足', '后悔', '焦虑']

export default function TradeDetailPage() {
    const params = useParams()
    const router = useRouter()
    const { token } = useAuth()
    const tradeId = parseInt(params.id as string)

    const [trade, setTrade] = useState<Trade | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState('')
    const [showCloseModal, setShowCloseModal] = useState(false)
    const [isClosing, setIsClosing] = useState(false)
    const [isDeleting, setIsDeleting] = useState(false)
    const [closeForm, setCloseForm] = useState({
        exit_price: '',
        exit_reason: '',
        exit_emotion: '平静',
        trade_review: '',
        rating: 3,
    })

    useEffect(() => {
        const fetchTrade = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                const data = await tradesAPI.get(token, tradeId)
                setTrade(data)
            } catch (err: any) {
                setError(err.message || '加载失败')
            } finally {
                setIsLoading(false)
            }
        }
        fetchTrade()
    }, [token, tradeId])

    const handleCloseTrade = async () => {
        if (!token || !trade) return
        setIsClosing(true)
        try {
            await tradesAPI.close(token, trade.id, {
                exit_price: parseFloat(closeForm.exit_price),
                exit_reason: closeForm.exit_reason || undefined,
                exit_emotion: closeForm.exit_emotion || undefined,
                trade_review: closeForm.trade_review || undefined,
                rating: closeForm.rating,
            })
            setShowCloseModal(false)
            // 重新加载交易数据
            const data = await tradesAPI.get(token, tradeId)
            setTrade(data)
        } catch (err: any) {
            setError(err.message || '平仓失败')
        } finally {
            setIsClosing(false)
        }
    }

    const handleDelete = async () => {
        if (!token || !trade) return
        if (!confirm('确定要删除这笔交易吗？此操作不可撤销。')) return

        setIsDeleting(true)
        try {
            await tradesAPI.delete(token, trade.id)
            router.push('/trades')
        } catch (err: any) {
            setError(err.message || '删除失败')
            setIsDeleting(false)
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (error || !trade) {
        return (
            <div className="max-w-2xl mx-auto text-center py-12">
                <AlertTriangle className="w-16 h-16 text-amber-500 mx-auto mb-4" />
                <h1 className="text-2xl font-bold mb-2">交易记录不存在</h1>
                <p className="text-slate-500 mb-6">{error || '该交易记录可能已被删除或ID无效'}</p>
                <Link href="/trades" className="btn btn-primary">
                    返回交易列表
                </Link>
            </div>
        )
    }

    const isOpen = trade.status === 'OPEN'
    const pnl = trade.pnl || 0
    const isPositive = pnl >= 0
    const currentPrice = isOpen ? trade.current_price : trade.exit_price

    return (
        <div className="max-w-2xl mx-auto space-y-6 pb-20 md:pb-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                    <Link
                        href="/trades"
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div>
                        <div className="flex items-center space-x-2">
                            <h1 className="text-2xl font-bold">{trade.symbol}</h1>
                            <span className={`badge ${isOpen ? 'badge-open' : 'badge-closed'}`}>
                                {isOpen ? '持仓中' : '已平仓'}
                            </span>
                        </div>
                        <p className="text-sm text-slate-500">{trade.exchange}</p>
                    </div>
                </div>
                <div className="flex space-x-2">
                    <button
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30"
                    >
                        {isDeleting ? (
                            <Loader2 className="w-5 h-5 animate-spin text-red-500" />
                        ) : (
                            <Trash2 className="w-5 h-5 text-red-500" />
                        )}
                    </button>
                </div>
            </div>

            {/* P&L Card */}
            <div className={`card p-6 ${isPositive ? 'bg-gradient-to-r from-emerald-50 to-teal-50 dark:from-emerald-900/20 dark:to-teal-900/20' : 'bg-gradient-to-r from-red-50 to-rose-50 dark:from-red-900/20 dark:to-rose-900/20'}`}>
                <div className="flex items-center justify-between">
                    <div>
                        <p className="text-sm text-slate-500 mb-1">盈亏</p>
                        <p className={`text-3xl font-bold ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                            {isPositive ? '+' : ''}${pnl.toFixed(2)}
                        </p>
                        <p className={`text-sm ${isPositive ? 'text-emerald-600' : 'text-red-600'}`}>
                            {isPositive ? '+' : ''}{trade.pnl_percent?.toFixed(2)}%
                        </p>
                    </div>
                    <div className={`w-16 h-16 rounded-2xl flex items-center justify-center ${isPositive ? 'bg-emerald-100 dark:bg-emerald-800' : 'bg-red-100 dark:bg-red-800'}`}>
                        {isPositive ? (
                            <TrendingUp className="w-8 h-8 text-emerald-600" />
                        ) : (
                            <TrendingDown className="w-8 h-8 text-red-600" />
                        )}
                    </div>
                </div>
            </div>

            {/* Trade Details */}
            <div className="card p-6">
                <div className="flex items-center space-x-2 mb-4">
                    <DollarSign className="w-5 h-5 text-primary-500" />
                    <h2 className="font-semibold">交易详情</h2>
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                        <p className="text-xs text-slate-500 mb-1">入场价格</p>
                        <p className="font-semibold">${trade.entry_price.toLocaleString()}</p>
                    </div>
                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                        <p className="text-xs text-slate-500 mb-1">{isOpen ? '当前价格' : '平仓价格'}</p>
                        <p className="font-semibold">${currentPrice?.toLocaleString() || '-'}</p>
                    </div>
                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                        <p className="text-xs text-slate-500 mb-1">数量</p>
                        <p className="font-semibold">{trade.quantity}</p>
                    </div>
                    <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                        <p className="text-xs text-slate-500 mb-1">持仓市值</p>
                        <p className="font-semibold">${((currentPrice || trade.entry_price) * trade.quantity).toLocaleString()}</p>
                    </div>
                </div>
            </div>

            {/* Timeline */}
            <div className="card p-6">
                <div className="flex items-center space-x-2 mb-4">
                    <Calendar className="w-5 h-5 text-indigo-500" />
                    <h2 className="font-semibold">时间线</h2>
                </div>
                <div className="space-y-4">
                    <div className="flex items-start space-x-3">
                        <div className="w-3 h-3 mt-1.5 rounded-full bg-emerald-500" />
                        <div>
                            <p className="font-medium">入场</p>
                            <p className="text-sm text-slate-500">
                                {new Date(trade.entry_time).toLocaleString('zh-CN')}
                            </p>
                        </div>
                    </div>
                    {trade.exit_time && (
                        <div className="flex items-start space-x-3">
                            <div className="w-3 h-3 mt-1.5 rounded-full bg-blue-500" />
                            <div>
                                <p className="font-medium">平仓</p>
                                <p className="text-sm text-slate-500">
                                    {new Date(trade.exit_time).toLocaleString('zh-CN')}
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Entry Analysis */}
            {trade.entry_reason && (
                <div className="card p-6">
                    <div className="flex items-center space-x-2 mb-4">
                        <FileText className="w-5 h-5 text-violet-500" />
                        <h2 className="font-semibold">入场分析</h2>
                    </div>
                    <p className="text-slate-600 dark:text-slate-400">{trade.entry_reason}</p>
                </div>
            )}

            {/* Entry Psychology */}
            {(trade.entry_emotion || trade.entry_confidence) && (
                <div className="card p-6">
                    <div className="flex items-center space-x-2 mb-4">
                        <Heart className="w-5 h-5 text-rose-500" />
                        <h2 className="font-semibold">入场心理</h2>
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        {trade.entry_emotion && (
                            <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                <p className="text-xs text-slate-500 mb-1">情绪状态</p>
                                <p className="font-semibold">{trade.entry_emotion}</p>
                            </div>
                        )}
                        {trade.entry_confidence && (
                            <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                <p className="text-xs text-slate-500 mb-1">信心程度</p>
                                <div className="flex items-center space-x-1">
                                    {[1, 2, 3, 4, 5].map((i) => (
                                        <Target
                                            key={i}
                                            className={`w-4 h-4 ${i <= trade.entry_confidence! ? 'text-primary-500' : 'text-slate-300 dark:text-slate-600'}`}
                                        />
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Exit Analysis (if closed) */}
            {!isOpen && trade.exit_reason && (
                <div className="card p-6">
                    <div className="flex items-center space-x-2 mb-4">
                        <FileText className="w-5 h-5 text-blue-500" />
                        <h2 className="font-semibold">平仓分析</h2>
                    </div>
                    <p className="text-slate-600 dark:text-slate-400">{trade.exit_reason}</p>
                    <div className="mt-4 grid grid-cols-2 gap-4">
                        {trade.exit_emotion && (
                            <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                <p className="text-xs text-slate-500 mb-1">平仓情绪</p>
                                <p className="font-semibold">{trade.exit_emotion}</p>
                            </div>
                        )}
                        {trade.rating && (
                            <div className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg">
                                <p className="text-xs text-slate-500 mb-1">交易评分</p>
                                <div className="flex items-center space-x-1">
                                    {[1, 2, 3, 4, 5].map((i) => (
                                        <span
                                            key={i}
                                            className={`text-lg ${i <= trade.rating! ? 'text-amber-400' : 'text-slate-300 dark:text-slate-600'}`}
                                        >
                                            ★
                                        </span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}

            {/* Trade Review */}
            {!isOpen && trade.trade_review && (
                <div className="card p-6">
                    <div className="flex items-center space-x-2 mb-4">
                        <Camera className="w-5 h-5 text-amber-500" />
                        <h2 className="font-semibold">交易复盘</h2>
                    </div>
                    <p className="text-slate-600 dark:text-slate-400">{trade.trade_review}</p>

                    {trade.lessons && trade.lessons.length > 0 && (
                        <div className="mt-4">
                            <p className="text-sm text-slate-500 mb-2">经验教训</p>
                            <div className="flex flex-wrap gap-2">
                                {trade.lessons.map((lesson, index) => (
                                    <span
                                        key={index}
                                        className="px-3 py-1 rounded-full bg-amber-100 dark:bg-amber-900/30 text-amber-700 dark:text-amber-400 text-sm"
                                    >
                                        {lesson}
                                    </span>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
            )}

            {/* Close Trade Button (if open) */}
            {isOpen && (
                <button
                    onClick={() => setShowCloseModal(true)}
                    className="w-full btn bg-blue-500 hover:bg-blue-600 text-white py-3 flex items-center justify-center space-x-2"
                >
                    <Check className="w-5 h-5" />
                    <span>平仓</span>
                </button>
            )}

            {/* Close Trade Modal */}
            {showCloseModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-slate-800 rounded-2xl max-w-md w-full max-h-[90vh] overflow-y-auto p-6">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-bold">平仓 {trade.symbol}</h2>
                            <button
                                onClick={() => setShowCloseModal(false)}
                                className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">平仓价格 *</label>
                                <input
                                    type="number"
                                    step="any"
                                    required
                                    value={closeForm.exit_price}
                                    onChange={(e) => setCloseForm({ ...closeForm, exit_price: e.target.value })}
                                    className="input"
                                    placeholder="0.00"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">平仓理由</label>
                                <textarea
                                    value={closeForm.exit_reason}
                                    onChange={(e) => setCloseForm({ ...closeForm, exit_reason: e.target.value })}
                                    className="input min-h-[80px]"
                                    placeholder="描述你的平仓理由..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">平仓情绪</label>
                                <div className="flex flex-wrap gap-2">
                                    {emotions.slice(0, 6).map((emotion) => (
                                        <button
                                            key={emotion}
                                            type="button"
                                            onClick={() => setCloseForm({ ...closeForm, exit_emotion: emotion })}
                                            className={`px-3 py-1.5 rounded-full text-sm transition-all ${closeForm.exit_emotion === emotion
                                                    ? 'bg-primary-500 text-white'
                                                    : 'bg-slate-100 dark:bg-slate-700'
                                                }`}
                                        >
                                            {emotion}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">交易复盘</label>
                                <textarea
                                    value={closeForm.trade_review}
                                    onChange={(e) => setCloseForm({ ...closeForm, trade_review: e.target.value })}
                                    className="input min-h-[100px]"
                                    placeholder="总结这笔交易的得失..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">交易评分</label>
                                <div className="flex space-x-2">
                                    {[1, 2, 3, 4, 5].map((i) => (
                                        <button
                                            key={i}
                                            type="button"
                                            onClick={() => setCloseForm({ ...closeForm, rating: i })}
                                            className="text-2xl"
                                        >
                                            <span className={i <= closeForm.rating ? 'text-amber-400' : 'text-slate-300'}>
                                                ★
                                            </span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <button
                                onClick={handleCloseTrade}
                                disabled={isClosing || !closeForm.exit_price}
                                className="w-full btn btn-primary py-3 flex items-center justify-center space-x-2"
                            >
                                {isClosing ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <Check className="w-5 h-5" />
                                )}
                                <span>{isClosing ? '处理中...' : '确认平仓'}</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
