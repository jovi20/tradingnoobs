"""
Trading Noobs Backend - Pydantic Schemas
"""
from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator
from typing import Any, Dict, Generic, List, Literal, Optional, TypeVar, Union
from datetime import datetime, date
from decimal import Decimal
from enum import Enum

from app_config.release_contract import (
    JOURNAL_BETA_CONTRACT,
    RAW_ASSET_TYPE_INPUT_PATTERN,
    RAW_CURRENCY_INPUT_PATTERN,
    RAW_INSTRUMENT_TYPE_INPUT_PATTERN,
    RAW_MARKET_INPUT_PATTERN,
)


# ============== Enums ==============



class StrategyStatusEnum(str, Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class PositionDirectionEnum(str, Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatusEnum(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class BatchTypeEnum(str, Enum):
    ENTRY = "ENTRY"
    EXIT = "EXIT"


class AssetCoreTypeEnum(str, Enum):
    STOCK = "STOCK"
    BOND = "BOND"
    FUND = "FUND"
    COMMODITY = "COMMODITY"
    FX = "FX"
    DERIVATIVE = "DERIVATIVE"
    CRYPTO = "CRYPTO"


class AssetMarketEnum(str, Enum):
    US = "US"
    HK = "HK"
    A_SHARE = "A_SHARE"
    CN_OTC = "CN_OTC"
    FOREX = "FOREX"
    COMMODITY_FUT = "COMMODITY_FUT"
    UK = "UK"
    CRYPTO = "CRYPTO"


class AssetCurrencyEnum(str, Enum):
    USD = "USD"
    HKD = "HKD"
    CNY = "CNY"
    EUR = "EUR"
    GBP = "GBP"


class AssetRiskLevelEnum(str, Enum):
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    GROWTH = "GROWTH"
    AGGRESSIVE = "AGGRESSIVE"
    HEDGE = "HEDGE"


class FreshnessStatusEnum(str, Enum):
    FRESH = "FRESH"
    DELAYED = "DELAYED"
    STALE = "STALE"
    DEGRADED = "DEGRADED"


class DataSourceEnum(str, Enum):
    MANUAL = "MANUAL"
    IMPORTED = "IMPORTED"
    SYNCED = "SYNCED"
    DERIVED = "DERIVED"
    AI_GENERATED = "AI_GENERATED"


class MaturityEnum(str, Enum):
    INSUFFICIENT_SAMPLE = "INSUFFICIENT_SAMPLE"
    EARLY_SIGNAL = "EARLY_SIGNAL"
    STABLE = "STABLE"


class ValueStatusEnum(str, Enum):
    ESTIMATED = "ESTIMATED"
    FINAL = "FINAL"


class TimelineHomePageStateEnum(str, Enum):
    ZERO = "ZERO"
    EMPTY_CONFIGURED = "EMPTY_CONFIGURED"
    SMALL_DATA = "SMALL_DATA"
    READY = "READY"


class TimelineViewEnum(str, Enum):
    ALL = "ALL"
    TRADING = "TRADING"
    REVIEW = "REVIEW"
    AI = "AI"
    EXCEPTION = "EXCEPTION"


class ReviewInboxKindEnum(str, Enum):
    MISSING_THESIS = "MISSING_THESIS"
    MISSING_REVIEW = "MISSING_REVIEW"
    CHECKLIST_MISS = "CHECKLIST_MISS"
    LOSING_STREAK = "LOSING_STREAK"
    DATA_STALE = "DATA_STALE"
    SYNC_EXCEPTION = "SYNC_EXCEPTION"
    DAILY_LOSS_LIMIT = "DAILY_LOSS_LIMIT"
    PORTFOLIO_CONCENTRATION = "PORTFOLIO_CONCENTRATION"
    DRAWDOWN_ALERT = "DRAWDOWN_ALERT"


class InboxSeverityEnum(str, Enum):
    INFO = "INFO"
    NOTICE = "NOTICE"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class RecommendedActionKindEnum(str, Enum):
    OPEN_POSITION_DETAIL = "OPEN_POSITION_DETAIL"
    START_REVIEW = "START_REVIEW"
    COMPLETE_THESIS = "COMPLETE_THESIS"
    OPEN_SYNC_STATUS = "OPEN_SYNC_STATUS"
    OPEN_INSIGHT = "OPEN_INSIGHT"
    OPEN_DASHBOARD = "OPEN_DASHBOARD"


class LinkedObjectTypeEnum(str, Enum):
    TRADING_POSITION = "TRADING_POSITION"
    POSITION_EVENT = "POSITION_EVENT"
    ACCOUNT = "ACCOUNT"
    INSIGHT_ARTIFACT = "INSIGHT_ARTIFACT"
    PORTFOLIO = "PORTFOLIO"


class TimelineGroupTypeEnum(str, Enum):
    DAY = "DAY"
    WEEK_BUCKET = "WEEK_BUCKET"


class TimelineEventTypeEnum(str, Enum):
    OPEN = "OPEN"
    ADD = "ADD"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"
    REVIEW_COMPLETED = "REVIEW_COMPLETED"
    AI_INSIGHT = "AI_INSIGHT"
    CHECKLIST_MISS = "CHECKLIST_MISS"
    LOSING_STREAK_ALERT = "LOSING_STREAK_ALERT"
    DATA_STALE = "DATA_STALE"
    SYNC_EXCEPTION = "SYNC_EXCEPTION"


T = TypeVar("T")


class TrustMeta(BaseModel):
    as_of: str
    generated_at: Optional[str] = None
    freshness: FreshnessStatusEnum
    source: DataSourceEnum
    maturity: Optional[MaturityEnum] = None
    value_status: Optional[ValueStatusEnum] = None
    source_refs: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class RiskRecommendedAction(BaseModel):
    kind: str
    label: str
    href: str


class RiskTrustMeta(BaseModel):
    freshness: FreshnessStatusEnum
    source: DataSourceEnum
    value_status: Optional[ValueStatusEnum] = None
    source_refs: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class RiskAlert(BaseModel):
    public_id: str
    kind: str
    severity: InboxSeverityEnum
    summary: str
    reason: str
    recommended_action: RiskRecommendedAction
    source_refs: List[str] = Field(default_factory=list)
    trust: RiskTrustMeta


class RiskPortfolioSummary(BaseModel):
    gross_exposure: float = 0.0
    net_liquidation_value: float = 0.0
    daily_pnl: Optional[float] = None
    daily_pnl_percent: Optional[float] = None
    max_drawdown: Optional[float] = None


class RiskSummaryResponse(BaseModel):
    as_of: str
    base_currency: str
    portfolio: RiskPortfolioSummary
    alerts: List[RiskAlert] = Field(default_factory=list)
    trust: RiskTrustMeta


class ReadModelEnvelope(BaseModel, Generic[T]):
    data: T
    meta: TrustMeta


class SummaryBar(BaseModel):
    period_label: str
    trade_count: int
    review_completion_rate: Optional[float] = None
    priority_alert_count: int
    trust: Optional[TrustMeta] = None


class ReviewInboxCounts(BaseModel):
    total: int
    high_priority: int


class ReviewInboxAction(BaseModel):
    kind: RecommendedActionKindEnum
    label: str
    href: str


class LinkedObjectRef(BaseModel):
    object_type: LinkedObjectTypeEnum
    public_id: str
    label: str
    href: str


class ReviewInboxItem(BaseModel):
    public_id: str
    kind: ReviewInboxKindEnum
    severity: InboxSeverityEnum
    summary: str
    reason: str
    recommended_action: ReviewInboxAction
    linked_object: LinkedObjectRef
    due_at: Optional[str] = None
    occurred_at: str
    trust: Optional[TrustMeta] = None


class ReviewInbox(BaseModel):
    counts: ReviewInboxCounts
    items: List[ReviewInboxItem] = Field(default_factory=list)
    trust: Optional[TrustMeta] = None


class TimelineImpactValue(BaseModel):
    amount: Optional[float] = None
    currency: Optional[str] = None
    percentage: Optional[float] = None


class TimelineInstrumentRef(BaseModel):
    asset_label: str
    instrument_label: str
    symbol: str
    href: str


class TimelineAccountRef(BaseModel):
    public_id: str
    label: str


class ExecutionDriftSummary(BaseModel):
    has_drift: bool
    entry_drift_pct: Optional[float] = None
    execution_quality: Optional[str] = None


class TimelineAiAnnotation(BaseModel):
    artifact_public_id: str
    summary: str
    href: str


class TimelineEventCard(BaseModel):
    event_public_id: str
    thread_public_id: str
    event_type: TimelineEventTypeEnum
    occurred_at: str
    headline: str
    summary: str
    impact_value: Optional[TimelineImpactValue] = None
    instrument: TimelineInstrumentRef
    account: Optional[TimelineAccountRef] = None
    tags: List[str] = Field(default_factory=list)
    emotion: Optional[str] = None
    confidence: Optional[float] = None
    checklist_summary: Optional[str] = None
    thesis_excerpt: Optional[str] = None
    invalidation_excerpt: Optional[str] = None
    execution_drift: Optional[ExecutionDriftSummary] = None
    ai_annotation: Optional[TimelineAiAnnotation] = None
    href: str
    trust: Optional[TrustMeta] = None


class TimelineGroup(BaseModel):
    group_key: str
    group_label: str
    group_type: TimelineGroupTypeEnum
    items: List[TimelineEventCard] = Field(default_factory=list)


class TimelineFeed(BaseModel):
    active_view: TimelineViewEnum
    next_cursor: Optional[str] = None
    groups: List[TimelineGroup] = Field(default_factory=list)
    trust: Optional[TrustMeta] = None


class WeeklyDisciplineSnapshot(BaseModel):
    headline: str
    summary: str
    trust: Optional[TrustMeta] = None


class ContextRailSelectedObject(BaseModel):
    object_type: LinkedObjectTypeEnum
    public_id: str
    title: str
    subtitle: Optional[str] = None
    href: str


class ContextRailQuickFilter(BaseModel):
    key: str
    label: str
    active: bool


class RelatedContextItem(BaseModel):
    label: str
    href: str


class ContextRail(BaseModel):
    selected_object: Optional[ContextRailSelectedObject] = None
    weekly_discipline_snapshot: Optional[WeeklyDisciplineSnapshot] = None
    quick_filters: List[ContextRailQuickFilter] = Field(default_factory=list)
    related_items: List[RelatedContextItem] = Field(default_factory=list)
    trust: Optional[TrustMeta] = None


class TimelineHomeData(BaseModel):
    page_state: TimelineHomePageStateEnum
    summary_bar: SummaryBar
    review_inbox: ReviewInbox
    timeline: TimelineFeed
    context_rail: ContextRail


class TimelineHomeResponse(ReadModelEnvelope[TimelineHomeData]):
    pass


JournalTimelineView = Literal["ALL", "TRADING", "REVIEW", "EXCEPTION"]
JournalTimelineEventType = Literal[
    "OPEN",
    "ADD",
    "REDUCE",
    "CLOSE",
    "REVIEW_COMPLETED",
    "CHECKLIST_MISS",
    "LOSING_STREAK_ALERT",
]
JournalTimelineDataSource = Literal["MANUAL", "IMPORTED", "DERIVED"]
JournalReviewInboxKind = Literal[
    "MISSING_THESIS",
    "MISSING_REVIEW",
    "CHECKLIST_MISS",
    "LOSING_STREAK",
]
JournalRecommendedActionKind = Literal[
    "OPEN_POSITION_DETAIL",
    "START_REVIEW",
    "COMPLETE_THESIS",
]
JournalLinkedObjectType = Literal["TRADING_POSITION", "POSITION_EVENT", "ACCOUNT"]


class JournalTrustMeta(BaseModel):
    as_of: str
    generated_at: Optional[str] = None
    freshness: FreshnessStatusEnum
    source: JournalTimelineDataSource
    maturity: Optional[MaturityEnum] = None
    value_status: Optional[ValueStatusEnum] = None
    source_refs: List[str] = Field(default_factory=list)
    note: Optional[str] = None


class JournalSummaryBar(BaseModel):
    period_label: str
    trade_count: int
    review_completion_rate: Optional[float] = None
    priority_alert_count: int
    trust: Optional[JournalTrustMeta] = None


class JournalReviewInboxAction(BaseModel):
    kind: JournalRecommendedActionKind
    label: str
    href: str


class JournalLinkedObjectRef(BaseModel):
    object_type: JournalLinkedObjectType
    public_id: str
    label: str
    href: str


class JournalReviewInboxItem(BaseModel):
    public_id: str
    kind: JournalReviewInboxKind
    severity: InboxSeverityEnum
    summary: str
    reason: str
    recommended_action: JournalReviewInboxAction
    linked_object: JournalLinkedObjectRef
    due_at: Optional[str] = None
    occurred_at: str
    trust: Optional[JournalTrustMeta] = None


class JournalReviewInbox(BaseModel):
    counts: ReviewInboxCounts
    items: List[JournalReviewInboxItem] = Field(default_factory=list)
    trust: Optional[JournalTrustMeta] = None


class JournalTimelineEventCard(BaseModel):
    """Timeline event contract published when AI is outside the deployment ceiling."""

    event_public_id: str
    thread_public_id: str
    event_type: JournalTimelineEventType
    occurred_at: str
    headline: str
    summary: str
    impact_value: Optional[TimelineImpactValue] = None
    instrument: TimelineInstrumentRef
    account: Optional[TimelineAccountRef] = None
    tags: List[str] = Field(default_factory=list)
    emotion: Optional[str] = None
    confidence: Optional[float] = None
    checklist_summary: Optional[str] = None
    thesis_excerpt: Optional[str] = None
    invalidation_excerpt: Optional[str] = None
    execution_drift: Optional[ExecutionDriftSummary] = None
    href: str
    trust: Optional[JournalTrustMeta] = None


class JournalTimelineGroup(BaseModel):
    group_key: str
    group_label: str
    group_type: TimelineGroupTypeEnum
    items: List[JournalTimelineEventCard] = Field(default_factory=list)


class JournalTimelineFeed(BaseModel):
    active_view: JournalTimelineView
    next_cursor: Optional[str] = None
    groups: List[JournalTimelineGroup] = Field(default_factory=list)
    trust: Optional[JournalTrustMeta] = None


class JournalWeeklyDisciplineSnapshot(BaseModel):
    headline: str
    summary: str
    trust: Optional[JournalTrustMeta] = None


class JournalContextRailSelectedObject(BaseModel):
    object_type: JournalLinkedObjectType
    public_id: str
    title: str
    subtitle: Optional[str] = None
    href: str


class JournalContextRail(BaseModel):
    selected_object: Optional[JournalContextRailSelectedObject] = None
    weekly_discipline_snapshot: Optional[JournalWeeklyDisciplineSnapshot] = None
    quick_filters: List[ContextRailQuickFilter] = Field(default_factory=list)
    related_items: List[RelatedContextItem] = Field(default_factory=list)
    trust: Optional[JournalTrustMeta] = None


class JournalTimelineHomeData(BaseModel):
    page_state: TimelineHomePageStateEnum
    summary_bar: JournalSummaryBar
    review_inbox: JournalReviewInbox
    timeline: JournalTimelineFeed
    context_rail: JournalContextRail


class JournalTimelineHomeResponse(ReadModelEnvelope[JournalTimelineHomeData]):
    meta: JournalTrustMeta


class TradingPositionLifecycleResponse(ReadModelEnvelope[Dict[str, Any]]):
    pass


# ============== Auth Schemas ==============

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    invite_code: str = Field(..., min_length=1)
    timezone: str = Field(..., min_length=1, max_length=50)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserBase(BaseModel):
    email: EmailStr


class UserResponse(UserBase):
    id: int
    public_id: str
    status: str
    is_active: bool
    role: str
    last_login_at: Optional[datetime] = None
    locale: Optional[str] = None
    timezone: Optional[str] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserProfileUpdate(BaseModel):
    locale: Optional[str] = Field(None, max_length=20)
    timezone: Optional[str] = Field(None, max_length=50)


class InvitationCreate(BaseModel):
    expires_in_hours: int = Field(default=24, ge=1, le=168)


class InvitationResponse(BaseModel):
    public_id: str
    expires_at: datetime
    redeemed_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvitationCreatedResponse(InvitationResponse):
    code: str


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)


class PasswordChangeResponse(BaseModel):
    message: str
    active_sessions_revoked: bool


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None




# ============== Strategy Schemas ==============

class StrategyCreate(BaseModel):
    name: str = Field(..., max_length=100)
    description: Optional[str] = None
    entry_rules: Optional[str] = None
    exit_rules: Optional[str] = None
    risk_rules: Optional[str] = None
    symbols: Optional[List[str]] = []
    checklist_items: Optional[List[dict]] = []  # [{"id": 1, "label": "...", "category": "entry", "required": True}, ...]


class StrategyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    entry_rules: Optional[str] = None
    exit_rules: Optional[str] = None
    risk_rules: Optional[str] = None
    symbols: Optional[List[str]] = None
    status: Optional[StrategyStatusEnum] = None
    checklist_items: Optional[List[dict]] = None


class StrategyResponse(BaseModel):
    id: int
    user_id: int
    name: str
    description: Optional[str]
    entry_rules: Optional[str]
    exit_rules: Optional[str]
    risk_rules: Optional[str]
    symbols: List[str]
    status: StrategyStatusEnum
    checklist_items: Optional[List[dict]] = []
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True


# ============== Daily Summary Schemas ==============

class DailySummaryCreate(BaseModel):
    date: date
    market_mood: Optional[str] = None
    personal_mood: Optional[str] = None
    summary: Optional[str] = None


class DailySummaryUpdate(BaseModel):
    market_mood: Optional[str] = None
    personal_mood: Optional[str] = None
    summary: Optional[str] = None


class DailySummaryResponse(BaseModel):
    id: int
    user_id: int
    date: date
    market_mood: Optional[str]
    personal_mood: Optional[str]
    summary: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============== Journal Entry Schemas ==============

class JournalEntryCreate(BaseModel):
    date: date
    content: str = Field(..., max_length=500)  # 每条限制500字


class JournalEntryUpdate(BaseModel):
    content: Optional[str] = Field(None, max_length=500)


class JournalEntryResponse(BaseModel):
    id: int
    user_id: int
    date: date
    content: str
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True

# ============== AI Summary Schemas ==============

class AISummaryResponse(BaseModel):
    id: int
    user_id: int
    date: date
    content: str
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============== User Settings Schemas ==============


class UserSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    theme: Optional[str] = Field(None, pattern="^(light|dark|system)$")
    up_color: Optional[str] = Field(None, pattern="^(GREEN|RED)$")
    display_currency: Literal["USD"] = "USD"


class UserSettingsResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    theme: str
    up_color: str = "GREEN"
    display_currency: Literal["USD"] = "USD"


class BrokerSyncRequest(BaseModel):
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class BrokerConnectionTestResponse(BaseModel):
    ok: bool
    provider: str
    message: str
    reference_code: Optional[str] = None


class BrokerSyncRunResponse(BaseModel):
    public_id: str
    provider: str
    market_type: Optional[str]
    status: str
    requested_start_date: Optional[date]
    requested_end_date: Optional[date]
    records_fetched: int
    records_inserted: int
    records_skipped: int
    error_message: Optional[str]
    metadata_json: Optional[Dict[str, Any]] = None
    started_at: Optional[datetime]
    finished_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class BrokerExecutionResponse(BaseModel):
    public_id: str
    provider: str
    market_type: Optional[str]
    account_ref: Optional[str]
    symbol: str
    side: str
    quantity: Decimal
    price: Decimal
    trade_time: datetime
    currency: Optional[str]
    commission: Optional[Decimal]
    commission_currency: Optional[str]
    external_trade_id: str
    external_order_id: Optional[str]
    import_status: str
    created_at: datetime

    class Config:
        from_attributes = True


# ============== Analysis Schemas ==============

class AnalysisType(str, Enum):
    HOLDING_PERIOD = "holding_period"
    LOSING_STREAK = "losing_streak"
    EMOTION_PNL = "emotion_pnl"
    CHECKLIST_EFFECT = "checklist_effect"
    STRATEGY_HEALTH = "strategy_health"


class AnalysisRequest(BaseModel):
    analysis_type: AnalysisType
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    @model_validator(mode="after")
    def validate_date_range(self):
        if (self.start_date is None) != (self.end_date is None):
            raise ValueError("start_date and end_date must be supplied together")

        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValueError("start_date must be before or equal to end_date")
            if (self.end_date - self.start_date).days + 1 > 366:
                raise ValueError("analysis date range cannot exceed 366 inclusive days")

        return self


class AnalysisResponse(BaseModel):
    analysis_type: AnalysisType
    raw_data: dict
    ai_insights: Optional[str]
    created_at: datetime


# ============== Market Data Schemas ==============

class MarketQuoteTrustMeta(BaseModel):
    freshness: str
    degraded: bool = False
    degraded_reason: Optional[str] = None
    source_refs: List[str] = Field(default_factory=list)
    as_of: Optional[datetime] = None


class MarketQuoteResponse(BaseModel):
    symbol: str
    asset_type: Optional[str] = None
    quote: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None
    freshness: str
    degraded: bool = False
    degraded_reason: Optional[str] = None
    source_refs: List[str] = Field(default_factory=list)
    as_of: Optional[datetime] = None
    error: Optional[str] = None
    trust: MarketQuoteTrustMeta


class MarketValidationResponse(BaseModel):
    valid: bool
    symbol: str
    asset_type: Optional[str] = None
    price: Optional[float] = None
    name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    provider: Optional[str] = None
    freshness: Optional[str] = None
    degraded: Optional[bool] = None
    degraded_reason: Optional[str] = None
    source_refs: Optional[List[str]] = None
    as_of: Optional[datetime] = None
    error: Optional[str] = None
    candidates: Optional[List[Dict[str, Any]]] = None
    raw_error: Optional[str] = None


# ============== Weekly Report Schemas ==============

class WeeklyReportCreate(BaseModel):
    week_start: date
    week_end: date


class WeeklyReportResponse(BaseModel):
    id: int
    user_id: int
    week_start: date
    week_end: date
    trades_summary: Optional[str]
    munger_evaluation: Optional[str]
    suggestions: Optional[str]
    created_at: datetime
    
    class Config:
        from_attributes = True


# ============== Dashboard Schemas ==============


class DashboardAccountBalance(BaseModel):
    name: str
    broker: str
    journal_balance: float
    accounting_health: str
    journal_balance_trusted: bool


class DashboardStats(BaseModel):
    journal_balance: float
    realized_pnl: float
    win_rate: float
    avg_pnl_ratio: float
    total_trades: int
    open_positions: int
    closed_trades: int
    account_balances: List[DashboardAccountBalance] = Field(default_factory=list)
    accounting_degraded: bool = False
    accounting_warnings: List[str] = Field(default_factory=list)


# ============== Trading Account Schemas ==============

class TradingAccountCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., max_length=100)
    broker: str = Field(..., max_length=50)
    account_type: Optional[str] = Field(None, max_length=50)
    currency: str = Field(default="USD", max_length=10)
    initial_balance: Optional[Decimal] = Field(default=None, ge=0)
    description: Optional[str] = None


class TradingAccountUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, max_length=100)
    broker: Optional[str] = Field(None, max_length=50)
    account_type: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, max_length=10)
    description: Optional[str] = None


