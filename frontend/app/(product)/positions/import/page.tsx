'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
    ArrowLeft,
    Download,
    FileCheck2,
    Loader2,
    RefreshCw,
} from 'lucide-react'
import { useAuth } from '@/contexts/AuthContext'
import {
    accountsAPI,
    ImportSession,
    positionsAPI,
    TradingAccount,
} from '@/lib/api'
import { FileDropzone } from '@/components/import/FileDropzone'
import { ImportPreviewTable } from '@/components/import/ImportPreviewTable'

interface PendingUpload {
    file: File
    idempotencyKey: string
}

export default function PositionImportPage() {
    const { token } = useAuth()
    const [accounts, setAccounts] = useState<TradingAccount[]>([])
    const [accountId, setAccountId] = useState('')
    const [session, setSession] = useState<ImportSession | null>(null)
    const [pendingUpload, setPendingUpload] = useState<PendingUpload | null>(null)
    const [isLoadingAccounts, setIsLoadingAccounts] = useState(true)
    const [isUploading, setIsUploading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    useEffect(() => {
        if (!token) return
        let active = true
        accountsAPI.list(token)
            .then(items => {
                if (!active) return
                const writable = items.filter(account => account.is_active)
                setAccounts(writable)
                setAccountId(current => current || writable[0]?.public_id || '')
            })
            .catch(caught => {
                if (active) setError(caught instanceof Error ? caught.message : '账户加载失败')
            })
            .finally(() => {
                if (active) setIsLoadingAccounts(false)
            })
        return () => {
            active = false
        }
    }, [token])

    const runUpload = async (upload: PendingUpload) => {
        if (!token || !accountId) {
            setError('请选择账户')
            return
        }
        setIsUploading(true)
        setError(null)
        try {
            const result = await positionsAPI.uploadImportPreview(
                token,
                accountId,
                upload.file,
                upload.idempotencyKey,
            )
            setSession(result)
            if (result.status === 'FAILED') {
                setError(result.error?.message || '文件解析失败')
            } else if (result.error_rows > 0) {
                setError(`${result.error_rows} 行需要修正`)
            }
        } catch (caught) {
            setError(caught instanceof Error ? caught.message : '上传失败')
        } finally {
            setIsUploading(false)
        }
    }

    const handleFileSelect = (file: File) => {
        const upload = {
            file,
            idempotencyKey: crypto.randomUUID(),
        }
        setPendingUpload(upload)
        void runUpload(upload)
    }

    const handleDownloadTemplate = async () => {
        if (!token) return
        setError(null)
        try {
            const blob = await positionsAPI.downloadImportTemplate(token)
            const url = URL.createObjectURL(blob)
            const anchor = document.createElement('a')
            anchor.href = url
            anchor.download = 'trading-journal-import-template.csv'
            anchor.click()
            URL.revokeObjectURL(url)
        } catch (caught) {
            setError(caught instanceof Error ? caught.message : '模板下载失败')
        }
    }

    if (isLoadingAccounts) {
        return (
            <div className="flex items-center justify-center py-20">
                <Loader2 className="w-7 h-7 animate-spin text-ink-muted" />
            </div>
        )
    }

    return (
        <div className="space-y-6 pb-20 md:pb-8">
            <div className="flex flex-wrap items-center justify-between gap-3 border-b border-line pb-4">
                <div className="flex items-center gap-3">
                    <Link
                        href="/positions"
                        className="btn btn-ghost p-2"
                        title="返回交易记录"
                        aria-label="返回交易记录"
                    >
                        <ArrowLeft className="w-4 h-4" />
                    </Link>
                    <div>
                        <h1 className="text-xl font-semibold">导入交易预览</h1>
                        <p className="text-sm text-ink-muted">通用文件导入</p>
                    </div>
                </div>
                <button
                    type="button"
                    onClick={() => void handleDownloadTemplate()}
                    className="btn btn-secondary flex items-center gap-2"
                >
                    <Download className="w-4 h-4" />
                    下载模板
                </button>
            </div>

            <div className="max-w-xl space-y-2">
                <label htmlFor="import-account" className="text-sm font-medium">
                    目标账户
                </label>
                <select
                    id="import-account"
                    value={accountId}
                    onChange={event => {
                        setAccountId(event.target.value)
                        setSession(null)
                        setPendingUpload(null)
                    }}
                    className="input w-full"
                    disabled={isUploading}
                >
                    {accounts.map(account => (
                        <option key={account.public_id} value={account.public_id}>
                            {account.name} · {account.currency}
                        </option>
                    ))}
                </select>
            </div>

            {accounts.length === 0 ? (
                <div className="border-y border-line py-12 text-center">
                    <p className="text-ink-soft">没有可写账户</p>
                    <Link href="/settings" className="btn btn-secondary mt-4">
                        管理账户
                    </Link>
                </div>
            ) : (
                <FileDropzone
                    onFileSelect={handleFileSelect}
                    isUploading={isUploading}
                    error={error}
                />
            )}

            {error && pendingUpload && !isUploading && !session && (
                <button
                    type="button"
                    className="btn btn-secondary flex items-center gap-2"
                    onClick={() => void runUpload(pendingUpload)}
                >
                    <RefreshCw className="w-4 h-4" />
                    重试
                </button>
            )}

            {session && (
                <section className="space-y-4" aria-labelledby="preview-heading">
                    <div className="flex flex-wrap items-center justify-between gap-3 border-y border-line py-4">
                        <div className="flex items-center gap-2">
                            <FileCheck2 className="w-5 h-5 text-ink-soft" />
                            <div>
                                <h2 id="preview-heading" className="text-base font-semibold">
                                    预览结果
                                </h2>
                                <p className="text-xs text-ink-muted">
                                    过期时间 {new Date(session.expires_at).toLocaleString()}
                                </p>
                            </div>
                        </div>
                        <dl className="flex gap-5 text-sm">
                            <div>
                                <dt className="text-xs text-ink-muted">总行数</dt>
                                <dd className="font-mono tn-nums">{session.total_rows}</dd>
                            </div>
                            <div>
                                <dt className="text-xs text-ink-muted">有效</dt>
                                <dd className="font-mono text-profit tn-nums">{session.valid_rows}</dd>
                            </div>
                            <div>
                                <dt className="text-xs text-ink-muted">错误</dt>
                                <dd className="font-mono text-loss tn-nums">{session.error_rows}</dd>
                            </div>
                            <div>
                                <dt className="text-xs text-ink-muted">警告</dt>
                                <dd className="font-mono text-warning tn-nums">{session.warning_rows}</dd>
                            </div>
                        </dl>
                    </div>
                    {session.rows.length > 0 ? (
                        <ImportPreviewTable rows={session.rows} />
                    ) : (
                        <div className="border-y border-line py-10 text-center text-ink-muted">
                            文件中没有交易行
                        </div>
                    )}
                </section>
            )}
        </div>
    )
}
