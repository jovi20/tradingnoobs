import { Bot, ExternalLink, RefreshCw, ShieldCheck, Sparkles } from 'lucide-react'

import {
    assertSupportedChartSchema,
    buildAuditableInsightCards,
    type AuditableInsightCard,
    type InsightRun,
} from '@/lib/insightArtifacts'

interface EvidenceLinkedInsightSidecarProps {
    runs?: InsightRun[]
    isLoading: boolean
    error: string | null
    title?: string
    limit?: number
    onRefresh: () => void | Promise<unknown>
}

export function EvidenceLinkedInsightSidecar({
    runs = [],
    isLoading,
    error,
    title = '可审计 AI 洞察',
    limit = 4,
    onRefresh,
}: EvidenceLinkedInsightSidecarProps) {
    const cards = buildAuditableInsightCards(runs, limit)

    return (
        <div className="card p-4">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <p className="text-xs font-semibold text-ink-faint">证据链洞察</p>
                    <h2 className="mt-1 text-lg font-semibold">{title}</h2>
                    <p className="mt-1 text-sm text-ink-muted">
                        这里只展示带有产物记录、来源引用和证据引用的 AI 结果。
                    </p>
                </div>
                <button
                    type="button"
                    onClick={() => onRefresh()}
                    className="rounded-md border border-line p-2 text-ink-muted transition-colors hover:bg-panel-subtle"
                    aria-label={`刷新${title}`}
                >
                    <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                </button>
            </div>

            {error && (
                <div className="mt-4 rounded-md border border-loss/30 bg-loss/10 px-3 py-2 text-sm text-loss">
                    洞察产物加载失败：{error}
                </div>
            )}

            <div className="mt-4 space-y-3">
                {cards.length > 0 ? (
                    cards.map((card) => (
                        <ArtifactCard key={card.artifact.public_id} card={card} />
                    ))
                ) : (
                    <div className="rounded-md border border-dashed border-line p-4 text-sm text-ink-muted">
                        暂无可审计的 AI 洞察。新产物生成后会出现在这里。
                    </div>
                )}
            </div>
        </div>
    )
}

function ArtifactCard({ card }: { card: AuditableInsightCard }) {
    return (
        <div className="rounded-lg border border-line bg-panel-subtle p-4">
            <div className="flex items-start justify-between gap-3">
                <div>
                    <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wide text-ink-faint">
                        <Sparkles className="w-3.5 h-3.5" />
                        {card.artifactType}
                    </div>
                    <p className="mt-2 font-semibold text-ink">{card.title}</p>
                </div>
                <Bot className="w-4 h-4 text-ink-faint" />
            </div>

            <p className="mt-3 text-sm leading-6 text-ink-soft">{card.primaryContent}</p>

            <div className="mt-3 flex flex-wrap gap-2">
                <span className="rounded-full bg-panel-subtle px-2.5 py-1 text-[11px] font-medium text-ink-soft">
                    {card.run.run_type}
                </span>
                {assertSupportedChartSchema(card.chartSchema) && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-profit/10 px-2.5 py-1 text-[11px] font-medium text-profit">
                        <ShieldCheck className="w-3 h-3" />
                        {card.chartSchema?.schema_version}
                    </span>
                )}
            </div>

            {card.evidenceRefs.length > 0 && (
                <div className="mt-3 flex flex-wrap gap-2">
                    {card.evidenceRefs.map((ref) => (
                        <span
                            key={ref}
                            className="rounded-full border border-line px-2.5 py-1 text-[11px] text-ink-muted"
                        >
                            {ref}
                        </span>
                    ))}
                </div>
            )}

            {card.sourceRefs.length > 0 && (
                <p className="mt-3 text-xs text-ink-faint">
                    来源引用：{card.sourceRefs.join(', ')}
                </p>
            )}

            <a
                href={card.href}
                className="mt-3 inline-flex items-center gap-1 text-xs font-semibold text-ai transition-opacity hover:opacity-80"
            >
                打开 AI 洞察
                <ExternalLink className="w-3 h-3" />
            </a>
        </div>
    )
}
