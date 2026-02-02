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


# ============== Auth Schemas ==============

class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)


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


class StrategyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    description: Optional[str] = None
    entry_rules: Optional[str] = None
    exit_rules: Optional[str] = None
    risk_rules: Optional[str] = None
    symbols: Optional[List[str]] = None
    status: Optional[StrategyStatusEnum] = None


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


# ============== User Settings Schemas ==============

class UserSettingsUpdate(BaseModel):
    theme: Optional[str] = Field(None, pattern="^(light|dark|system)$")
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

class DashboardStats(BaseModel):
    total_pnl: float
    win_rate: float
    avg_pnl_ratio: float
    total_trades: int
    open_positions: int
    closed_trades: int


# ============== Trading Account Schemas ==============

class TradingAccountCreate(BaseModel):
    name: str = Field(..., max_length=100)
    broker: str = Field(..., max_length=50)
    account_type: Optional[str] = Field(None, max_length=50)
    currency: str = Field(default="USD", max_length=10)
    initial_balance: Optional[Decimal] = None
    description: Optional[str] = None


class TradingAccountUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=100)
    broker: Optional[str] = Field(None, max_length=50)
    account_type: Optional[str] = Field(None, max_length=50)
    currency: Optional[str] = Field(None, max_length=10)
    initial_balance: Optional[Decimal] = None
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
    description: Optional[str]
    is_active: bool
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
