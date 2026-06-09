'use client'

import { useState, useEffect } from 'react'
import { useTheme } from '@/components/ThemeProvider'
import {
    Save,
    Key,
    Moon,
    Sun,
    Monitor,
    Plus,
    Trash2,
    Briefcase,
    Shield,
    CheckCircle2,
    XCircle,
    PlugZap,
    Server,
    Bot,
    Loader2,
    LogOut,
    Download,
    ChevronRight,
    Wallet
} from 'lucide-react'
import Link from 'next/link'
import { useAuth } from '@/contexts/AuthContext'
import {
    settingsAPI,
    accountsAPI,
    adminAPI,
    UserSettings,
    TradingAccount,
    TradingAccountCreate,
    API_BASE,
} from '@/lib/api'
import { TradingAccountViewModel, adaptTradingAccount, adaptTradingAccounts } from '@/lib/adapters/trading'
import {
    adaptSettingsPageData,
    buildIntegrationCredentialUpdates,
    buildPlatformSettingUpdates,
    SettingsPageState,
} from '@/lib/adapters/settings'
import { getCurrencySymbol } from '@/lib/symbolUtils'
import { SettingsAccountsOverview } from '@/components/settings/domain/SettingsAccountsOverview'
import { SettingsAppearanceCard } from '@/components/settings/domain/SettingsAppearanceCard'
import { SettingsAdminPlatformCard } from '@/components/settings/domain/SettingsAdminPlatformCard'
import { SettingsDataExportCard } from '@/components/settings/domain/SettingsDataExportCard'

const ACCOUNT_TYPES = [
    { value: 'Spot', label: '现货 (Spot)' },
    { value: 'Margin', label: '保证金 (Margin)' },
    { value: 'Unified', label: '统一账户 (Unified)' },
]

const CURRENCY_OPTIONS = [
    { value: 'USD', label: 'USD - 美元' },
    { value: 'HKD', label: 'HKD - 港币' },
    { value: 'CNY', label: 'CNY - 人民币' },
    { value: 'EUR', label: 'EUR - 欧元' },
    { value: 'GBP', label: 'GBP - 英镑' },
]

const ACCOUNT_TYPE_LABELS = Object.fromEntries(ACCOUNT_TYPES.map((item) => [item.value, item.label]))

