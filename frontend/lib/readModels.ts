export const homeReadModelPath = '/api/v1/read-models/home' as const

export const lifecycleReadModelPath = (positionPublicId: string) =>
    `/api/v1/read-models/trading-positions/${positionPublicId}/lifecycle` as const

export type TrustFreshness = 'FRESH' | 'DELAYED' | 'STALE' | 'DEGRADED'
export type TrustSource = 'MANUAL' | 'IMPORTED' | 'SYNCED' | 'DERIVED' | 'AI_GENERATED' | 'EXTERNAL'
export type TrustMaturity = 'INSUFFICIENT_SAMPLE' | 'EARLY_SIGNAL' | 'STABLE' | 'DERIVED'
export type TrustValueStatus = 'ESTIMATED' | 'FINAL'
export type TrustTone = 'ok' | 'watch' | 'danger' | 'muted'

export interface TrustMeta {
    as_of: string
    freshness: TrustFreshness
    source: TrustSource | string
    maturity: TrustMaturity | string
    value_status: TrustValueStatus | string
    generated_by: string
    source_refs: string[]
}

export interface TimelineEvent {
    public_id: string
    type: string
    occurred_at: string
    subject: string
    summary: string
    impact: Record<string, number | string | null>
    trust_meta: TrustMeta
    linked_object_public_id: string
    evidence_refs: string[]
}

export interface ReviewInboxItem {
    kind: string
    severity: 'INFO' | 'LOW' | 'MEDIUM' | 'HIGH' | 'BLOCKING' | string
    summary: string
    reason: string
    recommended_action: string
    linked_object_public_id: string
    due_state: string
    trust_meta: TrustMeta
}

export interface HomeReadModel {
    meta: TrustMeta
    timeline_events: TimelineEvent[]
    review_inbox: ReviewInboxItem[]
    context_rail: {
        open_positions: number
        closed_positions: number
        [key: string]: number | string | boolean | null
    }
}

export interface LifecycleNode {
    type: string
    occurred_at: string
    position_public_id: string
    event_public_id: string
    decision_fields: Record<string, unknown>
    execution_fields: Record<string, unknown>
    ledger_refs: string[]
    evidence_refs: string[]
}

export interface EvidenceItem {
    public_id: string
    kind: string
    source_name: string
    source_url_or_ref: string | null
    captured_at: string
    summary: string
    linked_tickers: string[]
    confidence: string
    invalidates_if: string | null
    linked_object_public_id?: string
}

export interface NarrativeSignal {
    public_id: string
    signal_type: string
    direction: string
    strength: string
    sample_size: number
    time_window: string | null
    summary?: string
    linked_evidence_public_ids: string[]
    trust_meta: TrustMeta
}

export interface LifecycleReadModel {
    meta: TrustMeta
    position_public_id: string
    lifecycle_nodes: LifecycleNode[]
    ledger_refs: string[]
    evidence_items: EvidenceItem[]
    narrative_signals: NarrativeSignal[]
}

export function trustToneForFreshness(freshness: TrustFreshness | string): TrustTone {
    if (freshness === 'FRESH') return 'ok'
    if (freshness === 'DELAYED') return 'watch'
    if (freshness === 'STALE' || freshness === 'DEGRADED') return 'danger'
    return 'muted'
}

export function formatTrustTimestamp(value: string): string {
    const date = new Date(value)
    if (Number.isNaN(date.getTime())) return value
    return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit',
    })
}

export function buildMockHomeReadModel({ nowIso }: { nowIso: string }): HomeReadModel {
    const meta: TrustMeta = {
        as_of: nowIso,
        freshness: 'FRESH',
        source: 'DERIVED',
        maturity: 'EARLY_SIGNAL',
        value_status: 'FINAL',
        generated_by: 'frontend_task4_mock_adapter',
        source_refs: ['mock:task4-home-read-model'],
    }

    return {
        meta,
        timeline_events: [
            {
                public_id: '01JTIMELINEOPEN0000000000',
                type: 'OPEN',
                occurred_at: nowIso,
                subject: 'AAPL',
                summary: 'OPEN 10 AAPL @ 195.20',
                impact: {
                    quantity: 10,
                    price: 195.2,
                    realized_pnl_net: null,
                },
                trust_meta: meta,
                linked_object_public_id: '01JPOSITIONTASK4000000000',
                evidence_refs: ['01JTIMELINEOPEN0000000000-THESIS'],
            },
        ],
        review_inbox: [
            {
                kind: 'MISSING_THESIS',
                severity: 'MEDIUM',
                summary: '补齐开仓 thesis',
                reason: '这笔交易已有执行记录，但还缺少可复盘的入场假设。',
                recommended_action: '在进入下一次复盘前补齐 thesis 和 invalidation rule。',
                linked_object_public_id: '01JPOSITIONTASK4000000000',
                due_state: 'OPEN',
                trust_meta: meta,
            },
        ],
        context_rail: {
            open_positions: 1,
            closed_positions: 0,
        },
    }
}
