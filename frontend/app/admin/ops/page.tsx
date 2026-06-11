'use client'

import { useState, type ReactNode } from 'react'
import Link from 'next/link'
import {
    AlertTriangle,
    CheckCircle2,
    DatabaseBackup,
    KeyRound,
    Loader2,
    LockKeyhole,
    ShieldCheck,
    UserPlus,
} from 'lucide-react'

import { useAuth } from '@/contexts/AuthContext'
import { adminAPI, type AdminBackupResponse, type AdminPasswordResetResponse, type AdminUserOperationResponse } from '@/lib/api'
import { formatBackupResult, formatPasswordResetNotice, isValidUserPublicIdInput } from '@/lib/adapters/admin-ops'

export default function AdminOperationsPage() {
    const { token, user } = useAuth()
    const [backupResult, setBackupResult] = useState<AdminBackupResponse | null>(null)
    const [promoteResult, setPromoteResult] = useState<AdminUserOperationResponse | null>(null)
    const [passwordResetResult, setPasswordResetResult] = useState<AdminPasswordResetResponse | null>(null)
    const [promoteUserPublicId, setPromoteUserPublicId] = useState('')
    const [resetUserPublicId, setResetUserPublicId] = useState('')
    const [isBackupRunning, setIsBackupRunning] = useState(false)
    const [isPromoteRunning, setIsPromoteRunning] = useState(false)
    const [isResetRunning, setIsResetRunning] = useState(false)
    const [error, setError] = useState('')

    const isAdmin = user?.role === 'admin'
    const formattedBackup = backupResult ? formatBackupResult(backupResult) : null
    const passwordResetNotice = passwordResetResult ? formatPasswordResetNotice(passwordResetResult) : null

    const triggerBackup = async () => {
        if (!token) return
        setError('')
        setIsBackupRunning(true)
        try {
            setBackupResult(await adminAPI.triggerBackup(token))
        } catch (err: any) {
            setError(err.message || '数据库备份失败')
        } finally {
            setIsBackupRunning(false)
        }
    }

    const promoteUser = async () => {
        if (!token || !isValidUserPublicIdInput(promoteUserPublicId)) return
        setError('')
        setIsPromoteRunning(true)
        try {
            setPromoteResult(await adminAPI.promoteUser(token, promoteUserPublicId.trim()))
        } catch (err: any) {
            setError(err.message || '提升管理员失败')
        } finally {
            setIsPromoteRunning(false)
        }
    }

    const resetPassword = async () => {
        if (!token || !isValidUserPublicIdInput(resetUserPublicId)) return
        setError('')
        setIsResetRunning(true)
        try {
            setPasswordResetResult(await adminAPI.resetUserPassword(token, resetUserPublicId.trim()))
        } catch (err: any) {
            setError(err.message || '重置密码失败')
        } finally {
            setIsResetRunning(false)
        }
    }

    if (!token) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="h-8 w-8 animate-spin text-primary-500" />
            </div>
        )
    }

    if (!isAdmin) {
        return (
            <div className="mx-auto max-w-xl py-20 text-center">
                <div className="card p-8">
                    <LockKeyhole className="mx-auto h-10 w-10 text-slate-400" />
                    <h1 className="mt-4 text-xl font-bold">需要管理员权限</h1>
                    <p className="mt-2 text-sm text-slate-500">管理员运维入口只开放给管理员账户。</p>
                    <Link href="/timeline" className="btn btn-primary mt-6 inline-flex">
                        返回时间线
                    </Link>
                </div>
            </div>
        )
    }

    return (
        <div className="space-y-6 pb-20 md:pb-8">
            <section className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-slate-950 p-6 text-white shadow-xl dark:border-slate-800">
                <div className="absolute -right-24 -top-24 h-64 w-64 rounded-full bg-cyan-400/20 blur-3xl" />
                <div className="absolute -bottom-28 left-16 h-56 w-56 rounded-full bg-amber-500/20 blur-3xl" />
                <div className="relative max-w-3xl">
                    <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs text-slate-200">
                        <ShieldCheck className="h-3.5 w-3.5 text-cyan-300" />
                        Admin operations
                    </div>
                    <h1 className="text-3xl font-black tracking-tight md:text-4xl">管理员运维控制台</h1>
                    <p className="mt-3 text-sm leading-6 text-slate-300">
                        把高风险操作从临时 shell 迁移到受权限保护、可审计的路径。当前支持 SQLite 备份、用户升 admin、临时密码重置。
                    </p>
                </div>
            </section>

            {error && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-200">
                    {error}
                </div>
            )}

            <section className="grid gap-6 lg:grid-cols-3">
                <OperationCard
                    icon={<DatabaseBackup className="h-5 w-5" />}
                    title="数据库备份"
                    description="触发一次本地 SQLite 数据库文件备份。PostgreSQL 在配置备份 provider 前会被拒绝。"
                >
                    <button
                        type="button"
                        onClick={triggerBackup}
                        disabled={isBackupRunning}
                        className="btn btn-primary w-full disabled:opacity-50"
                    >
                        {isBackupRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <DatabaseBackup className="mr-2 h-4 w-4" />}
                        触发备份
                    </button>
                    {formattedBackup && (
                        <ResultPanel tone="emerald">
                            <p className="font-semibold">{formattedBackup.backendLabel} backup {formattedBackup.statusLabel}</p>
                            <p className="mt-1 break-all font-mono text-xs">{formattedBackup.fileName}</p>
                            <p className="mt-1 text-xs text-slate-500">{formattedBackup.createdLabel}</p>
                            <p className="mt-2 text-sm">{formattedBackup.description}</p>
                            <p className="mt-2 break-all font-mono text-xs text-slate-500">{formattedBackup.path}</p>
                        </ResultPanel>
                    )}
                </OperationCard>

                <OperationCard
                    icon={<UserPlus className="h-5 w-5" />}
                    title="提升管理员"
                    description="把指定 public_id 用户显式提升为 admin。P17 不提供降级或删除账户能力。"
                >
                    <input
                        className="input"
                        value={promoteUserPublicId}
                        onChange={(event) => setPromoteUserPublicId(event.target.value)}
                        placeholder="user public_id"
                    />
                    <button
                        type="button"
                        onClick={promoteUser}
                        disabled={isPromoteRunning || !isValidUserPublicIdInput(promoteUserPublicId)}
                        className="btn btn-secondary w-full disabled:opacity-50"
                    >
                        {isPromoteRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <UserPlus className="mr-2 h-4 w-4" />}
                        提升为 admin
                    </button>
                    {promoteResult && (
                        <ResultPanel tone="emerald">
                            <p className="font-semibold">{promoteResult.user_public_id}</p>
                            <p className="mt-1 text-sm">Role: {promoteResult.role}</p>
                            <p className="mt-2 text-sm">{promoteResult.message}</p>
                        </ResultPanel>
                    )}
                </OperationCard>

                <OperationCard
                    icon={<KeyRound className="h-5 w-5" />}
                    title="重置密码"
                    description="生成一次性临时密码，更新用户凭据，并撤销现有 session/token。临时密码只在响应中显示一次。"
                >
                    <input
                        className="input"
                        value={resetUserPublicId}
                        onChange={(event) => setResetUserPublicId(event.target.value)}
                        placeholder="user public_id"
                    />
                    <button
                        type="button"
                        onClick={resetPassword}
                        disabled={isResetRunning || !isValidUserPublicIdInput(resetUserPublicId)}
                        className="btn btn-danger w-full disabled:opacity-50"
                    >
                        {isResetRunning ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <KeyRound className="mr-2 h-4 w-4" />}
                        重置密码
                    </button>
                    {passwordResetNotice && (
                        <ResultPanel tone="amber">
                            <div className="flex items-start gap-2">
                                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
                                <div>
                                    <p className="font-semibold">临时密码仅显示一次</p>
                                    <p className="mt-1 rounded-xl bg-slate-950 p-3 font-mono text-sm text-amber-100">
                                        {passwordResetNotice.temporaryPassword}
                                    </p>
                                    <p className="mt-2 text-xs">{passwordResetNotice.sessionNotice}</p>
                                    <p className="mt-2 text-xs">{passwordResetNotice.securityNotice}</p>
                                </div>
                            </div>
                        </ResultPanel>
                    )}
                </OperationCard>
            </section>
        </div>
    )
}

