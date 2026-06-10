import {
    ArrowDownCircle,
    ArrowUpCircle,
    Award,
    Calendar,
    Edit3,
    Loader2,
    MessageSquare,
    Target,
    TrendingUp,
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
    getRiskLevelInfo,
    type AssetCoreType,
    type AssetMarket,
    type AssetRiskLevel,
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
    isAnalyzing: boolean
    legacyBatchMutationState: LegacyMutationState
    legacyReviewDisplayState: LegacyReviewState
    onEditMetadata: () => void
    onEditExtremes: () => void
    onAnalyze: () => void
    onEditBatch: (batch: TradeBatchViewModel) => void
}

export function LifecycleMigrationPanel({
    position,
    hasTruthLifecycle,
    panel,
    sortedBatches,
    isAnalyzing,
    legacyBatchMutationState,
    legacyReviewDisplayState,
    onEditMetadata,
    onEditExtremes,
    onAnalyze,
    onEditBatch,
}: LifecycleMigrationPanelProps) {
    const currencySymbol = getCurrencySymbol(position.asset_metadata?.currency)
    const isPositive = Number(position.realized_pnl || 0) >= 0

    return (
        <Surface className="border-amber-200 bg-amber-50/70 p-5 dark:border-amber-900 dark:bg-amber-950/20">
            <div className="flex items-start gap-3">
                <div className="rounded-2xl bg-amber-100 p-2 text-amber-700 dark:bg-amber-500/15 dark:text-amber-200">
                    <Wrench className="h-5 w-5" />
                </div>
                <div>
                    <p className="text-[11px] font-black uppercase tracking-[0.2em] text-amber-800 dark:text-amber-200">{panel.title}</p>
                    <p className="mt-2 text-sm leading-6 text-amber-900 dark:text-amber-100">{panel.description}</p>
                    {hasTruthLifecycle && (
                        <p className="mt-2 text-xs text-amber-800/80 dark:text-amber-200/80">
                            New quantity, price, PnL, reversal, and adjustment writes belong to TradingPosition / PositionEvent.
                        </p>
                    )}
                </div>
            </div>

            <div className="mt-5 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
                <LegacyMetric label="持仓数量" value={Number(position.total_quantity).toLocaleString()} />
                <LegacyMetric
                    label="均价 / 当前价"
                    value={`${currencySymbol}${Number(position.average_entry_price || 0).toFixed(2)}${position.current_price ? ` -> ${currencySymbol}${Number(position.current_price).toFixed(2)}` : ''}`}
                />
                <LegacyMetric
                    label="Legacy realized PnL"
                    value={`${isPositive ? '+' : ''}${currencySymbol}${Number(position.realized_pnl || 0).toFixed(2)}`}
                    className={isPositive ? 'text-emerald-700 dark:text-emerald-300' : 'text-red-700 dark:text-red-300'}
                />
                <LegacyMetric label="开仓日期" value={new Date(position.opened_at).toLocaleDateString('zh-CN')} />
            </div>

            {position.asset_metadata && (
                <div className="mt-5 rounded-3xl border border-amber-200 bg-white/70 p-5 dark:border-amber-900/60 dark:bg-slate-950/30">
                    <div className="flex items-center justify-between gap-3">
                        <h3 className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.18em] text-amber-900 dark:text-amber-100">
                            <Target className="h-4 w-4" />
                            Legacy asset metadata
                        </h3>
                        <button type="button" onClick={onEditMetadata} className="rounded-lg bg-amber-100 p-2 text-amber-700 transition-colors hover:bg-amber-200 dark:bg-amber-500/15 dark:text-amber-200">
                            <Edit3 className="h-4 w-4" />
                        </button>
                    </div>
                    <div className="mt-4 grid gap-4 md:grid-cols-4">
                        <LegacyFact label="资产类型" value={`${getCoreTypeLabel(position.asset_metadata.core_type as AssetCoreType)} / ${position.asset_metadata.instrument}`} />
                        <LegacyFact label="交易市场" value={`${getMarketLabel(position.asset_metadata.market as AssetMarket)} · ${position.asset_metadata.currency}`} />
                        <LegacyFact label="所属板块" value={position.asset_metadata.sector || '未分类'} />
                        <LegacyFact label="风险评级" value={getRiskLevelInfo(position.asset_metadata.risk_level as AssetRiskLevel).label} />
                    </div>
                </div>
            )}

            <div className="mt-5 rounded-3xl border border-amber-200 bg-white/70 p-5 dark:border-amber-900/60 dark:bg-slate-950/30">
                <div className="flex items-center justify-between gap-3">
                    <h3 className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.18em] text-amber-900 dark:text-amber-100">
                        <TrendingUp className="h-4 w-4" />
                        Legacy MAE/MFE and drift
                    </h3>
                    <div className="flex gap-2">
                        <button type="button" onClick={onEditExtremes} className="rounded-lg bg-amber-100 p-2 text-amber-700 transition-colors hover:bg-amber-200 dark:bg-amber-500/15 dark:text-amber-200">
                            <Edit3 className="h-4 w-4" />
                        </button>
                        <button type="button" onClick={onAnalyze} disabled={isAnalyzing} className="rounded-lg bg-amber-100 p-2 text-amber-700 transition-colors hover:bg-amber-200 disabled:opacity-60 dark:bg-amber-500/15 dark:text-amber-200">
                            {isAnalyzing ? <Loader2 className="h-4 w-4 animate-spin" /> : <TrendingUp className="h-4 w-4" />}
                        </button>
                    </div>
                </div>
                <div className="mt-4 grid gap-4 md:grid-cols-2">
                    <LegacyFact
                        label="持仓期最高"
                        value={position.max_price_during_hold ? `${currencySymbol}${Number(position.max_price_during_hold).toFixed(2)}` : '-'}
                    />
                    <LegacyFact
                        label="持仓期最低"
                        value={position.min_price_during_hold ? `${currencySymbol}${Number(position.min_price_during_hold).toFixed(2)}` : '-'}
                    />
                </div>
                {position.drift_analysis?.has_planned_data && (
                    <div className="mt-4 grid gap-3 md:grid-cols-4">
                        <LegacyFact label="计划入场价" value={`${currencySymbol}${Number(position.planned_entry_price || 0).toFixed(2)}`} />
                        <LegacyFact label="实际入场价" value={`${currencySymbol}${Number(position.average_entry_price || 0).toFixed(2)}`} />
                        <LegacyFact label="入场偏移" value={`${position.drift_analysis.entry_drift_pct || 0}%`} />
                        <LegacyFact label="执行质量" value={position.drift_analysis.execution_quality || '未记录'} />
                    </div>
                )}
                {position.checklist_responses && Object.keys(position.checklist_responses).length > 0 && (
                    <div className="mt-4 rounded-2xl border border-amber-200/70 bg-amber-50/80 p-4 dark:border-amber-900/60 dark:bg-amber-950/20">
                        <p className="text-xs font-bold uppercase tracking-[0.16em] text-amber-800 dark:text-amber-200">Legacy checklist</p>
                        <div className="mt-3 flex flex-wrap gap-2">
                            {Object.entries(position.checklist_responses).map(([id, checked]) => (
                                <span key={id} className={`rounded-full px-2.5 py-1 text-xs font-semibold ${checked ? 'bg-emerald-100 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300' : 'bg-red-100 text-red-700 dark:bg-red-950/40 dark:text-red-300'}`}>
                                    #{id} {checked ? 'pass' : 'miss'}
                                </span>
                            ))}
                        </div>
                    </div>
                )}
            </div>

            <div className="mt-5 rounded-3xl border border-amber-200 bg-white/70 dark:border-amber-900/60 dark:bg-slate-950/30">
                <div className="border-b border-amber-200 p-5 dark:border-amber-900/60">
                    <h3 className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.18em] text-amber-900 dark:text-amber-100">
                        <Calendar className="h-4 w-4" />
                        Legacy trade batches ({sortedBatches.length})
                    </h3>
                </div>
                <div className="divide-y divide-amber-100 dark:divide-amber-900/40">
                    {sortedBatches.map((batch) => (
                        <div key={batch.id} className="flex items-start justify-between gap-4 p-4">
                            <div className="flex items-start gap-3">
                                <div className={`flex h-10 w-10 items-center justify-center rounded-xl ${batch.type === 'ENTRY' ? 'bg-emerald-100 dark:bg-emerald-900/30' : 'bg-red-100 dark:bg-red-900/30'}`}>
                                    {batch.type === 'ENTRY'
                                        ? <ArrowUpCircle className="h-5 w-5 text-emerald-500" />
                                        : <ArrowDownCircle className="h-5 w-5 text-red-500" />}
                                </div>
                                <div>
                                    <p className="font-semibold text-slate-900 dark:text-slate-100">
                                        {batch.type === 'ENTRY' ? '加仓' : '平仓'}
                                        <span className="ml-2 text-slate-500">{Number(batch.quantity).toLocaleString()} @ {currencySymbol}{Number(batch.price).toFixed(2)}</span>
                                    </p>
                                    <p className="mt-1 text-xs text-slate-500">{new Date(batch.time).toLocaleString('zh-CN')}</p>
                                    {batch.reason && (
                                        <p className="mt-2 text-sm text-slate-600 dark:text-slate-400">
                                            <MessageSquare className="mr-1 inline h-3 w-3" />
                                            {batch.reason}
                                        </p>
                                    )}
                                </div>
                            </div>
                            {legacyBatchMutationState.canMutate ? (
                                <button type="button" onClick={() => onEditBatch(batch)} title={legacyBatchMutationState.reason} className="rounded-lg p-2 text-slate-400 transition-colors hover:bg-amber-100 hover:text-amber-700 dark:hover:bg-amber-950/40">
                                    <Edit3 className="h-4 w-4" />
                                </button>
                            ) : (
                                <span title={legacyBatchMutationState.reason} className="rounded-full border border-amber-200 bg-amber-50 px-2.5 py-1 text-[11px] font-bold uppercase tracking-[0.14em] text-amber-700 dark:border-amber-900 dark:bg-amber-950/40 dark:text-amber-200">
                                    {legacyBatchMutationState.label}
                                </span>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            {legacyReviewDisplayState.shouldDisplay && position.trade_review && (
                <div className="mt-5 rounded-3xl border border-amber-200 bg-white/70 p-5 dark:border-amber-900/60 dark:bg-slate-950/30">
                    <h3 className="text-sm font-black uppercase tracking-[0.18em] text-amber-900 dark:text-amber-100">{legacyReviewDisplayState.label}</h3>
                    <p className="mt-2 text-xs font-semibold text-amber-800 dark:text-amber-200">
                        Legacy review is read-only migration context; canonical review lives in PositionEvent narrative.
                    </p>
                    <p className="mt-2 rounded-xl border border-amber-200 bg-amber-50 px-3 py-2 text-xs text-amber-800 dark:border-amber-900 dark:bg-amber-950/30 dark:text-amber-200">
                        {legacyReviewDisplayState.reason}
                    </p>
                    <p className="mt-4 whitespace-pre-wrap text-sm leading-6 text-slate-600 dark:text-slate-300">{position.trade_review}</p>
                </div>
            )}

            {position.lessons && position.lessons.length > 0 && (
                <div className="mt-5 rounded-3xl border border-amber-200 bg-white/70 p-5 dark:border-amber-900/60 dark:bg-slate-950/30">
                    <h3 className="flex items-center gap-2 text-sm font-black uppercase tracking-[0.18em] text-amber-900 dark:text-amber-100">
                        <Award className="h-4 w-4" />
                        Legacy lessons
                    </h3>
                    <div className="mt-3 flex flex-wrap gap-2">
                        {position.lessons.map((lesson, index) => (
                            <span key={`${lesson}-${index}`} className="rounded-full bg-amber-100 px-3 py-1 text-sm text-amber-700 dark:bg-amber-900/30 dark:text-amber-300">
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
        <div className="rounded-2xl border border-amber-200 bg-white/80 p-4 dark:border-amber-900/60 dark:bg-slate-950/30">
            <p className="text-[11px] font-bold uppercase tracking-[0.16em] text-amber-700 dark:text-amber-300">{label}</p>
            <p className={`mt-2 text-lg font-black text-slate-950 dark:text-white ${className}`}>{value}</p>
        </div>
    )
}

function LegacyFact({ label, value }: { label: string; value: string }) {
    return (
        <div>
            <p className="text-xs text-slate-500">{label}</p>
            <p className="mt-1 font-semibold text-slate-900 dark:text-slate-100">{value}</p>
        </div>
    )
}
