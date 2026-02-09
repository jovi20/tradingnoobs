'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import {
    ArrowLeft,
    Briefcase,
    Save,
    Trash2,
    Loader2,
    AlertCircle,
    CheckCircle2,
    TrendingUp,
    Shield,
    DollarSign,
    Key
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { accountsAPI, TradingAccount, TradingAccountCreate, Transaction } from '@/lib/api'
import { TransactionList } from '@/components/TransactionList'
import { TransactionForm } from '@/components/TransactionForm'

const ACCOUNT_TYPES = [
    { value: 'Spot', label: '现货 (Spot)' },
    { value: 'Margin', label: '保证金 (Margin)' },
    { value: 'Unified', label: '统一账户 (Unified)' },
]

export default function AccountDetailPage({ params }: { params: { id: string } }) {
    const { id } = params
    const router = useRouter()
    const { token } = useAuth()

    const [account, setAccount] = useState<TradingAccount | null>(null)
    const [transactions, setTransactions] = useState<Transaction[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [saved, setSaved] = useState(false)
    const [error, setError] = useState('')

    const [form, setForm] = useState<TradingAccountCreate>({
        name: '',
        broker: '',
        account_type: '',
        currency: 'USD',
        initial_balance: 0,
        cash_balance: 0,
        current_balance: 0,
        description: ''
    })

    useEffect(() => {
        const fetchData = async () => {
            if (!token || !id) return
            try {
                setIsLoading(true)
                const accountId = parseInt(id)
                const [accountData, txsData] = await Promise.all([
                    accountsAPI.get(token, accountId),
                    accountsAPI.getTransactions(token, accountId)
                ])
                setAccount(accountData)
                setTransactions(txsData)
                setForm({
                    name: accountData.name,
                    broker: accountData.broker,
                    account_type: accountData.account_type || '',
                    currency: accountData.currency,
                    initial_balance: accountData.initial_balance || 0,
                    cash_balance: accountData.cash_balance || 0,
                    current_balance: accountData.current_balance || 0,
                    description: accountData.description || ''
                })
            } catch (err: any) {
                console.error(err)
                setError(err.message || '加载账户失败')
            } finally {
                setIsLoading(false)
            }
        }
        fetchData()
    }, [token, id])

    const handleSave = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!token || !account) return
        setError('')
        setIsSaving(true)
        try {
            const updated = await accountsAPI.update(token, account.id, form)
            setAccount(updated)
            setSaved(true)
            setTimeout(() => setSaved(false), 3000)
        } catch (err: any) {
            setError(err.message || '保存失败')
        } finally {
            setIsSaving(false)
        }
    }

    const handleDelete = async () => {
        if (!token || !account || !confirm('确定要删除这个账户吗？此操作不可撤销，且会影响相关仓位统计。')) return
        try {
            await accountsAPI.delete(token, account.id)
            router.push('/settings')
        } catch (err: any) {
            setError(err.message || '删除失败')
        }
    }

    const refreshData = async () => {
        if (!token || !account) return
        try {
            const [accountData, txsData] = await Promise.all([
                accountsAPI.get(token, account.id),
                accountsAPI.getTransactions(token, account.id)
            ])
            setAccount(accountData)
            setTransactions(txsData)
        } catch (err) {
            console.error('Failed to refresh data:', err)
        }
    }

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center py-20 space-y-4">
                <Loader2 className="w-10 h-10 animate-spin text-indigo-500" />
                <p className="text-slate-500 animate-pulse font-medium">加载账户信息...</p>
            </div>
        )
    }

    if (!account) {
        return (
            <div className="max-w-xl mx-auto py-20 text-center space-y-6">
                <div className="inline-flex p-4 rounded-full bg-red-50 dark:bg-red-900/20 text-red-500">
                    <AlertCircle className="w-10 h-10" />
                </div>
                <div className="space-y-2">
                    <h2 className="text-2xl font-bold">账户未找到</h2>
                    <p className="text-slate-500">请求的账户可能已被删除或您没有访问权限。</p>
                </div>
                <button onClick={() => router.push('/settings')} className="btn btn-primary">
                    返回设置
                </button>
            </div>
        )
    }

    return (
        <div className="max-w-5xl mx-auto space-y-8 pb-20">
            {/* Header / Navigation */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                    <button
                        onClick={() => router.push('/settings')}
                        className="p-2 rounded-xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 hover:bg-slate-50 dark:hover:bg-slate-800 transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div>
                        <h1 className="text-2xl font-bold text-slate-900 dark:text-white">{account.name}</h1>
                        <p className="text-sm text-slate-500">管理您的实盘账户与资金流水</p>
                    </div>
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={handleDelete}
                        className="btn bg-white dark:bg-slate-900 border-red-100 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 flex items-center gap-2"
                    >
                        <Trash2 className="w-4 h-4" />
                        <span className="hidden sm:inline">删除账户</span>
                    </button>
                </div>
            </div>

            {error && (
                <div className="p-4 rounded-2xl bg-red-50 dark:bg-red-900/20 text-red-600 flex items-center gap-3 border border-red-100 dark:border-red-900/50">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <p className="text-sm font-medium">{error}</p>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Content: Info & Transactions */}
                <div className="lg:col-span-2 space-y-8">
                    {/* Account Stats Cards */}
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-2 rounded-lg bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 dark:text-emerald-400">
                                    <DollarSign className="w-5 h-5" />
                                </div>
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Available Cash</span>
                            </div>
                            <p className="text-2xl font-mono font-bold text-slate-900 dark:text-white">
                                {account.currency} {Number(account.cash_balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </p>
                        </div>
                        <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-2 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400">
                                    <TrendingUp className="w-5 h-5" />
                                </div>
                                <span className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Net Asset Value (NAV)</span>
                            </div>
                            <p className="text-2xl font-mono font-bold text-slate-900 dark:text-white">
                                {account.currency} {Number(account.current_balance || account.cash_balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </p>
                        </div>
                    </div>

                    {/* Transaction History (Integrated) */}
                    <div className="rounded-2xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800 overflow-hidden">
                        <div className="p-6 border-b border-slate-100 dark:border-slate-800 flex justify-between items-center bg-slate-50/50 dark:bg-slate-800/50">
                            <div className="flex items-center gap-2">
                                <Briefcase className="w-5 h-5 text-slate-400" />
                                <h2 className="text-lg font-bold">资金流水 (Fund Transactions)</h2>
                            </div>
                        </div>

                        <div className="p-6 space-y-8">
                            <div>
                                <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">记录新流水</h3>
                                <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                                    <TransactionForm
                                        token={token!}
                                        accountId={account.id}
                                        currency={account.currency}
                                        onSuccess={refreshData}
                                        onCancel={() => { }}
                                    />
                                </div>
                            </div>

                            <div>
                                <h3 className="text-sm font-semibold text-slate-900 dark:text-white mb-4">历史记录</h3>
                                <TransactionList
                                    token={token!}
                                    transactions={transactions}
                                    onDelete={refreshData}
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Sidebar: Detail Settings */}
                <div className="space-y-8">
                    <div className="p-6 rounded-2xl bg-white dark:bg-slate-900 border border-slate-100 dark:border-slate-800">
                        <h2 className="text-lg font-bold flex items-center gap-2 mb-6">
                            <Shield className="w-5 h-5 text-slate-400" />
                            账户基本信息
                        </h2>

                        <form onSubmit={handleSave} className="space-y-5">
                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">账户名称</label>
                                <input
                                    required
                                    className="input text-sm"
                                    value={form.name}
                                    onChange={e => setForm({ ...form, name: e.target.value })}
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">券商 / 交易所</label>
                                <input
                                    required
                                    className="input text-sm"
                                    value={form.broker}
                                    onChange={e => setForm({ ...form, broker: e.target.value })}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">账户类型</label>
                                    <select
                                        className="input text-sm"
                                        value={form.account_type || ''}
                                        onChange={e => setForm({ ...form, account_type: e.target.value })}
                                    >
                                        <option value="">请选择...</option>
                                        {ACCOUNT_TYPES.map(t => (
                                            <option key={t.value} value={t.value}>{t.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="space-y-1.5">
                                    <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">主要币种</label>
                                    <input
                                        className="input text-sm"
                                        value={form.currency}
                                        onChange={e => setForm({ ...form, currency: e.target.value })}
                                    />
                                </div>
                            </div>

                            <div className="h-px bg-slate-100 dark:bg-slate-800 my-2" />

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-emerald-500 uppercase tracking-wider">手动校准净值 (NAV)</label>
                                <input
                                    type="number"
                                    step="0.01"
                                    className="input text-sm border-emerald-100 dark:border-emerald-900/50 bg-emerald-50/10"
                                    value={form.current_balance || ''}
                                    onChange={e => setForm({ ...form, current_balance: parseFloat(e.target.value) })}
                                    placeholder="输入当前实际总资产"
                                />
                                <p className="text-[10px] text-slate-400">如果不输入，将由现金+持仓自动估算</p>
                            </div>

                            <div className="space-y-1.5">
                                <label className="text-xs font-bold text-slate-400 uppercase tracking-wider">备注 (Optional)</label>
                                <textarea
                                    className="input text-sm min-h-[80px] py-3"
                                    value={form.description || ''}
                                    onChange={e => setForm({ ...form, description: e.target.value })}
                                    placeholder="记录账户用途、杠杆倍数等..."
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={isSaving}
                                className="w-full btn btn-primary flex items-center justify-center gap-2"
                            >
                                {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : saved ? <CheckCircle2 className="w-4 h-4" /> : <Save className="w-4 h-4" />}
                                {isSaving ? '保存中...' : saved ? '保存成功' : '更新基本信息'}
                            </button>
                        </form>
                    </div>

                    <div className="p-6 rounded-2xl bg-slate-50 dark:bg-slate-800/20 border border-slate-100 dark:border-slate-800">
                        <h2 className="text-sm font-bold flex items-center gap-2 mb-4">
                            <Key className="w-4 h-4 text-slate-400" />
                            账户状态
                        </h2>
                        <div className="flex items-center justify-between">
                            <p className="text-xs text-slate-500">此账户目前对系统可见且已启用</p>
                            <div className={`w-3 h-3 rounded-full ${account.is_active ? 'bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-slate-300'}`} />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
