'use client'

import { useEffect, useEffectEvent, useMemo, useState, type ReactNode } from 'react'
import Link from 'next/link'
import { useSearchParams } from 'next/navigation'
import {
    AlertTriangle,
    Ban,
    CheckCircle2,
    Clipboard,
    DatabaseBackup,
    Flag,
    Gauge,
    HardDrive,
    KeyRound,
    Loader2,
    LockKeyhole,
    PlayCircle,
    Power,
    RefreshCcw,
    Save,
    Search,
    ShieldCheck,
    SlidersHorizontal,
    ToggleLeft,
    ToggleRight,
    UserCog,
    UserMinus,
    Users,
} from 'lucide-react'

import { useAuth } from '@/contexts/AuthContext'
import {
    adminAPI,
    type AdminBackupResponse,
    type AdminBackupSummary,
    type AdminJobStatus,
    type AdminOpsSummary,
    type AdminPasswordResetResponse,
    type AdminUserOperationResponse,
    type AdminUserSummary,
    type FeatureFlag,
} from '@/lib/api'
import { adaptAdminJobsPageData, getAdminJobStatusTone, type AdminJobViewModel } from '@/lib/adapters/admin-jobs'
import { formatBackupResult, formatPasswordResetNotice, isValidUserPublicIdInput } from '@/lib/adapters/admin-ops'

type OpsTab = 'backup' | 'users' | 'platform'
type UserFilter = 'all' | 'active' | 'disabled' | 'admin'

interface FeatureFlagForm {
    key: string
    enabled: boolean
    rolloutPercentage: string
    description: string
}

const emptyJobCounts: Record<AdminJobStatus, number> = {
    QUEUED: 0,
    RUNNING: 0,
    SUCCEEDED: 0,
    FAILED: 0,
    RETRYING: 0,
    CANCELLED: 0,
}

function jobCount(counts: AdminOpsSummary['job_counts'] | undefined, status: AdminJobStatus): number {
    return Number(counts?.[status] ?? 0)
}

