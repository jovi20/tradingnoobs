import type { RiskAlert, RiskAlertSeverity } from '../api.ts'
import type { WorkbenchTone } from './timeline-workbench.ts'

export interface RiskAlertSummary {
  headline: string
  detail: string
  tone: WorkbenchTone
  countLabel: string
}

const severityRank: Record<RiskAlertSeverity, number> = {
  CRITICAL: 4,
  WARNING: 3,
  NOTICE: 2,
  INFO: 1,
}

export function getRiskAlertTone(severity: RiskAlertSeverity): WorkbenchTone {
  if (severity === 'CRITICAL') return 'danger'
  if (severity === 'WARNING') return 'warning'
  if (severity === 'NOTICE') return 'review'
  return 'neutral'
}

export function getPrimaryRiskAlert(alerts: RiskAlert[]): RiskAlert | null {
  if (alerts.length === 0) return null
  return [...alerts].sort((a, b) => severityRank[b.severity] - severityRank[a.severity])[0]
}

export function summarizeRiskAlerts(alerts: RiskAlert[]): RiskAlertSummary {
  const primary = getPrimaryRiskAlert(alerts)
  if (!primary) {
    return {
      headline: '暂无风险预警',
      detail: '组合风险未触发当前阈值。',
      tone: 'positive',
      countLabel: '0 alerts',
    }
  }

  return {
    headline: primary.summary,
    detail: primary.reason,
    tone: getRiskAlertTone(primary.severity),
    countLabel: `${alerts.length} alerts`,
  }
}
