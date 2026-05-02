import { Download, Loader2 } from 'lucide-react'

interface SettingsDataExportCardProps {
    isExporting: boolean
    onExport: () => Promise<void> | void
}

export function SettingsDataExportCard({ isExporting, onExport }: SettingsDataExportCardProps) {
    return (
        <div className="card p-6">
            <h2 className="text-lg font-semibold mb-4 flex items-center space-x-2">
                <Download className="w-5 h-5 text-blue-500" />
                <span>数据导出</span>
            </h2>
            <p className="text-sm text-slate-500 mb-4">
                导出您的所有交易记录为 CSV 文件，包含持仓信息、交易批次、盈亏数据等。
            </p>
            <button
                onClick={onExport}
                disabled={isExporting}
                className="btn btn-secondary flex items-center justify-center space-x-2"
            >
                {isExporting ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                    <Download className="w-5 h-5" />
                )}
                <span>{isExporting ? '导出中...' : '导出交易数据'}</span>
            </button>
        </div>
    )
}
