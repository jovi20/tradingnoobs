import { Activity, ShieldCheck } from 'lucide-react'

import { MetricTile } from '@/components/ui/MetricTile'
import { Surface } from '@/components/ui/Surface'
import { getLifecycleReviewTone, type LifecycleDetailViewModel } from '@/lib/adapters/lifecycle'

interface LifecycleHeroProps {
    lifecycle: LifecycleDetailViewModel
}

export function LifecycleHero({ lifecycle }: LifecycleHeroProps) {
    const reviewTone = getLifecycleReviewTone(lifecycle.reviewStatus)

    return (
        <Surface className="overflow-hidden border-slate-900 bg-gradient-to-br from-slate-950 via-slate-900 to-cyan-950 p-0 text-white dark:border-slate-700">
            <div className="grid gap-0 lg:grid-cols-[minmax(0,1fr)_320px]">
                <div className="p-6 md:p-8">
                    <div className="flex items-center gap-2 text-sm font-bold text-cyan-100">
                        <ShieldCheck className="h-4 w-4" />
                        Truth thesis and result
                    </div>
                    <h2 className="mt-4 text-2xl font-black md:text-4xl">{lifecycle.summaryHeadline}</h2>
                    <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-300 md:text-base">{lifecycle.summaryBody}</p>
                    <div className="mt-6 grid gap-3 md:grid-cols-3">
                        {lifecycle.keyNumbers.map((item) => (
                            <MetricTile key={item.label} label={item.label} value={item.value} detail="truth lifecycle read model" />
                        ))}
                    </div>
                    <div className="mt-6 rounded-3xl border border-white/10 bg-white/[0.06] p-5">
                        <p className="text-[11px] font-bold uppercase tracking-[0.2em] text-cyan-100">Thesis</p>
                        <p className="mt-3 text-sm leading-6 text-slate-200">{lifecycle.thesis || '这笔交易还没有结构化 thesis。'}</p>
                        <div className="mt-4 grid gap-3 md:grid-cols-3">
                            <HeroMini label="Invalidation" value={lifecycle.invalidationRule || '未记录'} />
                            <HeroMini label="Planned Exit" value={lifecycle.plannedExitRule || '未记录'} />
                            <HeroMini label="Sizing" value={lifecycle.sizingRationale || '未记录'} />
                        </div>
                    </div>
                </div>
                <aside className="border-t border-white/10 bg-black/20 p-6 lg:border-l lg:border-t-0">
                    <div className="flex items-center gap-2 text-sm font-bold">
                        <Activity className="h-4 w-4 text-amber-200" />
                        Execution quality
                    </div>
                    <p className="mt-4 text-3xl font-black">{lifecycle.executionQuality || 'UNKNOWN'}</p>
                    <p className="mt-2 text-sm text-slate-300">{reviewTone.description}</p>
                    <div className="mt-5 rounded-2xl border border-white/10 bg-white/[0.06] p-4">
                        <p className="text-[11px] font-bold uppercase tracking-[0.18em] text-slate-400">Checklist miss</p>
                        <p className="mt-2 text-2xl font-black">{lifecycle.checklistMissCount ?? 0}</p>
                    </div>
                </aside>
            </div>
        </Surface>
    )
}

function HeroMini({ label, value }: { label: string; value: string }) {
    return (
        <div className="rounded-2xl border border-white/10 bg-black/20 p-3">
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-slate-500">{label}</p>
            <p className="mt-1 text-sm text-slate-200">{value}</p>
        </div>
    )
}
