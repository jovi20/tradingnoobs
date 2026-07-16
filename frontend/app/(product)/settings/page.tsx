'use client'

import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import Link from 'next/link'
import { useTheme } from '@/components/ThemeProvider'
import {
    Activity,
    BookOpen,
    Bot,
    CheckCircle2,
    Download,
    ExternalLink,
    Gauge,
    Info,
    KeyRound,
    Loader2,
    LogOut,
    Monitor,
    Moon,
    Palette,
    PlayCircle,
    Plus,
    Save,
    Settings2,
    Shield,
    Sun,
    UserRound,
    Wallet,
    X,
} from 'lucide-react'

import { useAuth } from '@/contexts/AuthContext'
import {
    API_BASE,
    accountsAPI,
    authAPI,
    brokerSyncAPI,
    settingsAPI,
    type BrokerExecution,
    type BrokerSyncRun,
    type TradingAccountCreate,
} from '@/lib/api'
import { adaptTradingAccount, type TradingAccountViewModel } from '@/lib/adapters/trading'
import {
    adaptSettingsPageData,
    type SettingsPageState,
} from '@/lib/adapters/settings'
import { SettingsAccountsOverview } from '@/components/settings/domain/SettingsAccountsOverview'
import { getLocalizedUiError } from '@/lib/authErrors'
import { BROKER_SYNC_RUNTIME_ENABLED, MARKET_RUNTIME_ENABLED } from '@/lib/release-profile'

const ACCOUNT_TYPES = [
    { value: 'Spot', label: '现金账户' },
    { value: 'Margin', label: '保证金账户' },
    { value: 'Unified', label: '统一账户' },
]

const CURRENCY_OPTIONS = [
    { value: 'USD', label: 'USD - 美元' },
    { value: 'HKD', label: 'HKD - 港币' },
    { value: 'CNY', label: 'CNY - 人民币' },
    { value: 'EUR', label: 'EUR - 欧元' },
    { value: 'GBP', label: 'GBP - 英镑' },
]

const LOCALE_OPTIONS = [
    { value: 'zh-CN', label: '简体中文' },
    { value: 'en-US', label: '英语' },
]

const TIMEZONE_OPTIONS = [
    { value: 'Asia/Shanghai', label: '上海（UTC+8）' },
    { value: 'America/New_York', label: '纽约（美东时间）' },
    { value: 'UTC', label: '协调世界时（UTC）' },
]

const ACCOUNT_TYPE_LABELS = Object.fromEntries(ACCOUNT_TYPES.map((item) => [item.value, item.label]))
const LOCALE_LABELS = Object.fromEntries(LOCALE_OPTIONS.map((item) => [item.value, item.label]))
const TIMEZONE_LABELS = Object.fromEntries(TIMEZONE_OPTIONS.map((item) => [item.value, item.label]))
const IBKR_FLEX_GUIDE_URL = 'https://www.interactivebrokers.com/campus/ibkr-api-page/flex-web-service/'
const BINANCE_API_GUIDE_URL = 'https://www.binance.com/en/support/faq/how-to-create-api-360002502072'
const BINANCE_SPOT_TRADES_DOC_URL = 'https://developers.binance.com/docs/binance-spot-api-docs/rest-api/account-endpoints'
const BINANCE_FUTURES_TRADES_DOC_URL = 'https://developers.binance.com/docs/derivatives/usds-margined-futures/account/rest-api/Account-Trade-List'

const BINANCE_MARKET_OPTIONS = [
    { value: 'SPOT', label: '现货' },
    { value: 'USD_M_FUTURES', label: 'U 本位合约' },
]

function hasUsableSecret(value: string | null | undefined): boolean {
    return Boolean(value && value.trim() && !value.includes('*'))
}

function parseSymbolList(value: string | null | undefined): string[] {
    if (!value) return []
    return Array.from(
        new Set(
            value
                .split(/[\s,;，；]+/)
                .map((item) => item.trim().toUpperCase())
                .filter(Boolean)
        )
    )
}

function formatBrokerMarket(value: string | null | undefined): string {
    return {
        SPOT: '现货',
        USD_M_FUTURES: 'U 本位合约',
    }[value || ''] || '未标明市场'
}

function formatBrokerSyncStatus(value: string): string {
    return {
        RUNNING: '同步中',
        SUCCEEDED: '已完成',
        FAILED: '失败',
    }[value] || '未知状态'
}

function formatExecutionSide(value: string): string {
    return {
        BUY: '买入',
        SELL: '卖出',
    }[value] || '方向未知'
}

