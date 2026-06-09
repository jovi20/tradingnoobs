import { Activity, Database, Sparkles } from 'lucide-react'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { StatusPill } from '@/components/ui/StatusPill'
import { Surface } from '@/components/ui/Surface'
import type { DashboardRiskPosture } from '@/lib/adapters/dashboard'

interface DashboardRiskRailProps {
    riskPosture: DashboardRiskPosture
    openPositionsCount: number
    hasPnlHistory: boolean
}

export function DashboardRiskRail({ riskPosture, openPositionsCount, hasPnlHistory }: DashboardRiskRailProps) {
    return (
        <aside className="space-y-4">
            <Surface variant="rail" className="p-4">
                <SectionHeader
                    eyebrow="Risk Posture"
                    title={riskPosture.label}
                    description={riskPosture.detail}
                    action={<StatusPill tone={riskPosture.tone}>{riskPosture.tone}</StatusPill>}
                />
                <div className="mt-4 h-2 rounded-full bg-slate-200 dark:bg-slate-800">
                    <div className={`h-2 rounded-full ${riskPosture.tone === 'danger' ? 'w-full bg-red-500' : riskPosture.tone === 'warning' ? 'w-2/3 bg-amber-500' : 'w-1/3 bg-emerald-500'}`} />
                </div>
            </Surface>
            <Surface className="p-4">
                <div className="flex items-start gap-3">
                    <Database className="mt-1 h-4 w-4 text-slate-400" />
                    <div>
                        <p className="text-sm font-semibold text-slate-950 dark:text-slate-50">数据新鲜度</p>
                        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                            {hasPnlHistory ? '资金曲线已加载，Dashboard 使用当前聚合数据。' : '资金曲线暂无数据，先展示结构和风险摘要。'}
                        </p>
                    </div>
                </div>
            </Surface>
            <Surface className="p-4">
                <div className="flex items-start gap-3">
                    <Activity className="mt-1 h-4 w-4 text-slate-400" />
                    <div>
                        <p className="text-sm font-semibold text-slate-950 dark:text-slate-50">组合活动</p>
                        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                            当前有 {openPositionsCount} 个打开交易对象，细节仍从交易页进入。
                        </p>
                    </div>
                </div>
            </Surface>
            <Surface className="p-4">
                <div className="flex items-start gap-3">
                    <Sparkles className="mt-1 h-4 w-4 text-amber-500" />
                    <div>
                        <p className="text-sm font-semibold text-slate-950 dark:text-slate-50">周度摘要</p>
                        <p className="mt-1 text-sm leading-6 text-slate-500 dark:text-slate-400">
                            本阶段先使用风险和结构数据生成可读摘要；AI insight 深读继续保留在洞察页。
                        </p>
                    </div>
                </div>
            </Surface>
        </aside>
    )
}
