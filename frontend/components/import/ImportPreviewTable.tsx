'use client'

import { AlertTriangle, CheckCircle, Info, XCircle } from 'lucide-react'
import { ImportPreviewRow } from '@/lib/api'

interface ImportPreviewTableProps {
    rows: ImportPreviewRow[]
}

export function ImportPreviewTable({ rows }: ImportPreviewTableProps) {
    const fieldLabels: Record<string, string> = {
        action: '操作',
        direction: '方向',
        fee_currency: '费用币种',
        price: '价格',
        quantity: '数量',
        timestamp: '时间',
    }
    const text = (value: unknown) => value === null || value === undefined || value === ''
        ? '-'
        : String(value)
    const formatDirection = (value: unknown) => {
        const labels: Record<string, string> = {
            LONG: '多头',
            SHORT: '空头',
        }
        const direction = String(value || '').toUpperCase()
        return labels[direction] || text(value)
    }
    const formatAction = (value: unknown) => {
        const action = String(value || '').toUpperCase()
        const labels: Record<string, string> = {
            OPEN: '开仓',
            ADD: '加仓',
            REDUCE: '减仓',
            CLOSE: '平仓',
        }
        return labels[action] || String(value || '-')
    }
    const formatIssue = (
        issue: ImportPreviewRow['errors'][number],
        kind: 'error' | 'warning',
    ) => {
        const field = issue.field ? fieldLabels[issue.field] : null
        const labels: Record<string, string> = {
            AMBIGUOUS_LOCAL_TIME: '本地时间处于夏令时重复区间，请提供明确时区偏移',
            DUPLICATE_ROW: '与前面的归一化交易重复，本行仍会保留',
            INSTRUMENT_IDENTITY_MISMATCH: '标的身份或币种与账户不一致',
            INVALID_IMPORT_NUMBER: `${field || '数值'}格式无效或不在允许范围内`,
            INVALID_IMPORT_TIMESTAMP: '时间必须是有效的 ISO-8601 日期时间',
            NONEXISTENT_LOCAL_TIME: '本地时间处于夏令时跳跃区间，请提供明确时区偏移',
            UNSUPPORTED_IMPORT_ACTION: '操作必须是开仓、加仓、减仓或平仓',
            UNSUPPORTED_IMPORT_DIRECTION: '方向必须是多头或空头',
            UNTRUSTED_SOURCE_ID_IGNORED: '通用文件中的外部交易编号不会作为可信来源标识',
        }
        return labels[issue.code]
            || `${kind === 'error' ? '校验失败' : '提示'}（${issue.code}）`
    }

    return (
        <div className="overflow-x-auto border border-line rounded-lg">
            <table className="w-full text-sm text-left">
                <thead className="text-xs text-ink-muted uppercase bg-panel-subtle">
                    <tr>
                        <th className="p-4">行</th>
                        <th className="p-4">状态</th>
                        <th className="p-4">时间</th>
                        <th className="p-4">标的</th>
                        <th className="p-4">方向</th>
                        <th className="p-4">操作</th>
                        <th className="p-4">价格</th>
                        <th className="p-4">数量</th>
                        <th className="p-4">标的身份</th>
                        <th className="p-4 w-1/3">校验</th>
                    </tr>
                </thead>
                <tbody className="divide-y divide-line">
                    {rows.map((row) => (
                        <tr
                            key={row.public_id}
                            className={`
                                hover:bg-panel-subtle transition-colors
                                ${!row.is_valid ? 'bg-loss/10' : ''}
                            `}
                        >
                            <td className="p-4 font-mono tn-nums">{row.row_number}</td>
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
                                {text(row.normalized_values.occurred_at)}
                            </td>
                            <td className="p-4 font-bold">
                                {text(row.normalized_values.symbol)}
                                <span className="block text-xs font-normal text-ink-muted">
                                    {text(row.normalized_values.exchange_code)}
                                </span>
                            </td>
                            <td className="p-4">
                                {formatDirection(row.normalized_values.direction)}
                            </td>
                            <td className="p-4">
                                <span className={`px-2 py-0.5 rounded text-xs font-medium ${['OPEN', 'ADD'].includes(String(row.normalized_values.action))
                                    ? 'bg-profit/10 text-profit'
                                    : 'bg-warning/12 text-warning'
                                    }`}>
                                    {formatAction(row.normalized_values.action)}
                                </span>
                            </td>
                            <td className="p-4 font-mono tn-nums">
                                {text(row.normalized_values.price)}
                            </td>
                            <td className="p-4 font-mono tn-nums">
                                {text(row.normalized_values.quantity)}
                            </td>
                            <td className="p-4 text-xs">
                                {text(row.normalized_values.asset_type)} · {text(row.normalized_values.market)}
                                <span className="block text-ink-muted">
                                    {row.normalized_values.instrument_resolution === 'CREATE_ON_CONFIRM'
                                        ? '确认时建档'
                                        : '已建档'}
                                </span>
                            </td>
                            <td className="p-4 text-xs">
                                {row.errors.length > 0 && (
                                    <div className="flex items-start gap-1 text-loss text-xs">
                                        <AlertTriangle className="w-3 h-3 mt-0.5 shrink-0" />
                                        <div className="flex flex-col">
                                            {row.errors.map((err, i) => (
                                                <span key={`${err.code}-${i}`}>
                                                    {formatIssue(err, 'error')}
                                                </span>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {row.warnings.length > 0 && (
                                    <div className="mt-1 flex items-start gap-1 text-warning">
                                        <Info className="w-3 h-3 mt-0.5 shrink-0" />
                                        <div className="flex flex-col">
                                            {row.warnings.map((warning, i) => (
                                                <span key={`${warning.code}-${i}`}>
                                                    {formatIssue(warning, 'warning')}
                                                </span>
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
