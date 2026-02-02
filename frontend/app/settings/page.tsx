'use client'

import { useState, useEffect } from 'react'
import { useTheme } from 'next-themes'
import {
    Save,
    Key,
    Moon,
    Sun,
    Monitor,
    Server,
    Bot,
    Loader2,
    Plus,
    Trash2,
    Briefcase,
    Shield,
    CheckCircle2,
    XCircle,
    PlugZap
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import { settingsAPI, accountsAPI, adminAPI, UserSettings, TradingAccount, TradingAccountCreate, SystemSetting } from '@/lib/api'

interface LocalSettings extends Partial<UserSettings> {
    // Local state for system settings (only utilized if admin)
    finnhub_api_key_system?: string
    llm_api_url_system?: string
    llm_api_key_system?: string
    llm_model_system?: string
    binance_api_secret?: string // Local only, not in UserSettings
}

export default function SettingsPage() {
    const { token, user } = useAuth()
    const { theme, setTheme } = useTheme()

    // User Settings State
    const [settings, setSettings] = useState<LocalSettings>({
        ibkr_host: '',
        ibkr_port: 7497,
        ibkr_client_id: 1,
        binance_api_key: '',
        binance_api_secret: '',
        // System defaults
        finnhub_api_key_system: '',
        llm_api_url_system: '',
        llm_api_key_system: '',
        llm_model_system: 'gpt-4',
    })

    // UI State
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [saved, setSaved] = useState(false)
    const [error, setError] = useState('')
    const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
    const [testMessage, setTestMessage] = useState('')

    // Accounts State
    const [accounts, setAccounts] = useState<TradingAccount[]>([])
    const [isAccountFormOpen, setIsAccountFormOpen] = useState(false)
    const [editingAccount, setEditingAccount] = useState<TradingAccount | null>(null)
    const [accountForm, setAccountForm] = useState<TradingAccountCreate>({
        name: '',
        broker: '',
        account_type: '',
        currency: 'USD',
        initial_balance: 0,
        description: ''
    })

    const isAdmin = user?.role === 'admin'

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                const promises: Promise<any>[] = [
                    settingsAPI.get(token),
                    accountsAPI.list(token)
                ]

                // If admin, fetch system settings too
                if (user?.role === 'admin') {
                    promises.push(adminAPI.listSettings(token))
                }

                const results = await Promise.all(promises)
                const userSettingsData = results[0]
                const accountsData = results[1]
                const systemSettingsData: SystemSetting[] = results[2] || []

                // Map system settings to local state
                const systemValues: Record<string, string> = {}
                systemSettingsData.forEach(s => {
                    systemValues[s.key] = s.value || ''
                })

                setSettings({
                    ...userSettingsData,
                    binance_api_secret: '', // Don't show secret
                    // System settings
                    finnhub_api_key_system: systemValues['finnhub_api_key'] || '',
                    llm_api_url_system: systemValues['llm_api_url'] || '',
                    llm_api_key_system: systemValues['llm_api_key'] || '',
                    llm_model_system: systemValues['llm_model'] || 'gpt-4',
                })
                setAccounts(accountsData)
            } catch (err) {
                console.error(err)
                setError('加载设置失败')
            } finally {
                setIsLoading(false)
            }
        }
        fetchData()
    }, [token, user])

    const handleSave = async () => {
        if (!token) return
        setError('')
        setIsSaving(true)
        try {
            // 1. Save User Settings
            await settingsAPI.update(token, {
                theme: theme || 'system',
                ibkr_host: settings.ibkr_host || undefined,
                ibkr_port: settings.ibkr_port || undefined,
                ibkr_client_id: settings.ibkr_client_id || undefined,
                binance_api_key: settings.binance_api_key || undefined,
                // Do NOT save finnhub/llm keys to user settings anymore
            })

            // 2. Save System Settings (if Admin)
            if (isAdmin) {
                const systemUpdates = [
                    { key: 'finnhub_api_key', value: settings.finnhub_api_key_system, desc: 'Finnhub Market Data API Key' },
                    { key: 'llm_api_url', value: settings.llm_api_url_system, desc: 'LLM API Base URL' },
                    { key: 'llm_api_key', value: settings.llm_api_key_system, desc: 'LLM API Key' },
                    { key: 'llm_model', value: settings.llm_model_system, desc: 'LLM Model Name' },
                ]

                await Promise.all(systemUpdates.map(item =>
                    adminAPI.updateSetting(token, item.key, { value: item.value, description: item.desc })
                ))
            }

            setSaved(true)
            setTimeout(() => setSaved(false), 3000)
        } catch (err: any) {
            setError(err.message || '保存失败')
        } finally {
            setIsSaving(false)
        }
    }

    const handleTestLLM = async () => {
        if (!token) return
        setTestStatus('testing')
        setTestMessage('')
        try {
            const result = await adminAPI.testLLM(token)
            setTestStatus('success')
            setTestMessage('连接成功')
        } catch (err: any) {
            setTestStatus('error')
            setTestMessage(err.message || '连接失败')
        }
    }

    const updateSetting = (key: keyof LocalSettings, value: string | number | null) => {
        setSettings((prev) => ({ ...prev, [key]: value }))
    }

    const handleOpenAddAccount = () => {
        setEditingAccount(null)
        setAccountForm({
            name: '',
            broker: '',
            account_type: '',
            currency: 'USD',
            initial_balance: 0,
            description: ''
        })
        setIsAccountFormOpen(true)
    }

    const handleOpenEditAccount = (account: TradingAccount) => {
        setEditingAccount(account)
        setAccountForm({
            name: account.name,
            broker: account.broker,
            account_type: account.account_type || '',
            currency: account.currency,
            initial_balance: account.initial_balance || 0,
            description: account.description || ''
        })
        setIsAccountFormOpen(true)
    }

    const handleAccountSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!token) return
        try {
            if (editingAccount) {
                // Update
                const updated = await accountsAPI.update(token, editingAccount.id, accountForm)
                setAccounts(accounts.map(a => a.id === updated.id ? updated : a))
            } else {
                // Create
                const created = await accountsAPI.create(token, accountForm)
                setAccounts([created, ...accounts])
            }
            setIsAccountFormOpen(false)
            setEditingAccount(null)
        } catch (err: any) {
            setError(err.message || '保存账户失败')
        }
    }

    const handleDeleteAccount = async (id: number) => {
        if (!token || !confirm('确定要删除这个账户标签吗？')) return
        try {
            await accountsAPI.delete(token, id)
            setAccounts(accounts.filter(a => a.id !== id))
        } catch (err: any) {
            setError(err.message || '删除失败')
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
        <div className="max-w-3xl mx-auto space-y-6 pb-20 md:pb-6">
            <h1 className="text-2xl font-bold flex items-center gap-2">
                设置
                {isAdmin && <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-100 text-indigo-600 dark:bg-indigo-900/30 dark:text-indigo-300">Admin</span>}
            </h1>

            {/* Error */}
            {error && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600">
                    {error}
                </div>
            )}

            {/* Theme */}
            <div className="card p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Moon className="w-5 h-5 text-indigo-500" />
                    <h2 className="text-lg font-semibold">主题</h2>
                </div>
                <div className="grid grid-cols-3 gap-3">
                    {[
                        { value: 'light', label: '日间', icon: Sun },
                        { value: 'dark', label: '夜间', icon: Moon },
                        { value: 'system', label: '跟随系统', icon: Monitor },
                    ].map(({ value, label, icon: Icon }) => (
                        <button
                            key={value}
                            onClick={() => setTheme(value)}
                            className={`p-4 rounded-xl border-2 transition-all flex flex-col items-center space-y-2 ${theme === value
                                ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/20'
                                : 'border-slate-200 dark:border-slate-700 hover:border-slate-300'
                                }`}
                        >
                            <Icon className={`w-6 h-6 ${theme === value ? 'text-primary-500' : 'text-slate-500'}`} />
                            <span className="text-sm font-medium">{label}</span>
                        </button>
                    ))}
                </div>
            </div>

            {/* Admin Global Settings */}
            {isAdmin && (
                <div className="card p-6 border-2 border-indigo-500/20">
                    <div className="flex items-center space-x-3 mb-6">
                        <Shield className="w-5 h-5 text-indigo-500" />
                        <div>
                            <h2 className="text-lg font-semibold text-indigo-600 dark:text-indigo-400">系统全局配置</h2>
                            <p className="text-xs text-slate-500">仅管理员可见，修改后对所有用户生效</p>
                        </div>
                    </div>

                    <div className="space-y-6">
                        {/* Market Data */}
                        <div className="space-y-4">
                            <h3 className="text-sm font-medium text-slate-900 dark:text-slate-200 flex items-center gap-2">
                                <Server className="w-4 h-4 text-emerald-500" />
                                行情数据 (Finnhub)
                            </h3>
                            <div>
                                <label className="block text-xs font-medium mb-1.5 text-slate-500">API Key</label>
                                <input
                                    type="password"
                                    value={settings.finnhub_api_key_system || ''}
                                    onChange={(e) => updateSetting('finnhub_api_key_system', e.target.value)}
                                    className="input font-mono"
                                    placeholder="••••••••"
                                />
                            </div>
                        </div>

                        <div className="h-px bg-slate-100 dark:bg-slate-700/50" />

                        {/* LLM Settings */}
                        <div className="space-y-4">
                            <h3 className="text-sm font-medium text-slate-900 dark:text-slate-200 flex items-center gap-2">
                                <Bot className="w-4 h-4 text-purple-500" />
                                LLM 周报配置
                            </h3>
                            <div>
                                <label className="block text-xs font-medium mb-1.5 text-slate-500">API URL</label>
                                <input
                                    type="text"
                                    value={settings.llm_api_url_system || ''}
                                    onChange={(e) => updateSetting('llm_api_url_system', e.target.value)}
                                    className="input font-mono"
                                    placeholder="https://api.openai.com/v1"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1.5 text-slate-500">API Key</label>
                                <input
                                    type="password"
                                    value={settings.llm_api_key_system || ''}
                                    onChange={(e) => updateSetting('llm_api_key_system', e.target.value)}
                                    className="input font-mono"
                                    placeholder="sk-..."
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1.5 text-slate-500">模型 (Model)</label>
                                <input
                                    type="text"
                                    value={settings.llm_model_system || ''}
                                    onChange={(e) => updateSetting('llm_model_system', e.target.value)}
                                    className="input font-mono"
                                    placeholder="gpt-4"
                                />
                            </div>

                            <div className="flex items-center space-x-4 pt-2">
                                <button
                                    onClick={handleTestLLM}
                                    disabled={testStatus === 'testing'}
                                    className="btn bg-slate-100 dark:bg-slate-700 hover:bg-slate-200 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200"
                                >
                                    {testStatus === 'testing' ? (
                                        <>
                                            <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                                            测试中...
                                        </>
                                    ) : (
                                        <>
                                            <PlugZap className="w-4 h-4 mr-2" />
                                            测试连接
                                        </>
                                    )}
                                </button>

                                {testStatus === 'success' && (
                                    <span className="text-emerald-500 text-sm flex items-center">
                                        <CheckCircle2 className="w-4 h-4 mr-1" />
                                        {testMessage}
                                    </span>
                                )}

                                {testStatus === 'error' && (
                                    <span className="text-red-500 text-sm flex items-center">
                                        <XCircle className="w-4 h-4 mr-1" />
                                        {testMessage}
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                </div>
            )}

            {/* Trading Accounts */}
            <div className="card p-6">
                <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center space-x-3">
                        <Briefcase className="w-5 h-5 text-slate-500" />
                        <h2 className="text-lg font-semibold">实盘账户管理</h2>
                    </div>
                    <button
                        onClick={handleOpenAddAccount}
                        className="btn btn-sm btn-outline flex items-center space-x-1"
                    >
                        <Plus className="w-4 h-4" />
                        <span>添加账户</span>
                    </button>
                </div>

                {isAccountFormOpen && (
                    <form onSubmit={handleAccountSubmit} className="mb-6 p-4 rounded-xl bg-slate-50 dark:bg-slate-800/50 border border-slate-200 dark:border-slate-700">
                        <h3 className="text-sm font-semibold mb-3">
                            {editingAccount ? '编辑账户' : '添加新账户'}
                        </h3>
                        <div className="grid grid-cols-2 gap-4 mb-4">
                            <div>
                                <label className="block text-xs font-medium mb-1">账户名称</label>
                                <input
                                    required
                                    className="input text-sm"
                                    value={accountForm.name}
                                    onChange={e => setAccountForm({ ...accountForm, name: e.target.value })}
                                    placeholder="例如: IBKR主账户"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1">券商/交易所</label>
                                <input
                                    required
                                    className="input text-sm"
                                    value={accountForm.broker}
                                    onChange={e => setAccountForm({ ...accountForm, broker: e.target.value })}
                                    placeholder="例如: Interactive Brokers"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1">账户类型</label>
                                <input
                                    className="input text-sm"
                                    value={accountForm.account_type || ''}
                                    onChange={e => setAccountForm({ ...accountForm, account_type: e.target.value })}
                                    placeholder="例如: Margin / Spot"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1">币种</label>
                                <input
                                    className="input text-sm"
                                    value={accountForm.currency}
                                    onChange={e => setAccountForm({ ...accountForm, currency: e.target.value })}
                                    placeholder="USD"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1">初始资金</label>
                                <input
                                    type="number"
                                    className="input text-sm"
                                    value={accountForm.initial_balance || ''}
                                    onChange={e => setAccountForm({ ...accountForm, initial_balance: parseFloat(e.target.value) })}
                                    placeholder="0.00"
                                />
                            </div>
                            <div>
                                <label className="block text-xs font-medium mb-1">备注</label>
                                <input
                                    className="input text-sm"
                                    value={accountForm.description || ''}
                                    onChange={e => setAccountForm({ ...accountForm, description: e.target.value })}
                                    placeholder="可选备注"
                                />
                            </div>
                        </div>
                        <div className="flex justify-end space-x-2">
                            <button
                                type="button"
                                onClick={() => setIsAccountFormOpen(false)}
                                className="px-3 py-1.5 text-sm text-slate-500 hover:text-slate-700 dark:text-slate-400 dark:hover:text-slate-200"
                            >
                                取消
                            </button>
                            <button
                                type="submit"
                                className="px-3 py-1.5 text-sm bg-indigo-500 text-white rounded-lg hover:bg-indigo-600"
                            >
                                {editingAccount ? '更新' : '添加'}
                            </button>
                        </div>
                    </form>
                )}

                <div className="space-y-3">
                    {accounts.length === 0 ? (
                        <p className="text-center text-slate-500 py-4 text-sm">暂无账户，请点击右上角添加</p>
                    ) : (
                        accounts.map(account => (
                            <div key={account.id} className="flex items-center justify-between p-3 rounded-xl bg-slate-50 dark:bg-slate-800/30 border border-slate-100 dark:border-slate-800">
                                <div>
                                    <div className="flex items-center space-x-2">
                                        <h3 className="font-medium">{account.name}</h3>
                                        <span className="text-xs px-2 py-0.5 rounded-full bg-slate-200 dark:bg-slate-700 text-slate-600 dark:text-slate-300">
                                            {account.broker}
                                        </span>
                                        {account.account_type && (
                                            <span className="text-xs text-slate-500">
                                                {account.account_type}
                                            </span>
                                        )}
                                    </div>
                                    <div className="flex items-center space-x-4 mt-1 text-xs text-slate-500">
                                        <span>{account.currency}</span>
                                        {account.initial_balance && (
                                            <span>初始: {account.initial_balance.toLocaleString()}</span>
                                        )}
                                        {account.description && (
                                            <span>{account.description}</span>
                                        )}
                                    </div>
                                </div>
                                <div className="flex space-x-1">
                                    <button
                                        onClick={() => handleOpenEditAccount(account)}
                                        className="p-2 text-slate-400 hover:text-indigo-500 transition-colors"
                                        title="编辑账户"
                                    >
                                        <Key className="w-4 h-4" />
                                    </button>
                                    <button
                                        onClick={() => handleDeleteAccount(account.id)}
                                        className="p-2 text-slate-400 hover:text-red-500 transition-colors"
                                        title="删除账户"
                                    >
                                        <Trash2 className="w-4 h-4" />
                                    </button>
                                </div>
                            </div>
                        ))
                    )}
                </div>
            </div>

            {/* IBKR Settings */}
            <div className="card p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Server className="w-5 h-5 text-blue-500" />
                    <h2 className="text-lg font-semibold">IBKR 盈透证券</h2>
                </div>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-2">TWS/Gateway 地址</label>
                        <input
                            type="text"
                            value={settings.ibkr_host || ''}
                            onChange={(e) => updateSetting('ibkr_host', e.target.value)}
                            className="input"
                            placeholder="127.0.0.1"
                        />
                    </div>
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-sm font-medium mb-2">端口</label>
                            <input
                                type="number"
                                value={settings.ibkr_port || ''}
                                onChange={(e) => updateSetting('ibkr_port', parseInt(e.target.value) || null)}
                                className="input"
                                placeholder="7497"
                            />
                        </div>
                        <div>
                            <label className="block text-sm font-medium mb-2">Client ID</label>
                            <input
                                type="number"
                                value={settings.ibkr_client_id || ''}
                                onChange={(e) => updateSetting('ibkr_client_id', parseInt(e.target.value) || null)}
                                className="input"
                                placeholder="1"
                            />
                        </div>
                    </div>
                </div>
            </div>

            {/* Binance Settings */}
            <div className="card p-6">
                <div className="flex items-center space-x-3 mb-4">
                    <Key className="w-5 h-5 text-amber-500" />
                    <h2 className="text-lg font-semibold">Binance 币安</h2>
                </div>
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium mb-2">API Key</label>
                        <input
                            type="password"
                            value={settings.binance_api_key || ''}
                            onChange={(e) => updateSetting('binance_api_key', e.target.value)}
                            className="input"
                            placeholder="••••••••"
                        />
                    </div>
                    <p className="text-xs text-slate-500">
                        ⚠️ 建议仅开启「只读」权限，禁用交易和提现功能
                    </p>
                </div>
            </div>

            {/* Save Button */}
            <button
                onClick={handleSave}
                disabled={isSaving}
                className="w-full btn btn-primary py-3 flex items-center justify-center space-x-2"
            >
                {isSaving ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                    <Save className="w-5 h-5" />
                )}
                <span>{isSaving ? '保存中...' : saved ? '已保存 ✓' : '保存设置'}</span>
            </button>
        </div>
    )
}
