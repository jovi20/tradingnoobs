"""
Trading Noobs Backend - Database Models
"""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    ForeignKey, Numeric, JSON, Enum as SQLEnum, Index
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum


class TradeStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class StrategyStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    ARCHIVED = "ARCHIVED"


class PositionDirection(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class PositionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


class BatchType(str, enum.Enum):
    ENTRY = "ENTRY"  # 加仓
    EXIT = "EXIT"    # 减仓


class AssetCoreType(str, enum.Enum):
    STOCK = "STOCK"
    BOND = "BOND"
    FUND = "FUND"
    COMMODITY = "COMMODITY"
    FX = "FX"
    DERIVATIVE = "DERIVATIVE"
    CRYPTO = "CRYPTO"


class AssetMarket(str, enum.Enum):
    US = "US"
    HK = "HK"
    A_SHARE = "A_SHARE"
    CN_OTC = "CN_OTC"
    FOREX = "FOREX"
    COMMODITY_FUT = "COMMODITY_FUT"
    UK = "UK"
    CRYPTO = "CRYPTO"


class AssetCurrency(str, enum.Enum):
    USD = "USD"
    HKD = "HKD"
    CNY = "CNY"
    EUR = "EUR"
    GBP = "GBP"


class AssetRiskLevel(str, enum.Enum):
    CONSERVATIVE = "CONSERVATIVE"
    MODERATE = "MODERATE"
    GROWTH = "GROWTH"
    AGGRESSIVE = "AGGRESSIVE"
    HEDGE = "HEDGE"


class AssetMetadata(Base):
    """标的元数据表 - 存储资产的多维属性"""
    __tablename__ = "asset_metadata"
    
    symbol = Column(String(50), primary_key=True, index=True) # Uppercase identifier
    name = Column(String(100), nullable=True)
    
    core_type = Column(SQLEnum(AssetCoreType), nullable=True)
    market = Column(SQLEnum(AssetMarket), nullable=True)
    currency = Column(SQLEnum(AssetCurrency), nullable=True)
    
    sector = Column(String(100), nullable=True)    # 行业/主题
    risk_level = Column(SQLEnum(AssetRiskLevel), nullable=True)
    instrument = Column(String(50), nullable=True)  # 具量化工具, 如 "Spot", "ETF", "Future"
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")  # user, admin
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    trades = relationship("Trade", back_populates="user")
    strategies = relationship("Strategy", back_populates="user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    daily_summaries = relationship("DailySummary", back_populates="user")
    weekly_reports = relationship("WeeklyReport", back_populates="user")
    trading_accounts = relationship("TradingAccount", back_populates="user")
    positions = relationship("Position", back_populates="user")
    daily_snapshots = relationship("DailySnapshot", back_populates="user")
    journal_entries = relationship("JournalEntry", back_populates="user")
    ai_summaries = relationship("AISummary", back_populates="user")


class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=True) # New: Link to Account
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    
    # Basic Info
    symbol = Column(String(50), nullable=False, index=True)
    exchange = Column(String(50), nullable=False)
    
    # Entry Info
    entry_price = Column(Numeric(20, 8), nullable=False)  # Cost basis including fees
    quantity = Column(Numeric(20, 8), nullable=False)
    entry_time = Column(DateTime(timezone=True), nullable=False)
    
    # Exit/Current Info
    current_price = Column(Numeric(20, 8), nullable=True)
    exit_price = Column(Numeric(20, 8), nullable=True)
    exit_time = Column(DateTime(timezone=True), nullable=True)
    status = Column(SQLEnum(TradeStatus), default=TradeStatus.OPEN, index=True)
    
    # Decision Records (Entry)
    entry_reason = Column(Text, nullable=True)
    entry_emotion = Column(String(50), nullable=True)
    entry_confidence = Column(Integer, nullable=True)  # 1-5
    
    # Exit Review
    exit_reason = Column(Text, nullable=True)
    exit_emotion = Column(String(50), nullable=True)
    trade_review = Column(Text, nullable=True)  # Markdown
    screenshots = Column(JSON, default=list)  # List of URLs
    lessons = Column(JSON, default=list)  # List of tags
    rating = Column(Integer, nullable=True)  # 1-5
    
    # Calculated PnL (Persisted for performance)
    pnl = Column(Numeric(20, 8), nullable=True)
    pnl_percent = Column(Numeric(10, 4), nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")
    trading_account = relationship("TradingAccount") # One-to-Many from Account to Trades
    
    # Indices for performance
    __table_args__ = (
        Index('idx_user_entry_time', 'user_id', 'entry_time'),
    )
    
    def calculate_pnl(self):
        """Logic to calculate and update pnl/pnl_percent columns"""
        price = self.exit_price if self.status == TradeStatus.CLOSED else self.current_price
        if price and self.entry_price:
            self.pnl = (float(price) - float(self.entry_price)) * float(self.quantity)
            if float(self.entry_price) > 0:
                self.pnl_percent = ((float(price) - float(self.entry_price)) / float(self.entry_price)) * 100
        return self.pnl


class Strategy(Base):
    __tablename__ = "strategies"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)  # Markdown
    entry_rules = Column(Text, nullable=True)
    exit_rules = Column(Text, nullable=True)
    risk_rules = Column(Text, nullable=True)
    symbols = Column(JSON, default=list)  # List of symbols
    status = Column(SQLEnum(StrategyStatus), default=StrategyStatus.ACTIVE)
    
    # Phase 1: Pre-Trade Checklist
    checklist_items = Column(JSON, default=list)  # [{"id": 1, "label": "成交量确认", "category": "entry", "required": True}, ...]
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="strategies")
    trades = relationship("Trade", back_populates="strategy")


