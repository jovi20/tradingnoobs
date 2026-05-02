export type FreshnessStatus = 'FRESH' | 'DELAYED' | 'STALE' | 'DEGRADED'
export type DataSource = 'MANUAL' | 'IMPORTED' | 'SYNCED' | 'DERIVED' | 'AI_GENERATED'
export type DataMaturity = 'INSUFFICIENT_SAMPLE' | 'EARLY_SIGNAL' | 'STABLE'
export type ValueStatus = 'ESTIMATED' | 'FINAL'

export interface TrustMeta {
    as_of: string
    generated_at?: string
    freshness: FreshnessStatus
    source: DataSource
    maturity?: DataMaturity
    value_status?: ValueStatus
    source_refs?: string[]
    note?: string
}

export interface ReadModelEnvelope<T> {
    data: T
    meta: TrustMeta
}

export type TimelineHomePageState = 'ZERO' | 'EMPTY_CONFIGURED' | 'SMALL_DATA' | 'READY'
export type TimelineView = 'ALL' | 'TRADING' | 'REVIEW' | 'AI' | 'EXCEPTION'
export type ReviewInboxKind =
    | 'MISSING_THESIS'
    | 'MISSING_REVIEW'
    | 'CHECKLIST_MISS'
    | 'LOSING_STREAK'
    | 'DATA_STALE'
    | 'SYNC_EXCEPTION'
export type InboxSeverity = 'INFO' | 'NOTICE' | 'WARNING' | 'CRITICAL'
export type RecommendedActionKind =
    | 'OPEN_POSITION_DETAIL'
    | 'START_REVIEW'
    | 'COMPLETE_THESIS'
    | 'OPEN_SYNC_STATUS'
    | 'OPEN_INSIGHT'
export type LinkedObjectType = 'TRADING_POSITION' | 'POSITION_EVENT' | 'ACCOUNT' | 'INSIGHT_ARTIFACT'
export type TimelineGroupType = 'DAY' | 'WEEK_BUCKET'
export type TimelineEventType =
    | 'OPEN'
    | 'ADD'
    | 'REDUCE'
    | 'CLOSE'
    | 'REVIEW_COMPLETED'
    | 'AI_INSIGHT'
    | 'CHECKLIST_MISS'
    | 'LOSING_STREAK_ALERT'
    | 'DATA_STALE'
    | 'SYNC_EXCEPTION'

export interface SummaryBar {
    period_label: string
    trade_count: number
    review_completion_rate: number | null
    net_equity_change: number | null
    priority_alert_count: number
    trust?: TrustMeta
}

export interface ReviewInboxAction {
    kind: RecommendedActionKind
    label: string
    href: string
}

export interface LinkedObjectRef {
    object_type: LinkedObjectType
    public_id: string
    label: string
    href: string
}

export interface ReviewInboxItem {
    public_id: string
    kind: ReviewInboxKind
    severity: InboxSeverity
    summary: string
    reason: string
    recommended_action: ReviewInboxAction
    linked_object: LinkedObjectRef
    due_at?: string
    occurred_at: string
    trust?: TrustMeta
}

export interface ReviewInbox {
    counts: {
        total: number
        high_priority: number
    }
    items: ReviewInboxItem[]
    trust?: TrustMeta
}

export interface TimelineImpactValue {
    amount?: number
    currency?: string
    percentage?: number
}

export interface TimelineInstrumentRef {
    asset_label: string
    instrument_label: string
    symbol: string
    href: string
}

export interface TimelineAccountRef {
    public_id: string
    label: string
}

export interface ExecutionDriftSummary {
    has_drift: boolean
    entry_drift_pct?: number
    execution_quality?: string
}

export interface TimelineAiAnnotation {
    artifact_public_id: string
    summary: string
    href: string
}

export interface TimelineEventCard {
    event_public_id: string
    thread_public_id: string
    event_type: TimelineEventType
    occurred_at: string
    headline: string
    summary: string
    impact_value?: TimelineImpactValue
    instrument: TimelineInstrumentRef
    account?: TimelineAccountRef
    tags?: string[]
    emotion?: string
    confidence?: number
    checklist_summary?: string
    thesis_excerpt?: string
    invalidation_excerpt?: string
    execution_drift?: ExecutionDriftSummary
    ai_annotation?: TimelineAiAnnotation
    href: string
    trust?: TrustMeta
}

export interface TimelineGroup {
    group_key: string
    group_label: string
    group_type: TimelineGroupType
    items: TimelineEventCard[]
}

export interface TimelineFeed {
    active_view: TimelineView
    next_cursor?: string
    groups: TimelineGroup[]
    trust?: TrustMeta
}

