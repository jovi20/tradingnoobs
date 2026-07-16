'use client'

import { useState } from 'react'
import {
    AlertTriangle,
    Ban,
    CheckCircle2,
    Clock3,
    ListFilter,
    Loader2,
    PlayCircle,
    RotateCcw,
    ShieldAlert,
    Zap,
} from 'lucide-react'

import type { AdminJobRunDetail, AdminJobStatus } from '@/lib/api'
import type { AdminJobViewModel } from '@/lib/adapters/admin-jobs'
import { formatAdminJobRecommendedAction, getAdminJobStatusTone } from '@/lib/adapters/admin-jobs'

const STATUS_FILTERS: Array<{ value: AdminJobStatus | 'ALL'; label: string }> = [
    { value: 'ALL', label: '全部状态' },
    { value: 'QUEUED', label: '排队中' },
    { value: 'RUNNING', label: '运行中' },
    { value: 'FAILED', label: '已失败' },
    { value: 'RETRYING', label: '重试中' },
    { value: 'SUCCEEDED', label: '已成功' },
    { value: 'CANCELLED', label: '已取消' },
]
const FORCE_CANCEL_CONFIRMATION = 'FORCE CANCEL'

interface AdminJobsConsoleProps {
    jobs: AdminJobViewModel[]
    counts: Record<AdminJobStatus, number>
    queues: string[]
    total: number
    statusFilter: AdminJobStatus | 'ALL'
    queueFilter: string
    selectedJob: AdminJobRunDetail | null
    isLoading: boolean
    isDetailLoading: boolean
    isActionRunning: boolean
    error: string
    onStatusFilterChange: (status: AdminJobStatus | 'ALL') => void
    onQueueFilterChange: (queueName: string) => void
    onRefresh: () => void
    onSelectJob: (jobPublicId: string) => void
    onRequeueJob: (jobPublicId: string) => void
    onCancelJob: (jobPublicId: string) => void
    onForceCancelJob: (jobPublicId: string) => void
}