class DailySummary(Base):
    __tablename__ = "daily_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    date = Column(Date, nullable=False, index=True)
    market_mood = Column(String(50), nullable=True)
    personal_mood = Column(String(50), nullable=True)
    summary = Column(Text, nullable=True)  # Markdown
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="daily_summaries")


class JournalEntry(Base):
    """用户随笔 - 每天最多5条，每条最多500字"""
    __tablename__ = "journal_entries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    content = Column(String(500), nullable=False)  # 限制500字
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="journal_entries")
    
    __table_args__ = (
        Index('idx_journal_user_date', 'user_id', 'date'),
    )


class AISummary(Base):
    """AI 每日总结 - 每天最多生成一次"""
    __tablename__ = "ai_summaries"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date = Column(Date, nullable=False, index=True)
    content = Column(Text, nullable=False)  # Markdown 格式的总结内容
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="ai_summaries")
    
    __table_args__ = (
        Index('idx_ai_summary_user_date', 'user_id', 'date', unique=True),
    )


class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Theme
    theme = Column(String(20), default="system")  # light/dark/system
    up_color = Column(String(20), default="GREEN") # GREEN or RED
    
    # Exchange API Keys (encrypted in production)
    ibkr_host = Column(String(255), nullable=True)
    ibkr_port = Column(Integer, nullable=True)
    ibkr_client_id = Column(Integer, nullable=True)
    binance_api_key = Column(String(255), nullable=True)
    binance_api_secret = Column(String(255), nullable=True)
    finnhub_api_key = Column(String(255), nullable=True)
    
    # LLM API
    llm_api_url = Column(String(500), nullable=True)
    llm_api_key = Column(String(255), nullable=True)
    llm_model = Column(String(100), nullable=True)
    
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="settings")


class WeeklyReport(Base):
    __tablename__ = "weekly_reports"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    week_start = Column(Date, nullable=False, index=True)
    week_end = Column(Date, nullable=False)
    trades_summary = Column(Text, nullable=True)
    munger_evaluation = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User", back_populates="weekly_reports")


class TradingAccount(Base):
    """用户的实盘账户标签"""
    __tablename__ = "trading_accounts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    name = Column(String(100), nullable=False)  # 账户名称，如 "IBKR主账户"
    broker = Column(String(50), nullable=False)  # 券商/交易所，如 "IBKR", "Binance"
    account_type = Column(String(50), nullable=True)  # 账户类型，如 "现货", "合约", "保证金"
    currency = Column(String(10), default="USD")  # 账户币种
    currency = Column(String(10), default="USD")  # 账户币种
    initial_balance = Column(Numeric(20, 2), nullable=True)  # 初始资金
    cash_balance = Column(Numeric(20, 2), nullable=True, default=0) # 当前现金余额
    current_balance = Column(Numeric(20, 2), nullable=True, default=0) # 当前净值 (NAV) - Manually Synced
    description = Column(Text, nullable=True)  # 备注
    is_active = Column(Boolean, default=True)  # 是否启用
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="trading_accounts")
    transactions = relationship("Transaction", back_populates="trading_account", cascade="all, delete-orphan")


