'use client'

import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { UploadCloud, AlertCircle } from 'lucide-react'

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
            'application/vnd.ms-excel': ['.xls'],
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx']
        },
        maxFiles: 1,
        disabled: isUploading
    })

    return (
        <div className="w-full">
            <div
                {...getRootProps()}
                className={`border-2 border-dashed rounded-xl p-10 text-center cursor-pointer transition-all
                    ${isDragActive ? 'border-primary-500 bg-primary-50 dark:bg-primary-900/10' : 'border-slate-300 dark:border-slate-700 hover:border-primary-400 dark:hover:border-primary-600'}
                    ${isUploading ? 'opacity-50 cursor-not-allowed' : ''}
                    ${error ? 'border-red-300 bg-red-50 dark:bg-red-900/10' : ''}
                `}
            >
                <input {...getInputProps()} />

                <div className="flex flex-col items-center gap-4">
                    <div className="p-4 rounded-full bg-slate-100 dark:bg-slate-800 text-primary-600 dark:text-primary-400">
                        <UploadCloud className="w-8 h-8" />
                    </div>

                    <div>
                        <p className="text-lg font-medium text-slate-700 dark:text-slate-300">
                            {isDragActive ? 'Drop the file here' : '点击或拖拽文件上传'}
                        </p>
                        <p className="text-sm text-slate-500 mt-1">
                            支持 CSV, Excel (.xlsx, .xls)
                        </p>
                    </div>
                </div>
            </div>

            {error && (
                <div className="flex items-center gap-2 mt-3 text-sm text-red-600 dark:text-red-400">
                    <AlertCircle className="w-4 h-4" />
                    <span>{error}</span>
                </div>
            )}
        </div>
    )
}