class TradingAccountResponse(BaseModel):
    id: int
    public_id: str
    user_id: int
    name: str
    broker: str
    account_type: Optional[str]
    currency: str
    initial_balance: Optional[Decimal]
    journal_balance: Decimal
    accounting_health: str
    trade_source_state: str
    journal_balance_trusted: bool
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True



# ============== Transaction Schemas ==============

class TransactionBase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: str # TransactionType enum value
    amount: Decimal
    currency: str = "USD"
    date: datetime
    description: Optional[str] = None

class TransactionCreate(TransactionBase):
    amount: Decimal = Field(..., gt=0)

class TransactionResponse(TransactionBase):
    id: int
    public_id: str
    account_id: int
    created_at: datetime
    updated_at: Optional[datetime]
    reverses_transaction_public_id: Optional[str] = None
    reversed_by_transaction_public_id: Optional[str] = None
    reversal_reason: Optional[str] = None
    request_id: Optional[str] = None

    class Config:
        from_attributes = True


class FinancialFactReverseCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    occurred_at: datetime
    reason: str = Field(..., min_length=1, max_length=1000)


class CashDividendEffectEnum(str, Enum):
    RECEIVED = "RECEIVED"
    PAID_IN_LIEU = "PAID_IN_LIEU"


# ============== System Settings Schemas ==============

