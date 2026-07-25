'use client'

import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, AlertCircle, Loader2 } from 'lucide-react'

interface FileDropzoneProps {
    onFileSelect: (file: File) => void
    isUploading: boolean
    error?: string | null
}

export function FileDropzone({ onFileSelect, isUploading, error }: FileDropzoneProps) {
    const onDrop = useCallback((acceptedFiles: File[]) => {
        if (acceptedFiles?.length > 0) {
            onFileSelect(acceptedFiles[0])
        }
    }, [onFileSelect])

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: {
            'text/csv': ['.csv'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
        },
        maxFiles: 1,
        maxSize: 10 * 1024 * 1024,
        disabled: isUploading
    })

    return (
        <div className="w-full">
            <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-md p-10 text-center cursor-pointer transition-colors
                    ${isDragActive ? 'border-ink bg-panel-subtle' : 'border-line-strong hover:border-ink-muted'}
                    ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
                    ${error ? 'border-loss/40 bg-loss/10' : ''}
                `}
            >
                <input {...getInputProps({ 'aria-label': '选择要导入的交易文件' })} />

                <div className="flex flex-col items-center gap-4">
                    <div className="p-4 rounded-full bg-panel-subtle text-ink-soft">
                        {isUploading
                            ? <Loader2 className="w-8 h-8 animate-spin" />
                            : <UploadCloud className="w-8 h-8" />}
                    </div>

                    <div>
                        <p className="text-lg font-medium text-ink-soft">
                            {isDragActive ? '松开即可上传文件' : '点击或拖拽文件上传'}
                        </p>
                        <p className="text-sm text-ink-muted mt-1">
                            CSV 或 XLSX，最大 10 MB
                        </p>
                    </div>
                </div>
            </div>

            {error && (
                <div className="flex items-center gap-2 mt-3 text-sm text-loss">
                    <AlertCircle className="w-4 h-4" />
                    <span>{error}</span>
                </div>
            )}
        </div>
    )
}
