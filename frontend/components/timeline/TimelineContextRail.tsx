import Link from 'next/link'
import { ChevronRight } from 'lucide-react'

import type { TimelineHomeViewModel } from '@/lib/adapters/timeline'
import { Surface } from '@/components/ui/Surface'

interface TimelineContextRailProps {
    contextRail: TimelineHomeViewModel['contextRail']
    onSelectView: (value: string) => void
}

export function TimelineContextRail({ contextRail, onSelectView }: TimelineContextRailProps) {
    const selectedObject = contextRail.selected_object?.object_type === 'INSIGHT_ARTIFACT'
        || contextRail.selected_object?.href.startsWith('/insights')
        ? undefined
        : contextRail.selected_object
    const quickFilters = contextRail.quick_filters.filter((filter) => filter.key !== 'AI')
    const quickFilterLabels: Record<string, string> = {
        ALL: '全部',
        TRADING: '交易',
        REVIEW: '复盘',
        EXCEPTION: '异常',
    }
    const objectTypeLabels: Record<string, string> = {
        TRADING_POSITION: '交易持仓',
        POSITION_EVENT: '持仓事件',
        ACCOUNT: '交易账户',
        PORTFOLIO: '投资组合',
    }
    return (
        <aside className="space-y-4">
            <Surface className="p-4">
                <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-faint">上下文栏</h2>
                {selectedObject ? (
                    <div className="mt-4 rounded-md border border-line bg-panel-subtle/60 p-4">
                        <p className="text-xs text-ink-faint">
                            {objectTypeLabels[selectedObject.object_type] ?? selectedObject.object_type}
                        </p>
                        <p className="mt-1 font-semibold text-ink">{selectedObject.title}</p>
                        {selectedObject.subtitle && (
                            <p className="mt-1 text-sm text-ink-muted">{selectedObject.subtitle}</p>
                        )}
                        <Link
                            href={selectedObject.href}
                            className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-ai transition-opacity hover:opacity-80"
                        >
                            打开详情
                            <ChevronRight className="h-3 w-3" />
                        </Link>
                    </div>
                ) : (
                    <p className="mt-4 text-sm text-ink-muted">选中一个对象后，这里会展示它的摘要和相关上下文。</p>
                )}
            </Surface>

            <Surface className="p-4">
                <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-faint">快速筛选</h2>
                <div className="mt-4 flex flex-wrap gap-2">
                    {quickFilters.map((filter) => (
                        <button
                            key={filter.key}
                            type="button"
                            onClick={() => onSelectView(filter.key)}
                            className={`rounded-full px-3 py-1.5 text-xs font-medium transition-colors ${
                                filter.active
                                    ? 'bg-ink text-canvas'
                                    : 'bg-panel-subtle text-ink-muted hover:text-ink'
                            }`}
                        >
                            {quickFilterLabels[filter.key] ?? filter.label}
                        </button>
                    ))}
                </div>
            </Surface>

            {contextRail.weekly_discipline_snapshot && (
                <Surface className="p-4">
                    <h2 className="text-[11px] font-semibold uppercase tracking-[0.16em] text-ink-faint">本周纪律画像</h2>
                    <p className="mt-4 font-semibold text-ink">{contextRail.weekly_discipline_snapshot.headline}</p>
                    <p className="mt-2 text-sm text-ink-muted">
                        {contextRail.weekly_discipline_snapshot.summary}
                    </p>
                </Surface>
            )}
        </aside>
    )
}