export interface WeeklyDisciplineSnapshot {
    headline: string
    summary: string
    trust?: TrustMeta
}

export interface ContextRailSelectedObject {
    object_type: LinkedObjectType
    public_id: string
    title: string
    subtitle?: string
    href: string
}

export interface ContextRailQuickFilter {
    key: string
    label: string
    active: boolean
}

export interface RelatedContextItem {
    label: string
    href: string
}

export interface ContextRail {
    selected_object?: ContextRailSelectedObject
    weekly_discipline_snapshot?: WeeklyDisciplineSnapshot
    quick_filters: ContextRailQuickFilter[]
    related_items?: RelatedContextItem[]
    trust?: TrustMeta
}

export interface TimelineHomeData {
    page_state: TimelineHomePageState
    summary_bar: SummaryBar
    review_inbox: ReviewInbox
    timeline: TimelineFeed
    context_rail: ContextRail
}

export type TimelineHomeResponse = ReadModelEnvelope<TimelineHomeData>

export type LifecycleReviewStatus = 'OPEN' | 'CLOSED_PENDING_REVIEW' | 'REVIEWED'
export type LifecycleNodeType = 'OPEN' | 'ADD' | 'REDUCE' | 'CLOSE' | 'REVIEW' | 'AI_CONCLUSION'

export interface LifecyclePositionSummary {
    public_id: string
    title: string
    status: 'OPEN' | 'CLOSED' | 'ARCHIVED' | 'ERROR'
    side: 'LONG' | 'SHORT'
    account: {
        public_id: string
        label: string
    }
    asset: {
        symbol: string
        asset_label: string
        instrument_label: string
    }
    opened_at: string
    closed_at?: string
    realized_pnl_gross?: number
    realized_pnl_net?: number
    total_fees?: number
    holding_period_seconds?: number
    pnl_basis: {
        cost_basis_method: string
        realized_definition: string
        unrealized_definition: string
        fee_treatment: string
        fx_treatment: string
    }
}

export interface LifecycleThesisBlock {
    source_event_public_id?: string
    thesis?: string
    invalidation_rule?: string
    planned_exit_rule?: string
    sizing_rationale?: string
    expected_holding_period?: string
    checklist_snapshot?: Array<{
        label: string
        checked: boolean
    }>
}

export interface LifecycleNode {
    node_public_id: string
    node_type: LifecycleNodeType
    occurred_at: string
    title: string
    summary: string
    related_event_public_id?: string
    quantities?: {
        quantity?: number
        price?: number
        currency?: string
    }
    pnl_delta?: {
        realized_gross?: number
        realized_net?: number
    }
    emotion?: string
    confidence?: number
    note?: string
    evidence_refs?: Array<{
        ref_type: string
        public_id: string
        label: string
        href: string
    }>
    href?: string
}

export interface LifecycleResultSummary {
    headline: string
    summary: string
    key_numbers: Array<{
        label: string
        value: string
    }>
}

export interface LifecycleExecutionQuality {
    execution_quality?: string
    drift_summary?: string
    checklist_miss_count?: number
}

export interface LifecycleEmotionPath {
    points: Array<{
        occurred_at: string
        emotion: string
        confidence?: number
    }>
}

export interface LifecycleLedgerSummary {
    account_currency: string
    cash_effects: Array<{
        entry_public_id: string
        entry_type: string
        amount: number
        currency: string
        amount_in_account_ccy?: number
        occurred_at: string
    }>
    total_fees?: number
    total_dividends?: number
    total_adjustments?: number
}

export interface LifecycleEvidenceList {
    items: Array<{
        ref_type: string
        public_id: string
        label: string
        href: string
    }>
}

export interface LifecycleAiSidecar {
    items: Array<{
        insight_run_public_id?: string
        insight_artifact_public_id?: string
        title?: string
        conclusion?: string
        coverage_summary?: string
        confidence_label?: string
        recommended_action?: string
        evidence_refs?: Array<{
            ref_type: string
            public_id: string
            label: string
            href: string
        }>
        href?: string
    }>
}

export interface LifecycleDetailData {
    review_status: LifecycleReviewStatus
    position_summary: LifecyclePositionSummary
    thesis_block: LifecycleThesisBlock
    lifecycle_thread: {
        nodes: LifecycleNode[]
    }
    result_summary: LifecycleResultSummary
    execution_quality: LifecycleExecutionQuality
    discipline_profile?: {
        headline: string
        summary: string
    } | null
    emotion_path?: LifecycleEmotionPath | null
    ledger_summary: LifecycleLedgerSummary
    evidence_list: LifecycleEvidenceList
    ai_sidecar: LifecycleAiSidecar
}

export type LifecycleDetailResponse = ReadModelEnvelope<LifecycleDetailData>
