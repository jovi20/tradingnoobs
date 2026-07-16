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

const severityLabels: Record<RiskAlertSeverity, string> = {
  CRITICAL: '严重',
  WARNING: '警告',
  NOTICE: '提示',
  INFO: '信息',
}

const containsChinese = (value: string): boolean => /[\u3400-\u9fff]/.test(value)

export function getRiskAlertTone(severity: RiskAlertSeverity): WorkbenchTone {
  if (severity === 'CRITICAL') return 'danger'
  if (severity === 'WARNING') return 'warning'
  if (severity === 'NOTICE') return 'review'
  return 'neutral'
}

export function getRiskAlertSeverityLabel(severity: RiskAlertSeverity): string {
  return severityLabels[severity]
}

export function formatRiskAlertReason(alert: Pick<RiskAlert, 'kind' | 'reason'>): string {
  const reason = alert.reason?.trim() || ''
  if (containsChinese(reason)) return reason

  if (alert.kind === 'DAILY_LOSS_LIMIT') return '当日损益已超过设定的风险阈值。'
  if (alert.kind === 'CONCENTRATION') return '单一持仓敞口已超过组合集中度阈值。'
  if (alert.kind === 'DRAWDOWN') return '组合回撤已超过设定的风险阈值。'
  if (alert.kind === 'DATA_STALE') return '行情数据已过期，请刷新后再判断风险。'
  return '风险指标已触发，请查看相关数据并及时处理。'
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
      countLabel: '0 条提醒',
    }
  }

  return {
    headline: primary.summary,
    detail: formatRiskAlertReason(primary),
    tone: getRiskAlertTone(primary.severity),
    countLabel: `${alerts.length} 条提醒`,
  }
}