export function AdminJobsConsole({
    jobs,
    counts,
    queues,
    total,
    statusFilter,
    queueFilter,
    selectedJob,
    isLoading,
    isDetailLoading,
    isActionRunning,
    error,
    onStatusFilterChange,
    onQueueFilterChange,
    onRefresh,
    onSelectJob,
    onRequeueJob,
    onCancelJob,
    onForceCancelJob,
}: AdminJobsConsoleProps) {
    const selectedTone = selectedJob ? getAdminJobStatusTone(selectedJob.status) : null
    const selectedRecommendedActionLabel = formatAdminJobRecommendedAction(selectedJob?.recommended_action)
    const [forceCancelConfirmation, setForceCancelConfirmation] = useState({ jobPublicId: '', value: '' })
    const activeForceCancelConfirmation =
        selectedJob?.status === 'RUNNING' && forceCancelConfirmation.jobPublicId === selectedJob.public_id
            ? forceCancelConfirmation.value
            : ''
    const isForceCancelConfirmed = activeForceCancelConfirmation.trim() === FORCE_CANCEL_CONFIRMATION

    return (
        <div className="space-y-6 pb-20 md:pb-8">
            <section className="relative overflow-hidden rounded-lg border border-line bg-ink p-6 text-canvas">
                <div className="absolute -right-24 -top-24 h-64 w-64 rounded-full bg-profit/20 blur-3xl" />
                <div className="absolute -bottom-28 left-16 h-56 w-56 rounded-full bg-ai/20 blur-3xl" />
                <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
                    <div>
                        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs text-canvas/80">
                            <Zap className="h-3.5 w-3.5 text-profit" />
                            异步任务控制
                        </div>
                        <h1 className="text-3xl font-black tracking-tight md:text-4xl">后台任务控制台</h1>
                        <p className="mt-3 max-w-2xl text-sm leading-6 text-canvas/80">
                            查看事件发件箱派生的后台任务，追踪执行器状态、失败原因与事件历史。
                            失败任务可重新入队，未执行任务可取消，强制取消仅用于处理超时锁。
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={onRefresh}
                        className="btn bg-panel text-ink hover:bg-panel-subtle"
                    >
                        {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RotateCcw className="mr-2 h-4 w-4" />}
                        刷新任务
                    </button>
                </div>
            </section>

            {error && (
                <div className="rounded-lg border border-loss/30 bg-loss/10 p-4 text-sm text-loss">
                    {error}
                </div>
            )}

            <section className="grid gap-3 md:grid-cols-6">
                {STATUS_FILTERS.filter((item) => item.value !== 'ALL').map((item) => {
                    const tone = getAdminJobStatusTone(item.value as AdminJobStatus)
                    return (
                        <button
                            key={item.value}
                            type="button"
                            onClick={() => onStatusFilterChange(item.value as AdminJobStatus)}
                            className={`card p-4 text-left transition-colors ${
                                statusFilter === item.value ? 'ring-2 ring-ink' : ''
                            }`}
                        >
                            <div className={`mb-3 h-2 w-10 rounded-full ${tone.accent}`} />
                            <p className="text-xs text-ink-muted">{tone.label}</p>
                            <p className="mt-1 text-2xl font-black tn-nums">{counts[item.value as AdminJobStatus]}</p>
                        </button>
                    )
                })}
            </section>

            <section className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
                <div className="card overflow-hidden">
                    <div className="flex flex-col gap-3 border-b border-line p-4 md:flex-row md:items-center md:justify-between">
                        <div>
                            <h2 className="flex items-center gap-2 text-lg font-bold">
                                <ListFilter className="h-5 w-5" />
                                任务记录
                            </h2>
                            <p className="text-xs text-ink-muted">已显示 {jobs.length} 项，共 {total} 项</p>
                        </div>
                        <div className="grid grid-cols-2 gap-2 md:flex">
                            <select
                                className="input text-sm"
                                value={statusFilter}
                                onChange={(event) => onStatusFilterChange(event.target.value as AdminJobStatus | 'ALL')}
                            >
                                {STATUS_FILTERS.map((item) => (
                                    <option key={item.value} value={item.value}>{item.label}</option>
                                ))}
                            </select>
                            <select
                                className="input text-sm"
                                value={queueFilter}
                                onChange={(event) => onQueueFilterChange(event.target.value)}
                            >
                                <option value="">全部队列</option>
                                {queues.map((queueName) => (
                                    <option key={queueName} value={queueName}>{queueName}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {isLoading ? (
                        <div className="flex justify-center p-12">
                            <Loader2 className="h-8 w-8 animate-spin text-ink-faint" />
                        </div>
                    ) : jobs.length === 0 ? (
                        <div className="p-12 text-center text-sm text-ink-muted">没有符合筛选条件的任务。</div>
                    ) : (
                        <div className="divide-y divide-line">
                            {jobs.map((job) => (
                                <button
                                    key={job.public_id}
                                    type="button"
                                    onClick={() => onSelectJob(job.public_id)}
                                    className="flex w-full flex-col gap-3 p-4 text-left transition-colors hover:bg-panel-subtle"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="min-w-0">
                                            <p className="truncate text-sm font-bold">{job.definition.display_name}</p>
                                            <p className="mt-1 truncate font-mono text-xs text-ink-muted">{job.public_id}</p>
                                        </div>
                                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${job.statusClassName}`}>
                                            {job.statusLabel}
                                        </span>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-3 text-xs text-ink-muted">
                                        <span>{job.queue_name}</span>
                                        <span>{job.attemptLabel}</span>
                                        <span>{job.createdLabel}</span>
                                        {job.error_message && (
                                            <span className="inline-flex items-center gap-1 text-loss">
                                                <AlertTriangle className="h-3.5 w-3.5" />
                                                {job.error_message}
                                            </span>
                                        )}
                                        {job.recoveryHint && (
                                            <span className="inline-flex items-center gap-1 text-warning">
                                                <ShieldAlert className="h-3.5 w-3.5" />
                                                {job.recoveryHint}
                                            </span>
                                        )}
                                        {job.recommendedActionLabel && (
                                            <span className="rounded-full bg-panel-subtle px-2 py-0.5 font-semibold text-ink-soft">
                                                建议：{job.recommendedActionLabel}
                                            </span>
                                        )}
                                    </div>
                                </button>
                            ))}
                        </div>
                    )}
                </div>

                <aside className="card min-h-[520px] overflow-hidden">
                    {!selectedJob ? (
                        <div className="flex h-full min-h-[420px] flex-col items-center justify-center p-8 text-center">
                            <ShieldAlert className="h-10 w-10 text-ink-faint" />
                            <h3 className="mt-4 font-bold">选择一个任务</h3>
                            <p className="mt-2 text-sm text-ink-muted">查看任务载荷、执行结果、错误和状态事件。</p>
                        </div>
                    ) : (
                        <div className="space-y-5 p-5">
                            <div className="flex items-start justify-between gap-3">
                                <div>
                                    <p className="font-mono text-xs text-ink-muted">{selectedJob.public_id}</p>
                                    <h3 className="mt-1 text-xl font-black">{selectedJob.definition.display_name}</h3>
                                </div>
                                {selectedTone && (
                                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${selectedTone.className}`}>
                                        {selectedTone.label}
                                    </span>
                                )}
                            </div>

                            {isDetailLoading && (
                                <div className="rounded-lg bg-panel-subtle p-4 text-sm text-ink-muted">
                                    <Loader2 className="mr-2 inline h-4 w-4 animate-spin" />
                                    正在加载详情...
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-3 text-sm">
                                <Metric label="队列" value={selectedJob.queue_name} />
                                <Metric label="尝试次数" value={`${selectedJob.attempt_count}/${selectedJob.max_attempts}`} />
                                <Metric label="锁定者" value={selectedJob.locked_by || '无'} />
                                <Metric label="下次运行" value={selectedJob.next_run_at ? new Date(selectedJob.next_run_at).toLocaleString('zh-CN') : '暂无'} />
                            </div>

                            {(selectedJob.stale_reason || selectedRecommendedActionLabel || selectedJob.force_cancel_warning) && (
                                <div className="rounded-lg border border-warning/30 bg-warning/12 p-4 text-sm text-warning">
                                    <div className="flex items-start gap-3">
                                        <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" />
                                        <div className="space-y-2">
                                            {selectedJob.stale_reason && (
                                                <p>
                                                    <span className="font-bold">超时原因：</span>
                                                    {selectedJob.stale_reason}
                                                </p>
                                            )}
                                            {selectedRecommendedActionLabel && (
                                                <p>
                                                    <span className="font-bold">建议操作：</span>
                                                    {selectedRecommendedActionLabel}
                                                </p>
                                            )}
                                            {selectedJob.force_cancel_warning && (
                                                <p>
                                                    <span className="font-bold">强制取消警告：</span>
                                                    {selectedJob.force_cancel_warning}
                                                </p>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            )}

                            <div>
                                <h4 className="mb-3 text-sm font-bold">业务锁</h4>
                                {selectedJob.business_locks.length === 0 ? (
                                    <p className="rounded-lg border border-dashed border-line p-3 text-sm text-ink-muted">
                                        该任务没有记录业务锁。
                                    </p>
                                ) : (
                                    <div className="space-y-2">
                                        {selectedJob.business_locks.map((businessLock) => (
                                            <div key={businessLock.public_id} className="rounded-lg border border-line p-3 text-sm">
                                                <div className="flex items-center justify-between gap-3">
                                                    <span className="font-semibold">{businessLock.scope}</span>
                                                    <span className="rounded-full bg-panel-subtle px-2 py-0.5 text-xs font-semibold text-ink-soft">
                                                        {businessLock.status}
                                                    </span>
                                                </div>
                                                <p className="mt-1 break-all font-mono text-xs text-ink-muted">{businessLock.resource_key}</p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="space-y-3">
                                {selectedJob.status === 'RUNNING' && (
                                    <div className="rounded-lg border border-loss/30 bg-loss/10 p-3 text-sm text-loss">
                                        <label className="block text-xs font-bold uppercase tracking-[0.18em] text-loss">
                                            输入 {FORCE_CANCEL_CONFIRMATION} 以解锁强制取消
                                        </label>
                                        <input
                                            className="input mt-2 border-loss/40 bg-panel text-sm"
                                            value={activeForceCancelConfirmation}
                                            onChange={(event) => setForceCancelConfirmation({
                                                jobPublicId: selectedJob.public_id,
                                                value: event.target.value,
                                            })}
                                            placeholder={FORCE_CANCEL_CONFIRMATION}
                                        />
                                        <p className="mt-2 text-xs">
                                            强制取消仅用于超时的执行器锁，它会释放活动业务锁并记录警告元数据。
                                        </p>
                                    </div>
                                )}
                                <div className="flex gap-2">
                                    <button
                                        type="button"
                                        disabled={isActionRunning || !(selectedJob.status === 'FAILED' || selectedJob.status === 'RETRYING')}
                                        onClick={() => onRequeueJob(selectedJob.public_id)}
                                        className="btn btn-secondary flex-1 disabled:opacity-50"
                                    >
                                        <PlayCircle className="mr-2 h-4 w-4" />
                                        重新入队
                                    </button>
                                    <button
                                        type="button"
                                        disabled={isActionRunning || !(selectedJob.status === 'QUEUED' || selectedJob.status === 'RETRYING')}
                                        onClick={() => onCancelJob(selectedJob.public_id)}
                                        className="btn btn-outline flex-1 disabled:opacity-50"
                                    >
                                        <Ban className="mr-2 h-4 w-4" />
                                        取消
                                    </button>
                                    <button
                                        type="button"
                                        disabled={isActionRunning || selectedJob.status !== 'RUNNING' || !isForceCancelConfirmed}
                                        onClick={() => {
                                            if (!isForceCancelConfirmed) return
                                            onForceCancelJob(selectedJob.public_id)
                                        }}
                                        className="btn btn-danger flex-1 disabled:opacity-50"
                                        title="强制取消仅适用于运行中的任务，并会释放该任务持有的活动业务锁。"
                                    >
                                        <ShieldAlert className="mr-2 h-4 w-4" />
                                        强制取消
                                    </button>
                                </div>
                            </div>

                            <JsonBlock title="任务载荷（payload）" value={selectedJob.payload} />
                            <JsonBlock title="执行结果（result）" value={selectedJob.result} />

                            <div>
                                <h4 className="mb-3 flex items-center gap-2 text-sm font-bold">
                                    <Clock3 className="h-4 w-4" />
                                    事件历史
                                </h4>
                                <div className="space-y-3">
                                    {selectedJob.events.map((event) => (
                                        <div key={event.public_id} className="rounded-lg border border-line p-3 text-sm">
                                            <div className="flex items-center justify-between gap-2">
                                                <span className="font-semibold">{event.event_type}</span>
                                                <span className="text-xs text-ink-muted">
                                                    {new Date(event.created_at).toLocaleString('zh-CN')}
                                                </span>
                                            </div>
                                            <p className="mt-1 text-xs text-ink-muted">
                                                {event.from_status || 'START'} → {event.to_status || 'LOG'}
                                            </p>
                                            {event.message && <p className="mt-2 text-sm">{event.message}</p>}
                                        </div>
                                    ))}
                                    {selectedJob.events.length === 0 && (
                                        <p className="text-sm text-ink-muted">暂无事件历史。</p>
                                    )}
                                </div>
                            </div>
                        </div>
                    )}
                </aside>
            </section>
        </div>
    )
}

function Metric({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-lg bg-panel-subtle p-3">
            <p className="text-xs text-ink-muted">{label}</p>
            <p className="mt-1 truncate text-sm font-semibold">{value}</p>
        </div>
    )
}

function JsonBlock({ title, value }: { title: string; value: Record<string, unknown> }) {
    return (
        <div>
            <h4 className="mb-2 flex items-center gap-2 text-sm font-bold">
                <CheckCircle2 className="h-4 w-4" />
                {title}
            </h4>
            <pre className="max-h-48 overflow-auto rounded-lg bg-ink p-4 text-xs text-profit">
                {JSON.stringify(value, null, 2)}
            </pre>
        </div>
    )
}
