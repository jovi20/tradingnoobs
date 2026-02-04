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
import { positionsAPI, Position, TradeBatch } from '@/lib/api'

export default function PositionDetailPage() {
    const { token } = useAuth()
    const router = useRouter()
    const params = useParams()
    const positionId = parseInt(params.id as string)

    const [position, setPosition] = useState<Position | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [error, setError] = useState('')
    const [isDeleting, setIsDeleting] = useState(false)

    useEffect(() => {
        const fetchPosition = async () => {
            if (!token || isNaN(positionId)) return
            try {
                const data = await positionsAPI.get(token, positionId)
                setPosition(data)
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
        if (!window.confirm('确定要删除这个持仓记录吗？所有相关的交易批次也会被删除。')) return

        setIsDeleting(true)
        try {
            await positionsAPI.delete(token, position.id)
            router.push('/positions')
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

    if (error || !position) {
        return (
            <div className="card p-8 text-center">
                <p className="text-red-500 mb-4">{error || '持仓不存在'}</p>
                <Link href="/positions" className="btn btn-secondary">
                    返回列表
                </Link>
            </div>
        )
    }

    const isPositive = Number(position.realized_pnl) >= 0
    const isOpen = position.status === 'OPEN'

    // Sort batches by time
    const sortedBatches = [...(position.batches || [])].sort(
        (a, b) => new Date(a.time).getTime() - new Date(b.time).getTime()
    )

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                    <Link
                        href="/positions"
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-800"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </Link>
                    <div>
                        <h1 className="text-2xl font-bold flex items-center space-x-2">
                            <span>{position.symbol}</span>
                            <span className={`text-sm px-2 py-1 rounded-full ${isOpen
                                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                                    : 'bg-slate-100 text-slate-700 dark:bg-slate-700 dark:text-slate-300'
                                }`}>
                                {isOpen ? '持仓中' : '已平仓'}
                            </span>
                        </h1>
                        <p className="text-sm text-slate-500">
                            {position.exchange} · {position.direction === 'LONG' ? '做多' : '做空'}
                        </p>
                    </div>
                </div>
                <div className="flex space-x-2">
                    {isOpen && (
                        <Link
                            href={`/positions/${position.id}/add-batch`}
                            className="btn btn-primary flex items-center space-x-2"
                        >
                            <Plus className="w-4 h-4" />
                            <span>加减仓</span>
                        </Link>
                    )}
                    <button
                        onClick={handleDelete}
                        disabled={isDeleting}
                        className="btn btn-danger flex items-center space-x-2"
                    >
                        {isDeleting ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                            <Trash2 className="w-4 h-4" />
                        )}
                        <span>删除</span>
                    </button>
                </div>
            </div>

            {/* Summary Card */}
            <div className="card p-6">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <div>
                        <p className="text-sm text-slate-500 mb-1">持仓数量</p>
                        <p className="text-xl font-bold">{Number(position.total_quantity).toLocaleString()}</p>
                    </div>
                    <div>
                        <p className="text-sm text-slate-500 mb-1">均价</p>
                        <p className="text-xl font-bold">${Number(position.average_entry_price || 0).toFixed(2)}</p>
                    </div>
                    <div>
                        <p className="text-sm text-slate-500 mb-1">已实现盈亏</p>
                        <p className={`text-xl font-bold ${isPositive ? 'pnl-positive' : 'pnl-negative'}`}>
                            {isPositive ? '+' : ''}${Number(position.realized_pnl).toFixed(2)}
                        </p>
                    </div>
                    <div>
                        <p className="text-sm text-slate-500 mb-1">开仓时间</p>
                        <p className="text-lg font-medium">
                            {new Date(position.opened_at).toLocaleDateString('zh-CN')}
                        </p>
                    </div>
                </div>
            </div>

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
                                            {batch.type === 'ENTRY' ? '加仓' : '减仓'}
                                            <span className="ml-2 text-slate-500">
                                                {Number(batch.quantity).toLocaleString()} @ ${Number(batch.price).toFixed(2)}
                                            </span>
                                        </p>
                                        <p className="text-sm text-slate-500">
                                            {new Date(batch.time).toLocaleString('zh-CN')}
                                        </p>
                                    </div>
                                </div>
                                <div className="text-right">
                                    {batch.type === 'EXIT' && batch.pnl !== null && (
                                        <p className={`font-bold ${Number(batch.pnl) >= 0 ? 'pnl-positive' : 'pnl-negative'}`}>
                                            {Number(batch.pnl) >= 0 ? '+' : ''}${Number(batch.pnl).toFixed(2)}
                                        </p>
                                    )}
                                    {batch.confidence && (
                                        <div className="flex items-center justify-end space-x-1 text-sm text-slate-400">
                                            <Target className="w-3 h-3" />
                                            <span>信心度 {batch.confidence}/5</span>
                                        </div>
                                    )}
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
        </div>
    )
}
