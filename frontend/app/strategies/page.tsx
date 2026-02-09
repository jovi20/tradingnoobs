'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'
import {
    Plus,
    Layers,
    Edit2,
    Trash2,
    TrendingUp,
    CheckCircle,
    PauseCircle,
    Archive,
    Loader2,
    X
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { strategiesAPI, Strategy, StrategyCreate, ChecklistItem } from '@/lib/api'

function StrategyCard({
    strategy,
    onEdit,
    onDelete
}: {
    strategy: Strategy
    onEdit: () => void
    onDelete: () => void
}) {
    const getStatusIcon = () => {
        switch (strategy.status) {
            case 'ACTIVE':
                return <CheckCircle className="w-4 h-4 text-emerald-500" />
            case 'PAUSED':
                return <PauseCircle className="w-4 h-4 text-amber-500" />
            case 'ARCHIVED':
                return <Archive className="w-4 h-4 text-slate-400" />
        }
    }

    const getStatusText = () => {
        switch (strategy.status) {
            case 'ACTIVE': return '使用中'
            case 'PAUSED': return '已暂停'
            case 'ARCHIVED': return '已归档'
        }
    }

    return (
        <div className="card p-6 hover:scale-[1.01] transition-transform">
            <div className="flex items-start justify-between mb-4">
                <div className="flex items-center space-x-3">
                    <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center">
                        <Layers className="w-6 h-6 text-white" />
                    </div>
                    <div>
                        <h3 className="font-semibold text-lg">{strategy.name}</h3>
                        <div className="flex items-center space-x-1 text-sm text-slate-500">
                            {getStatusIcon()}
                            <span>{getStatusText()}</span>
                        </div>
                    </div>
                </div>
                <div className="flex space-x-1">
                    <button
                        onClick={onEdit}
                        className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
                    >
                        <Edit2 className="w-4 h-4 text-slate-500" />
                    </button>
                    <button
                        onClick={onDelete}
                        className="p-2 rounded-lg hover:bg-red-100 dark:hover:bg-red-900/30"
                    >
                        <Trash2 className="w-4 h-4 text-red-500" />
                    </button>
                </div>
            </div>

            {strategy.description && (
                <p className="text-sm text-slate-600 dark:text-slate-400 mb-4">
                    {strategy.description}
                </p>
            )}

            {strategy.symbols && strategy.symbols.length > 0 && (
                <div className="flex flex-wrap gap-2 mb-4">
                    {strategy.symbols.map((symbol) => (
                        <span
                            key={symbol}
                            className="px-2 py-1 rounded-md bg-slate-100 dark:bg-slate-700 text-xs font-medium"
                        >
                            {symbol}
                        </span>
                    ))}
                </div>
            )}

            <div className="space-y-2 text-sm">
                {strategy.entry_rules && (
                    <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 rounded-lg">
                        <p className="text-xs text-emerald-600 dark:text-emerald-400 font-medium mb-1">入场规则</p>
                        <p className="text-slate-600 dark:text-slate-400">{strategy.entry_rules}</p>
                    </div>
                )}
                {strategy.exit_rules && (
                    <div className="p-3 bg-blue-50 dark:bg-blue-900/20 rounded-lg">
                        <p className="text-xs text-blue-600 dark:text-blue-400 font-medium mb-1">出场规则</p>
                        <p className="text-slate-600 dark:text-slate-400">{strategy.exit_rules}</p>
                    </div>
                )}
                {strategy.risk_rules && (
                    <div className="p-3 bg-amber-50 dark:bg-amber-900/20 rounded-lg">
                        <p className="text-xs text-amber-600 dark:text-amber-400 font-medium mb-1">风控规则</p>
                        <p className="text-slate-600 dark:text-slate-400">{strategy.risk_rules}</p>
                    </div>
                )}
            </div>
        </div>
    )
}

export default function StrategiesPage() {
    const { token } = useAuth()
    const [strategies, setStrategies] = useState<Strategy[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [showModal, setShowModal] = useState(false)
    const [isSubmitting, setIsSubmitting] = useState(false)
    const [editingStrategy, setEditingStrategy] = useState<Strategy | null>(null)
    const [form, setForm] = useState<StrategyCreate>({
        name: '',
        description: '',
        entry_rules: '',
        exit_rules: '',
        risk_rules: '',
        symbols: [],
        checklist_items: [],
    })

    const fetchStrategies = async () => {
        if (!token) return
        try {
            setIsLoading(true)
            const data = await strategiesAPI.list(token)
            setStrategies(data)
        } catch (err) {
            console.error(err)
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        fetchStrategies()
    }, [token])

    const openCreateModal = () => {
        setEditingStrategy(null)
        setForm({
            name: '',
            description: '',
            entry_rules: '',
            exit_rules: '',
            risk_rules: '',
            symbols: [],
            checklist_items: [],
        })
        setShowModal(true)
    }

    const openEditModal = (strategy: Strategy) => {
        setEditingStrategy(strategy)
        setForm({
            name: strategy.name,
            description: strategy.description || '',
            entry_rules: strategy.entry_rules || '',
            exit_rules: strategy.exit_rules || '',
            risk_rules: strategy.risk_rules || '',
            symbols: strategy.symbols || [],
            checklist_items: strategy.checklist_items || [],
        })
        setShowModal(true)
    }

    const handleSubmit = async () => {
        if (!token || !form.name) return
        setIsSubmitting(true)
        try {
            if (editingStrategy) {
                await strategiesAPI.update(token, editingStrategy.id, form)
            } else {
                await strategiesAPI.create(token, form)
            }
            setShowModal(false)
            fetchStrategies()
        } catch (err) {
            console.error(err)
        } finally {
            setIsSubmitting(false)
        }
    }

    const handleDelete = async (strategy: Strategy) => {
        if (!token) return
        if (!confirm(`确定要删除策略 "${strategy.name}" 吗?`)) return
        try {
            await strategiesAPI.delete(token, strategy.id)
            fetchStrategies()
        } catch (err) {
            console.error(err)
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 animate-spin text-primary-500" />
            </div>
        )
    }

    return (
        <div className="space-y-6 pb-20 md:pb-6">
            {/* Header */}
            <div className="flex items-center justify-between">
                <h1 className="text-2xl font-bold">交易策略</h1>
                <button onClick={openCreateModal} className="btn btn-primary flex items-center">
                    <Plus className="w-4 h-4 mr-1" />
                    新增策略
                </button>
            </div>

            {/* Strategy List */}
            {strategies.length === 0 ? (
                <div className="card p-12 text-center">
                    <Layers className="w-16 h-16 text-slate-300 mx-auto mb-4" />
                    <p className="text-slate-500 mb-4">暂无交易策略</p>
                    <button onClick={openCreateModal} className="btn btn-primary inline-flex items-center space-x-2">
                        <Plus className="w-5 h-5" />
                        <span>创建第一个策略</span>
                    </button>
                </div>
            ) : (
                <div className="grid md:grid-cols-2 gap-4">
                    {strategies.map((strategy) => (
                        <StrategyCard
                            key={strategy.id}
                            strategy={strategy}
                            onEdit={() => openEditModal(strategy)}
                            onDelete={() => handleDelete(strategy)}
                        />
                    ))}
                </div>
            )}

            {/* Create/Edit Modal */}
            {showModal && (
                <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
                    <div className="bg-white dark:bg-slate-800 rounded-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto p-6">
                        <div className="flex items-center justify-between mb-6">
                            <h2 className="text-xl font-bold">
                                {editingStrategy ? '编辑策略' : '新增策略'}
                            </h2>
                            <button
                                onClick={() => setShowModal(false)}
                                className="p-2 rounded-lg hover:bg-slate-100 dark:hover:bg-slate-700"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-sm font-medium mb-2">策略名称 *</label>
                                <input
                                    type="text"
                                    value={form.name}
                                    onChange={(e) => setForm({ ...form, name: e.target.value })}
                                    className="input"
                                    placeholder="例如：趋势突破策略"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">策略描述</label>
                                <textarea
                                    value={form.description}
                                    onChange={(e) => setForm({ ...form, description: e.target.value })}
                                    className="input min-h-[80px]"
                                    placeholder="简要描述策略的核心逻辑..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">入场规则</label>
                                <textarea
                                    value={form.entry_rules}
                                    onChange={(e) => setForm({ ...form, entry_rules: e.target.value })}
                                    className="input min-h-[80px]"
                                    placeholder="描述入场条件..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">出场规则</label>
                                <textarea
                                    value={form.exit_rules}
                                    onChange={(e) => setForm({ ...form, exit_rules: e.target.value })}
                                    className="input min-h-[80px]"
                                    placeholder="描述止盈止损条件..."
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium mb-2">风控规则</label>
                                <textarea
                                    value={form.risk_rules}
                                    onChange={(e) => setForm({ ...form, risk_rules: e.target.value })}
                                    className="input min-h-[80px]"
                                    placeholder="描述仓位管理和风险控制..."
                                />
                            </div>

                            {/* Phase 1: Pre-Trade Checklist Editor */}
                            <div className="border-t border-slate-200 dark:border-slate-700 pt-4">
                                <div className="flex items-center justify-between mb-3">
                                    <label className="block text-sm font-medium">交易前检查清单</label>
                                    <button
                                        type="button"
                                        onClick={() => {
                                            const newItem: ChecklistItem = {
                                                id: Date.now(),
                                                label: '',
                                                category: 'entry',
                                                required: false
                                            }
                                            setForm({
                                                ...form,
                                                checklist_items: [...(form.checklist_items || []), newItem]
                                            })
                                        }}
                                        className="text-xs px-2 py-1 bg-primary-100 dark:bg-primary-900/30 text-primary-600 dark:text-primary-400 rounded hover:bg-primary-200 dark:hover:bg-primary-900/50"
                                    >
                                        + 添加检查项
                                    </button>
                                </div>
                                <p className="text-xs text-slate-500 mb-3">开仓时需要确认的检查项，帮助执行交易纪律</p>

                                {(form.checklist_items || []).length === 0 ? (
                                    <p className="text-sm text-slate-400 text-center py-4 border border-dashed border-slate-200 dark:border-slate-700 rounded-lg">
                                        暂无检查项，点击上方按钮添加
                                    </p>
                                ) : (
                                    <div className="space-y-2">
                                        {(form.checklist_items || []).map((item, index) => (
                                            <div key={item.id} className="flex items-center gap-2 p-2 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                                                <input
                                                    type="text"
                                                    value={item.label}
                                                    onChange={(e) => {
                                                        const updated = [...(form.checklist_items || [])]
                                                        updated[index] = { ...item, label: e.target.value }
                                                        setForm({ ...form, checklist_items: updated })
                                                    }}
                                                    className="flex-1 input text-sm py-1"
                                                    placeholder="例如：成交量确认"
                                                />
                                                <select
                                                    value={item.category || 'entry'}
                                                    onChange={(e) => {
                                                        const updated = [...(form.checklist_items || [])]
                                                        updated[index] = { ...item, category: e.target.value as 'entry' | 'risk' | 'exit' | 'other' }
                                                        setForm({ ...form, checklist_items: updated })
                                                    }}
                                                    className="input text-xs py-1 w-20"
                                                >
                                                    <option value="entry">入场</option>
                                                    <option value="risk">风控</option>
                                                    <option value="exit">出场</option>
                                                    <option value="other">其他</option>
                                                </select>
                                                <label className="flex items-center text-xs">
                                                    <input
                                                        type="checkbox"
                                                        checked={item.required || false}
                                                        onChange={(e) => {
                                                            const updated = [...(form.checklist_items || [])]
                                                            updated[index] = { ...item, required: e.target.checked }
                                                            setForm({ ...form, checklist_items: updated })
                                                        }}
                                                        className="mr-1"
                                                    />
                                                    必填
                                                </label>
                                                <button
                                                    type="button"
                                                    onClick={() => {
                                                        const updated = (form.checklist_items || []).filter((_, i) => i !== index)
                                                        setForm({ ...form, checklist_items: updated })
                                                    }}
                                                    className="p-1 text-red-500 hover:bg-red-100 dark:hover:bg-red-900/30 rounded"
                                                >
                                                    <X className="w-4 h-4" />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <button
                                onClick={handleSubmit}
                                disabled={isSubmitting || !form.name}
                                className="w-full btn btn-primary py-3 flex items-center justify-center space-x-2"
                            >
                                {isSubmitting ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <Plus className="w-5 h-5" />
                                )}
                                <span>{isSubmitting ? '保存中...' : editingStrategy ? '保存修改' : '创建策略'}</span>
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    )
}