class SystemSettingBase(BaseModel):
    key: str = Field(..., max_length=50)
    value: Optional[str] = None
    description: Optional[str] = None

class SystemSettingUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None

class SystemSettingResponse(SystemSettingBase):
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class PlatformSettingBase(BaseModel):
    key: str = Field(..., max_length=100)
    value: Optional[str] = None
    description: Optional[str] = None


class PlatformSettingUpdate(BaseModel):
    value: Optional[str] = None
    description: Optional[str] = None


class PlatformSettingResponse(PlatformSettingBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class IntegrationCredentialUpdate(BaseModel):
    secret_value: str = Field(..., min_length=1)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class IntegrationCredentialActiveUpdate(BaseModel):
    is_active: bool


class IntegrationCredentialResponse(BaseModel):
    id: int
    provider_key: str
    credential_key: str
    masked_value: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    is_configured: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class FeatureFlagUpdate(BaseModel):
    enabled: bool
    actor_targets: List[str] = []
    rollout_percentage: Optional[int] = Field(None, ge=0, le=100)
    expires_at: Optional[datetime] = None
    description: Optional[str] = None


class FeatureFlagResponse(BaseModel):
    id: int
    key: str
    enabled: bool
    actor_targets: List[str] = []
    rollout_percentage: Optional[int] = None
    expires_at: Optional[datetime] = None
    description: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ============== Admin Operations Schemas ==============

class AdminOperationStatus(str, Enum):
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"


class AdminBackupResponse(BaseModel):
    status: AdminOperationStatus
    backup_id: str
    path: str
    database_backend: str
    created_at: datetime
    message: str


class AdminBackupSummaryResponse(BaseModel):
    backup_id: str
    path: str
    database_backend: str
    created_at: datetime
    size_bytes: int


class AdminOpsSummaryResponse(BaseModel):
    database_backend: str
    backup_provider_configured: bool
    backup_count: int
    latest_backup_at: Optional[datetime] = None
    user_count: int
    active_user_count: int
    admin_count: int
    job_counts: Dict[str, int]
    stale_running_job_count: int
    platform_setting_count: int
    configured_integration_count: int
    active_integration_count: int
    enabled_feature_flag_count: int
    expired_feature_flag_count: int
    active_business_lock_count: int
    expired_business_lock_count: int


class AdminUserOperationResponse(BaseModel):
    status: AdminOperationStatus
    user_public_id: str
    role: str
    message: str


class AdminUserRoleUpdate(BaseModel):
    role: str


class AdminUserActiveUpdate(BaseModel):
    is_active: bool


class AdminUserSummaryResponse(BaseModel):
    public_id: str
    email: EmailStr
    status: str
    is_active: bool
    role: str
    last_login_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AdminPasswordResetResponse(BaseModel):
    status: AdminOperationStatus
    user_public_id: str
    temporary_password: str
    active_sessions_revoked: bool
    revoked_session_count: int
    revoked_token_count: int
    message: str


# ============== Position & Batch Schemas ==============

class TradeBatchCreate(BaseModel):
    type: BatchTypeEnum
    price: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)
    time: datetime
    reason: Optional[str] = None
    emotion: Optional[str] = None
    confidence: Optional[int] = Field(None, ge=1, le=5)


