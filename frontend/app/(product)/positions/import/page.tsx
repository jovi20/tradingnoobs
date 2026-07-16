'use client'

import { useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Upload, FileText, Check, AlertCircle, Download } from 'lucide-react'
import { FileDropzone } from '@/components/import/FileDropzone'
import { ImportPreviewTable } from '@/components/import/ImportPreviewTable'
import { positionsAPI, accountsAPI } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import CustomSelect from '@/components/CustomSelect'

import { PageFrame } from '@/components/ui/PageFrame'
import { Button } from '@/components/ui/Button'
import { Callout } from '@/components/ui/Callout'
import { cn } from '@/lib/cn'

export default function ImportPage() {
    const { token } = useAuth()

    // Steps: 0 = Upload, 1 = Preview, 2 = Success
    const [step, setStep] = useState(0)

    const [file, setFile] = useState<File | null>(null)
    const [accountId, setAccountId] = useState<number | null>(null)
    const [isUploading, setIsUploading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [previewData, setPreviewData] = useState<any>(null)
    const [selectedIndices, setSelectedIndices] = useState<number[]>([])
    const [fileToken, setFileToken] = useState<string>('')

    const { data: accounts = [] } = useQuery({
        queryKey: ['accounts', token],
        queryFn: () => accountsAPI.list(token!),
        enabled: !!token
    })

    const handleFileUpload = async (uploadedFile: File) => {
        if (!token) return
        setFile(uploadedFile)
        setIsUploading(true)
        setError(null)
        try {
            const data = await positionsAPI.importUpload(token, uploadedFile)
            setPreviewData(data)
            setFileToken(data.file_token)
            const validIndices = data.preview_rows.filter((r: any) => r.is_valid).map((r: any) => r.index)
            setSelectedIndices(validIndices)
            setStep(1)
        } catch (err: any) {
            setError(err.message || '文件上传失败')
        } finally {
            setIsUploading(false)
        }
    }

    const handleConfirmImport = async () => {
        if (!token || !fileToken || !accountId) return
        setIsUploading(true)
        try {
            await positionsAPI.importConfirm(token, {
                file_token: fileToken,
                account_id: accountId,
                selected_indices: selectedIndices
            })
            setStep(2)
        } catch (err: any) {
            setError(err.message || '导入失败')
        } finally {
            setIsUploading(false)
        }
    }

    const handleDownloadTemplate = async () => {
        if (!token) return
        try {
            const blob = await positionsAPI.getImportTemplate(token)
            const url = window.URL.createObjectURL(blob)
            const a = document.createElement('a')
            a.href = url
            a.download = 'trade_import_template.csv'
            document.body.appendChild(a)
            a.click()
            window.URL.revokeObjectURL(url)
            a.remove()
        } catch (e) {
            console.error('模板下载失败', e)
            setError('模板下载失败，请稍后重试')
        }
    }

    const steps = [
        { id: 0, label: '上传文件', icon: Upload },
        { id: 1, label: '预览数据', icon: FileText },
        { id: 2, label: '完成', icon: Check },
    ]

    return (
        <PageFrame density="normal">
            <div className="flex items-center gap-3">
                <Link href="/positions" aria-label="返回交易记录" className="rounded-md p-2 text-ink-muted transition-colors hover:bg-panel-subtle hover:text-ink">
                    <ArrowLeft className="h-5 w-5" />
                </Link>
                <div>
                    <h1 className="text-2xl font-semibold tracking-tight text-ink">批量导入交易</h1>
                    <p className="text-sm text-ink-muted">通过 CSV 或 Excel 文件导入历史交易记录</p>
                </div>
            </div>

            {/* Stepper */}
            <div className="relative flex items-center justify-between px-8">
                <div className="absolute left-0 top-5 -z-10 h-px w-full bg-line" />
                {steps.map((s) => (
                    <div key={s.id} className="flex flex-col items-center gap-2 bg-canvas px-2">
                        <div className={cn(
                            'flex h-10 w-10 items-center justify-center rounded-full border-2 transition-colors',
                            step >= s.id ? 'border-ink bg-ink text-canvas' : 'border-line-strong bg-panel text-ink-faint',
                        )}>
                            <s.icon className="h-5 w-5" />
                        </div>
                        <span className={cn('text-xs font-medium', step >= s.id ? 'text-ink' : 'text-ink-muted')}>
                            {s.label}
                        </span>
                    </div>
                ))}
            </div>

            <div className="rounded-lg border border-line bg-panel p-6 shadow-panel dark:shadow-none md:p-8">
                {step === 0 && (
                    <div className="mx-auto max-w-xl space-y-8">
                        <div className="space-y-2">
                            <label className="text-sm font-semibold text-ink-soft">1. 选择目标账户</label>
                            <CustomSelect
                                value={accountId || ''}
                                onChange={setAccountId}
                                options={accounts.map(a => ({ value: a.id, label: a.name }))}
                                placeholder="请选择账户…"
                                className="w-full"
                            />
                        </div>

                        <div className="space-y-2">
                            <div className="flex items-center justify-between">
                                <label className="text-sm font-semibold text-ink-soft">2. 上传文件</label>
                                <button type="button" onClick={handleDownloadTemplate} className="flex items-center gap-1 text-xs text-ai transition-opacity hover:opacity-80">
                                    <Download className="h-3 w-3" /> 下载模板
                                </button>
                            </div>
                            <FileDropzone onFileSelect={handleFileUpload} isUploading={isUploading} error={error} />
                        </div>
                    </div>
                )}

                {step === 1 && previewData && (
                    <div className="space-y-6">
                        <div className="flex flex-wrap items-center justify-between gap-3">
                            <div className="flex gap-4 text-sm">
                                <span className="text-ink-muted">总行数：<span className="font-medium text-ink tn-nums">{previewData.total_rows}</span></span>
                                <span className="text-ink-muted">有效：<span className="font-medium text-profit tn-nums">{previewData.valid_rows}</span></span>
                                <span className="text-ink-muted">错误：<span className="font-medium text-loss tn-nums">{previewData.error_rows}</span></span>
                            </div>
                            <div className="flex gap-3">
                                <Button variant="secondary" onClick={() => setStep(0)}>重新上传</Button>
                                <Button onClick={handleConfirmImport} loading={isUploading} disabled={selectedIndices.length === 0} className="min-w-[120px]">
                                    确认导入 ({selectedIndices.length})
                                </Button>
                            </div>
                        </div>

                        {error && (
                            <Callout kind="error" icon={<AlertCircle className="h-4 w-4" />}>{error}</Callout>
                        )}

                        <ImportPreviewTable
                            rows={previewData.preview_rows}
                            selectedIndices={selectedIndices}
                            onToggleSelection={setSelectedIndices}
                        />
                    </div>
                )}

                {step === 2 && (
                    <div className="space-y-6 py-10 text-center">
                        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-profit/10 text-profit">
                            <Check className="h-8 w-8" />
                        </div>
                        <div>
                            <h3 className="text-xl font-semibold text-ink">导入成功</h3>
                            <p className="mt-2 text-ink-muted">成功导入 {selectedIndices.length} 条交易记录</p>
                        </div>
                        <div className="flex justify-center gap-4">
                            <Button variant="secondary" onClick={() => { setStep(0); setFile(null); setPreviewData(null) }}>继续导入</Button>
                            <Link href="/positions" className="inline-flex h-10 items-center justify-center rounded-md bg-ink px-4 text-sm font-medium text-canvas transition-colors hover:bg-ink-soft">
                                查看交易记录
                            </Link>
                        </div>
                    </div>
                )}
            </div>
        </PageFrame>
    )
}
