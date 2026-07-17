import {
    ArrowDownCircle,
    ArrowUpCircle,
    Award,
    Calendar,
    Edit3,
    MessageSquare,
    Target,
    Wrench,
} from 'lucide-react'

import { Surface } from '@/components/ui/Surface'
import type { LifecycleLegacyPanelState } from '@/lib/adapters/lifecycle'
import {
    type TradeBatchViewModel,
    type PositionViewModel,
} from '@/lib/adapters/trading'
import {
    getCoreTypeLabel,
    getCurrencySymbol,
    getMarketLabel,
    type AssetCoreType,
    type AssetMarket,
} from '@/lib/symbolUtils'

interface LegacyMutationState {
    canMutate: boolean
    label: string
    reason: string
}

interface LegacyReviewState {
    shouldDisplay: boolean
    isMigrationOnly: boolean
    label: string
    reason: string
}

interface LifecycleMigrationPanelProps {
    position: PositionViewModel
    hasTruthLifecycle: boolean
    panel: LifecycleLegacyPanelState
    sortedBatches: TradeBatchViewModel[]
    legacyBatchMutationState: LegacyMutationState
    legacyReviewDisplayState: LegacyReviewState
    onEditMetadata: () => void
    onEditBatch: (batch: TradeBatchViewModel) => void
}

