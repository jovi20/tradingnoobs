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

    return (
        <div className="overflow-x-auto border border-slate-200 dark:border-slate-700 rounded-lg">
            <table className="w-full text-sm text-left">
                <thead className="text-xs text-slate-500 uppercase bg-slate-50 dark:bg-slate-800">
                    <tr>
                        <th className="p-4 w-4">
                            <input
                                type="checkbox"
                                checked={isAllSelected}
                                onChange={toggleAll}
                                className="rounded border-slate-300 text-primary-600 focus:ring-primary-500"
                                disabled={allValidIndices.length === 0}
                            />
                        </th>
                        <th className="p-4">状态</th>
                        <th className="p-4">Time</th>
                        <th className="p-4">Symbol</th>
                        <th className="p-4">Action</th>
                        <th className="p-4">Price</th>
                        <th className="p-4">Qty</th>
                        <th className="p-4">Strategy</th>
                        <th className="p-4">Emotion</th>
                        <th className="p-4 w-1/4">Message/Reason</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
                    {rows.map((row) => (
                        <tr
                            key={row.index}
                            className={`
                                hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors
                                ${!row.is_valid ? 'bg-red-50/50 dark:bg-red-900/10' : ''}
                            `}
                        >
                            <td className="p-4">
                                <input
                                    type="checkbox"
                                    checked={selectedIndices.includes(row.index)}
                                    onChange={() => toggleRow(row.index)}
                                    disabled={!row.is_valid}
                                    className="rounded border-slate-300 text-primary-600 focus:ring-primary-500 disabled:opacity-50"
                                />
                            </td>
                            <td className="p-4">
                                {row.is_valid ? (
                                    <span className="flex items-center text-emerald-600">
                                        <CheckCircle className="w-4 h-4 mr-1" /> Valid
                                    </span>
                                ) : (
                                    <span className="flex items-center text-red-600">
                                        <XCircle className="w-4 h-4 mr-1" /> Error
                                    </span>
                                )}
                            </td>
                            <td className="p-4 font-mono text-slate-700 dark:text-slate-300">
                                {row.data.date || row.data.time || '-'}
                            </td>
                            <td className="p-4 font-bold">
                                {row.data.symbol || row.data.code || '-'}
                            </td>
                            <td className="p-4">
                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${String(row.data.action || row.data.operation).toUpperCase().includes('OPEN') || String(row.data.action).includes('BUY')
                                    ? 'bg-emerald-100 text-emerald-700'
                                    : 'bg-amber-100 text-amber-700'
                                    }`}>
                                    {row.data.action || row.data.operation || row.data.side || '-'}
                                </span>
                            </td>
                            <td className="p-4 font-mono">
                                {row.data.price || row.data.cost || '-'}
                            </td>
                            <td className="p-4 font-mono">
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
                                    <span className="text-slate-500">Conf: {row.data.confidence}</span>
                                )}
                            </td>
                            <td className="p-4 text-xs">
                                {row.data.reason && (
                                    <div className="mb-1 text-slate-600 dark:text-slate-400 italic">
                                        &quot;{row.data.reason}&quot;
                                    </div>
                                )}
                                {row.errors.length > 0 && (
                                    <div className="flex items-start gap-1 text-red-600 text-xs">
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
