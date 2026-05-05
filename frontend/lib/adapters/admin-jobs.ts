import type { AdminJobListResponse, AdminJobRunSummary, AdminJobStatus } from '../api.ts'

const STATUS_TONES: Record<AdminJobStatus, { label: string; className: string; accent: string }> = {
    QUEUED: {
        label: 'Queued',
        className: 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200',
        accent: 'bg-slate-400',
    },
    RUNNING: {
        label: 'Running',
        className: 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-200',
        accent: 'bg-blue-500',
    },
    SUCCEEDED: {
        label: 'Succeeded',
        className: 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-200',
        accent: 'bg-emerald-500',
    },
    FAILED: {
        label: 'Failed',
        className: 'bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-200',
        accent: 'bg-rose-500',
    },
    RETRYING: {
        label: 'Retrying',
        className: 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-200',
        accent: 'bg-amber-500',
    },
    CANCELLED: {
        label: 'Cancelled',
        className: 'bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-300',
        accent: 'bg-zinc-400',
    },
}

export interface AdminJobViewModel extends AdminJobRunSummary {
    statusLabel: string
    statusClassName: string
    statusAccentClassName: string
    attemptLabel: string
    createdLabel: string
    actionState: {
        canRequeue: boolean
        canCancel: boolean
    }
}

export function getAdminJobStatusTone(status: AdminJobStatus) {
    return STATUS_TONES[status]
}

export function getAdminJobActions(status: AdminJobStatus) {
    return {
        canRequeue: status === 'FAILED' || status === 'RETRYING',
        canCancel: status === 'QUEUED' || status === 'RETRYING',
    }
}

function formatDateTime(value: string | null): string {
    if (!value) return 'Not scheduled'
    return new Date(value).toLocaleString('zh-CN')
}

function adaptJob(item: AdminJobRunSummary): AdminJobViewModel {
    const tone = getAdminJobStatusTone(item.status)
    return {
        ...item,
        statusLabel: tone.label,
        statusClassName: tone.className,
        statusAccentClassName: tone.accent,
        attemptLabel: `${item.attempt_count}/${item.max_attempts} attempts`,
        createdLabel: formatDateTime(item.created_at),
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