class SystemSetting(Base):
    """全局系统设置 (Admin Only)"""
    __tablename__ = "system_settings"
    
    key = Column(String(50), primary_key=True)  # 配置键，如 'finnhub_api_key'
    value = Column(Text, nullable=True)         # 配置值
    description = Column(String(200), nullable=True) # 描述
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Position(Base):
    """持仓记录 - 汇总同标的的交易批次"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=True)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    
    symbol = Column(String(50), nullable=False, index=True)
    exchange = Column(String(50), nullable=False)
    asset_type = Column(String(20), nullable=True)  # Enhanced Type: EQUITY, ETF_BOND, etc.
    direction = Column(SQLEnum(PositionDirection), nullable=False)  # LONG or SHORT
    status = Column(SQLEnum(PositionStatus), default=PositionStatus.OPEN, index=True)
    
    # Aggregated Values (updated on each batch)
    total_quantity = Column(Numeric(20, 8), default=0)  # Current holding
    average_entry_price = Column(Numeric(20, 8), nullable=True)  # Weighted avg
    realized_pnl = Column(Numeric(20, 8), default=0)  # Sum of closed batch PnLs
    
    # Timestamps
    opened_at = Column(DateTime(timezone=True), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Review (applied when position is fully closed)
    trade_review = Column(Text, nullable=True)
    screenshots = Column(JSON, default=list)
    lessons = Column(JSON, default=list)
    rating = Column(Integer, nullable=True)
    
    # Phase 1: Pre-Trade Checklist Responses
    checklist_responses = Column(JSON, nullable=True)  # {"1": true, "2": false, ...}
    checklist_completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Phase 1: Plan Drift Detection
    planned_entry_price = Column(Numeric(20, 8), nullable=True)   # 计划入场价
    planned_stop_loss = Column(Numeric(20, 8), nullable=True)     # 计划止损价
    planned_take_profit = Column(JSON, nullable=True)             # 计划止盈价 [{"price": 100, "percent": 50}, ...]
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    asset_metadata_symbol = Column(String(50), ForeignKey("asset_metadata.symbol"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="positions")
    trading_account = relationship("TradingAccount")
    strategy = relationship("Strategy")
    asset_metadata = relationship("AssetMetadata")
    batches = relationship("TradeBatch", back_populates="position", order_by="TradeBatch.time")
    
    @property
    def unrealized_pnl(self):
        """Calculate unrealized P&L for open positions"""
        # This would need current_price from market data
        return None  # To be computed with live price


class TradeBatch(Base):
    """交易批次 - 加仓/减仓记录"""
    __tablename__ = "trade_batches"
    
    id = Column(Integer, primary_key=True, index=True)
    position_id = Column(Integer, ForeignKey("positions.id"), nullable=False)
    
    type = Column(SQLEnum(BatchType), nullable=False)  # ENTRY or EXIT
    price = Column(Numeric(20, 8), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    time = Column(DateTime(timezone=True), nullable=False)
    
    # Decision Records
    reason = Column(Text, nullable=True)
    emotion = Column(String(50), nullable=True)
    confidence = Column(Integer, nullable=True)  # 1-5
    
    # PnL (only for EXIT batches)
    pnl = Column(Numeric(20, 8), nullable=True)  # Computed on exit
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    position = relationship("Position", back_populates="batches")


class DailySnapshot(Base):
    """每日资产快照 - 记录每日总资产净值"""
    __tablename__ = "daily_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    date = Column(Date, nullable=False, index=True)
    total_equity = Column(Numeric(20, 2), nullable=False)   # 总权益 (Cash + Market Value)
    total_assets = Column(Numeric(20, 2), nullable=False)   # 总资产 (Gross)
    total_liabilities = Column(Numeric(20, 2), nullable=False) # 总负债
    net_transfers = Column(Numeric(20, 2), default=0)       # 当日净充提
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    # Relationships
    user = relationship("User", back_populates="daily_snapshots")


class TransactionType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    INTEREST = "INTEREST"
    FEE = "FEE"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"


class Transaction(Base):
    """资金流水 - 记录充提、利息、费用等"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)
    
    type = Column(SQLEnum(TransactionType), nullable=False)
    amount = Column(Numeric(20, 2), nullable=False) # Signed amount: Deposit (+), Withdrawal (-)
    currency = Column(String(10), default="USD")
    date = Column(DateTime(timezone=True), nullable=False, default=func.now())
    description = Column(Text, nullable=True)
    related_tx_id = Column(Integer, nullable=True) # For transfers between accounts

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    trading_account = relationship("TradingAccount", back_populates="transactions")