export default function SettingsPage() {
    const { token, user, logout, refreshSettings, refreshUser } = useAuth()
    const { theme, setTheme } = useTheme()
    const [settings, setSettings] = useState<SettingsPageState>({
        ibkr_flex_query_id: '',
        ibkr_flex_token: '',
        ibkr_flex_start_date: '',
        binance_api_key: '',
        binance_api_secret: '',
        binance_market_type: 'SPOT',
        binance_symbols_text: '',
    })
    const [accounts, setAccounts] = useState<TradingAccountViewModel[]>([])
    const [isAccountFormOpen, setIsAccountFormOpen] = useState(false)
    const [accountForm, setAccountForm] = useState<TradingAccountCreate>({
        name: '',
        broker: '',
        account_type: '',
        currency: 'USD',
        description: '',
    })
    const [profileForm, setProfileForm] = useState({
        locale: user?.locale || 'zh-CN',
        timezone: user?.timezone || 'Asia/Shanghai',
    })
    const [passwordForm, setPasswordForm] = useState({
        currentPassword: '',
        newPassword: '',
        confirmPassword: '',
    })
    const [isLoading, setIsLoading] = useState(true)
    const [isSaving, setIsSaving] = useState(false)
    const [isChangingPassword, setIsChangingPassword] = useState(false)
    const [saved, setSaved] = useState(false)
    const [error, setError] = useState('')
    const [notice, setNotice] = useState('')
    const [passwordMessage, setPasswordMessage] = useState('')
    const [isExporting, setIsExporting] = useState(false)
    const [brokerSyncRuns, setBrokerSyncRuns] = useState<BrokerSyncRun[]>([])
    const [brokerExecutions, setBrokerExecutions] = useState<BrokerExecution[]>([])
    const [brokerAction, setBrokerAction] = useState<string | null>(null)
    const [brokerMessage, setBrokerMessage] = useState('')

    const isAdmin = user?.role === 'admin'
    const activeAccountCount = accounts.filter((account) => account.is_active).length
    const accountCurrencies = useMemo(
        () => Array.from(new Set(accounts.map((account) => account.currency))).filter(Boolean),
        [accounts]
    )
    const hasIBKRFlexConfig = Boolean(
        settings.ibkr_flex_query_id && (hasUsableSecret(settings.ibkr_flex_token) || settings.ibkr_flex_token_masked)
    )
    const configuredBinanceSymbols = parseSymbolList(settings.binance_symbols_text)
    const hasBinanceConfig = Boolean(
        (hasUsableSecret(settings.binance_api_key) || settings.binance_api_key_masked) &&
        (hasUsableSecret(settings.binance_api_secret) || settings.binance_api_secret_configured) &&
        settings.binance_market_type &&
        configuredBinanceSymbols.length > 0
    )
    const completionItems = useMemo(() => [
        {
            label: '交易账户',
            done: accounts.length > 0,
            detail: accounts.length > 0 ? `${accounts.length} 个账户` : '尚未添加',
        },
        {
            label: '个人资料',
            done: Boolean(profileForm.locale && profileForm.timezone),
            detail: `${LOCALE_LABELS[profileForm.locale] || '简体中文'} · ${TIMEZONE_LABELS[profileForm.timezone] || '上海（UTC+8）'}`,
        },
        {
            label: '显示偏好',
            done: Boolean((settings.display_currency || 'USD') && (settings.up_color || 'GREEN')),
            detail: `${settings.display_currency || 'USD'} · ${settings.up_color === 'RED' ? '红涨' : '绿涨'}`,
        },
        ...(BROKER_SYNC_RUNTIME_ENABLED ? [{
            label: '连接配置',
            done: hasIBKRFlexConfig || hasBinanceConfig,
            detail: hasIBKRFlexConfig ? 'IBKR Flex 已就绪' : hasBinanceConfig ? 'Binance 已就绪' : '未配置',
        }] : []),
    ], [
        accounts.length,
        hasBinanceConfig,
        hasIBKRFlexConfig,
        profileForm.locale,
        profileForm.timezone,
        settings,
    ])
    const completionPercent = Math.round(
        (completionItems.filter((item) => item.done).length / completionItems.length) * 100
    )

    useEffect(() => {
        let cancelled = false
        if (!token) return

        const fetchData = async () => {
            try {
                setIsLoading(true)
                setError('')
                const promises: Promise<any>[] = [
                    settingsAPI.get(token),
                    accountsAPI.list(token),
                ]
                if (BROKER_SYNC_RUNTIME_ENABLED) {
                    promises.push(
                        brokerSyncAPI.listRuns(token, 5).catch(() => []),
                        brokerSyncAPI.listExecutions(token, 5).catch(() => []),
                    )
                }

                const results = await Promise.all(promises)
                if (cancelled) return
                const adapted = adaptSettingsPageData({
                    userSettings: results[0],
                    accounts: results[1],
                })

                setSettings(adapted.settings)
                setAccounts(adapted.accounts)
                setBrokerSyncRuns(results[2] || [])
                setBrokerExecutions(results[3] || [])
            } catch (err) {
                console.error(err)
                if (!cancelled) setError('加载设置失败')
            } finally {
                if (!cancelled) setIsLoading(false)
            }
        }

        void fetchData()
        return () => {
            cancelled = true
        }
    }, [token, user])

    const reloadSavedState = async () => {
        if (!token) return
        const promises: Promise<any>[] = [
            settingsAPI.get(token),
            accountsAPI.list(token),
        ]
        if (BROKER_SYNC_RUNTIME_ENABLED) {
            promises.push(
                brokerSyncAPI.listRuns(token, 5).catch(() => []),
                brokerSyncAPI.listExecutions(token, 5).catch(() => []),
            )
        }

        const results = await Promise.all(promises)
        const adapted = adaptSettingsPageData({
            userSettings: results[0],
            accounts: results[1],
        })
        setSettings(adapted.settings)
        setAccounts(adapted.accounts)
        setBrokerSyncRuns(results[2] || [])
        setBrokerExecutions(results[3] || [])
    }

    const updateSetting = (key: keyof SettingsPageState, value: string | number | null) => {
        setSettings((prev) => ({ ...prev, [key]: value }))
    }

    const handleSave = async () => {
        if (!token) return
        setError('')
        setIsSaving(true)
        try {
            const settingsPayload: SettingsPageState = {
                theme: theme || 'system',
                up_color: settings.up_color || 'GREEN',
                display_currency: settings.display_currency || 'USD',
            }

            if (BROKER_SYNC_RUNTIME_ENABLED) {
                settingsPayload.ibkr_flex_query_id = settings.ibkr_flex_query_id || undefined
                settingsPayload.ibkr_flex_start_date = settings.ibkr_flex_start_date || undefined
                settingsPayload.binance_market_type = settings.binance_market_type || 'SPOT'
                settingsPayload.binance_symbols = parseSymbolList(settings.binance_symbols_text)
                if (hasUsableSecret(settings.ibkr_flex_token)) {
                    settingsPayload.ibkr_flex_token = settings.ibkr_flex_token?.trim()
                }
                if (hasUsableSecret(settings.binance_api_key)) {
                    settingsPayload.binance_api_key = settings.binance_api_key?.trim()
                }
                if (hasUsableSecret(settings.binance_api_secret)) {
                    settingsPayload.binance_api_secret = settings.binance_api_secret?.trim()
                }
            }

            await Promise.all([
                settingsAPI.update(token, settingsPayload),
                authAPI.updateMe(token, {
                    locale: profileForm.locale || 'zh-CN',
                    timezone: profileForm.timezone || 'Asia/Shanghai',
                }),
            ])

            await refreshUser()
            await refreshSettings()
            await reloadSavedState()
            setSaved(true)
            setNotice('设置已保存')
            window.setTimeout(() => setSaved(false), 3000)
            window.setTimeout(() => setNotice(''), 3000)
        } catch (err: unknown) {
            setError(getLocalizedUiError(err, '保存失败，请稍后重试'))
        } finally {
            setIsSaving(false)
        }
    }

    const handleBrokerAction = async (
        actionKey: string,
        action: () => Promise<{ ok?: boolean; message?: string; status?: string; records_inserted?: number; records_skipped?: number }>
    ) => {
        if (!token) return
        setError('')
        setBrokerMessage('')
        setBrokerAction(actionKey)
        try {
            await handleSave()
            const result = await action()
            if ('records_inserted' in result) {
                setBrokerMessage(`同步完成：新增 ${result.records_inserted || 0} 条，跳过 ${result.records_skipped || 0} 条`)
            } else {
                setBrokerMessage(getLocalizedUiError(
                    result.message,
                    result.ok === false ? '连接测试失败，请检查配置' : '连接测试成功'
                ))
            }
            await reloadSavedState()
        } catch (err: unknown) {
            setBrokerMessage(getLocalizedUiError(err, '操作失败，请稍后重试'))
        } finally {
            setBrokerAction(null)
        }
    }

    const brokerSyncPayload = () => ({
        start_date: settings.ibkr_flex_start_date || undefined,
    })

    const handleChangePassword = async (event: FormEvent) => {
        event.preventDefault()
        if (!token) return
        setError('')
        setPasswordMessage('')

        if (passwordForm.newPassword !== passwordForm.confirmPassword) {
            setError('两次输入的新密码不一致')
            return
        }
        if (passwordForm.newPassword.length < 8) {
            setError('新密码至少需要 8 位')
            return
        }

        setIsChangingPassword(true)
        try {
            const response = await authAPI.changePassword(token, {
                current_password: passwordForm.currentPassword,
                new_password: passwordForm.newPassword,
            })
            setPasswordForm({
                currentPassword: '',
                newPassword: '',
                confirmPassword: '',
            })
            setPasswordMessage(response.active_sessions_revoked ? '密码已更新，其它登录会话已失效' : '密码已更新')
        } catch (err: unknown) {
            setError(getLocalizedUiError(err, '修改密码失败，请稍后重试'))
        } finally {
            setIsChangingPassword(false)
        }
    }

    const handleExportData = async () => {
        if (!token) return
        setError('')
        setIsExporting(true)
        try {
            const response = await fetch(`${API_BASE}/api/positions/export/csv`, {
                headers: { Authorization: `Bearer ${token}` },
            })
            if (!response.ok) throw new Error('Export failed')

            const blob = await response.blob()
            const url = window.URL.createObjectURL(blob)
            const link = document.createElement('a')
            link.href = url
            link.download = `trading_data_${new Date().toISOString().slice(0, 10)}.csv`
            document.body.appendChild(link)
            link.click()
            window.URL.revokeObjectURL(url)
            link.remove()
        } catch (err) {
            console.error('Export error:', err)
            setError('导出失败，请稍后重试')
        } finally {
            setIsExporting(false)
        }
    }

    const handleOpenAddAccount = () => {
        setAccountForm({
            name: '',
            broker: '',
            account_type: '',
            currency: 'USD',
            description: '',
        })
        setIsAccountFormOpen(true)
    }

    const handleAccountSubmit = async (event: FormEvent) => {
        event.preventDefault()
        if (!token) return
        setError('')
        try {
            const created = await accountsAPI.create(token, accountForm)
            setAccounts([adaptTradingAccount(created), ...accounts])
            setIsAccountFormOpen(false)
        } catch (err: unknown) {
            setError(getLocalizedUiError(err, '保存账户失败，请稍后重试'))
        }
    }

    if (isLoading) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-ink-muted" />
            </div>
        )
    }

    return (
        <div className="mx-auto max-w-7xl space-y-5 pb-20 md:pb-8">
            <section className="border-b border-line pb-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                    <div>
                        <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-panel-subtle px-3 py-1 text-xs font-semibold text-ink-soft">
                            <Settings2 className="h-3.5 w-3.5" />
                            设置
                        </div>
                        <h1 className="text-2xl font-black tracking-tight text-ink md:text-3xl">
                            设置与账户中心
                        </h1>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        {isAdmin && (
                            <>
                                <Link href="/admin/ops" className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-transparent px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel-subtle">
                                    <Gauge className="mr-2 h-4 w-4" />
                                    运维工作台
                                </Link>
                                <Link href="/admin/jobs" className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-transparent px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel-subtle">
                                    <PlayCircle className="mr-2 h-4 w-4" />
                                    任务
                                </Link>
                            </>
                        )}
                        <button
                            type="button"
                            onClick={handleSave}
                            disabled={isSaving}
                            className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft disabled:opacity-50"
                        >
                            {isSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                            {saved ? '已保存' : '保存'}
                        </button>
                    </div>
                </div>
            </section>

            {error && (
                <div className="rounded-lg border border-loss/30 bg-loss/10 p-4 text-sm text-loss">
                    {error}
                </div>
            )}

            {notice && (
                <div className="rounded-lg border border-profit/30 bg-profit/10 p-4 text-sm text-profit">
                    {notice}
                </div>
            )}

            <section className="grid gap-3 md:grid-cols-4">
                <SummaryTile icon={<UserRound className="h-4 w-4" />} label="当前账号" value={user?.email || '未知'} detail={isAdmin ? '管理员' : '普通用户'} />
                <SummaryTile icon={<Wallet className="h-4 w-4" />} label="交易账户" value={String(accounts.length)} detail={`${activeAccountCount} 个启用`} />
                <SummaryTile icon={<Palette className="h-4 w-4" />} label="显示偏好" value={settings.display_currency || 'USD'} detail={settings.up_color === 'RED' ? '红涨绿跌' : '绿涨红跌'} />
                <SummaryTile icon={<Activity className="h-4 w-4" />} label="配置完成度" value={`${completionPercent}%`} detail={`${completionItems.filter((item) => item.done).length}/${completionItems.length} 项已完成`} />
            </section>

            <section className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_24rem]">
                <div className="space-y-5">
                    <SettingsAccountsOverview
                        accounts={accounts}
                        onAddAccount={handleOpenAddAccount}
                        accountTypeLabels={ACCOUNT_TYPE_LABELS}
                    />

                    <section className="rounded-lg border border-line bg-panel shadow-panel dark:shadow-none">
                        <div className="border-b border-line p-4">
                            <h2 className="flex items-center gap-2 text-base font-bold">
                                <UserRound className="h-4 w-4" />
                                个人资料
                            </h2>
                            <p className="mt-1 text-xs text-ink-muted">控制时间显示、默认语言和账户身份信息。</p>
                        </div>
                        <div className="grid gap-4 p-4 md:grid-cols-3">
                            <label className="block">
                                <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">登录邮箱</span>
                                <input className="input text-sm" value={user?.email || ''} disabled />
                            </label>
                            <label className="block">
                                <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">语言</span>
                                <select
                                    className="input text-sm"
                                    value={profileForm.locale}
                                    onChange={(event) => setProfileForm((current) => ({ ...current, locale: event.target.value }))}
                                >
                                    {LOCALE_OPTIONS.map((item) => (
                                        <option key={item.value} value={item.value}>{item.label}</option>
                                    ))}
                                </select>
                            </label>
                            <label className="block">
                                <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">时区</span>
                                <select
                                    className="input text-sm"
                                    value={profileForm.timezone}
                                    onChange={(event) => setProfileForm((current) => ({ ...current, timezone: event.target.value }))}
                                >
                                    {TIMEZONE_OPTIONS.map((item) => (
                                        <option key={item.value} value={item.value}>{item.label}</option>
                                    ))}
                                </select>
                            </label>
                        </div>
                    </section>

                    <section className="rounded-lg border border-line bg-panel shadow-panel dark:shadow-none">
                        <div className="border-b border-line p-4">
                            <h2 className="flex items-center gap-2 text-base font-bold">
                                <Palette className="h-4 w-4" />
                                显示与交易习惯
                            </h2>
                            <p className="mt-1 text-xs text-ink-muted">主题、涨跌颜色和默认展示币种。</p>
                        </div>
                        <div className="grid gap-4 p-4 lg:grid-cols-[minmax(0,0.9fr)_minmax(0,1.1fr)]">
                            <div>
                                <p className="mb-3 text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">主题</p>
                                <div className="grid grid-cols-3 gap-2">
                                    {[
                                        { value: 'light', label: '日间', icon: Sun },
                                        { value: 'dark', label: '夜间', icon: Moon },
                                        { value: 'system', label: '系统', icon: Monitor },
                                    ].map(({ value, label, icon: Icon }) => (
                                        <button
                                            key={value}
                                            type="button"
                                            onClick={() => setTheme(value)}
                                            className={`rounded-lg border p-3 text-center transition-colors ${
                                                theme === value
                                                    ? 'border-ink bg-ink text-canvas'
                                                    : 'border-line hover:bg-panel-subtle'
                                            }`}
                                        >
                                            <Icon className="mx-auto h-4 w-4" />
                                            <span className="mt-2 block text-xs font-semibold">{label}</span>
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="grid gap-4 sm:grid-cols-2">
                                <SettingPanel title="涨跌颜色">
                                    <div className="grid gap-2">
                                        <ChoiceButton
                                            active={!settings.up_color || settings.up_color === 'GREEN'}
                                            label="绿涨红跌"
                                            detail="国际市场 / 加密资产"
                                            onClick={() => updateSetting('up_color', 'GREEN')}
                                        />
                                        <ChoiceButton
                                            active={settings.up_color === 'RED'}
                                            label="红涨绿跌"
                                            detail="A 股习惯"
                                            onClick={() => updateSetting('up_color', 'RED')}
                                        />
                                    </div>
                                </SettingPanel>

                                <SettingPanel title="显示币种">
                                    <div className="grid grid-cols-2 gap-2">
                                        {CURRENCY_OPTIONS.map(({ value }) => (
                                            <button
                                                key={value}
                                                type="button"
                                                onClick={() => updateSetting('display_currency', value)}
                                                className={`rounded-lg border px-3 py-2 text-sm font-semibold transition-colors ${
                                                    (settings.display_currency || 'USD') === value
                                                        ? 'border-ink bg-ink text-canvas'
                                                        : 'border-line hover:bg-panel-subtle'
                                                }`}
                                            >
                                                {value}
                                            </button>
                                        ))}
                                    </div>
                                </SettingPanel>
                            </div>
                        </div>
                    </section>

                    {BROKER_SYNC_RUNTIME_ENABLED && (
                    <section className="rounded-lg border border-line bg-panel shadow-panel dark:shadow-none">
                        <div className="border-b border-line p-4">
                            <h2 className="flex items-center gap-2 text-base font-bold">
                                <Activity className="h-4 w-4" />
                                连接与数据源
                            </h2>
                            <p className="mt-1 text-xs text-ink-muted">维护交易记录回补凭据。密钥留空时不会覆盖已保存配置。</p>
                        </div>
                        <div className="grid gap-4 p-4 xl:grid-cols-2">
                            <SettingPanel title="IBKR Flex 历史回补">
                                <div className="grid gap-3 sm:grid-cols-2">
                                    <label className="block">
                                        <span className="mb-1.5 block text-xs text-ink-muted">Flex Query ID</span>
                                        <input
                                            className="input font-mono text-sm"
                                            value={settings.ibkr_flex_query_id || ''}
                                            onChange={(event) => updateSetting('ibkr_flex_query_id', event.target.value)}
                                            placeholder="例如: 123456"
                                        />
                                    </label>
                                    <label className="block">
                                        <span className="mb-1.5 block text-xs text-ink-muted">Flex Token</span>
                                        <input
                                            className="input font-mono text-sm"
                                            type="password"
                                            value={settings.ibkr_flex_token || ''}
                                            onChange={(event) => updateSetting('ibkr_flex_token', event.target.value)}
                                            placeholder={settings.ibkr_flex_token_masked || '新 Flex Token'}
                                        />
                                    </label>
                                    <label className="block sm:col-span-2">
                                        <span className="mb-1.5 block text-xs text-ink-muted">回补起始日期</span>
                                        <input
                                            className="input text-sm"
                                            type="date"
                                            value={settings.ibkr_flex_start_date || ''}
                                            onChange={(event) => updateSetting('ibkr_flex_start_date', event.target.value)}
                                        />
                                    </label>
                                </div>
                                <ConnectionStatus ready={hasIBKRFlexConfig} readyLabel="IBKR Flex 已配置" emptyLabel="缺少 Flex Query ID / Token" />
                                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                                    <button
                                        type="button"
                                        className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-panel-subtle px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel disabled:opacity-50"
                                        disabled={brokerAction !== null}
                                        onClick={() => handleBrokerAction('ibkr-test', () => brokerSyncAPI.testIBKR(token!))}
                                    >
                                        {brokerAction === 'ibkr-test' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Activity className="mr-2 h-4 w-4" />}
                                        测试连接
                                    </button>
                                    <button
                                        type="button"
                                        className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft disabled:opacity-50"
                                        disabled={brokerAction !== null}
                                        onClick={() => handleBrokerAction('ibkr-sync', () => brokerSyncAPI.syncIBKR(token!, brokerSyncPayload()))}
                                    >
                                        {brokerAction === 'ibkr-sync' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                                        回补成交
                                    </button>
                                </div>
                                <ParameterGuide
                                    title="IBKR 参数获取指南"
                                    items={[
                                        '在 IBKR Client Portal 创建 Flex Query，类型建议选择成交确认（Trade Confirmation）或活动报告（Activity）。',
                                        '打开 Flex Web Service，复制 Token；进入已创建的 Flex Query，复制 Query ID。',
                                        '报告格式建议选择 XML，字段需包含账号、成交时间、交易标的（symbol）、买卖方向、数量、价格、手续费、成交编号。',
                                        '回补起始日期用于限制首次导入范围，避免重复拉取太久远的历史。',
                                    ]}
                                    links={[
                                        { label: 'IBKR Flex Web Service', href: IBKR_FLEX_GUIDE_URL },
                                    ]}
                                />
                            </SettingPanel>

                            <SettingPanel title="Binance API">
                                <div className="grid gap-3 sm:grid-cols-2">
                                    <label className="block sm:col-span-2">
                                        <span className="mb-1.5 block text-xs text-ink-muted">市场类型</span>
                                        <select
                                            className="input text-sm"
                                            value={settings.binance_market_type || 'SPOT'}
                                            onChange={(event) => updateSetting('binance_market_type', event.target.value)}
                                        >
                                            {BINANCE_MARKET_OPTIONS.map((item) => (
                                                <option key={item.value} value={item.value}>{item.label}</option>
                                            ))}
                                        </select>
                                    </label>
                                    <label className="block">
                                        <span className="mb-1.5 block text-xs text-ink-muted">API Key</span>
                                        <input
                                            className="input font-mono text-sm"
                                            type="password"
                                            value={settings.binance_api_key || ''}
                                            onChange={(event) => updateSetting('binance_api_key', event.target.value)}
                                            placeholder={settings.binance_api_key_masked || '新 API Key'}
                                        />
                                    </label>
                                    <label className="block">
                                        <span className="mb-1.5 block text-xs text-ink-muted">API Secret</span>
                                        <input
                                            className="input font-mono text-sm"
                                            type="password"
                                            value={settings.binance_api_secret || ''}
                                            onChange={(event) => updateSetting('binance_api_secret', event.target.value)}
                                            placeholder="新 API Secret"
                                        />
                                    </label>
                                    <label className="block sm:col-span-2">
                                        <span className="mb-1.5 block text-xs text-ink-muted">同步交易对</span>
                                        <textarea
                                            className="input min-h-24 font-mono text-sm"
                                            value={settings.binance_symbols_text || ''}
                                            onChange={(event) => updateSetting('binance_symbols_text', event.target.value)}
                                            placeholder="BTCUSDT, ETHUSDT&#10;SOLUSDT"
                                        />
                                        <span className="mt-1 block text-xs text-ink-muted">支持逗号、空格或换行分隔；系统会按交易对拉取账户成交。</span>
                                    </label>
                                </div>
                                <ConnectionStatus ready={hasBinanceConfig} readyLabel="Binance 成交同步已配置" emptyLabel="缺少 API Key / Secret / 同步交易对" />
                                <div className="mt-3 grid gap-2 sm:grid-cols-2">
                                    <button
                                        type="button"
                                        className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-panel-subtle px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel disabled:opacity-50"
                                        disabled={brokerAction !== null}
                                        onClick={() => handleBrokerAction('binance-test', () => brokerSyncAPI.testBinance(token!))}
                                    >
                                        {brokerAction === 'binance-test' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Activity className="mr-2 h-4 w-4" />}
                                        测试连接
                                    </button>
                                    <button
                                        type="button"
                                        className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft disabled:opacity-50"
                                        disabled={brokerAction !== null}
                                        onClick={() => handleBrokerAction('binance-sync', () => brokerSyncAPI.syncBinance(token!, {}))}
                                    >
                                        {brokerAction === 'binance-sync' ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                                        同步成交
                                    </button>
                                </div>
                                <ParameterGuide
                                    title="Binance 参数获取指南"
                                    items={[
                                        '在 Binance API Management 新建 API Key，保存 API Key 和 Secret。',
                                        '权限只需要读取账户/交易记录；不要开启提现权限。',
                                        '现货成交记录需按交易对（symbol）查询，所以这里必须填写要回补的交易对。',
                                        '如果使用 U 本位合约，市场类型选择 U 本位合约，并填写对应合约交易对。',
                                        '接口只读取账户成交，不同步行情、K 线或标的价格。',
                                    ]}
                                    links={[
                                        { label: '创建 Binance API Key', href: BINANCE_API_GUIDE_URL },
                                        { label: '现货成交接口', href: BINANCE_SPOT_TRADES_DOC_URL },
                                        { label: 'U 本位成交接口', href: BINANCE_FUTURES_TRADES_DOC_URL },
                                    ]}
                                />
                            </SettingPanel>
                        </div>
                        {(brokerMessage || brokerSyncRuns.length > 0 || brokerExecutions.length > 0) && (
                            <div className="border-t border-line p-4">
                                {brokerMessage && (
                                    <div className="mb-3 rounded-lg bg-panel-subtle p-3 text-sm text-ink-soft">
                                        {brokerMessage}
                                    </div>
                                )}
                                <BrokerSyncSnapshot runs={brokerSyncRuns} executions={brokerExecutions} />
                            </div>
                        )}
                    </section>
                    )}

                    {isAdmin && (
                        <section className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
                            <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                                <div>
                                    <h2 className="flex items-center gap-2 text-base font-bold">
                                        <Bot className="h-4 w-4" />
                                        管理员配置中心
                                    </h2>
                                    <p className="mt-1 text-sm leading-6 text-ink-muted">
                                        {MARKET_RUNTIME_ENABLED
                                            ? '全局 LLM、行情密钥、集成启停和功能开关已统一放到运维工作台的平台页签。'
                                            : '全局 LLM、集成启停和功能开关已统一放到运维工作台的平台页签。'}
                                    </p>
                                </div>
                                <Link href="/admin/ops?tab=platform" className="inline-flex shrink-0 items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft">
                                    <Gauge className="mr-2 h-4 w-4" />
                                    打开平台配置
                                </Link>
                            </div>
                        </section>
                    )}
                </div>

                <aside className="space-y-5">
                    <section className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
                        <h2 className="flex items-center gap-2 text-base font-bold">
                            <Shield className="h-4 w-4" />
                            配置状态
                        </h2>
                        <div className="mt-4 space-y-2">
                            {completionItems.map((item) => (
                                <div key={item.label} className="flex items-center justify-between gap-3 rounded-lg bg-panel-subtle p-3">
                                    <div>
                                        <p className="text-sm font-semibold">{item.label}</p>
                                        <p className="mt-1 text-xs text-ink-muted">{item.detail}</p>
                                    </div>
                                    <span className={`rounded-full p-1 ${
                                        item.done
                                            ? 'bg-profit/10 text-profit'
                                            : 'bg-warning/12 text-warning'
                                    }`}>
                                        <CheckCircle2 className="h-4 w-4" />
                                    </span>
                                </div>
                            ))}
                        </div>
                    </section>

                    <section className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
                        <h2 className="flex items-center gap-2 text-base font-bold">
                            <KeyRound className="h-4 w-4" />
                            身份与安全
                        </h2>
                        <div className="mt-4 rounded-lg bg-panel-subtle p-3">
                            <p className="text-xs text-ink-muted">登录邮箱</p>
                            <p className="mt-1 break-all text-sm font-semibold">{user?.email}</p>
                        </div>
                        <div className="mt-3 grid grid-cols-2 gap-2">
                            <SecurityFact label="角色" value={isAdmin ? '管理员' : '普通用户'} />
                            <SecurityFact label="状态" value={user?.is_active ? '已启用' : '已停用'} />
                        </div>
                        <form onSubmit={handleChangePassword} className="mt-4 space-y-3 border-t border-line pt-4">
                            <label className="block">
                                <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">当前密码</span>
                                <input
                                    className="input text-sm"
                                    type="password"
                                    value={passwordForm.currentPassword}
                                    onChange={(event) => setPasswordForm((current) => ({ ...current, currentPassword: event.target.value }))}
                                    autoComplete="current-password"
                                />
                            </label>
                            <label className="block">
                                <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">新密码</span>
                                <input
                                    className="input text-sm"
                                    type="password"
                                    value={passwordForm.newPassword}
                                    onChange={(event) => setPasswordForm((current) => ({ ...current, newPassword: event.target.value }))}
                                    autoComplete="new-password"
                                />
                            </label>
                            <label className="block">
                                <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">确认新密码</span>
                                <input
                                    className="input text-sm"
                                    type="password"
                                    value={passwordForm.confirmPassword}
                                    onChange={(event) => setPasswordForm((current) => ({ ...current, confirmPassword: event.target.value }))}
                                    autoComplete="new-password"
                                />
                            </label>
                            {passwordMessage && (
                                <div className="rounded-lg bg-profit/10 p-3 text-xs text-profit">
                                    {passwordMessage}
                                </div>
                            )}
                            <button
                                type="submit"
                                disabled={isChangingPassword || !passwordForm.currentPassword || !passwordForm.newPassword || !passwordForm.confirmPassword}
                                className="inline-flex w-full items-center justify-center gap-2 rounded-md border border-line bg-panel-subtle px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel disabled:opacity-50"
                            >
                                {isChangingPassword ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <KeyRound className="mr-2 h-4 w-4" />}
                                修改密码
                            </button>
                        </form>
                        <button
                            type="button"
                            onClick={logout}
                            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md border border-loss/40 bg-transparent px-4 py-2 text-sm font-medium text-loss transition-colors hover:bg-loss/10"
                        >
                            <LogOut className="mr-2 h-4 w-4" />
                            退出登录
                        </button>
                    </section>

                    <section className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
                        <h2 className="flex items-center gap-2 text-base font-bold">
                            <Download className="h-4 w-4" />
                            数据与迁移
                        </h2>
                        <p className="mt-2 text-sm leading-6 text-ink-muted">
                            导出交易 CSV，用于备份、表格分析或迁移到其他工具。
                        </p>
                        <div className="mt-4 grid grid-cols-2 gap-2">
                            <SecurityFact label="账户数" value={String(accounts.length)} />
                            <SecurityFact label="币种" value={accountCurrencies.join(' / ') || '暂无'} />
                        </div>
                        <button
                            type="button"
                            onClick={handleExportData}
                            disabled={isExporting}
                            className="mt-4 inline-flex w-full items-center justify-center gap-2 rounded-md border border-line bg-panel-subtle px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel disabled:opacity-50"
                        >
                            {isExporting ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Download className="mr-2 h-4 w-4" />}
                            {isExporting ? '导出中…' : '导出交易数据'}
                        </button>
                    </section>

                    {isAdmin && (
                        <section className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
                            <h2 className="flex items-center gap-2 text-base font-bold">
                                <Bot className="h-4 w-4" />
                                管理员入口
                            </h2>
                            <div className="mt-4 grid gap-2">
                                <Link href="/admin/ops?tab=platform" className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft">
                                    <Gauge className="mr-2 h-4 w-4" />
                                    平台配置中心
                                </Link>
                                <Link href="/admin/jobs" className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-transparent px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel-subtle">
                                    <PlayCircle className="mr-2 h-4 w-4" />
                                    后台任务
                                </Link>
                            </div>
                        </section>
                    )}
                </aside>
            </section>

            {isAccountFormOpen && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-ink/40 p-4">
                    <div className="w-full max-w-lg rounded-lg bg-panel shadow-pop">
                        <form onSubmit={handleAccountSubmit}>
                            <div className="flex items-center justify-between border-b border-line p-5">
                                <div>
                                    <h3 className="text-lg font-black">添加新账户</h3>
                                    <p className="mt-1 text-sm text-ink-muted">账户用于归集持仓、现金和交易流水。</p>
                                </div>
                                <button
                                    type="button"
                                    onClick={() => setIsAccountFormOpen(false)}
                                    className="rounded-lg p-2 text-ink-muted transition-colors hover:bg-panel-subtle"
                                    aria-label="关闭添加账户对话框"
                                    title="关闭"
                                >
                                    <X className="h-4 w-4" />
                                </button>
                            </div>

                            <div className="grid gap-4 p-5 sm:grid-cols-2">
                                <label className="block sm:col-span-2">
                                    <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">账户名称</span>
                                    <input
                                        required
                                        className="input text-sm"
                                        value={accountForm.name}
                                        onChange={(event) => setAccountForm({ ...accountForm, name: event.target.value })}
                                        placeholder="例如: IBKR 主账户"
                                    />
                                </label>
                                <label className="block">
                                    <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">券商</span>
                                    <input
                                        required
                                        className="input text-sm"
                                        value={accountForm.broker}
                                        onChange={(event) => setAccountForm({ ...accountForm, broker: event.target.value })}
                                        placeholder="Interactive Brokers"
                                    />
                                </label>
                                <label className="block">
                                    <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">类型</span>
                                    <select
                                        className="input text-sm"
                                        value={accountForm.account_type || ''}
                                        onChange={(event) => setAccountForm({ ...accountForm, account_type: event.target.value })}
                                    >
                                        <option value="">请选择…</option>
                                        {ACCOUNT_TYPES.map((item) => (
                                            <option key={item.value} value={item.value}>{item.label}</option>
                                        ))}
                                    </select>
                                </label>
                                <label className="block">
                                    <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">币种</span>
                                    <select
                                        className="input text-sm"
                                        value={accountForm.currency}
                                        onChange={(event) => setAccountForm({ ...accountForm, currency: event.target.value })}
                                    >
                                        {CURRENCY_OPTIONS.map((item) => (
                                            <option key={item.value} value={item.value}>{item.label}</option>
                                        ))}
                                    </select>
                                </label>
                                <label className="block sm:col-span-2">
                                    <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">备注</span>
                                    <textarea
                                        className="input min-h-24 text-sm"
                                        value={accountForm.description || ''}
                                        onChange={(event) => setAccountForm({ ...accountForm, description: event.target.value })}
                                        placeholder="用途、账户范围或风控备注"
                                    />
                                </label>
                            </div>

                            <div className="flex justify-end gap-2 border-t border-line p-5">
                                <button type="button" onClick={() => setIsAccountFormOpen(false)} className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-panel-subtle px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel">取消</button>
                                <button type="submit" className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft">
                                    <Plus className="mr-2 h-4 w-4" />
                                    添加账户
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    )
}

function SummaryTile({
    icon,
    label,
    value,
    detail,
}: {
    icon: ReactNode
    label: string
    value: string
    detail: string
}) {
    return (
        <div className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
            <div className="flex items-center justify-between gap-3">
                <span className="rounded-lg bg-panel-subtle p-2 text-ink-soft">{icon}</span>
                <span className="text-xs text-ink-muted">{label}</span>
            </div>
            <p className="mt-3 truncate text-xl font-black tn-nums">{value}</p>
            <p className="mt-1 truncate text-xs text-ink-muted">{detail}</p>
        </div>
    )
}

function SettingPanel({ title, children }: { title: string; children: ReactNode }) {
    return (
        <div className="rounded-lg bg-panel-subtle p-3">
            <p className="mb-3 text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">{title}</p>
            {children}
        </div>
    )
}

function ChoiceButton({
    active,
    label,
    detail,
    onClick,
}: {
    active: boolean
    label: string
    detail: string
    onClick: () => void
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`rounded-lg border p-3 text-left transition-colors ${
                active
                    ? 'border-ink bg-panel'
                    : 'border-line bg-panel-subtle hover:bg-panel'
            }`}
        >
            <p className="text-sm font-semibold">{label}</p>
            <p className="mt-1 text-xs text-ink-muted">{detail}</p>
        </button>
    )
}

function ConnectionStatus({
    ready,
    readyLabel,
    emptyLabel,
}: {
    ready: boolean
    readyLabel: string
    emptyLabel: string
}) {
    return (
        <div className={`mt-3 rounded-lg px-3 py-2 text-xs font-semibold ${
            ready
                ? 'bg-profit/10 text-profit'
                : 'bg-warning/12 text-warning'
        }`}>
            {ready ? readyLabel : emptyLabel}
        </div>
    )
}

function ParameterGuide({
    title,
    items,
    links,
}: {
    title: string
    items: string[]
    links: Array<{ label: string; href: string }>
}) {
    return (
        <div className="mt-3 rounded-lg border border-line bg-panel p-3">
            <div className="flex items-center gap-2 text-xs font-bold text-ink-soft">
                <BookOpen className="h-4 w-4" />
                {title}
            </div>
            <div className="mt-3 grid gap-2">
                {items.map((item) => (
                    <div key={item} className="flex gap-2 text-xs leading-5 text-ink-soft">
                        <Info className="mt-0.5 h-3.5 w-3.5 shrink-0 text-ink-faint" />
                        <span>{item}</span>
                    </div>
                ))}
            </div>
            <div className="mt-3 flex flex-wrap gap-2">
                {links.map((link) => (
                    <a
                        key={link.href}
                        href={link.href}
                        target="_blank"
                        rel="noreferrer"
                        className="inline-flex items-center gap-1 rounded-md border border-line px-2.5 py-1.5 text-xs font-semibold text-ink-soft transition-colors hover:bg-panel-subtle"
                    >
                        {link.label}
                        <ExternalLink className="h-3.5 w-3.5" />
                    </a>
                ))}
            </div>
        </div>
    )
}

function BrokerSyncSnapshot({
    runs,
    executions,
}: {
    runs: BrokerSyncRun[]
    executions: BrokerExecution[]
}) {
    return (
        <div className="grid gap-3 lg:grid-cols-2">
            <div className="rounded-lg bg-panel-subtle p-3">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">最近同步</p>
                <div className="mt-3 space-y-2">
                    {runs.length === 0 ? (
                        <p className="text-sm text-ink-muted">暂无同步记录</p>
                    ) : runs.map((run) => (
                        <div key={run.public_id} className="rounded-md bg-panel p-2 text-xs">
                            <div className="flex items-center justify-between gap-2">
                                <span className="font-semibold">{run.provider} · {formatBrokerMarket(run.market_type)}</span>
                                <span className="rounded-full bg-panel-subtle px-2 py-0.5 font-semibold">{formatBrokerSyncStatus(run.status)}</span>
                            </div>
                            <p className="mt-1 text-ink-muted tn-nums">
                                拉取 {run.records_fetched} · 新增 {run.records_inserted} · 跳过 {run.records_skipped}
                            </p>
                        </div>
                    ))}
                </div>
            </div>
            <div className="rounded-lg bg-panel-subtle p-3">
                <p className="text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">最近成交</p>
                <div className="mt-3 space-y-2">
                    {executions.length === 0 ? (
                        <p className="text-sm text-ink-muted">暂无原始成交</p>
                    ) : executions.map((execution) => (
                        <div key={execution.public_id} className="rounded-md bg-panel p-2 text-xs">
                            <div className="flex items-center justify-between gap-2">
                                <span className="font-semibold">{execution.symbol}</span>
                                <span className="tn-nums">{formatExecutionSide(execution.side)} {Number(execution.quantity).toLocaleString('zh-CN')}</span>
                            </div>
                            <p className="mt-1 text-ink-muted tn-nums">
                                {execution.provider} · {new Date(execution.trade_time).toLocaleString('zh-CN')} · {Number(execution.price).toLocaleString('zh-CN')}
                            </p>
                        </div>
                    ))}
                </div>
            </div>
        </div>
    )
}

function SecurityFact({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-lg bg-panel-subtle p-3">
            <p className="text-xs text-ink-muted">{label}</p>
            <p className="mt-1 text-sm font-semibold">{value}</p>
        </div>
    )
}