class TradeBatchUpdate(BaseModel):
    price: Optional[Decimal] = Field(None, gt=0)
    quantity: Optional[Decimal] = Field(None, gt=0)
    time: Optional[datetime] = None
    reason: Optional[str] = None
    emotion: Optional[str] = None
    confidence: Optional[int] = Field(None, ge=1, le=5)


class TradingPositionEventNarrativeUpdate(BaseModel):
    reason: Optional[str] = None
    emotion: Optional[str] = None
    confidence: Optional[int] = Field(None, ge=1, le=5)
    thesis: Optional[str] = None
    edge_source: Optional[str] = None
    disconfirming_evidence: Optional[str] = None
    invalidation_rule: Optional[str] = None
    expected_holding_period: Optional[str] = None
    planned_exit_rule: Optional[str] = None
    sizing_rationale: Optional[str] = None
    checklist_snapshot: Optional[dict] = None
    note: Optional[str] = None


class TradingPositionDividendCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    effect: CashDividendEffectEnum = CashDividendEffectEnum.RECEIVED
    currency: str = Field(default="USD", max_length=10)
    occurred_at: datetime
    fx_rate_to_account_ccy: Decimal = Field(default=Decimal("1"), gt=0)
    note: Optional[str] = None


class TradingPositionManualAdjustmentCreate(BaseModel):
    amount: Decimal
    currency: str = Field(default="USD", max_length=10)
    occurred_at: datetime
    fx_rate_to_account_ccy: Decimal = Field(default=Decimal("1"), gt=0)
    note: Optional[str] = None