export default function SettingsPage() {
    const { token, user, logout, refreshSettings } = useAuth()
    const { theme, setTheme } = useTheme()

    // User Settings State
    const [settings, setSettings] = useState<SettingsPageState>({
        ibkr_host: '',
        ibkr_port: 7497,
        ibkr_client_id: 1,
        binance_api_key: '',
        binance_api_secret: '',
    })

    // UI State
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [saved, setSaved] = useState(false)
    const [error, setError] = useState('')
    const [testStatus, setTestStatus] = useState<'idle' | 'testing' | 'success' | 'error'>('idle')
    const [testMessage, setTestMessage] = useState('')

    // Accounts State
    const [accounts, setAccounts] = useState<TradingAccountViewModel[]>([])
    const [isAccountFormOpen, setIsAccountFormOpen] = useState(false)
    const [editingAccount, setEditingAccount] = useState<TradingAccount | null>(null)
    const [accountForm, setAccountForm] = useState<TradingAccountCreate>({
        name: '',
        broker: '',
        account_type: '',
        currency: 'USD',
        description: ''
    })

    const refreshAccounts = async () => {
        if (!token) return
        try {
            const data = await accountsAPI.list(token)
            setAccounts(adaptTradingAccounts(data))
        } catch (err) {
            console.error('Failed to refresh accounts:', err)
        }
    }

    const isAdmin = user?.role === 'admin'
    const [isExporting, setIsExporting] = useState(false)

    const handleExportData = async () => {
        if (!token) return
        setIsExporting(true)
        try {
            const response = await fetch(`${API_BASE}/api/positions/export/csv`, {
                headers: { Authorization: `Bearer ${token}` }
            })
            if (!response.ok) throw new Error('Export failed')

            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = `trading_data_${new Date().toISOString().slice(0, 10)}.csv`
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            a.remove()
        } catch (err) {
            console.error('Export error:', err)
            setError('导出失败，请稍后重试')
        } finally {
            setIsExporting(false)
        }
    }

    useEffect(() => {
        const fetchData = async () => {
            if (!token) return
            try {
                setIsLoading(true)
                const promises: Promise<any>[] = [
                    settingsAPI.get(token),
                    accountsAPI.list(token),
                ]

                // If admin, fetch system settings too
                if (user?.role === 'admin') {
                    promises.push(adminAPI.listPlatformSettings(token))
                    promises.push(adminAPI.listIntegrationCredentials(token))
                }

                const results = await Promise.all(promises)
                const userSettingsData = results[0]
                const accountsData = results[1]
                const platformSettings = results[2] || []
                const integrationCredentials = results[3] || []

                const adapted = adaptSettingsPageData({
                    userSettings: userSettingsData,
                    accounts: accountsData,
                    platformSettings,
                    integrationCredentials,
                })

                setSettings(adapted.settings)
                setAccounts(adapted.accounts)
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
                up_color: settings.up_color || 'GREEN',
                display_currency: settings.display_currency || 'USD',
                ibkr_host: settings.ibkr_host || undefined,
                ibkr_port: settings.ibkr_port || undefined,
                ibkr_client_id: settings.ibkr_client_id || undefined,
                binance_api_key: settings.binance_api_key || undefined,
                // Do NOT save finnhub/llm keys to user settings anymore
            })

            // 2. Save System Settings (if Admin)
            if (isAdmin) {
                const platformUpdates = buildPlatformSettingUpdates(settings)
                const integrationUpdates = buildIntegrationCredentialUpdates(settings)

                await Promise.all([
                    ...platformUpdates.map((item) =>
                        adminAPI.upsertPlatformSetting(token, item.key, {
                            value: item.value,
                            description: item.description,
                        })
                    ),
                    ...integrationUpdates.map((item) =>
                        adminAPI.upsertIntegrationCredential(token, item.providerKey, item.credentialKey, {
                            secret_value: item.secret_value,
                            description: item.description,
                            is_active: item.is_active,
                        })
                    ),
                ])
            }

            // Sync global state
            await refreshSettings()

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

    const updateSetting = (key: keyof SettingsPageState, value: string | number | null) => {
        setSettings((prev) => ({ ...prev, [key]: value }))
    }

    const handleOpenAddAccount = () => {
        setEditingAccount(null)
        setAccountForm({
            name: '',
            broker: '',
            account_type: '',
            currency: 'USD',
            description: ''
        })
        setIsAccountFormOpen(true)
    }

    const handleAccountSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        if (!token) return
        try {
            // Create only (Edit moved to detail page)
            const created = await accountsAPI.create(token, accountForm)
            setAccounts([adaptTradingAccount(created), ...accounts])
            setIsAccountFormOpen(false)
        } catch (err: any) {
            setError(err.message || '保存账户失败')
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
                {isAdmin && <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-900 dark:bg-slate-800 dark:text-slate-300">Admin</span>}
            </h1>

            {/* Error */}
            {error && (
                <div className="p-4 rounded-xl bg-red-50 dark:bg-red-900/20 text-red-600">
                    {error}
                </div>
            )}

            <SettingsAccountsOverview
                accounts={accounts}
                onAddAccount={handleOpenAddAccount}
                accountTypeLabels={ACCOUNT_TYPE_LABELS}
            />

            <SettingsAppearanceCard
                theme={theme}
                setTheme={setTheme}
                settings={settings}
                onUpdateSetting={updateSetting}
                currencyOptions={CURRENCY_OPTIONS}
            />

            {/* Admin Global Settings */}
            {isAdmin && (
                <SettingsAdminPlatformCard
                    settings={settings}
                    testStatus={testStatus}
                    testMessage={testMessage}
                    onUpdateSetting={updateSetting}
                    onTestLLM={handleTestLLM}
                />
            )}

            {/* IBKR Settings deprecated (Configuration moved to Account Setup) */}

            {/* Binance Settings deprecated (Configuration moved to Account Setup) */}

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

            {/* Data Export Section */}
            <SettingsDataExportCard isExporting={isExporting} onExport={handleExportData} />

            {/* Logout Button (Mobile Access) */}
            <div className="pt-6 border-t border-slate-200 dark:border-slate-700 md:hidden">
                <button
                    onClick={logout}
                    className="w-full btn btn-outline border-red-200 text-red-600 hover:bg-red-50 dark:border-red-900/30 dark:hover:bg-red-900/20 flex items-center justify-center space-x-2"
                >
                    <LogOut className="w-5 h-5" />
                    <span>退出登录</span>
                </button>
            </div>

            {/* Account Form Modal (For Add Account) */}
            {isAccountFormOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50 backdrop-blur-sm">
                    <div className="bg-white dark:bg-slate-900 rounded-xl shadow-2xl w-full max-w-md p-6">
                        <form onSubmit={handleAccountSubmit} className="space-y-4">
                            <h3 className="text-lg font-bold">
                                添加新账户
                            </h3>
                            <div className="grid grid-cols-2 gap-4">
                                <div className="col-span-2">
                                    <label className="label-text mb-1 block">账户名称</label>
                                    <input
                                        required
                                        className="input text-sm"
                                        value={accountForm.name}
                                        onChange={e => setAccountForm({ ...accountForm, name: e.target.value })}
                                        placeholder="例如: IBKR主账户"
                                    />
                                </div>
                                <div>
                                    <label className="label-text mb-1 block">券商</label>
                                    <input
                                        required
                                        className="input text-sm"
                                        value={accountForm.broker}
                                        onChange={e => setAccountForm({ ...accountForm, broker: e.target.value })}
                                        placeholder="Interactive Brokers"
                                    />
                                </div>
                                <div>
                                    <label className="label-text mb-1 block">类型</label>
                                    <select
                                        className="input text-sm"
                                        value={accountForm.account_type || ''}
                                        onChange={e => setAccountForm({ ...accountForm, account_type: e.target.value })}
                                    >
                                        <option value="">请选择...</option>
                                        {ACCOUNT_TYPES.map(t => (
                                            <option key={t.value} value={t.value}>{t.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div>
                                    <label className="label-text mb-1 block">币种</label>
                                    <select
                                        className="input text-sm"
                                        value={accountForm.currency}
                                        onChange={e => setAccountForm({ ...accountForm, currency: e.target.value })}
                                    >
                                        {CURRENCY_OPTIONS.map(c => (
                                            <option key={c.value} value={c.value}>{c.label}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <div className="flex justify-end gap-2 pt-4">
                                <button type="button" onClick={() => setIsAccountFormOpen(false)} className="btn btn-ghost">取消</button>
                                <button type="submit" className="btn btn-primary">确定</button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}