function OperationCard({
    icon,
    title,
    description,
    children,
}: {
    icon: ReactNode
    title: string
    description: string
    children: ReactNode
}) {
    return (
        <div className="card flex min-h-[360px] flex-col gap-4 p-5">
            <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-slate-950 text-white shadow-lg dark:bg-white dark:text-slate-950">
                {icon}
            </div>
            <div>
                <h2 className="text-lg font-black">{title}</h2>
                <p className="mt-2 text-sm leading-6 text-slate-500">{description}</p>
            </div>
            <div className="mt-auto space-y-3">{children}</div>
        </div>
    )
}

function ResultPanel({ tone, children }: { tone: 'emerald' | 'amber'; children: ReactNode }) {
    const className = tone === 'emerald'
        ? 'border-emerald-200 bg-emerald-50 text-emerald-900 dark:border-emerald-900/50 dark:bg-emerald-950/30 dark:text-emerald-100'
        : 'border-amber-200 bg-amber-50 text-amber-900 dark:border-amber-900/50 dark:bg-amber-950/30 dark:text-amber-100'
    return (
        <div className={`rounded-2xl border p-4 text-sm ${className}`}>
            <div className="mb-2 flex items-center gap-2 text-xs font-bold uppercase tracking-[0.18em]">
                <CheckCircle2 className="h-3.5 w-3.5" />
                Result
            </div>
            {children}
        </div>
    )
}