class TradingPositionTradeEventTypeEnum(str, Enum):
    ADD = "ADD"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"


class TradingPositionTradeEventCreate(BaseModel):
    event_type: TradingPositionTradeEventTypeEnum
    quantity: Decimal = Field(..., gt=0)
    price: Decimal = Field(..., gt=0)
    currency: str = Field(default="USD", max_length=10)
    occurred_at: datetime
    fee_amount: Decimal = Field(default=Decimal("0"), ge=0)
    fee_currency: Optional[str] = Field(default=None, max_length=10)
    fx_rate_to_account_ccy: Decimal = Field(default=Decimal("1"), gt=0)
    reason: Optional[str] = None
    emotion: Optional[str] = None
    confidence: Optional[int] = Field(None, ge=1, le=5)
    note: Optional[str] = None


class TradingPositionTradeEventReverseCreate(BaseModel):
    occurred_at: datetime
    reason: str = Field(..., min_length=1, max_length=1000)
    note: Optional[str] = None


class TradingPositionVoidCreate(BaseModel):
    occurred_at: datetime
    reason: str = Field(..., min_length=1, max_length=1000)


class TradeBatchResponse(BaseModel):
    id: int
    public_id: str
    position_id: int
    type: BatchTypeEnum
    price: Decimal
    quantity: Decimal
    time: datetime
    reason: Optional[str]
    emotion: Optional[str]
    confidence: Optional[int]
    pnl: Optional[Decimal]
    created_at: datetime

    class Config:
        from_attributes = True


