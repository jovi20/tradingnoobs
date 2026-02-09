"""
Trading Noobs Backend - Pydantic Schemas
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from datetime import datetime, date
from decimal import Decimal
from enum import Enum


# ============== Enums ==============

class TradeStatusEnum(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


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
    is_active: bool
    role: str
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[int] = None


# ============== Trade Schemas ==============

class TradeCreate(BaseModel):
    symbol: str = Field(..., max_length=50)
    exchange: Optional[str] = Field(None, max_length=50) # Derived from Account if not provided
    account_id: int = Field(...) # Required now
    entry_price: Decimal = Field(..., gt=0)
    quantity: Decimal = Field(..., gt=0)
    entry_time: datetime
    status: TradeStatusEnum = TradeStatusEnum.OPEN  # 交易状态：OPEN(持仓中) 或 CLOSED(已平仓)
    strategy_id: Optional[int] = None
    entry_reason: Optional[str] = None
    entry_emotion: Optional[str] = None
    entry_confidence: Optional[int] = Field(None, ge=1, le=5)
    # 可选的平仓信息（当 status=CLOSED 时使用）
    exit_price: Optional[Decimal] = Field(None, gt=0)
    exit_time: Optional[datetime] = None
    exit_reason: Optional[str] = None



class TradeClose(BaseModel):
    exit_price: Decimal = Field(..., gt=0)
    exit_reason: Optional[str] = None
    exit_emotion: Optional[str] = None
    trade_review: Optional[str] = None
    screenshots: Optional[List[str]] = []
    lessons: Optional[List[str]] = []
    rating: Optional[int] = Field(None, ge=1, le=5)


class TradeUpdate(BaseModel):
    entry_reason: Optional[str] = None
    entry_emotion: Optional[str] = None
    entry_confidence: Optional[int] = Field(None, ge=1, le=5)
    current_price: Optional[Decimal] = None


class TradeResponse(BaseModel):
    id: int
    user_id: int
    account_id: Optional[int]
    strategy_id: Optional[int]
    symbol: str
    exchange: str
    entry_price: Decimal
    quantity: Decimal
    entry_time: datetime
    current_price: Optional[float]
    exit_price: Optional[Decimal]
    exit_time: Optional[datetime]
    status: TradeStatusEnum
    entry_reason: Optional[str]
    entry_emotion: Optional[str]
    entry_confidence: Optional[int]
    exit_reason: Optional[str]
    exit_emotion: Optional[str]
    trade_review: Optional[str]
    screenshots: List[str]
    lessons: List[str]
    rating: Optional[int]
    created_at: datetime
    pnl: Optional[float] = None
    pnl_percent: Optional[float] = None
    
    class Config:
        from_attributes = True


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
    ibkr_host: Optional[str]
    ibkr_port: Optional[int]
    ibkr_client_id: Optional[int]
    binance_api_key: Optional[str]  # Will be masked in response
    finnhub_api_key: Optional[str]  # Will be masked
    llm_api_url: Optional[str]
    llm_model: Optional[str]
    
    class Config:
        from_attributes = True


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
    user_id: int
    name: str
    broker: str
    account_type: Optional[str]
    currency: str
    initial_balance: Optional[Decimal]
    cash_balance: Optional[Decimal]
    current_balance: Optional[Decimal]
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


class TradeBatchResponse(BaseModel):
    id: int
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
    
    class Config:
        from_attributes = True


class PositionListResponse(BaseModel):
    """Lighter response for list view (without batches)"""
    id: int
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

