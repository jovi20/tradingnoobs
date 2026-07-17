'use client'

import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import Link from 'next/link'
import { useTheme } from '@/components/ThemeProvider'
import {
    Activity,
    Bot,
    CheckCircle2,
    Download,
    Gauge,
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
    settingsAPI,
    type TradingAccountCreate,
} from '@/lib/api'
import { adaptTradingAccount, type TradingAccountViewModel } from '@/lib/adapters/trading'
import {
    adaptSettingsPageData,
    type SettingsPageState,
} from '@/lib/adapters/settings'
import { SettingsAccountsOverview } from '@/components/settings/domain/SettingsAccountsOverview'
import { getLocalizedUiError } from '@/lib/authErrors'

const ACCOUNT_TYPES = [
    { value: 'Spot', label: '现金账户' },
]

const CURRENCY_OPTIONS = [
    { value: 'USD', label: 'USD - 美元' },
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

export default function SettingsPage() {
    const { token, user, logout, refreshSettings, refreshUser } = useAuth()
    const { theme, setTheme } = useTheme()
    const [settings, setSettings] = useState<SettingsPageState>({})
    const [accounts, setAccounts] = useState<TradingAccountViewModel[]>([])
    const [isAccountFormOpen, setIsAccountFormOpen] = useState(false)
    const [accountForm, setAccountForm] = useState<TradingAccountCreate>({
        name: '',
        broker: '',
        account_type: 'Spot',
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
    const isAdmin = user?.role === 'admin'
    const activeAccountCount = accounts.filter((account) => account.is_active).length
    const accountCurrencies = useMemo(
        () => Array.from(new Set(accounts.map((account) => account.currency))).filter(Boolean),
        [accounts]
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
    ], [
        accounts.length,
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
                const results = await Promise.all([
                    settingsAPI.get(token),
                    accountsAPI.list(token),
                ])
                if (cancelled) return
                const adapted = adaptSettingsPageData({
                    userSettings: results[0],
                    accounts: results[1],
                })

                setSettings(adapted.settings)
                setAccounts(adapted.accounts)
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
        const results = await Promise.all([
            settingsAPI.get(token),
            accountsAPI.list(token),
        ])
        const adapted = adaptSettingsPageData({
            userSettings: results[0],
            accounts: results[1],
        })
        setSettings(adapted.settings)
        setAccounts(adapted.accounts)
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
            account_type: 'Spot',
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
                                        placeholder="例如: 主交易账户"
                                    />
                                </label>
                                <label className="block">
                                    <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">券商</span>
                                    <input
                                        required
                                        className="input text-sm"
                                        value={accountForm.broker}
                                        onChange={(event) => setAccountForm({ ...accountForm, broker: event.target.value })}
                                        placeholder="券商或交易所名称"
                                    />
                                </label>
                                <label className="block">
                                    <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">类型</span>
                                    <select
                                        className="input text-sm"
                                        value="Spot"
                                        disabled
                                    >
                                        {ACCOUNT_TYPES.map((item) => (
                                            <option key={item.value} value={item.value}>{item.label}</option>
                                        ))}
                                    </select>
                                </label>
                                <label className="block">
                                    <span className="mb-1.5 block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">币种</span>
                                    <select
                                        className="input text-sm"
                                        value="USD"
                                        disabled
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

function SecurityFact({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-lg bg-panel-subtle p-3">
            <p className="text-xs text-ink-muted">{label}</p>
            <p className="mt-1 text-sm font-semibold">{value}</p>
        </div>
    )
}
