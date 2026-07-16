import { Activity, Database, Sparkles } from 'lucide-react'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { StatusPill } from '@/components/ui/StatusPill'
import { Surface } from '@/components/ui/Surface'
import type { DashboardRiskPosture } from '@/lib/adapters/dashboard'
import type { RiskAlert } from '@/lib/api'
import { RiskAlertStack } from '@/components/risk/RiskAlertStack'

interface DashboardRiskRailProps {
    riskPosture: DashboardRiskPosture
    openPositionsCount: number
    hasPnlHistory: boolean
    riskAlerts?: RiskAlert[]
}

export function DashboardRiskRail({ riskPosture, openPositionsCount, hasPnlHistory, riskAlerts = [] }: DashboardRiskRailProps) {
    const riskLevelLabel = riskPosture.tone === 'danger'
        ? '高风险'
        : riskPosture.tone === 'warning'
            ? '需关注'
            : '健康'

    return (
        <aside className="space-y-4">
            <Surface variant="rail" className="p-4">
                <SectionHeader
                    eyebrow="风险态势"
                    title={riskPosture.label}
                    description={riskPosture.detail}
                    action={<StatusPill tone={riskPosture.tone}>{riskLevelLabel}</StatusPill>}
                />
                <div className="mt-4 h-2 rounded-full bg-panel-subtle">
                    <div className={`h-2 rounded-full ${riskPosture.tone === 'danger' ? 'w-full bg-loss' : riskPosture.tone === 'warning' ? 'w-2/3 bg-warning' : 'w-1/3 bg-profit'}`} />
                </div>
            </Surface>
            <RiskAlertStack alerts={riskAlerts} />
            <Surface className="p-4">
                <div className="flex items-start gap-3">
                    <Database className="mt-1 h-4 w-4 text-ink-faint" />
                    <div>
                        <p className="text-sm font-semibold text-ink">数据新鲜度</p>
                        <p className="mt-1 text-sm leading-6 text-ink-muted">
                            {hasPnlHistory ? '资金曲线已加载，看板使用当前聚合数据。' : '资金曲线暂无数据，先展示结构和风险摘要。'}
                        </p>
                    </div>
                </div>
            </Surface>
            <Surface className="p-4">
                <div className="flex items-start gap-3">
                    <Activity className="mt-1 h-4 w-4 text-ink-faint" />
                    <div>
                        <p className="text-sm font-semibold text-ink">组合活动</p>
                        <p className="mt-1 text-sm leading-6 text-ink-muted">
                            当前有 {openPositionsCount} 个打开交易对象，细节仍从交易页进入。
                        </p>
                    </div>
                </div>
            </Surface>
            <Surface className="p-4">
                <div className="flex items-start gap-3">
                    <Sparkles className="mt-1 h-4 w-4 text-warning" />
                    <div>
                        <p className="text-sm font-semibold text-ink">周度摘要</p>
                        <p className="mt-1 text-sm leading-6 text-ink-muted">
                            本阶段先使用风险和结构数据生成可读摘要；AI 洞察深读继续保留在洞察页。
                        </p>
                    </div>
                </div>
            </Surface>
        </aside>
    )
}
