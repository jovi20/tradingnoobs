import Link from 'next/link'
import { AlertTriangle, CheckCircle2, ShieldAlert } from 'lucide-react'

import {
    formatRiskAlertReason,
    getRiskAlertSeverityLabel,
    getRiskAlertTone,
    summarizeRiskAlerts,
} from '@/lib/adapters/risk-alerts'
import type { RiskAlert } from '@/lib/api'
import { StatusPill } from '@/components/ui/StatusPill'

interface RiskAlertStackProps {
    alerts: RiskAlert[]
}

export function RiskAlertStack({ alerts }: RiskAlertStackProps) {
    const summary = summarizeRiskAlerts(alerts)
    const hasAlerts = alerts.length > 0

    return (
        <div className="rounded-lg border border-line bg-panel p-4">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <div className="mb-2 flex items-center gap-2">
                        {hasAlerts ? (
                            <ShieldAlert className="h-4 w-4 text-warning" />
                        ) : (
                            <CheckCircle2 className="h-4 w-4 text-profit" />
                        )}
                        <p className="text-sm font-semibold text-ink">风险提醒</p>
                    </div>
                    <p className="text-sm font-semibold text-ink-soft">{summary.headline}</p>
                    <p className="mt-1 text-xs leading-5 text-ink-muted">{summary.detail}</p>
                </div>
                <StatusPill tone={summary.tone}>{summary.countLabel}</StatusPill>
            </div>

            {alerts.length > 0 && (
                <div className="mt-4 space-y-2">
                    {alerts.slice(0, 3).map((alert) => (
                        <Link
                            key={alert.public_id}
                            href={alert.recommended_action.href}
                            className="block rounded-md border border-line p-3 text-sm transition-colors hover:border-line-strong"
                        >
                            <div className="flex items-start gap-2">
                                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-warning" />
                                <div>
                                    <StatusPill tone={getRiskAlertTone(alert.severity)}>
                                        {getRiskAlertSeverityLabel(alert.severity)}
                                    </StatusPill>
                                    <p className="mt-1 font-semibold text-ink-soft">{alert.summary}</p>
                                    <p className="mt-1 text-xs leading-5 text-ink-muted">{formatRiskAlertReason(alert)}</p>
                                </div>
                            </div>
                        </Link>
                    ))}
                </div>
            )}
        </div>
    )
}
