import Link from 'next/link'
import { ChevronRight } from 'lucide-react'

import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'

interface TimelineContextRailProps {
    contextRail: TimelineHomeViewModel['contextRail']
    onSelectView: (value: string) => void
}

export function TimelineContextRail({ contextRail, onSelectView }: TimelineContextRailProps) {
    return (
        <aside className="space-y-4">
            <div className="card p-4">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">上下文栏</h2>
                {contextRail.selected_object ? (
                    <div className="mt-4 rounded-xl border border-slate-200 p-4 dark:border-slate-700">
                        <p className="text-xs text-slate-400">{contextRail.selected_object.object_type}</p>
                        <p className="mt-1 font-semibold">{contextRail.selected_object.title}</p>
                        {contextRail.selected_object.subtitle && (
                            <p className="mt-1 text-sm text-slate-500">{contextRail.selected_object.subtitle}</p>
                        )}
                        <Link
                            href={contextRail.selected_object.href}
                            className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-primary-600"
                        >
                            打开详情
                            <ChevronRight className="w-3 h-3" />
                        </Link>
                    </div>
                ) : (
                    <p className="mt-4 text-sm text-slate-500">选中一个对象后，这里会展示它的摘要和相关上下文。</p>
                )}
            </div>

            <div className="card p-4">
                <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">快速筛选</h2>
                <div className="mt-4 flex flex-wrap gap-2">
                    {contextRail.quick_filters.map((filter) => (
                        <button
                            key={filter.key}
                            type="button"
                            onClick={() => onSelectView(filter.key)}
                            className={`rounded-full px-3 py-1.5 text-xs font-medium transition ${
                                filter.active
                                    ? 'bg-slate-900 text-white dark:bg-white dark:text-slate-900'
                                    : 'bg-slate-100 text-slate-600 hover:bg-slate-200 dark:bg-slate-800 dark:text-slate-300 dark:hover:bg-slate-700'
                            }`}
                        >
                            {filter.label}
                        </button>
                    ))}
                </div>
            </div>

            {contextRail.weekly_discipline_snapshot && (
                <div className="card p-4">
                    <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-400">本周纪律画像</h2>
                    <p className="mt-4 font-semibold">{contextRail.weekly_discipline_snapshot.headline}</p>
                    <p className="mt-2 text-sm text-slate-500">
                        {contextRail.weekly_discipline_snapshot.summary}
                    </p>
                </div>
            )}
        </aside>
    )
}
