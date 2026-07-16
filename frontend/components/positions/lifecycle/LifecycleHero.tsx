import { Activity, ShieldCheck } from 'lucide-react'

import { MetricTile } from '@/components/ui/MetricTile'
import { Surface } from '@/components/ui/Surface'
import { getLifecycleReviewTone, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'

interface LifecycleHeroProps {
    lifecycle: LifecycleDetailViewModel
}

export function LifecycleHero({ lifecycle }: LifecycleHeroProps) {
    const reviewTone = getLifecycleReviewTone(lifecycle.reviewStatus)
    const executionQualityLabel = {
        EXCELLENT: '优秀',
        GOOD: '良好',
        FAIR: '一般',
        POOR: '较差',
    }[lifecycle.executionQuality || ''] || '未评估'

    return (
        <Surface className="overflow-hidden border-line bg-panel p-0 text-ink">
            <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="p-6 md:p-8">
                    <div className="flex items-center gap-2 text-sm font-bold text-ai">
                        <ShieldCheck className="h-4 w-4" />
                        交易依据与结果
                    </div>
                    <h2 className="mt-4 text-2xl font-black md:text-4xl">{lifecycle.summaryHeadline}</h2>
                    <p className="mt-3 max-w-3xl text-sm leading-6 text-ink-soft md:text-base">{lifecycle.summaryBody}</p>
                    <div className="mt-6 grid gap-3 md:grid-cols-3">
                        {lifecycle.keyNumbers.map((item) => (
                            <MetricTile key={item.label} label={item.label} value={item.value} detail="由交易事件汇总" />
                        ))}
                    </div>
                    <div className="mt-6 rounded-lg border border-line bg-panel-subtle p-5">
                        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-ai">交易假设</p>
                        <p className="mt-3 text-sm leading-6 text-ink-soft">{lifecycle.thesis || '这笔交易还没有结构化交易假设。'}</p>
                        <div className="mt-4 grid gap-3 md:grid-cols-3">
                            <HeroMini label="失效条件" value={lifecycle.invalidationRule || '未记录'} />
                            <HeroMini label="退出计划" value={lifecycle.plannedExitRule || '未记录'} />
                            <HeroMini label="仓位依据" value={lifecycle.sizingRationale || '未记录'} />
                        </div>
                    </div>
                </div>
                <aside className="border-t border-line bg-panel-subtle p-6 lg:border-l lg:border-t-0">
                    <div className="flex items-center gap-2 text-sm font-bold">
                        <Activity className="h-4 w-4 text-warning" />
                        执行质量
                    </div>
                    <p className="mt-4 text-3xl font-black">{executionQualityLabel}</p>
                    <p className="mt-2 text-sm text-ink-soft">{reviewTone.description}</p>
                    <div className="mt-5 rounded-lg border border-line bg-panel p-4">
                        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-ink-muted">检查项遗漏</p>
                        <p className="mt-2 text-2xl font-black tn-nums">{lifecycle.checklistMissCount ?? 0}</p>
                    </div>
                </aside>
            </div>
        </Surface>
    )
}

function HeroMini({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-lg border border-line bg-panel p-3">
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-ink-muted">{label}</p>
            <p className="mt-1 text-sm text-ink-soft">{value}</p>
        </div>
    )
}
