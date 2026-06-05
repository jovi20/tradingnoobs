'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Loader2, LockKeyhole } from 'lucide-react'

import { AdminJobsConsole } from '@/components/admin/domain/AdminJobsConsole'
import { useAuth } from '@/contexts/AuthContext'
import { adminAPI, type AdminJobRunDetail, type AdminJobStatus } from '@/lib/api'
import { adaptAdminJobsPageData, type AdminJobViewModel } from '@/lib/adapters/admin-jobs'

export default function AdminJobsPage() {
    const { token, user } = useAuth()
    const [jobs, setJobs] = useState<AdminJobViewModel[]>([])
    const [counts, setCounts] = useState<Record<AdminJobStatus, number>>({
        QUEUED: 0,
        RUNNING: 0,
        SUCCEEDED: 0,
        FAILED: 0,
        RETRYING: 0,
        CANCELLED: 0,
    })
    const [queues, setQueues] = useState<string[]>([])
    const [total, setTotal] = useState(0)
    const [statusFilter, setStatusFilter] = useState<AdminJobStatus | 'ALL'>('ALL')
    const [queueFilter, setQueueFilter] = useState('')
    const [selectedJob, setSelectedJob] = useState<AdminJobRunDetail | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isDetailLoading, setIsDetailLoading] = useState(false)
    const [isActionRunning, setIsActionRunning] = useState(false)
    const [error, setError] = useState('')

    const isAdmin = user?.role === 'admin'

    const loadJobs = async () => {
        if (!token || !isAdmin) return
        setError('')
        setIsLoading(true)
        try {
            const response = await adminAPI.listJobs(token, {
                status: statusFilter === 'ALL' ? undefined : statusFilter,
                queue_name: queueFilter || undefined,
                limit: 50,
            })
            const adapted = adaptAdminJobsPageData(response)
            setJobs(adapted.items)
            setCounts(adapted.counts)
            setQueues(adapted.queues)
            setTotal(adapted.total)
            if (selectedJob && !adapted.items.some((job) => job.public_id === selectedJob.public_id)) {
                setSelectedJob(null)
            }
        } catch (err: any) {
            setError(err.message || '加载任务失败')
        } finally {
            setIsLoading(false)
        }
    }

    const loadJobDetail = async (jobPublicId: string) => {
        if (!token) return
        setError('')
        setIsDetailLoading(true)
        try {
            const detail = await adminAPI.getJob(token, jobPublicId)
            setSelectedJob(detail)
        } catch (err: any) {
            setError(err.message || '加载任务详情失败')
        } finally {
            setIsDetailLoading(false)
        }
    }

    useEffect(() => {
        loadJobs()
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [token, isAdmin, statusFilter, queueFilter])

    const runAction = async (action: 'requeue' | 'cancel' | 'force-cancel', jobPublicId: string) => {
        if (!token) return
        setError('')
        setIsActionRunning(true)
        try {
            const detail = action === 'requeue'
                ? await adminAPI.requeueJob(token, jobPublicId)
                : action === 'force-cancel'
                    ? await adminAPI.forceCancelJob(token, jobPublicId)
                    : await adminAPI.cancelJob(token, jobPublicId)
            setSelectedJob(detail)
            await loadJobs()
        } catch (err: any) {
            setError(err.message || '任务操作失败')
        } finally {
            setIsActionRunning(false)
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
                    <p className="mt-2 text-sm text-slate-500">Job 控制台只开放给管理员账户。</p>
                    <Link href="/timeline" className="btn btn-primary mt-6 inline-flex">
                        返回时间线
                    </Link>
                </div>
            </div>
        )
    }

    return (
        <AdminJobsConsole
            jobs={jobs}
            counts={counts}
            queues={queues}
            total={total}
            statusFilter={statusFilter}
            queueFilter={queueFilter}
            selectedJob={selectedJob}
            isLoading={isLoading}
            isDetailLoading={isDetailLoading}
            isActionRunning={isActionRunning}
            error={error}
            onStatusFilterChange={setStatusFilter}
            onQueueFilterChange={setQueueFilter}
            onRefresh={loadJobs}
            onSelectJob={loadJobDetail}
            onRequeueJob={(jobPublicId) => runAction('requeue', jobPublicId)}
            onCancelJob={(jobPublicId) => runAction('cancel', jobPublicId)}
            onForceCancelJob={(jobPublicId) => runAction('force-cancel', jobPublicId)}
        />
    )
}
