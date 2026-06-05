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
import { getAdminJobStatusTone } from '@/lib/adapters/admin-jobs'

const STATUS_FILTERS: Array<{ value: AdminJobStatus | 'ALL'; label: string }> = [
    { value: 'ALL', label: 'All' },
    { value: 'QUEUED', label: 'Queued' },
    { value: 'RUNNING', label: 'Running' },
    { value: 'FAILED', label: 'Failed' },
    { value: 'RETRYING', label: 'Retrying' },
    { value: 'SUCCEEDED', label: 'Succeeded' },
    { value: 'CANCELLED', label: 'Cancelled' },
]

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

    return (
        <div className="space-y-6 pb-20 md:pb-8">
            <section className="relative overflow-hidden rounded-[2rem] border border-slate-200 bg-slate-950 p-6 text-white shadow-xl dark:border-slate-800">
                <div className="absolute -right-24 -top-24 h-64 w-64 rounded-full bg-emerald-400/20 blur-3xl" />
                <div className="absolute -bottom-28 left-16 h-56 w-56 rounded-full bg-blue-500/20 blur-3xl" />
                <div className="relative flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
                    <div>
                        <div className="mb-4 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/10 px-3 py-1 text-xs text-slate-200">
                            <Zap className="h-3.5 w-3.5 text-emerald-300" />
                            Async control room
                        </div>
                        <h1 className="text-3xl font-black tracking-tight md:text-4xl">后台任务控制台</h1>
                        <p className="mt-3 max-w-2xl text-sm leading-6 text-slate-300">
                            查看 outbox 派生出的 job，追踪 worker 状态、失败原因与事件历史。这里先做安全操作：
                            失败任务可重新入队，未执行任务可取消，运行中任务等待后续 heartbeat/interrupt 机制。
                        </p>
                    </div>
                    <button
                        type="button"
                        onClick={onRefresh}
                        className="btn bg-white text-slate-950 hover:bg-slate-100"
                    >
                        {isLoading ? <Loader2 className="mr-2 h-4 w-4 animate-spin" /> : <RotateCcw className="mr-2 h-4 w-4" />}
                        刷新任务
                    </button>
                </div>
            </section>

            {error && (
                <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-sm text-rose-700 dark:border-rose-900/40 dark:bg-rose-950/30 dark:text-rose-200">
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
                            className={`card p-4 text-left transition hover:-translate-y-0.5 ${
                                statusFilter === item.value ? 'ring-2 ring-slate-900 dark:ring-white' : ''
                            }`}
                        >
                            <div className={`mb-3 h-2 w-10 rounded-full ${tone.accent}`} />
                            <p className="text-xs text-slate-500">{tone.label}</p>
                            <p className="mt-1 text-2xl font-black">{counts[item.value as AdminJobStatus]}</p>
                        </button>
                    )
                })}
            </section>

            <section className="grid gap-6 lg:grid-cols-[minmax(0,1.15fr)_minmax(360px,0.85fr)]">
                <div className="card overflow-hidden">
                    <div className="flex flex-col gap-3 border-b border-slate-100 p-4 dark:border-slate-800 md:flex-row md:items-center md:justify-between">
                        <div>
                            <h2 className="flex items-center gap-2 text-lg font-bold">
                                <ListFilter className="h-5 w-5" />
                                Job runs
                            </h2>
                            <p className="text-xs text-slate-500">Showing {jobs.length} of {total}</p>
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
                                <option value="">All queues</option>
                                {queues.map((queueName) => (
                                    <option key={queueName} value={queueName}>{queueName}</option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {isLoading ? (
                        <div className="flex justify-center p-12">
                            <Loader2 className="h-8 w-8 animate-spin text-slate-400" />
                        </div>
                    ) : jobs.length === 0 ? (
                        <div className="p-12 text-center text-sm text-slate-500">没有符合筛选条件的任务。</div>
                    ) : (
                        <div className="divide-y divide-slate-100 dark:divide-slate-800">
                            {jobs.map((job) => (
                                <button
                                    key={job.public_id}
                                    type="button"
                                    onClick={() => onSelectJob(job.public_id)}
                                    className="flex w-full flex-col gap-3 p-4 text-left transition hover:bg-slate-50 dark:hover:bg-slate-800/60"
                                >
                                    <div className="flex items-start justify-between gap-3">
                                        <div className="min-w-0">
                                            <p className="truncate text-sm font-bold">{job.definition.display_name}</p>
                                            <p className="mt-1 truncate font-mono text-xs text-slate-500">{job.public_id}</p>
                                        </div>
                                        <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${job.statusClassName}`}>
                                            {job.statusLabel}
                                        </span>
                                    </div>
                                    <div className="flex flex-wrap items-center gap-3 text-xs text-slate-500">
                                        <span>{job.queue_name}</span>
                                        <span>{job.attemptLabel}</span>
                                        <span>{job.createdLabel}</span>
                                        {job.error_message && (
                                            <span className="inline-flex items-center gap-1 text-rose-600">
                                                <AlertTriangle className="h-3.5 w-3.5" />
                                                {job.error_message}
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
                            <ShieldAlert className="h-10 w-10 text-slate-300" />
                            <h3 className="mt-4 font-bold">选择一个任务</h3>
                            <p className="mt-2 text-sm text-slate-500">查看 payload、result、错误和状态事件。</p>
                        </div>
                    ) : (
                        <div className="space-y-5 p-5">
                            <div className="flex items-start justify-between gap-3">
                                <div>
                                    <p className="font-mono text-xs text-slate-500">{selectedJob.public_id}</p>
                                    <h3 className="mt-1 text-xl font-black">{selectedJob.definition.display_name}</h3>
                                </div>
                                {selectedTone && (
                                    <span className={`rounded-full px-2.5 py-1 text-xs font-semibold ${selectedTone.className}`}>
                                        {selectedTone.label}
                                    </span>
                                )}
                            </div>

                            {isDetailLoading && (
                                <div className="rounded-2xl bg-slate-50 p-4 text-sm text-slate-500 dark:bg-slate-800">
                                    <Loader2 className="mr-2 inline h-4 w-4 animate-spin" />
                                    正在加载详情...
                                </div>
                            )}

                            <div className="grid grid-cols-2 gap-3 text-sm">
                                <Metric label="Queue" value={selectedJob.queue_name} />
                                <Metric label="Attempts" value={`${selectedJob.attempt_count}/${selectedJob.max_attempts}`} />
                                <Metric label="Locked by" value={selectedJob.locked_by || 'None'} />
                                <Metric label="Next run" value={selectedJob.next_run_at ? new Date(selectedJob.next_run_at).toLocaleString('zh-CN') : 'None'} />
                            </div>

                            <div>
                                <h4 className="mb-3 text-sm font-bold">Business locks</h4>
                                {selectedJob.business_locks.length === 0 ? (
                                    <p className="rounded-2xl border border-dashed border-slate-200 p-3 text-sm text-slate-500 dark:border-slate-800">
                                        No business locks recorded for this job.
                                    </p>
                                ) : (
                                    <div className="space-y-2">
                                        {selectedJob.business_locks.map((businessLock) => (
                                            <div key={businessLock.public_id} className="rounded-2xl border border-slate-100 p-3 text-sm dark:border-slate-800">
                                                <div className="flex items-center justify-between gap-3">
                                                    <span className="font-semibold">{businessLock.scope}</span>
                                                    <span className="rounded-full bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-300">
                                                        {businessLock.status}
                                                    </span>
                                                </div>
                                                <p className="mt-1 break-all font-mono text-xs text-slate-500">{businessLock.resource_key}</p>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>

                            <div className="flex gap-2">
                                <button
                                    type="button"
                                    disabled={isActionRunning || !(selectedJob.status === 'FAILED' || selectedJob.status === 'RETRYING')}
                                    onClick={() => onRequeueJob(selectedJob.public_id)}
                                    className="btn btn-secondary flex-1 disabled:opacity-50"
                                >
                                    <PlayCircle className="mr-2 h-4 w-4" />
                                    Requeue
                                </button>
                                <button
                                    type="button"
                                    disabled={isActionRunning || !(selectedJob.status === 'QUEUED' || selectedJob.status === 'RETRYING')}
                                    onClick={() => onCancelJob(selectedJob.public_id)}
                                    className="btn btn-outline flex-1 disabled:opacity-50"
                                >
                                    <Ban className="mr-2 h-4 w-4" />
                                    Cancel
                                </button>
                                <button
                                    type="button"
                                    disabled={isActionRunning || selectedJob.status !== 'RUNNING'}
                                    onClick={() => onForceCancelJob(selectedJob.public_id)}
                                    className="btn btn-danger flex-1 disabled:opacity-50"
                                    title="Force-cancel only applies to RUNNING jobs and releases active business locks owned by this job."
                                >
                                    <ShieldAlert className="mr-2 h-4 w-4" />
                                    Force
                                </button>
                            </div>

                            <JsonBlock title="Payload" value={selectedJob.payload} />
                            <JsonBlock title="Result" value={selectedJob.result} />

                            <div>
                                <h4 className="mb-3 flex items-center gap-2 text-sm font-bold">
                                    <Clock3 className="h-4 w-4" />
                                    Event history
                                </h4>
                                <div className="space-y-3">
                                    {selectedJob.events.map((event) => (
                                        <div key={event.public_id} className="rounded-2xl border border-slate-100 p-3 text-sm dark:border-slate-800">
                                            <div className="flex items-center justify-between gap-2">
                                                <span className="font-semibold">{event.event_type}</span>
                                                <span className="text-xs text-slate-500">
                                                    {new Date(event.created_at).toLocaleString('zh-CN')}
                                                </span>
                                            </div>
                                            <p className="mt-1 text-xs text-slate-500">
                                                {event.from_status || 'START'} → {event.to_status || 'LOG'}
                                            </p>
                                            {event.message && <p className="mt-2 text-sm">{event.message}</p>}
                                        </div>
                                    ))}
                                    {selectedJob.events.length === 0 && (
                                        <p className="text-sm text-slate-500">暂无事件历史。</p>
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
        <div className="rounded-2xl bg-slate-50 p-3 dark:bg-slate-800">
            <p className="text-xs text-slate-500">{label}</p>
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
            <pre className="max-h-48 overflow-auto rounded-2xl bg-slate-950 p-4 text-xs text-emerald-100">
                {JSON.stringify(value, null, 2)}
            </pre>
        </div>
    )
}
