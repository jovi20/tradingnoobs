'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { ArrowLeft, Upload, FileText, Check, AlertCircle, Loader2, Download } from 'lucide-react'
import { FileDropzone } from '@/components/import/FileDropzone'
import { ImportPreviewTable } from '@/components/import/ImportPreviewTable'
import { positionsAPI, accountsAPI, TradingAccount } from '@/lib/api'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '@/contexts/AuthContext'
import CustomSelect from '@/components/CustomSelect'

export default function ImportPage() {
    const router = useRouter()
    const { token } = useAuth()

    // Steps: 0 = Upload, 1 = Preview, 2 = Success
    const [step, setStep] = useState(0)

    // State
    const [file, setFile] = useState<File | null>(null)
    const [accountId, setAccountId] = useState<number | null>(null)
    const [isUploading, setIsUploading] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Preview Data
    const [previewData, setPreviewData] = useState<any>(null)
    const [selectedIndices, setSelectedIndices] = useState<number[]>([])
    const [fileToken, setFileToken] = useState<string>('')

    // Accounts Query
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

            // Auto-select valid rows
            const validIndices = data.preview_rows
                .filter((r: any) => r.is_valid)
                .map((r: any) => r.index)
            setSelectedIndices(validIndices)

            setStep(1)
        } catch (err: any) {
            setError(err.message || 'Upload failed')
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
            setError(err.message || 'Import failed')
        } finally {
            setIsUploading(false)
        }
    }

    const handleDownloadTemplate = async () => {
        if (!token) return;
        try {
            // We trigger download by opening the URL directly or fetching blob
            // Direct URL is simpler if auth works (cookie?) 
            // But we use header auth, so we need fetch blob
            const blob = await positionsAPI.getImportTemplate(token);
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = "trade_import_template.csv";
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            a.remove();
        } catch (e) {
            console.error("Download failed", e);
            setError("Failed to download template");
        }
    }

    return (
        <div className="max-w-4xl mx-auto space-y-8 pb-20">
            {/* Header */}
            <div className="flex items-center gap-4">
                <Link href="/positions" className="p-2 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg transition-colors">
                    <ArrowLeft className="w-5 h-5 text-slate-500" />
                </Link>
                <div>
                    <h1 className="text-2xl font-bold">批量导入交易</h1>
                    <p className="text-slate-500 text-sm">通过 CSV 或 Excel 上传历史交易记录</p>
                </div>
            </div>

            {/* Stepper */}
            <div className="flex items-center justify-between relative px-10">
                <div className="absolute left-0 top-1/2 w-full h-0.5 bg-slate-200 dark:bg-slate-700 -z-10" />

                {[
                    { id: 0, label: '上传文件', icon: Upload },
                    { id: 1, label: '预览数据', icon: FileText },
                    { id: 2, label: '完成', icon: Check }
                ].map((s) => (
                    <div key={s.id} className="flex flex-col items-center gap-2 bg-white dark:bg-slate-900 px-2">
                        <div className={`
                            w-10 h-10 rounded-full flex items-center justify-center border-2 transition-all
                            ${step >= s.id
                                ? 'bg-primary-600 border-primary-600 text-white'
                                : 'bg-white dark:bg-slate-800 border-slate-300 dark:border-slate-600 text-slate-400'}
                        `}>
                            <s.icon className="w-5 h-5" />
                        </div>
                        <span className={`text-xs font-medium ${step >= s.id ? 'text-primary-600' : 'text-slate-500'}`}>
                            {s.label}
                        </span>
                    </div>
                ))}
            </div>

            <div className="card p-6 md:p-8">
                {/* Step 0: Upload */}
                {step === 0 && (
                    <div className="space-y-8 max-w-xl mx-auto">
                        <div className="space-y-2">
                            <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                                1. 选择目标账户
                            </label>
                            <CustomSelect
                                value={accountId || ''}
                                onChange={setAccountId}
                                options={accounts.map(a => ({ value: a.id, label: a.name }))}
                                placeholder="请选择账户..."
                                className="w-full"
                            />
                        </div>

                        <div className="space-y-2">
                            <div className="flex justify-between items-center">
                                <label className="text-sm font-medium text-slate-700 dark:text-slate-300">
                                    2. 上传文件
                                </label>
                                <button
                                    onClick={handleDownloadTemplate}
                                    className="text-xs text-primary-600 hover:underline flex items-center gap-1"
                                >
                                    <Download className="w-3 h-3" /> 下载模板
                                </button>
                            </div>
                            <FileDropzone
                                onFileSelect={handleFileUpload}
                                isUploading={isUploading}
                                error={error}
                            />
                        </div>
                    </div>
                )}

                {/* Step 1: Preview */}
                {step === 1 && previewData && (
                    <div className="space-y-6">
                        <div className="flex items-center justify-between">
                            <div className="flex gap-4">
                                <div className="text-sm">
                                    <span className="text-slate-500">总行数:</span>
                                    <span className="font-medium ml-1">{previewData.total_rows}</span>
                                </div>
                                <div className="text-sm">
                                    <span className="text-slate-500">有效:</span>
                                    <span className="font-medium text-emerald-600 ml-1">{previewData.valid_rows}</span>
                                </div>
                                <div className="text-sm">
                                    <span className="text-slate-500">错误:</span>
                                    <span className="font-medium text-red-600 ml-1">{previewData.error_rows}</span>
                                </div>
                            </div>
                            <div className="flex gap-3">
                                <button
                                    onClick={() => setStep(0)}
                                    className="btn btn-secondary"
                                >
                                    重新上传
                                </button>
                                <button
                                    onClick={handleConfirmImport}
                                    disabled={selectedIndices.length === 0 || isUploading}
                                    className="btn btn-primary min-w-[120px]"
                                >
                                    {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : `确认导入 (${selectedIndices.length})`}
                                </button>
                            </div>
                        </div>

                        {error && (
                            <div className="p-3 bg-red-50 text-red-600 rounded-lg text-sm flex items-center gap-2">
                                <AlertCircle className="w-4 h-4" />
                                {error}
                            </div>
                        )}

                        <ImportPreviewTable
                            rows={previewData.preview_rows}
                            selectedIndices={selectedIndices}
                            onToggleSelection={setSelectedIndices}
                        />
                    </div>
                )}

                {/* Step 2: Success */}
                {step === 2 && (
                    <div className="text-center py-10 space-y-6">
                        <div className="w-16 h-16 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
                            <Check className="w-8 h-8" />
                        </div>
                        <div>
                            <h3 className="text-xl font-bold text-slate-900 dark:text-white">导入成功</h3>
                            <p className="text-slate-500 mt-2">
                                成功导入 {selectedIndices.length} 条交易记录
                            </p>
                        </div>
                        <div className="flex justify-center gap-4">
                            <button
                                onClick={() => {
                                    setStep(0)
                                    setFile(null)
                                    setPreviewData(null)
                                }}
                                className="btn btn-secondary"
                            >
                                继续导入
                            </button>
                            <Link href="/positions" className="btn btn-primary">
                                查看交易记录
                            </Link>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}