function formatBytes(value: number): string {
    if (value < 1024) return `${value} B`
    if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`
    return `${(value / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(value: string | null | undefined): string {
    if (!value) return '暂无'
    return new Date(value).toLocaleString('zh-CN')
}

function formatUserRole(role: string): string {
    return role === 'admin' ? '管理员' : '普通用户'
}

function formatUserState(isActive: boolean): string {
    return isActive ? '已启用' : '已停用'
}

function formatUserStatus(status: string): string {
    const labels: Record<string, string> = {
        ACTIVE: '正常',
        INACTIVE: '已停用',
        DISABLED: '已停用',
        LOCKED: '已锁定',
    }
    return labels[status.toUpperCase()] ?? status
}

export default function AdminOperationsPage() {
    const { token, user } = useAuth()
    const searchParams = useSearchParams()
    const [summary, setSummary] = useState<AdminOpsSummary | null>(null)
    const [users, setUsers] = useState<AdminUserSummary[]>([])
    const [backups, setBackups] = useState<AdminBackupSummary[]>([])
    const [featureFlags, setFeatureFlags] = useState<FeatureFlag[]>([])
    const [recentJobs, setRecentJobs] = useState<AdminJobViewModel[]>([])
    const [jobCounts, setJobCounts] = useState<Record<AdminJobStatus, number>>(emptyJobCounts)
    const [backupResult, setBackupResult] = useState<AdminBackupResponse | null>(null)
    const [userActionResult, setUserActionResult] = useState<AdminUserOperationResponse | null>(null)
    const [passwordResetResult, setPasswordResetResult] = useState<AdminPasswordResetResponse | null>(null)
    const [selectedUserPublicId, setSelectedUserPublicId] = useState('')
    const [manualUserPublicId, setManualUserPublicId] = useState('')
    const [userSearch, setUserSearch] = useState('')
    const [userFilter, setUserFilter] = useState<UserFilter>('all')
    const [activeTab, setActiveTab] = useState<OpsTab>(() => {
        const tabParam = searchParams.get('tab')
        return tabParam === 'backup' || tabParam === 'users' || tabParam === 'platform'
            ? tabParam
            : 'backup'
    })
    const [featureFlagForm, setFeatureFlagForm] = useState<FeatureFlagForm>({
        key: '',
        enabled: true,
        rolloutPercentage: '',
        description: '',
    })
    const [isLoading, setIsLoading] = useState(true)
    const [isBackupRunning, setIsBackupRunning] = useState(false)
    const [isRoleRunning, setIsRoleRunning] = useState(false)
    const [isActiveRunning, setIsActiveRunning] = useState(false)
    const [isResetRunning, setIsResetRunning] = useState(false)
    const [isFlagSaving, setIsFlagSaving] = useState(false)
    const [copiedSecret, setCopiedSecret] = useState(false)
    const [error, setError] = useState('')
    const [platformMessage, setPlatformMessage] = useState('')

    const isAdmin = user?.role === 'admin'
    const formattedBackup = backupResult ? formatBackupResult(backupResult) : null
    const passwordResetNotice = passwordResetResult ? formatPasswordResetNotice(passwordResetResult) : null
    const targetUserPublicId = (selectedUserPublicId || manualUserPublicId).trim()
    const selectedUser = users.find((item) => item.public_id === targetUserPublicId) || null
    const userMetrics = useMemo(() => {
        const active = users.filter((item) => item.is_active).length
        const admins = users.filter((item) => item.role === 'admin').length
        return { total: users.length, active, admins }
    }, [users])

    const filteredUsers = useMemo(() => {
        const query = userSearch.trim().toLowerCase()
        return users.filter((item) => {
            const matchesQuery = !query
                || item.email.toLowerCase().includes(query)
                || item.public_id.toLowerCase().includes(query)
            const matchesFilter =
                userFilter === 'all'
                || (userFilter === 'active' && item.is_active)
                || (userFilter === 'disabled' && !item.is_active)
                || (userFilter === 'admin' && item.role === 'admin')
            return matchesQuery && matchesFilter
        })
    }, [users, userSearch, userFilter])

    const riskItems = useMemo(() => {
        const items: string[] = []
        if (summary && !summary.backup_provider_configured) items.push('备份服务未配置')
        if (summary && summary.backup_count === 0) items.push('没有数据库备份记录')
        if (jobCount(summary?.job_counts, 'FAILED') > 0) items.push('存在失败任务')
        if (jobCount(summary?.job_counts, 'RETRYING') > 0) items.push('存在重试任务')
        if ((summary?.stale_running_job_count || 0) > 0) items.push('存在运行超时的任务')
        if ((summary?.expired_business_lock_count || 0) > 0) items.push('存在过期业务锁')
        if ((summary?.expired_feature_flag_count || 0) > 0) items.push('存在过期的功能开关')
        if (summary && summary.admin_count < 1) items.push('没有管理员账户')
        return items
    }, [summary])

    const loadOpsData = async () => {
        if (!token || !isAdmin) return
        setError('')
        setIsLoading(true)
        try {
            const [
                summaryData,
                usersData,
                backupsData,
                jobsData,
                featureFlagsData,
            ] = await Promise.all([
                adminAPI.getOpsSummary(token),
                adminAPI.listUsers(token, 200),
                adminAPI.listBackups(token, 10),
                adminAPI.listJobs(token, { limit: 12 }),
                adminAPI.listFeatureFlags(token),
            ])
            const adaptedJobs = adaptAdminJobsPageData(jobsData)
            const nextSelectedUser = usersData.find((item) => item.public_id === selectedUserPublicId)
                ? selectedUserPublicId
                : usersData[0]?.public_id || ''

            setSummary(summaryData)
            setUsers(usersData)
            setBackups(backupsData)
            setFeatureFlags(featureFlagsData)
            setRecentJobs(adaptedJobs.items.slice(0, 6))
            setJobCounts(adaptedJobs.counts)
            setSelectedUserPublicId(nextSelectedUser)
            setManualUserPublicId((current) => nextSelectedUser ? '' : current)
        } catch (err: any) {
            setError(err.message || '加载运维数据失败')
        } finally {
            setIsLoading(false)
        }
    }

    const loadOpsDataFromEffect = useEffectEvent(() => {
        void loadOpsData()
    })

    useEffect(() => {
        if (!token || !isAdmin) return
        const loadTimer = window.setTimeout(() => {
            loadOpsDataFromEffect()
        }, 0)
        return () => window.clearTimeout(loadTimer)
    }, [token, isAdmin])

    const triggerBackup = async () => {
        if (!token) return
        setError('')
        setIsBackupRunning(true)
        try {
            setBackupResult(await adminAPI.triggerBackup(token))
            setActiveTab('backup')
            await loadOpsData()
        } catch (err: any) {
            setError(err.message || '数据库备份失败')
        } finally {
            setIsBackupRunning(false)
        }
    }

    const updateRole = async (role: 'user' | 'admin') => {
        if (!token || !isValidUserPublicIdInput(targetUserPublicId)) return
        setError('')
        setUserActionResult(null)
        setIsRoleRunning(true)
        try {
            const result = await adminAPI.updateUserRole(token, targetUserPublicId, role)
            setUserActionResult(result)
            setActiveTab('users')
            await loadOpsData()
        } catch (err: any) {
            setError(err.message || '更新用户角色失败')
        } finally {
            setIsRoleRunning(false)
        }
    }

    const toggleActive = async () => {
        if (!token || !selectedUser || !isValidUserPublicIdInput(targetUserPublicId)) return
        setError('')
        setUserActionResult(null)
        setIsActiveRunning(true)
        try {
            const result = await adminAPI.updateUserActive(token, targetUserPublicId, !selectedUser.is_active)
            setUserActionResult(result)
            setActiveTab('users')
            await loadOpsData()
        } catch (err: any) {
            setError(err.message || '更新用户状态失败')
        } finally {
            setIsActiveRunning(false)
        }
    }

    const resetPassword = async () => {
        if (!token || !isValidUserPublicIdInput(targetUserPublicId)) return
        setError('')
        setCopiedSecret(false)
        setPasswordResetResult(null)
        setIsResetRunning(true)
        try {
            setPasswordResetResult(await adminAPI.resetUserPassword(token, targetUserPublicId))
            setActiveTab('users')
            await loadOpsData()
        } catch (err: any) {
            setError(err.message || '重置密码失败')
        } finally {
            setIsResetRunning(false)
        }
    }

    const copyTemporaryPassword = async () => {
        if (!passwordResetNotice?.temporaryPassword) return
        await navigator.clipboard.writeText(passwordResetNotice.temporaryPassword)
        setCopiedSecret(true)
        window.setTimeout(() => setCopiedSecret(false), 1800)
    }

    const saveFeatureFlag = async () => {
        if (!token || !featureFlagForm.key.trim()) return
        setError('')
        setPlatformMessage('')
        setIsFlagSaving(true)
        try {
            const rollout = featureFlagForm.rolloutPercentage.trim()
                ? Number(featureFlagForm.rolloutPercentage)
                : null
            await adminAPI.upsertFeatureFlag(token, featureFlagForm.key.trim(), {
                enabled: featureFlagForm.enabled,
                rollout_percentage: rollout,
                description: featureFlagForm.description.trim() || undefined,
            })
            setPlatformMessage('功能开关已保存')
            setFeatureFlagForm({
                key: '',
                enabled: true,
                rolloutPercentage: '',
                description: '',
            })
            await loadOpsData()
        } catch (err: any) {
            setError(err.message || '保存功能开关失败')
        } finally {
            setIsFlagSaving(false)
        }
    }

    const toggleFeatureFlag = async (flag: FeatureFlag) => {
        if (!token) return
        setError('')
        setPlatformMessage('')
        setIsFlagSaving(true)
        try {
            await adminAPI.upsertFeatureFlag(token, flag.key, {
                enabled: !flag.enabled,
                actor_targets: flag.actor_targets,
                rollout_percentage: flag.rollout_percentage,
                expires_at: flag.expires_at,
                description: flag.description || undefined,
            })
            setPlatformMessage(`${flag.key} 已${flag.enabled ? '关闭' : '开启'}`)
            await loadOpsData()
        } catch (err: any) {
            setError(err.message || '更新功能开关失败')
        } finally {
            setIsFlagSaving(false)
        }
    }

    if (!token) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-ink-muted" />
            </div>
        )
    }

    if (!isAdmin) {
        return (
            <div className="mx-auto max-w-xl py-20 text-center">
                <div className="rounded-lg border border-line bg-panel p-8 shadow-panel dark:shadow-none">
                    <LockKeyhole className="mx-auto h-10 w-10 text-ink-faint" />
                    <h1 className="mt-4 text-xl font-bold">需要管理员权限</h1>
                    <p className="mt-2 text-sm text-ink-muted">管理员运维入口只开放给管理员账户。</p>
                    <Link href="/timeline" className="mt-6 inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft">
                        返回时间线
                    </Link>
                </div>
            </div>
        )
    }

    return (
        <div className="mx-auto max-w-7xl space-y-5 pb-20 md:pb-8">
            <section className="border-b border-line pb-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
                    <div>
                        <div className="mb-3 inline-flex items-center gap-2 rounded-full bg-panel-subtle px-3 py-1 text-xs font-semibold text-ink-soft">
                            <ShieldCheck className="h-3.5 w-3.5" />
                            管理运维
                        </div>
                        <h1 className="text-2xl font-black tracking-tight text-ink md:text-3xl">
                            运维与管理工作台
                        </h1>
                    </div>
                    <div className="flex flex-wrap gap-2">
                        <Link href="/admin/jobs" className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-transparent px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel-subtle">
                            <PlayCircle className="mr-2 h-4 w-4" />
                            任务控制台
                        </Link>
                        <button
                            type="button"
                            onClick={loadOpsData}
                            disabled={isLoading}
                            className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-panel-subtle px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel disabled:opacity-50"
                        >
                            {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RefreshCcw className="mr-2 h-4 w-4" />}
                            刷新
                        </button>
                    </div>
                </div>
            </section>

            {error && (
                <div className="rounded-lg border border-loss/30 bg-loss/10 p-4 text-sm text-loss">
                    {error}
                </div>
            )}

            {platformMessage && (
                <div className="rounded-lg border border-profit/30 bg-profit/10 p-4 text-sm text-profit">
                    {platformMessage}
                </div>
            )}

            <section className="grid gap-3 md:grid-cols-6">
                <StatusTile icon={<Users className="h-4 w-4" />} label="用户" value={String(summary?.user_count ?? userMetrics.total)} detail={`${summary?.active_user_count ?? userMetrics.active} 个已启用`} />
                <StatusTile icon={<ShieldCheck className="h-4 w-4" />} label="管理员" value={String(summary?.admin_count ?? userMetrics.admins)} detail="拥有管理权限的用户" />
                <StatusTile icon={<DatabaseBackup className="h-4 w-4" />} label="备份" value={String(summary?.backup_count ?? backups.length)} detail={summary?.latest_backup_at ? formatDate(summary.latest_backup_at) : '暂无记录'} />
                <StatusTile icon={<Gauge className="h-4 w-4" />} label="运行任务" value={String(jobCount(summary?.job_counts, 'RUNNING') || jobCounts.RUNNING)} detail={`${jobCount(summary?.job_counts, 'QUEUED') || jobCounts.QUEUED} 个排队中`} />
                <StatusTile icon={<Flag className="h-4 w-4" />} label="功能开关" value={String(featureFlags.length)} detail={`${summary?.enabled_feature_flag_count ?? featureFlags.filter((item) => item.enabled).length} 个已启用`} />
                <StatusTile icon={<AlertTriangle className="h-4 w-4" />} label="风险" value={String(riskItems.length)} detail={riskItems[0] || '无异常'} tone={riskItems.length > 0 ? 'danger' : 'neutral'} />
            </section>

            <section className="grid grid-cols-[minmax(0,1fr)] gap-5 xl:grid-cols-[minmax(0,0.95fr)_minmax(450px,1.05fr)]">
                <div className="min-w-0 space-y-5">
                    <div className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
                        <div className="flex items-center justify-between gap-3">
                            <div>
                                <h2 className="flex items-center gap-2 text-base font-bold">
                                    <HardDrive className="h-4 w-4" />
                                    系统状态
                                </h2>
                                <p className="mt-1 text-xs text-ink-muted">数据库、备份、任务、配置和业务锁状态。</p>
                            </div>
                            <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                                riskItems.length > 0
                                    ? 'bg-warning/12 text-warning'
                                    : 'bg-profit/10 text-profit'
                            }`}>
                                {riskItems.length > 0 ? '需关注' : '运行正常'}
                            </span>
                        </div>
                        <div className="mt-4 grid gap-3 sm:grid-cols-3">
                            <SystemFact label="数据库" value={summary?.database_backend || '未知'} />
                            <SystemFact label="备份服务" value={summary?.backup_provider_configured ? '已配置' : '未配置'} />
                            <SystemFact label="超时任务" value={String(summary?.stale_running_job_count ?? 0)} />
                            <SystemFact label="启用功能开关" value={String(summary?.enabled_feature_flag_count ?? featureFlags.filter((item) => item.enabled).length)} />
                            <SystemFact label="活动业务锁" value={String(summary?.active_business_lock_count ?? 0)} />
                            <SystemFact label="过期功能开关" value={String(summary?.expired_feature_flag_count ?? 0)} />
                        </div>
                        {riskItems.length > 0 && (
                            <div className="mt-4 rounded-lg border border-warning/30 bg-warning/12 p-3 text-sm text-warning">
                                {riskItems.map((item) => (
                                    <p key={item} className="flex items-center gap-2">
                                        <AlertTriangle className="h-4 w-4" />
                                        {item}
                                    </p>
                                ))}
                            </div>
                        )}
                    </div>

                    <div className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
                        <div className="flex items-center justify-between gap-3">
                            <div>
                                <h2 className="flex items-center gap-2 text-base font-bold">
                                    <Gauge className="h-4 w-4" />
                                    任务健康
                                </h2>
                                <p className="mt-1 text-xs text-ink-muted">最近任务状态和后台队列入口。</p>
                            </div>
                            <Link href="/admin/jobs" className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-transparent px-4 py-2 text-xs font-medium text-ink-soft transition-colors hover:bg-panel-subtle">
                                打开任务
                            </Link>
                        </div>
                        <div className="mt-4 grid grid-cols-3 gap-2">
                            {(['RUNNING', 'FAILED', 'RETRYING'] as AdminJobStatus[]).map((status) => {
                                const tone = getAdminJobStatusTone(status)
                                const value = jobCount(summary?.job_counts, status) || jobCounts[status]
                                return (
                                    <div key={status} className="rounded-lg bg-panel-subtle p-3">
                                        <div className={`mb-2 h-1.5 w-8 rounded-full ${tone.accent}`} />
                                        <p className="text-xs text-ink-muted">{tone.label}</p>
                                        <p className="mt-1 text-xl font-black tn-nums">{value}</p>
                                    </div>
                                )
                            })}
                        </div>
                        <div className="mt-4 divide-y divide-line">
                            {recentJobs.length === 0 ? (
                                <div className="rounded-lg border border-dashed border-line p-5 text-center text-sm text-ink-muted">
                                    暂无后台任务。
                                </div>
                            ) : (
                                recentJobs.map((job) => (
                                    <div key={job.public_id} className="flex items-center justify-between gap-3 py-3">
                                        <div className="min-w-0">
                                            <p className="truncate text-sm font-semibold">{job.definition.display_name}</p>
                                            <p className="mt-1 truncate font-mono text-xs text-ink-muted">{job.queue_name} · {job.createdLabel}</p>
                                        </div>
                                        <span className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${job.statusClassName}`}>
                                            {job.statusLabel}
                                        </span>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    <div className="rounded-lg border border-line bg-panel p-4 shadow-panel dark:shadow-none">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                            <div>
                                <h2 className="flex items-center gap-2 text-base font-bold">
                                    <Users className="h-4 w-4" />
                                    用户目录
                                </h2>
                                <p className="mt-1 text-xs text-ink-muted">已显示 {filteredUsers.length} 人 · 共 {users.length} 人</p>
                            </div>
                            <select
                                className="input max-w-[11rem] py-2 text-sm"
                                value={userFilter}
                                onChange={(event) => setUserFilter(event.target.value as UserFilter)}
                            >
                                <option value="all">全部用户</option>
                                <option value="active">已启用</option>
                                <option value="disabled">已停用</option>
                                <option value="admin">管理员</option>
                            </select>
                        </div>
                        <div className="relative mt-4">
                            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-faint" />
                            <input
                                className="input py-2 pl-10 text-sm"
                                value={userSearch}
                                onChange={(event) => setUserSearch(event.target.value)}
                                placeholder="搜索邮箱或公开 ID（public_id）"
                            />
                        </div>
                        <div className="mt-4 max-h-[28rem] space-y-2 overflow-auto pr-1">
                            {filteredUsers.length === 0 ? (
                                <EmptyResult icon={<Users className="h-5 w-5" />} text="没有匹配的用户。" />
                            ) : (
                                filteredUsers.map((item) => {
                                    const isSelected = item.public_id === targetUserPublicId
                                    const isSelf = item.public_id === user?.public_id
                                    return (
                                        <button
                                            key={item.public_id}
                                            type="button"
                                            onClick={() => {
                                                setSelectedUserPublicId(item.public_id)
                                                setManualUserPublicId('')
                                                setActiveTab('users')
                                            }}
                                            className={`flex w-full items-center justify-between gap-3 rounded-lg border p-3 text-left transition-colors ${
                                                isSelected
                                                    ? 'border-ink bg-panel-subtle'
                                                    : 'border-line hover:border-line-strong hover:bg-panel-subtle'
                                            }`}
                                        >
                                            <div className="min-w-0">
                                                <p className="truncate text-sm font-semibold">{item.email}</p>
                                                <p className="mt-1 truncate font-mono text-xs text-ink-muted">{item.public_id}</p>
                                            </div>
                                            <div className="flex shrink-0 items-center gap-2">
                                                {isSelf && (
                                                    <span className="rounded-full bg-ai/10 px-2 py-0.5 text-xs font-semibold text-ai">
                                                        当前用户
                                                    </span>
                                                )}
                                                <span className={`rounded-full px-2 py-0.5 text-xs font-semibold ${
                                                    item.role === 'admin'
                                                        ? 'bg-ink text-canvas'
                                                        : 'bg-panel-subtle text-ink-soft'
                                                }`}>
                                                    {formatUserRole(item.role)}
                                                </span>
                                                <span className={`h-2.5 w-2.5 rounded-full ${item.is_active ? 'bg-profit' : 'bg-ink-faint'}`} />
                                            </div>
                                        </button>
                                    )
                                })
                            )}
                        </div>
                    </div>
                </div>

                <div className="min-w-0 rounded-lg border border-line bg-panel shadow-panel dark:shadow-none">
                    <div className="border-b border-line p-2">
                        <div className="grid grid-cols-3 gap-2">
                            <TabButton active={activeTab === 'backup'} onClick={() => setActiveTab('backup')} icon={<DatabaseBackup className="h-4 w-4" />} label="备份" />
                            <TabButton active={activeTab === 'users'} onClick={() => setActiveTab('users')} icon={<UserCog className="h-4 w-4" />} label="用户" />
                            <TabButton active={activeTab === 'platform'} onClick={() => setActiveTab('platform')} icon={<SlidersHorizontal className="h-4 w-4" />} label="配置" />
                        </div>
                    </div>

                    <div className="p-5">
                        {activeTab === 'backup' && (
                            <div className="space-y-5">
                                <PanelHeading
                                    icon={<DatabaseBackup className="h-5 w-5" />}
                                    title="备份管理"
                                    detail="触发数据库备份，查看最近备份文件、大小和生成时间。"
                                />
                                <button
                                    type="button"
                                    onClick={triggerBackup}
                                    disabled={isBackupRunning || summary?.backup_provider_configured === false}
                                    className="inline-flex w-full items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft disabled:opacity-50"
                                >
                                    {isBackupRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <DatabaseBackup className="mr-2 h-4 w-4" />}
                                    立即备份
                                </button>
                                {formattedBackup && (
                                    <ResultPanel tone="success" title="备份完成">
                                        <dl className="grid gap-3 text-sm">
                                            <ResultRow label="数据库" value={formattedBackup.backendLabel} />
                                            <ResultRow label="状态" value={formattedBackup.statusLabel} />
                                            <ResultRow label="文件" value={formattedBackup.fileName} mono />
                                            <ResultRow label="创建时间" value={formattedBackup.createdLabel} />
                                            <ResultRow label="路径" value={formattedBackup.path} mono />
                                        </dl>
                                    </ResultPanel>
                                )}
                                <div>
                                    <h3 className="mb-3 text-sm font-bold">备份历史</h3>
                                    <div className="space-y-2">
                                        {backups.length === 0 ? (
                                            <EmptyResult icon={<DatabaseBackup className="h-5 w-5" />} text="还没有备份记录。" />
                                        ) : (
                                            backups.map((backup) => (
                                                <div key={backup.backup_id} className="rounded-lg border border-line p-3 text-sm">
                                                    <div className="flex items-center justify-between gap-3">
                                                        <span className="font-semibold">{backup.backup_id}</span>
                                                        <span className="rounded-full bg-panel-subtle px-2 py-0.5 text-xs text-ink-soft tn-nums">
                                                            {formatBytes(backup.size_bytes)}
                                                        </span>
                                                    </div>
                                                    <p className="mt-1 text-xs text-ink-muted">{formatDate(backup.created_at)}</p>
                                                    <p className="mt-1 break-all font-mono text-xs text-ink-muted">{backup.path}</p>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}

                        {activeTab === 'users' && (
                            <div className="space-y-5">
                                <PanelHeading
                                    icon={<UserCog className="h-5 w-5" />}
                                    title="用户管理"
                                    detail="管理用户角色、启停状态和密码重置。危险操作带有后端保护。"
                                />
                                <div className="space-y-3">
                                    <label className="block text-xs font-bold uppercase tracking-[0.14em] text-ink-muted">目标用户</label>
                                    <select
                                        className="input"
                                        value={selectedUserPublicId}
                                        onChange={(event) => {
                                            setSelectedUserPublicId(event.target.value)
                                            setManualUserPublicId('')
                                        }}
                                    >
                                        {users.map((item) => (
                                            <option key={item.public_id} value={item.public_id}>
                                                {item.email} · {formatUserRole(item.role)} · {formatUserState(item.is_active)}
                                            </option>
                                        ))}
                                    </select>
                                    <input
                                        className="input font-mono text-sm"
                                        value={manualUserPublicId}
                                        onChange={(event) => {
                                            setManualUserPublicId(event.target.value)
                                            setSelectedUserPublicId('')
                                        }}
                                        placeholder="或手动输入用户公开 ID"
                                    />
                                </div>

                                {selectedUser && (
                                    <div className="rounded-lg bg-panel-subtle p-4">
                                        <div className="flex items-start justify-between gap-3">
                                            <div className="min-w-0">
                                                <p className="truncate font-semibold">{selectedUser.email}</p>
                                                <p className="mt-1 break-all font-mono text-xs text-ink-muted">{selectedUser.public_id}</p>
                                            </div>
                                            <div className="flex shrink-0 gap-2">
                                                <span className="rounded-full bg-ink px-2.5 py-1 text-xs font-semibold text-canvas">
                                                    {formatUserRole(selectedUser.role)}
                                                </span>
                                                <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                                                    selectedUser.is_active
                                                        ? 'bg-profit/10 text-profit'
                                                        : 'bg-panel-subtle text-ink-muted'
                                                }`}>
                                                    {formatUserState(selectedUser.is_active)}
                                                </span>
                                            </div>
                                        </div>
                                        <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-ink-muted">
                                            <span>状态：{formatUserStatus(selectedUser.status)}</span>
                                            <span>创建日期：{new Date(selectedUser.created_at).toLocaleDateString('zh-CN')}</span>
                                            <span className="col-span-2">最近登录：{selectedUser.last_login_at ? formatDate(selectedUser.last_login_at) : '从未登录'}</span>
                                        </div>
                                    </div>
                                )}

                                <div className="grid gap-3 sm:grid-cols-2">
                                    <button
                                        type="button"
                                        onClick={() => updateRole('admin')}
                                        disabled={isRoleRunning || !isValidUserPublicIdInput(targetUserPublicId) || selectedUser?.role === 'admin'}
                                        className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-panel-subtle px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel disabled:opacity-50"
                                    >
                                        {isRoleRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <ShieldCheck className="mr-2 h-4 w-4" />}
                                        设为管理员
                                    </button>
                                    <button
                                        type="button"
                                        onClick={() => updateRole('user')}
                                        disabled={isRoleRunning || !isValidUserPublicIdInput(targetUserPublicId) || selectedUser?.role === 'user'}
                                        className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-transparent px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel-subtle disabled:opacity-50"
                                    >
                                        {isRoleRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <UserMinus className="mr-2 h-4 w-4" />}
                                        设为普通用户
                                    </button>
                                    <button
                                        type="button"
                                        onClick={toggleActive}
                                        disabled={isActiveRunning || !selectedUser || !isValidUserPublicIdInput(targetUserPublicId)}
                                        className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-panel-subtle px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel disabled:opacity-50"
                                    >
                                        {isActiveRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : selectedUser?.is_active ? <Ban className="mr-2 h-4 w-4" /> : <Power className="mr-2 h-4 w-4" />}
                                        {selectedUser?.is_active ? '停用用户' : '启用用户'}
                                    </button>
                                    <button
                                        type="button"
                                        onClick={resetPassword}
                                        disabled={isResetRunning || !isValidUserPublicIdInput(targetUserPublicId)}
                                        className="inline-flex items-center justify-center gap-2 rounded-md bg-loss px-4 py-2 text-sm font-medium text-white transition-colors hover:opacity-90 disabled:opacity-50"
                                    >
                                        {isResetRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <KeyRound className="mr-2 h-4 w-4" />}
                                        重置密码
                                    </button>
                                </div>

                                {userActionResult && (
                                    <ResultPanel tone="success" title="用户操作完成">
                                        <ResultRow label="用户" value={userActionResult.user_public_id} mono />
                                        <ResultRow label="角色" value={formatUserRole(userActionResult.role)} />
                                        <p className="mt-3 text-sm">用户信息已更新。</p>
                                    </ResultPanel>
                                )}

                                {passwordResetNotice && (
                                    <ResultPanel tone="warning" title="临时密码">
                                        <div className="rounded-lg bg-ink p-3 text-warning">
                                            <div className="flex items-center justify-between gap-3">
                                                <code className="break-all text-sm">{passwordResetNotice.temporaryPassword}</code>
                                                <button
                                                    type="button"
                                                    onClick={copyTemporaryPassword}
                                                    className="rounded-lg p-2 text-warning transition-colors hover:bg-canvas/10"
                                                    title="复制临时密码"
                                                    aria-label="复制临时密码"
                                                >
                                                    {copiedSecret ? <CheckCircle2 className="h-4 w-4" /> : <Clipboard className="h-4 w-4" />}
                                                </button>
                                            </div>
                                        </div>
                                        <p className="mt-3 text-xs">{passwordResetNotice.sessionNotice}</p>
                                        <p className="mt-2 text-xs">{passwordResetNotice.securityNotice}</p>
                                    </ResultPanel>
                                )}
                            </div>
                        )}

                        {activeTab === 'platform' && (
                            <div className="space-y-5">
                                <PanelHeading
                                    icon={<SlidersHorizontal className="h-5 w-5" />}
                                    title="平台控制"
                                    detail="管理运行时功能开关及灰度比例。"
                                />

                                <div className="rounded-lg border border-line p-4">
                                    <h3 className="mb-4 flex items-center gap-2 text-sm font-bold">
                                        <Flag className="h-4 w-4" />
                                        功能开关
                                    </h3>
                                    <div className="grid gap-3">
                                        <input
                                            className="input font-mono text-sm"
                                            value={featureFlagForm.key}
                                            onChange={(event) => setFeatureFlagForm((current) => ({ ...current, key: event.target.value }))}
                                            placeholder="flag_key"
                                        />
                                        <div className="grid gap-3 sm:grid-cols-[1fr_8rem]">
                                            <input
                                                className="input text-sm"
                                                value={featureFlagForm.description}
                                                onChange={(event) => setFeatureFlagForm((current) => ({ ...current, description: event.target.value }))}
                                                placeholder="描述"
                                            />
                                            <input
                                                className="input text-sm"
                                                type="number"
                                                min={0}
                                                max={100}
                                                value={featureFlagForm.rolloutPercentage}
                                                onChange={(event) => setFeatureFlagForm((current) => ({ ...current, rolloutPercentage: event.target.value }))}
                                                placeholder="灰度比例 %"
                                            />
                                        </div>
                                        <div className="grid gap-2 sm:grid-cols-[1fr_1fr]">
                                            <button
                                                type="button"
                                                onClick={() => setFeatureFlagForm((current) => ({ ...current, enabled: !current.enabled }))}
                                                className="inline-flex items-center justify-center gap-2 rounded-md border border-line bg-transparent px-4 py-2 text-sm font-medium text-ink-soft transition-colors hover:bg-panel-subtle"
                                            >
                                                {featureFlagForm.enabled ? <ToggleRight className="mr-2 h-4 w-4" /> : <ToggleLeft className="mr-2 h-4 w-4" />}
                                                {featureFlagForm.enabled ? '默认开启' : '默认关闭'}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={saveFeatureFlag}
                                                disabled={isFlagSaving || !featureFlagForm.key.trim()}
                                                className="inline-flex items-center justify-center gap-2 rounded-md bg-ink px-4 py-2 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft disabled:opacity-50"
                                            >
                                                {isFlagSaving ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <Save className="mr-2 h-4 w-4" />}
                                                保存开关
                                            </button>
                                        </div>
                                    </div>

                                    <div className="mt-4 space-y-2">
                                        {featureFlags.length === 0 ? (
                                            <EmptyResult icon={<Flag className="h-5 w-5" />} text="还没有功能开关。" />
                                        ) : (
                                            featureFlags.map((flag) => (
                                                <div key={flag.key} className="flex items-center justify-between gap-3 rounded-lg border border-line p-3 text-sm">
                                                    <div className="min-w-0">
                                                        <p className="truncate font-semibold">{flag.key}</p>
                                                        <p className="mt-1 truncate text-xs text-ink-muted">
                                                            {flag.description || '暂无描述'} · 灰度比例 {flag.rollout_percentage ?? '全部'}
                                                        </p>
                                                    </div>
                                                    <button
                                                        type="button"
                                                        onClick={() => toggleFeatureFlag(flag)}
                                                        disabled={isFlagSaving}
                                                        className={`inline-flex shrink-0 items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold transition-colors ${
                                                            flag.enabled
                                                                ? 'bg-profit/10 text-profit hover:bg-profit/20'
                                                                : 'bg-panel-subtle text-ink-soft hover:bg-panel'
                                                        }`}
                                                    >
                                                        {flag.enabled ? <ToggleRight className="h-3.5 w-3.5" /> : <ToggleLeft className="h-3.5 w-3.5" />}
                                                        {flag.enabled ? '已开启' : '已关闭'}
                                                    </button>
                                                </div>
                                            ))
                                        )}
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </section>
        </div>
    )
}

function StatusTile({
    icon,
    label,
    value,
    detail,
    tone = 'neutral',
}: {
    icon: ReactNode
    label: string
    value: string
    detail: string
    tone?: 'neutral' | 'danger'
}) {
    return (
        <div className={`rounded-lg border bg-panel p-4 shadow-panel dark:shadow-none ${
            tone === 'danger' ? 'border-loss/40' : 'border-line'
        }`}>
            <div className="flex items-center justify-between gap-3">
                <span className="rounded-lg bg-panel-subtle p-2 text-ink-soft">{icon}</span>
                <span className="text-xs text-ink-muted">{label}</span>
            </div>
            <p className="mt-3 text-2xl font-black tn-nums">{value}</p>
            <p className="mt-1 truncate text-xs text-ink-muted">{detail}</p>
        </div>
    )
}

function SystemFact({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-lg bg-panel-subtle p-3">
            <p className="text-xs text-ink-muted">{label}</p>
            <p className="mt-1 truncate text-sm font-semibold">{value}</p>
        </div>
    )
}

function TabButton({
    active,
    icon,
    label,
    onClick,
}: {
    active: boolean
    icon: ReactNode
    label: string
    onClick: () => void
}) {
    return (
        <button
            type="button"
            onClick={onClick}
            className={`inline-flex items-center justify-center gap-2 rounded-lg px-3 py-2 text-sm font-semibold transition-colors ${
                active
                    ? 'bg-ink text-canvas'
                    : 'text-ink-muted hover:bg-panel-subtle hover:text-ink'
            }`}
        >
            {icon}
            {label}
        </button>
    )
}

function PanelHeading({ icon, title, detail }: { icon: ReactNode; title: string; detail: string }) {
    return (
        <div className="flex items-start gap-3">
            <div className="rounded-lg bg-ink p-3 text-canvas">{icon}</div>
            <div>
                <h2 className="text-lg font-black">{title}</h2>
                <p className="mt-1 text-sm leading-6 text-ink-muted">{detail}</p>
            </div>
        </div>
    )
}

function ResultPanel({
    tone,
    title,
    children,
}: {
    tone: 'success' | 'warning'
    title: string
    children: ReactNode
}) {
    const className = tone === 'success'
        ? 'border-profit/30 bg-profit/10 text-profit'
        : 'border-warning/30 bg-warning/12 text-warning'
    const Icon = tone === 'success' ? CheckCircle2 : AlertTriangle
    return (
        <div className={`rounded-lg border p-4 ${className}`}>
            <div className="mb-3 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.14em]">
                <Icon className="h-4 w-4" />
                {title}
            </div>
            {children}
        </div>
    )
}

function ResultRow({ label, value, mono = false }: { label: string; value: string; mono?: boolean }) {
    return (
        <div className="grid gap-1 sm:grid-cols-[7rem_minmax(0,1fr)]">
            <dt className="text-xs font-bold uppercase tracking-[0.12em] opacity-70">{label}</dt>
            <dd className={`break-all ${mono ? 'font-mono text-xs' : ''}`}>{value}</dd>
        </div>
    )
}

function EmptyResult({ icon, text }: { icon: ReactNode; text: string }) {
    return (
        <div className="flex min-h-32 flex-col items-center justify-center rounded-lg border border-dashed border-line p-6 text-center text-sm text-ink-muted">
            <div className="mb-3 rounded-lg bg-panel-subtle p-3 text-ink-faint">{icon}</div>
            {text}
        </div>
    )
}
