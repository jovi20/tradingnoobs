'use client'

import { AlertTriangle, CheckCircle, XCircle } from 'lucide-react'

interface ImportPreviewRow {
    index: number
    data: Record<string, any>
    is_valid: boolean
    errors: string[]
    parsed?: any
}

interface ImportPreviewTableProps {
    rows: ImportPreviewRow[]
    selectedIndices: number[]
    onToggleSelection: (indices: number[]) => void
}

export function ImportPreviewTable({ rows, selectedIndices, onToggleSelection }: ImportPreviewTableProps) {
    const allValidIndices = rows.filter(r => r.is_valid).map(r => r.index)
    const isAllSelected = selectedIndices.length === allValidIndices.length && allValidIndices.length > 0

    const toggleAll = () => {
        if (isAllSelected) {
            onToggleSelection([])
        } else {
            onToggleSelection(allValidIndices)
        }
    }

    const toggleRow = (index: number) => {
        if (selectedIndices.includes(index)) {
            onToggleSelection(selectedIndices.filter(i => i !== index))
        } else {
            onToggleSelection([...selectedIndices, index])
        }
    }

    const formatAction = (value: unknown) => {
        const action = String(value || '').toUpperCase()
        const labels: Record<string, string> = {
            OPEN: '开仓',
            ENTRY: '加仓',
            BUY: '买入',
            CLOSE: '平仓',
            EXIT: '减仓',
            SELL: '卖出',
        }
        return labels[action] || String(value || '-')
    }

    return (
        <div className="overflow-x-auto border border-line rounded-lg">
            <table className="w-full text-sm text-left">
                <thead className="text-xs text-ink-muted uppercase bg-panel-subtle">
                    <tr>
                        <th className="p-4 w-4">
                            <input
                                type="checkbox"
                                checked={isAllSelected}
                                onChange={toggleAll}
                                aria-label="选择全部有效记录"
                                className="rounded border-line-strong text-ink focus:ring-ink/30"
                                disabled={allValidIndices.length === 0}
                            />
                        </th>
                        <th className="p-4">状态</th>
                        <th className="p-4">时间</th>
                        <th className="p-4">标的</th>
                        <th className="p-4">操作</th>
                        <th className="p-4">价格</th>
                        <th className="p-4">数量</th>
                        <th className="p-4">策略</th>
                        <th className="p-4">情绪</th>
                        <th className="p-4 w-1/4">信息 / 原因</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-line">
                    {rows.map((row) => (
                        <tr
                            key={row.index}
                            className={`
                                hover:bg-panel-subtle transition-colors
                                ${!row.is_valid ? 'bg-loss/10' : ''}
                            `}
                        >
                            <td className="p-4">
                                <input
                                    type="checkbox"
                                    checked={selectedIndices.includes(row.index)}
                                    onChange={() => toggleRow(row.index)}
                                    aria-label={`选择第 ${row.index + 1} 条记录`}
                                    disabled={!row.is_valid}
                                    className="rounded border-line-strong text-ink focus:ring-ink/30 disabled:opacity-50"
                                />
                            </td>
                            <td className="p-4">
                                {row.is_valid ? (
                                    <span className="flex items-center text-profit">
                                        <CheckCircle className="w-4 h-4 mr-1" /> 有效
                                    </span>
                                ) : (
                                    <span className="flex items-center text-loss">
                                        <XCircle className="w-4 h-4 mr-1" /> 有错误
                                    </span>
                                )}
                            </td>
                            <td className="p-4 font-mono text-ink-soft tn-nums">
                                {row.data.date || row.data.time || '-'}
                            </td>
                            <td className="p-4 font-bold">
                                {row.data.symbol || row.data.code || '-'}
                            </td>
                            <td className="p-4">
                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${String(row.data.action || row.data.operation).toUpperCase().includes('OPEN') || String(row.data.action).includes('BUY')
                                    ? 'bg-profit/10 text-profit'
                                    : 'bg-warning/12 text-warning'
                                    }`}>
                                    {formatAction(row.data.action || row.data.operation || row.data.side)}
                                </span>
                            </td>
                            <td className="p-4 font-mono tn-nums">
                                {row.data.price || row.data.cost || '-'}
                            </td>
                            <td className="p-4 font-mono tn-nums">
                                {row.data.quantity || row.data.amount || '-'}
                            </td>
                            <td className="p-4">
                                {row.data.strategy || '-'}
                            </td>
                            <td className="p-4 text-xs">
                                {row.data.emotion && (
                                    <span className="block">{row.data.emotion}</span>
                                )}
                                {row.data.confidence && (
                                    <span className="text-ink-muted">信心：{row.data.confidence}</span>
                                )}
                            </td>
                            <td className="p-4 text-xs">
                                {row.data.reason && (
                                    <div className="mb-1 text-ink-soft italic">
                                        &quot;{row.data.reason}&quot;
                                    </div>
                                )}
                                {row.errors.length > 0 && (
                                    <div className="flex items-start gap-1 text-loss text-xs">
                                        <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                                        <div className="flex flex-col">
                                            {row.errors.map((err, i) => (
                                                <span key={i}>{err}</span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    )
}
