import type { AdminJobListResponse, AdminJobRecommendedAction, AdminJobRunSummary, AdminJobStatus } from '../api.ts'

const STATUS_TONES: Record<AdminJobStatus, { label: string; className: string; accent: string }> = {
    QUEUED: {
        label: '排队中',
        className: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
        accent: 'bg-slate-400',
    },
    RUNNING: {
        label: '运行中',
        className: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-200',
        accent: 'bg-blue-500',
    },
    SUCCEEDED: {
        label: '已成功',
        className: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200',
        accent: 'bg-emerald-500',
    },
    FAILED: {
        label: '已失败',
        className: 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-200',
        accent: 'bg-rose-500',
    },
    RETRYING: {
        label: '重试中',
        className: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-200',
        accent: 'bg-amber-500',
    },
    CANCELLED: {
        label: '已取消',
        className: 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300',
        accent: 'bg-zinc-400',
    },
}

const RECOMMENDED_ACTION_LABELS: Record<AdminJobRecommendedAction, string> = {
    REQUEUE: '重新入队',
    CANCEL: '取消',
    FORCE_CANCEL: '强制取消',
    WAIT: '等待',
}

export interface AdminJobViewModel extends AdminJobRunSummary {
    statusLabel: string
    statusClassName: string
    statusAccentClassName: string
    attemptLabel: string
    createdLabel: string
    recoveryHint: string | null
    recommendedActionLabel: string | null
    forceCancelWarning: string | null
    actionState: {
        canRequeue: boolean
        canCancel: boolean
        canForceCancel: boolean
    }
}

export function getAdminJobStatusTone(status: AdminJobStatus) {
    return STATUS_TONES[status]
}

export function getAdminJobActions(status: AdminJobStatus) {
    return {
        canRequeue: status === 'FAILED' || status === 'RETRYING',
        canCancel: status === 'QUEUED' || status === 'RETRYING',
        canForceCancel: status === 'RUNNING',
    }
}

function formatDateTime(value: string | null): string {
    if (!value) return '未调度'
    return new Date(value).toLocaleString('zh-CN')
}

export function formatAdminJobRecommendedAction(action: AdminJobRecommendedAction | null | undefined): string | null {
    return action ? RECOMMENDED_ACTION_LABELS[action] : null
}

function adaptJob(item: AdminJobRunSummary): AdminJobViewModel {
    const tone = getAdminJobStatusTone(item.status)
    return {
        ...item,
        statusLabel: tone.label,
        statusClassName: tone.className,
        statusAccentClassName: tone.accent,
        attemptLabel: `尝试 ${item.attempt_count}/${item.max_attempts} 次`,
        createdLabel: formatDateTime(item.created_at),
        recoveryHint: item.stale_reason ?? null,
        recommendedActionLabel: formatAdminJobRecommendedAction(item.recommended_action),
        forceCancelWarning: item.force_cancel_warning ?? null,
        actionState: getAdminJobActions(item.status),
    }
}

export function adaptAdminJobsPageData(response: AdminJobListResponse): {
    items: AdminJobViewModel[]
    total: number
    limit: number
    counts: Record<AdminJobStatus, number>
    latestFailures: AdminJobViewModel[]
    queues: string[]
} {
    const items = response.items.map(adaptJob)
    const counts: Record<AdminJobStatus, number> = {
        QUEUED: 0,
        RUNNING: 0,
        SUCCEEDED: 0,
        FAILED: 0,
        RETRYING: 0,
        CANCELLED: 0,
    }
    for (const item of items) {
        counts[item.status] += 1
    }

    return {
        items,
        total: response.total,
        limit: response.limit,
        counts,
        latestFailures: items.filter((item) => item.status === 'FAILED').slice(0, 3),
        queues: Array.from(new Set(items.map((item) => item.queue_name))).sort(),
    }
}
