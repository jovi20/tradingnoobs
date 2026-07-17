'use client'

import { useState, useEffect } from 'react'
import { useParams, useRouter } from 'next/navigation'
import {
    ArrowLeft,
    Briefcase,
    Save,
    Trash2,
    Loader2,
    AlertCircle,
    CheckCircle2,
    Shield,
    DollarSign,
    Key
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { accountsAPI } from '@/lib/api'
import { TransactionList } from '@/components/TransactionList'
import { TransactionForm } from '@/components/TransactionForm'
import { adaptTradingAccount, adaptTransactions, TradingAccountViewModel, TransactionViewModel } from '@/lib/adapters/trading'
import { buildAccountMetadataUpdate, type AccountMetadataForm } from '@/lib/accountUpdates'

import { getCurrencySymbol } from '@/lib/symbolUtils'

const ACCOUNT_TYPES = [
    { value: 'Spot', label: '现金账户' },
]

export default function AccountDetailPage() {
    const params = useParams()
    const id = params.id as string
    const router = useRouter()
    const { token } = useAuth()

    const [account, setAccount] = useState<TradingAccountViewModel | null>(null)
    const [transactions, setTransactions] = useState<TransactionViewModel[]>([])
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [saved, setSaved] = useState(false)
    const [error, setError] = useState('')

    const [form, setForm] = useState<AccountMetadataForm>({
        name: '',
        broker: '',
        account_type: '',
        currency: 'USD',
        description: ''
    })

    useEffect(() => {
        const fetchData = async () => {
            if (!token || !id) return
            try {
                setIsLoading(true)
                const [accountData, txsData] = await Promise.all([
                    accountsAPI.get(token, id),
                    accountsAPI.getTransactions(token, id)
                ])
                setAccount(adaptTradingAccount(accountData))
                setTransactions(adaptTransactions(txsData))
                setForm({
                    name: accountData.name,
                    broker: accountData.broker,
                    account_type: 'Spot',
                    currency: 'USD',
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
            const updated = await accountsAPI.update(
                token,
                account.routeId,
                buildAccountMetadataUpdate(form)
            )
            setAccount(adaptTradingAccount(updated))
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
            await accountsAPI.delete(token, account.routeId)
            router.push('/settings')
        } catch (err: any) {
            setError(err.message || '删除失败')
        }
    }

    const refreshData = async () => {
        if (!token || !account) return
        try {
            const [accountData, txsData] = await Promise.all([
                accountsAPI.get(token, account.routeId),
                accountsAPI.getTransactions(token, account.routeId)
            ])
            setAccount(adaptTradingAccount(accountData))
            setTransactions(adaptTransactions(txsData))
        } catch (err) {
            console.error('Failed to refresh data:', err)
        }
    }

    if (isLoading) {
        return (
            <div className="flex flex-col items-center justify-center py-20 space-y-4">
                <Loader2 className="w-10 h-10 animate-spin text-ai" />
                <p className="text-ink-muted animate-pulse font-medium">加载账户信息…</p>
            </div>
        )
    }

    if (!account) {
        return (
            <div className="max-w-xl mx-auto py-20 text-center space-y-6">
                <div className="inline-flex p-4 rounded-full bg-loss/8 dark:bg-loss/8 text-loss">
                    <AlertCircle className="w-10 h-10" />
                </div>
                <div className="space-y-2">
                    <h2 className="text-2xl font-bold">账户未找到</h2>
                    <p className="text-ink-muted">请求的账户可能已被删除或您没有访问权限。</p>
                </div>
                <button type="button" onClick={() => router.push('/settings')} className="btn btn-primary">
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
                        type="button"
                        onClick={() => router.push('/settings')}
                        aria-label="返回设置"
                        title="返回设置"
                        className="p-2 rounded-md border border-line bg-panel transition-colors hover:bg-panel-subtle"
                    >
                        <ArrowLeft className="w-5 h-5" />
                    </button>
                    <div>
                        <h1 className="text-2xl font-bold text-ink">{account.name}</h1>
                        <p className="text-sm text-ink-muted">管理账户资料与资金流水</p>
                    </div>
                </div>
                <div className="flex gap-2">
                    <button
                        type="button"
                        onClick={handleDelete}
                        aria-label="删除账户"
                        className="btn flex items-center gap-2 border-loss/30 bg-panel text-loss hover:bg-loss/8"
                    >
                        <Trash2 className="w-4 h-4" />
                        <span className="hidden sm:inline">删除账户</span>
                    </button>
                </div>
            </div>

            {error && (
                <div role="alert" className="flex items-center gap-3 rounded-lg border border-loss/30 bg-loss/8 p-4 text-loss">
                    <AlertCircle className="w-5 h-5 flex-shrink-0" />
                    <p className="text-sm font-medium">{error}</p>
                </div>
            )}

            <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                {/* Main Content: Info & Transactions */}
                <div className="lg:col-span-2 space-y-8">
                    {/* Account Stats Cards */}
                    <div className="grid grid-cols-1 gap-4 sm:max-w-sm">
                        <div className="rounded-lg border border-line bg-panel p-6">
                            <div className="flex justify-between items-start mb-4">
                                <div className="p-2 rounded-lg bg-profit/8 dark:bg-profit/8 text-profit dark:text-profit">
                                    <DollarSign className="w-5 h-5" />
                                </div>
                                <span className="text-[10px] font-bold text-ink-faint">日志余额</span>
                            </div>
                            <p className="text-2xl font-mono font-bold text-ink">
                                {getCurrencySymbol(account.currency)} {Number(account.journal_balance || 0).toLocaleString(undefined, { minimumFractionDigits: 2 })}
                            </p>
                        </div>
                    </div>

                    {/* Transaction History (Integrated) */}
                    <div className="overflow-hidden rounded-lg border border-line bg-panel">
                        <div className="flex items-center justify-between border-b border-line bg-panel-subtle/50 p-6">
                            <div className="flex items-center gap-2">
                                <Briefcase className="w-5 h-5 text-ink-faint" />
                                <h2 className="text-lg font-bold">资金流水</h2>
                            </div>
                        </div>

                        <div className="p-6 space-y-8">
                            <div>
                                <h3 className="mb-4 text-sm font-semibold text-ink">记录新流水</h3>
                                <div className="rounded-md border border-line bg-panel-subtle p-4">
                                    <TransactionForm
                                        token={token!}
                                        accountId={account.routeId}
                                        currency={account.currency}
                                        onSuccess={refreshData}
                                    />
                                </div>
                            </div>

                            <div>
                                <h3 className="mb-4 text-sm font-semibold text-ink">历史记录</h3>
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
                    <div className="rounded-lg border border-line bg-panel p-6">
                        <h2 className="text-lg font-bold flex items-center gap-2 mb-6">
                            <Shield className="w-5 h-5 text-ink-faint" />
                            账户基本信息
                        </h2>

                        <form onSubmit={handleSave} className="space-y-5">
                            <div className="space-y-1.5">
                                <label htmlFor="account-name" className="text-xs font-bold text-ink-faint uppercase tracking-wider">账户名称</label>
                                <input
                                    id="account-name"
                                    required
                                    className="input text-sm"
                                    value={form.name}
                                    onChange={e => setForm({ ...form, name: e.target.value })}
                                />
                            </div>

                            <div className="space-y-1.5">
                                <label htmlFor="account-broker" className="text-xs font-bold text-ink-faint uppercase tracking-wider">券商或交易所</label>
                                <input
                                    id="account-broker"
                                    required
                                    className="input text-sm"
                                    value={form.broker}
                                    onChange={e => setForm({ ...form, broker: e.target.value })}
                                />
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div className="space-y-1.5">
                                    <label htmlFor="account-type" className="text-xs font-bold text-ink-faint uppercase tracking-wider">账户类型</label>
                                    <select
                                        id="account-type"
                                        className="input text-sm"
                                        value="Spot"
                                        disabled
                                    >
                                        {ACCOUNT_TYPES.map(t => (
                                            <option key={t.value} value={t.value}>{t.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="space-y-1.5">
                                    <label htmlFor="account-currency" className="text-xs font-bold text-ink-faint uppercase tracking-wider">主要币种</label>
                                    <input
                                        id="account-currency"
                                        className="input text-sm"
                                        value="USD"
                                        readOnly
                                    />
                                </div>
                            </div>

                            <div className="space-y-1.5">
                                <label htmlFor="account-description" className="text-xs font-bold text-ink-faint uppercase tracking-wider">备注</label>
                                <textarea
                                    id="account-description"
                                    className="input text-sm min-h-[80px] py-3"
                                    value={form.description || ''}
                                    onChange={e => setForm({ ...form, description: e.target.value })}
                                    placeholder="记录账户用途、杠杆倍数等信息"
                                />
                            </div>

                            <button
                                type="submit"
                                disabled={isSaving}
                                className="w-full btn btn-primary flex items-center justify-center gap-2"
                            >
                                {isSaving ? <Loader2 className="w-4 h-4 animate-spin" /> : saved ? <CheckCircle2 className="w-4 h-4" /> : <Save className="w-4 h-4" />}
                                {isSaving ? '保存中…' : saved ? '保存成功' : '更新基本信息'}
                            </button>
                        </form>
                    </div>

                    <div className="rounded-lg border border-line bg-panel-subtle p-6">
                        <h2 className="text-sm font-bold flex items-center gap-2 mb-4">
                            <Key className="w-4 h-4 text-ink-faint" />
                            账户状态
                        </h2>
                        <div className="flex items-center justify-between">
                            <p className="text-xs text-ink-muted">
                                {account.is_active ? '账户已启用' : '账户已停用'}
                            </p>
                            <div
                                aria-hidden="true"
                                className={`w-3 h-3 rounded-full ${account.is_active ? 'bg-profit shadow-[0_0_8px_rgba(16,185,129,0.5)]' : 'bg-line-strong'}`}
                            />
                        </div>
                    </div>
                </div>
            </div>
        </div>
    )
}