class AssetMetadataResponse(BaseModel):
    symbol: str
    name: Optional[str]
    core_type: Optional[AssetCoreTypeEnum]
    market: Optional[AssetMarketEnum]
    currency: Optional[AssetCurrencyEnum]
    sector: Optional[str]
    instrument: Optional[str]
    
    class Config:
        from_attributes = True


class PositionInstrumentIdentityCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    core_type: str = Field(
        ...,
        json_schema_extra={
            "pattern": RAW_ASSET_TYPE_INPUT_PATTERN,
            "x-canonical-values": list(JOURNAL_BETA_CONTRACT.instruments.asset_types),
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    )
    market: str = Field(
        ...,
        json_schema_extra={
            "pattern": RAW_MARKET_INPUT_PATTERN,
            "x-canonical-values": list(JOURNAL_BETA_CONTRACT.instruments.markets),
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    )
    currency: str = Field(
        ...,
        json_schema_extra={
            "pattern": RAW_CURRENCY_INPUT_PATTERN,
            "x-canonical-values": list(JOURNAL_BETA_CONTRACT.currency.account_base_currencies),
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    )
    instrument: str = Field(
        ...,
        json_schema_extra={
            "pattern": RAW_INSTRUMENT_TYPE_INPUT_PATTERN,
            "x-canonical-values": list(JOURNAL_BETA_CONTRACT.instruments.instrument_types),
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    )


class PositionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: int
    symbol: str = Field(
        ...,
        json_schema_extra={
            "pattern": JOURNAL_BETA_CONTRACT.instruments.raw_normalized_symbol_input_pattern,
            "x-normalized-pattern": JOURNAL_BETA_CONTRACT.instruments.normalized_symbol_pattern,
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    )
    exchange_code: str = Field(
        ...,
        json_schema_extra={
            "pattern": JOURNAL_BETA_CONTRACT.instruments.raw_exchange_code_input_pattern,
            "x-normalized-pattern": JOURNAL_BETA_CONTRACT.instruments.exchange_code_pattern,
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    )
    asset_type: str = Field(
        ...,
        json_schema_extra={
            "pattern": RAW_ASSET_TYPE_INPUT_PATTERN,
            "x-canonical-values": list(JOURNAL_BETA_CONTRACT.instruments.asset_types),
            "x-normalization": JOURNAL_BETA_CONTRACT.instruments.identity_token_normalization,
        },
    )
    direction: PositionDirectionEnum
    strategy_id: Optional[int] = None
    # First batch info
    entry_price: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)
    entry_time: datetime
    entry_reason: Optional[str] = None
    entry_emotion: Optional[str] = None
    entry_confidence: Optional[int] = Field(None, ge=1, le=5)
    fee_amount: Decimal = Field(default=Decimal("0"), ge=0)
    fee_currency: Optional[str] = None
    # Phase 1: Plan Drift Detection
    planned_entry_price: Optional[Decimal] = None
    planned_stop_loss: Optional[Decimal] = None
    planned_take_profit: Optional[List[dict]] = None  # [{"price": 100, "percent": 50}, ...]
    # Phase 1: Checklist Responses
    checklist_responses: Optional[dict] = None  # {"1": true, "2": false, ...}
    asset_metadata: PositionInstrumentIdentityCreate


class OpenPositionExistsDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["OPEN_POSITION_EXISTS"]
    message: str
    position_public_id: str


class AmbiguousOpenPositionDetail(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: Literal["AMBIGUOUS_OPEN_POSITION"]
    message: str


class PositionCreateConflictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    detail: Union[OpenPositionExistsDetail, AmbiguousOpenPositionDetail] = Field(
        discriminator="code"
    )


class PositionUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    strategy_id: Optional[int] = None
    trade_review: Optional[str] = None
    screenshots: Optional[List[str]] = None
    lessons: Optional[List[str]] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    # Phase 1: Plan Drift Detection
    planned_entry_price: Optional[Decimal] = None
    planned_stop_loss: Optional[Decimal] = None
    planned_take_profit: Optional[List[dict]] = None
    # Phase 1: Checklist Responses
    checklist_responses: Optional[dict] = None


class PositionResponse(BaseModel):
    id: int
    public_id: str
    truth_position_public_id: Optional[str] = None
    user_id: int
    account_id: Optional[int]
    strategy_id: Optional[int]
    symbol: str
    exchange: str
    asset_type: Optional[str] = None
    direction: PositionDirectionEnum
    status: PositionStatusEnum
    total_quantity: Decimal
    average_entry_price: Optional[Decimal]
    realized_pnl: Decimal
    opened_at: datetime
    closed_at: Optional[datetime]
    trade_review: Optional[str]
    screenshots: List[str]
    lessons: List[str]
    rating: Optional[int]
    created_at: datetime
    updated_at: Optional[datetime]
    asset_metadata: Optional[AssetMetadataResponse] = None
    batches: List[TradeBatchResponse] = []
    # Phase 1: Plan Drift Detection
    planned_entry_price: Optional[Decimal] = None
    planned_stop_loss: Optional[Decimal] = None
    planned_take_profit: Optional[List[dict]] = None
    # Phase 1: Checklist Responses
    checklist_responses: Optional[dict] = None
    checklist_completed_at: Optional[datetime] = None
    # Phase 1: Plan Drift Analysis (computed from planned vs actual)
    drift_analysis: Optional[dict] = None  # {"entry_drift_pct": 1.5, "has_drift": True, ...}
    
    class Config:
        from_attributes = True


class PositionListResponse(BaseModel):
    """Lighter response for list view (without batches)"""
    id: int
    public_id: str
    truth_position_public_id: Optional[str] = None
    account_id: Optional[int]
    symbol: str
    exchange: str
    asset_type: Optional[str] = None
    direction: PositionDirectionEnum
    status: PositionStatusEnum
    total_quantity: Decimal
    average_entry_price: Optional[Decimal]
    realized_pnl: Decimal
    opened_at: datetime
    closed_at: Optional[datetime]
    created_at: datetime
    asset_metadata: Optional[AssetMetadataResponse] = None
    batches: List[TradeBatchResponse] = []

    class Config:
        from_attributes = True


class PositionMarketAnalysisResponse(PositionResponse):
    """Optional MARKET capability DTO, never published by the journal router."""

    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    max_price_during_hold: Optional[float] = None
    min_price_during_hold: Optional[float] = None


# ============== Import Schemas ==============

class ImportIssue(BaseModel):
    code: str
    field: Optional[str] = None
    message: str


class ImportPreviewRow(BaseModel):
    public_id: str
    row_number: int
    raw_values: Dict[str, Any]
    normalized_values: Dict[str, Any]
    is_valid: bool
    errors: List[ImportIssue] = Field(default_factory=list)
    warnings: List[ImportIssue] = Field(default_factory=list)


class ImportSessionResponse(BaseModel):
    schema_version: Literal[1] = 1
    session_public_id: str
    account_public_id: str
    adapter_kind: Literal["GENERIC_BOOTSTRAP", "IBKR_FLEX_XML_V1"]
    file_format: Literal["CSV_UTF8", "XLSX", "XML"]
    status: Literal[
        "UPLOADING",
        "PREVIEW_READY",
        "CONFIRMING",
        "COMPLETED",
        "COMPLETED_NOOP",
        "CONFLICTED",
        "FAILED",
        "EXPIRED",
    ]
    expires_at: datetime
    total_rows: int
    valid_rows: int
    error_rows: int
    warning_rows: int
    error: Optional[ImportIssue] = None
    rows: List[ImportPreviewRow] = Field(default_factory=list)
    confirm_available: bool = False
    source_preview: Optional[Dict[str, Any]] = None


class ImportConfirmRequest(BaseModel):
    session_public_id: str
    selected_row_public_ids: List[str] = Field(default_factory=list)


class ImportConfirmSourceIds(BaseModel):
    position_public_ids: List[str] = Field(default_factory=list)
    event_public_ids: List[str] = Field(default_factory=list)
    posting_public_ids: List[str] = Field(default_factory=list)


class ImportConfirmResponse(BaseModel):
    schema_version: Literal[1] = 1
    session_public_id: str
    account_public_id: str
    status: Literal["COMPLETED", "COMPLETED_NOOP"]
    selected_row_count: int
    position_count: int
    event_count: int
    posting_count: int
    source_ids: ImportConfirmSourceIds