export function LifecycleMigrationPanel({
    position,
    hasTruthLifecycle,
    panel,
    sortedBatches,
    legacyBatchMutationState,
    legacyReviewDisplayState,
    onEditMetadata,
    onEditBatch,
}: LifecycleMigrationPanelProps) {
    const currencySymbol = getCurrencySymbol(position.asset_metadata?.currency)
    const isPositive = Number(position.realized_pnl || 0) >= 0

    return (
        <Surface className="border-warning/30 bg-warning/8 p-5">
            <div className="flex items-start gap-3">
                <div className="rounded-lg bg-warning/12 p-2 text-warning">
                    <Wrench className="h-5 w-5" />
                </div>
                <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-warning">{panel.title}</p>
                    <p className="mt-2 text-sm leading-6 text-ink-soft">{panel.description}</p>
                    {hasTruthLifecycle && (
                        <p className="mt-2 text-xs text-ink-muted">
                            新的数量、价格、盈亏、撤销和调整操作均写入权威审计生命周期。
                        </p>
                    )}
                </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <LegacyMetric label="持仓数量" value={Number(position.total_quantity).toLocaleString()} />
                <LegacyMetric
                    label="持仓均价"
                    value={`${currencySymbol}${Number(position.average_entry_price || 0).toFixed(2)}`}
                />
                <LegacyMetric
                    label="旧版已实现盈亏"
                    value={`${isPositive ? '+' : ''}${currencySymbol}${Number(position.realized_pnl || 0).toFixed(2)}`}
                    className={isPositive ? 'text-profit' : 'text-loss'}
                />
                <LegacyMetric label="开仓日期" value={new Date(position.opened_at).toLocaleDateString('zh-CN')} />
            </div>

            {position.asset_metadata && (
                <div className="mt-5 rounded-lg border border-line bg-panel p-5">
                    <div className="flex items-center justify-between gap-3">
                        <h3 className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.18em] text-warning">
                            <Target className="h-4 w-4" />
                            旧版资产元数据
                        </h3>
                        <button type="button" onClick={onEditMetadata} aria-label="编辑旧版资产属性" title="编辑旧版资产属性" className="rounded-md bg-warning/12 p-2 text-warning transition-colors hover:bg-warning/20">
                            <Edit3 className="h-4 w-4" />
                        </button>
                    </div>
                    <div className="mt-4 grid gap-4 md:grid-cols-3">
                        <LegacyFact
                            label="资产类型"
                            value={position.asset_metadata.instrument
                                ? `${getCoreTypeLabel(position.asset_metadata.core_type as AssetCoreType)} / ${position.asset_metadata.instrument}`
                                : getCoreTypeLabel(position.asset_metadata.core_type as AssetCoreType)}
                        />
                        <LegacyFact label="交易市场" value={`${getMarketLabel(position.asset_metadata.market as AssetMarket)} · ${position.asset_metadata.currency}`} />
                        <LegacyFact label="所属板块" value={position.asset_metadata.sector || '未分类'} />
                    </div>
                </div>
            )}

            <div className="mt-5 rounded-lg border border-line bg-panel p-5">
                <h3 className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.18em] text-warning">
                    <Target className="h-4 w-4" />
                    旧版计划与执行偏移
                </h3>
                {position.drift_analysis?.has_planned_data && (
                    <div className="mt-4 grid gap-3 md:grid-cols-4">
                        <LegacyFact label="计划入场价" value={`${currencySymbol}${Number(position.planned_entry_price || 0).toFixed(2)}`} />
                        <LegacyFact label="实际入场价" value={`${currencySymbol}${Number(position.average_entry_price || 0).toFixed(2)}`} />
                        <LegacyFact label="入场偏移" value={`${position.drift_analysis.entry_drift_pct || 0}%`} />
                        <LegacyFact label="执行质量" value={position.drift_analysis.execution_quality || '未记录'} />
                    </div>
                )}
                {position.checklist_responses && Object.keys(position.checklist_responses).length > 0 && (
                    <div className="mt-4 rounded-md border border-warning/30 bg-warning/8 p-4">
                        <p className="text-xs font-bold uppercase tracking-[0.16em] text-warning">旧版检查清单</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                            {Object.entries(position.checklist_responses).map(([id, checked]) => (
                                <span key={id} className={`rounded-full px-2.5 py-1 text-xs font-semibold ${checked ? 'bg-profit/10 text-profit' : 'bg-loss/10 text-loss'}`}>
                                    #{id} {checked ? '通过' : '未通过'}
                                </span>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            <div className="mt-5 rounded-lg border border-line bg-panel">
                <div className="border-b border-line p-5">
                    <h3 className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.18em] text-warning">
                        <Calendar className="h-4 w-4" />
                        旧版交易批次（{sortedBatches.length}）
                    </h3>
                </div>
                <div className="divide-y divide-line">
                    {sortedBatches.map((batch) => (
                        <div key={batch.id} className="flex items-start justify-between gap-4 p-4">
                            <div className="flex items-start gap-3">
                                <div className={`flex h-10 w-10 items-center justify-center rounded-md ${batch.type === 'ENTRY' ? 'bg-profit/10' : 'bg-loss/10'}`}>
                                    {batch.type === 'ENTRY'
                                        ? <ArrowUpCircle className="h-5 w-5 text-profit" />
                                        : <ArrowDownCircle className="h-5 w-5 text-loss" />}
                                </div>
                                <div>
                                    <p className="font-semibold text-ink">
                                        {batch.type === 'ENTRY' ? '加仓' : '平仓'}
                                        <span className="ml-2 text-ink-muted tn-nums">{Number(batch.quantity).toLocaleString()} @ {currencySymbol}{Number(batch.price).toFixed(2)}</span>
                                    </p>
                                    <p className="mt-1 text-xs text-ink-muted tn-nums">{new Date(batch.time).toLocaleString('zh-CN')}</p>
                                    {batch.reason && (
                                        <p className="mt-2 text-sm text-ink-soft">
                                            <MessageSquare className="mr-1 inline h-3 w-3" />
                                            {batch.reason}
                                        </p>
                                    )}
                                </div>
                            </div>
                            {legacyBatchMutationState.canMutate ? (
                                <button type="button" onClick={() => onEditBatch(batch)} aria-label={`编辑${batch.type === 'ENTRY' ? '加仓' : '平仓'}记录`} title={`编辑${batch.type === 'ENTRY' ? '加仓' : '平仓'}记录`} className="rounded-md p-2 text-ink-faint transition-colors hover:bg-warning/12 hover:text-warning">
                                    <Edit3 className="h-4 w-4" />
                                </button>
                            ) : (
                                <span title={legacyBatchMutationState.reason} className="rounded-full border border-warning/30 bg-warning/8 px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.14em] text-warning">
                                    {legacyBatchMutationState.label}
                                </span>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {legacyReviewDisplayState.shouldDisplay && position.trade_review && (
                <div className="mt-5 rounded-lg border border-line bg-panel p-5">
                    <h3 className="text-sm font-black uppercase tracking-[0.18em] text-warning">{legacyReviewDisplayState.label}</h3>
                    <p className="mt-2 text-xs font-semibold text-ink-soft">
                        旧版复盘仅作为只读迁移参考；权威复盘叙事记录在审计事件中。
                    </p>
                    <p className="mt-2 rounded-md border border-warning/30 bg-warning/8 px-3 py-2 text-xs text-warning">
                        {legacyReviewDisplayState.reason}
                    </p>
                    <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-ink-soft">{position.trade_review}</p>
                </div>
            )}

            {position.lessons && position.lessons.length > 0 && (
                <div className="mt-5 rounded-lg border border-line bg-panel p-5">
                    <h3 className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.18em] text-warning">
                        <Award className="h-4 w-4" />
                        旧版经验记录
                    </h3>
                    <div className="mt-3 flex flex-wrap gap-2">
                        {position.lessons.map((lesson, index) => (
                            <span key={`${lesson}-${index}`} className="rounded-full bg-warning/12 px-3 py-1 text-sm text-warning">
                                {lesson}
                            </span>
                        ))}
                    </div>
                </div>
            )}
        </Surface>
    )
}

function LegacyMetric({ label, value, className = '' }: { label: string; value: string; className?: string }) {
    return (
        <div className="rounded-lg border border-line bg-panel p-4">
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-warning">{label}</p>
            <p className={`mt-2 text-lg font-black text-ink tn-nums ${className}`}>{value}</p>
        </div>
    )
}

function LegacyFact({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <p className="text-xs text-ink-muted">{label}</p>
            <p className="mt-1 font-semibold text-ink">{value}</p>
        </div>
    )
}
