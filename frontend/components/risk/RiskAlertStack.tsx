import Link from 'next/link'
import { AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react'

import { getRiskAlertTone, summarizeRiskAlerts } from '@/lib/adapters/risk-alerts'
import type { RiskAlert } from '@/lib/api'
import { StatusPill } from '@/components/ui/StatusPill'

interface RiskAlertStackProps {
    alerts: RiskAlert[]
}

export function RiskAlertStack({ alerts }: RiskAlertStackProps) {
    const summary = summarizeRiskAlerts(alerts)
    const hasAlerts = alerts.length > 0

    return (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-950/60">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <div className="mb-2 flex items-center gap-2">
                        {hasAlerts ? (
                            <ShieldAlert className="h-4 w-4 text-amber-500" />
                        ) : (
                            <CheckCircle2 className="h-4 w-4 text-emerald-500" />
                        )}
                        <p className="text-sm font-semibold text-slate-950 dark:text-slate-50">风险提醒</p>
                    </div>
                    <p className="text-sm font-semibold text-slate-800 dark:text-slate-100">{summary.headline}</p>
                    <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{summary.detail}</p>
                </div>
                <StatusPill tone={summary.tone}>{summary.countLabel}</StatusPill>
            </div>

            {alerts.length > 0 && (
                <div className="mt-4 space-y-2">
                    {alerts.slice(0, 3).map((alert) => (
                        <Link
                            key={alert.public_id}
                            href={alert.recommended_action.href}
                            className="block rounded-xl border border-slate-100 p-3 text-sm transition hover:border-slate-300 dark:border-slate-800 dark:hover:border-slate-700"
                        >
                            <div className="flex items-start gap-2">
                                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" />
                                <div>
                                    <StatusPill tone={getRiskAlertTone(alert.severity)}>{alert.severity}</StatusPill>
                                    <p className="mt-1 font-semibold text-slate-800 dark:text-slate-100">{alert.summary}</p>
                                    <p className="mt-1 text-xs leading-5 text-slate-500 dark:text-slate-400">{alert.reason}</p>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    )
}
