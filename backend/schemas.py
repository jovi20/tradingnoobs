"""
Trading Noobs Backend - Pydantic Schemas
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Generic, List, Optional, TypeVar
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


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


class LinkedObjectTypeEnum(str, Enum):
    TRADING_POSITION = "TRADING_POSITION"
    POSITION_EVENT = "POSITION_EVENT"
    ACCOUNT = "ACCOUNT"
    INSIGHT_ARTIFACT = "INSIGHT_ARTIFACT"


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


class ReadModelEnvelope(BaseModel, Generic[T]):
    data: T
    meta: TrustMeta


class SummaryBar(BaseModel):
    period_label: str
    trade_count: int
    review_completion_rate: Optional[float] = None
    net_equity_change: Optional[float] = None
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


# ============== Auth Schemas ==============

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    invite_code: str = Field(..., min_length=1)


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
    theme: Optional[str] = Field(None, pattern="^(light|dark|system)$")
    up_color: Optional[str] = Field(None, pattern="^(GREEN|RED)$")
    display_currency: Optional[str] = Field(None, pattern="^(USD|HKD|CNY|EUR|GBP)$")
    ibkr_host: Optional[str] = None
    ibkr_port: Optional[int] = None
    ibkr_client_id: Optional[int] = None
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    llm_api_url: Optional[str] = None
    llm_api_key: Optional[str] = None
    llm_model: Optional[str] = None


class UserSettingsResponse(BaseModel):
    id: int
    user_id: int
    theme: str
    up_color: str = "GREEN"
    display_currency: str = "USD"
    ibkr_host: Optional[str]
    ibkr_port: Optional[int]
    ibkr_client_id: Optional[int]
    binance_api_key: Optional[str]  # Will be masked in response
    finnhub_api_key: Optional[str]  # Will be masked
    llm_api_url: Optional[str]
    llm_model: Optional[str]
    
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


class AnalysisResponse(BaseModel):
    analysis_type: AnalysisType
    raw_data: dict
    ai_insights: Optional[str]
    created_at: datetime


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

class AssetAllocation(BaseModel):
    name: str # 'Stocks', 'Crypto', 'Cash'
    value: float
    percent: float 

class PositionMover(BaseModel):
    id: int
    symbol: str
    asset_type: Optional[str] = None
    currency: Optional[str] = None  # 标的原生币种
    change_percent: float
    current_price: float

class SankeyNode(BaseModel):
    name: str

class SankeyLink(BaseModel):
    source: int
    target: int
    value: float

class PortfolioFlow(BaseModel):
    nodes: List[SankeyNode]
    links: List[SankeyLink]

class DashboardStats(BaseModel):
    total_assets: float = 0.0  # Added for frontend percentage calculation
    total_pnl: float
    win_rate: float
    avg_pnl_ratio: float
    total_trades: int
    open_positions: int
    closed_trades: int
    asset_allocation: List[AssetAllocation] = []
    core_type_allocation: List[AssetAllocation] = []
    market_allocation: List[AssetAllocation] = []
    risk_level_allocation: List[AssetAllocation] = []
    account_allocation: List['AccountAllocation'] = []
    top_movers: List[PositionMover] = []
    bottom_movers: List[PositionMover] = []
    portfolio_flow: Optional[PortfolioFlow] = None
    
    # Risk Metrics
    sharpe_ratio: Optional[float] = None
    sortino_ratio: Optional[float] = None
    calmar_ratio: Optional[float] = None
    max_drawdown: Optional[float] = None


class AccountAllocation(BaseModel):
    name: str 
    broker: str
    value: float
    percent: float


# ============== Trading Account Schemas ==============

class TradingAccountCreate(BaseModel):
    name: str = Field(..., max_length=100)
    broker: str = Field(..., max_length=50)
    account_type: Optional[str] = Field(None, max_length=50)
    currency: str = Field(default="USD", max_length=10)
    initial_balance: Optional[Decimal] = None
    initial_balance: Optional[Decimal] = None
    cash_balance: Optional[Decimal] = None
    current_balance: Optional[Decimal] = None
    total_assets: Optional[Decimal] = None
    total_liabilities: Optional[Decimal] = None
    description: Optional[str] = None


class TradingAccountUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    broker: Optional[str] = Field(None, max_length=50)
    account_type: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, max_length=10)
    initial_balance: Optional[Decimal] = None
    cash_balance: Optional[Decimal] = None
    current_balance: Optional[Decimal] = None
    total_assets: Optional[Decimal] = None
    total_liabilities: Optional[Decimal] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class TradingAccountResponse(BaseModel):
    id: int
    public_id: str
    user_id: int
    name: str
    broker: str
    account_type: Optional[str]
    currency: str
    initial_balance: Optional[Decimal]
    cash_balance: Optional[Decimal]
    current_balance: Optional[Decimal]
    market_value: Optional[Decimal] = None
    total_equity: Optional[Decimal] = None
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: Optional[datetime]
    
    class Config:
        from_attributes = True



# ============== Transaction Schemas ==============

class TransactionBase(BaseModel):
    type: str # TransactionType enum value
    amount: Decimal
    currency: str = "USD"
    date: datetime
    description: Optional[str] = None

class TransactionCreate(TransactionBase):
    pass

class TransactionResponse(TransactionBase):
    id: int
    public_id: str
    account_id: int
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        from_attributes = True


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
    currency: str = Field(default="USD", max_length=10)
    occurred_at: datetime
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
    risk_level: Optional[AssetRiskLevelEnum]
    instrument: Optional[str]
    
    class Config:
        from_attributes = True


class AssetMetadataUpdate(BaseModel):
    name: Optional[str] = None
    core_type: Optional[str] = None # Using str to allow flexible input or enum mapping in router
    market: Optional[str] = None
    currency: Optional[str] = None
    sector: Optional[str] = None
    risk_level: Optional[str] = None
    instrument: Optional[str] = None


class PositionCreate(BaseModel):
    account_id: int
    symbol: str = Field(..., max_length=50)
    asset_type: Optional[str] = None
    direction: PositionDirectionEnum
    strategy_id: Optional[int] = None
    # First batch info
    entry_price: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)
    entry_time: datetime
    entry_reason: Optional[str] = None
    entry_emotion: Optional[str] = None
    entry_confidence: Optional[int] = Field(None, ge=1, le=5)
    # Phase 1: Plan Drift Detection
    planned_entry_price: Optional[Decimal] = None
    planned_stop_loss: Optional[Decimal] = None
    planned_take_profit: Optional[List[dict]] = None  # [{"price": 100, "percent": 50}, ...]
    # Phase 1: Checklist Responses
    checklist_responses: Optional[dict] = None  # {"1": true, "2": false, ...}


class PositionUpdate(BaseModel):
    strategy_id: Optional[int] = None
    trade_review: Optional[str] = None
    screenshots: Optional[List[str]] = None
    lessons: Optional[List[str]] = None
    rating: Optional[int] = Field(None, ge=1, le=5)
    asset_metadata: Optional[AssetMetadataUpdate] = None
    # Phase 1: Plan Drift Detection
    planned_entry_price: Optional[Decimal] = None
    planned_stop_loss: Optional[Decimal] = None
    planned_take_profit: Optional[List[dict]] = None
    # Phase 1: Checklist Responses
    checklist_responses: Optional[dict] = None


class PositionResponse(BaseModel):
    id: int
    public_id: str
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
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
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
    
    # Phase 2: MAE/MFE
    max_price_during_hold: Optional[float] = None
    min_price_during_hold: Optional[float] = None
    
    class Config:
        from_attributes = True


class PositionListResponse(BaseModel):
    """Lighter response for list view (without batches)"""
    id: int
    public_id: str
    account_id: Optional[int]
    symbol: str
    exchange: str
    asset_type: Optional[str] = None
    direction: PositionDirectionEnum
    status: PositionStatusEnum
    total_quantity: Decimal
    average_entry_price: Optional[Decimal]
    realized_pnl: Decimal
    current_price: Optional[float] = None  # Live price for open positions
    unrealized_pnl: Optional[float] = None  # Unrealized P&L
    opened_at: datetime
    closed_at: Optional[datetime]
    created_at: datetime
    asset_metadata: Optional[AssetMetadataResponse] = None
    batches: List[TradeBatchResponse] = []

    class Config:
        from_attributes = True


# ============== Import Schemas ==============

class ImportPreviewRow(BaseModel):
    index: int
    data: dict  # Raw data from file
    is_valid: bool
    errors: List[str] = []
    parsed: Optional[dict] = None  # Parsed and normalized data

class ImportPreviewResponse(BaseModel):
    total_rows: int
    valid_rows: int
    error_rows: int
    preview_rows: List[ImportPreviewRow]  # First N rows or all validation errors
    file_token: str  # Temporary token to reference uploaded file cache

class ImportConfirmRequest(BaseModel):
    file_token: str
    account_id: Optional[int] = None # Target account if not specified in file
    selected_indices: Optional[List[int]] = None # If None, import all valid rows
