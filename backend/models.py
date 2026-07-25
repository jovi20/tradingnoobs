"""
Trading Noobs Backend - Database Models
"""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    ForeignKey, Numeric, JSON, Enum as SQLEnum, Index, UniqueConstraint, text
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import enum
import uuid




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


class TradeInstrumentType(str, enum.Enum):
    SPOT = "SPOT"
    EQUITY_OPTION = "EQUITY_OPTION"


class TradingPositionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    ARCHIVED = "ARCHIVED"
    ERROR = "ERROR"


class TradingPositionSide(str, enum.Enum):
    LONG = "LONG"
    SHORT = "SHORT"


class PositionEventType(str, enum.Enum):
    OPEN = "OPEN"
    ADD = "ADD"
    REDUCE = "REDUCE"
    CLOSE = "CLOSE"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"
    CASH_ADJUSTMENT = "CASH_ADJUSTMENT"
    STOCK_SPLIT = "STOCK_SPLIT"
    TRANSFER_IN = "TRANSFER_IN"
    TRANSFER_OUT = "TRANSFER_OUT"
    OPTION_EXERCISE = "OPTION_EXERCISE"
    OPTION_ASSIGNMENT = "OPTION_ASSIGNMENT"
    OPTION_EXPIRY = "OPTION_EXPIRY"
    REVERSAL = "REVERSAL"
    MANUAL_ADJUSTMENT = "MANUAL_ADJUSTMENT"


class AccountLedgerEntryType(str, enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    DIVIDEND = "DIVIDEND"
    FEE = "FEE"
    CASH_ADJUSTMENT = "CASH_ADJUSTMENT"
    REALIZED_PNL = "REALIZED_PNL"


class JobRunStatus(str, enum.Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    CANCELLED = "CANCELLED"


class JobRunEventType(str, enum.Enum):
    STATUS_CHANGED = "STATUS_CHANGED"
    ATTEMPT_STARTED = "ATTEMPT_STARTED"
    ATTEMPT_FAILED = "ATTEMPT_FAILED"
    RETRY_SCHEDULED = "RETRY_SCHEDULED"
    LOG = "LOG"
    CANCELLED = "CANCELLED"


class BusinessLockStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    RELEASED = "RELEASED"
    EXPIRED = "EXPIRED"


class OutboxEventStatus(str, enum.Enum):
    PENDING = "PENDING"
    PUBLISHED = "PUBLISHED"
    FAILED = "FAILED"
    DISCARDED = "DISCARDED"


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


class AssetMaster(Base):
    __tablename__ = "asset_master"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    canonical_code = Column(String(100), unique=True, index=True, nullable=False)
    display_symbol = Column(String(50), nullable=False)
    name = Column(String(150), nullable=False)
    asset_type = Column(String(50), nullable=False)
    quote_currency = Column(String(10), nullable=True)
    country_code = Column(String(10), nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")
    sector = Column(String(100), nullable=True)
    industry = Column(String(100), nullable=True)
    metadata_json = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    instruments = relationship("TradeInstrument", back_populates="asset", cascade="all, delete-orphan")
    provider_symbol_mappings = relationship(
        "ProviderSymbolMapping",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    latest_market_quotes = relationship(
        "LatestMarketQuote",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    daily_price_bars = relationship(
        "PriceBarDaily",
        back_populates="asset",
        cascade="all, delete-orphan",
    )
    market_data_watermarks = relationship(
        "MarketDataWatermark",
        back_populates="asset",
        cascade="all, delete-orphan",
    )


class TradeInstrument(Base):
    __tablename__ = "trade_instruments"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    asset_id = Column(Integer, ForeignKey("asset_master.id"), nullable=False)
    instrument_type = Column(SQLEnum(TradeInstrumentType), nullable=False, default=TradeInstrumentType.SPOT)
    display_name = Column(String(150), nullable=False)
    contract_symbol = Column(String(100), nullable=False)
    option_type = Column(String(20), nullable=True)
    strike_price = Column(Numeric(20, 8), nullable=True)
    expiration_date = Column(Date, nullable=True)
    multiplier = Column(Numeric(20, 8), nullable=True)
    settlement_type = Column(String(20), nullable=True)
    status = Column(String(20), nullable=False, default="ACTIVE")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    asset = relationship("AssetMaster", back_populates="instruments")
    positions = relationship("TradingPosition", back_populates="instrument")
    provider_symbol_mappings = relationship(
        "ProviderSymbolMapping",
        back_populates="instrument",
        cascade="all, delete-orphan",
    )


class ProviderSymbolMapping(Base):
    """Provider-specific symbol for an asset or a concrete trade instrument."""

    __tablename__ = "provider_symbol_mappings"

    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("asset_master.id", ondelete="CASCADE"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("trade_instruments.id", ondelete="CASCADE"), nullable=True)
    provider_key = Column(String(50), nullable=False)
    provider_symbol = Column(String(150), nullable=False)
    provider_market = Column(String(50), nullable=False)
    capabilities_json = Column(JSON, nullable=False, default=list)
    quality_status = Column(String(30), nullable=False, default="ACTIVE")
    first_seen_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    last_verified_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    asset = relationship("AssetMaster", back_populates="provider_symbol_mappings")
    instrument = relationship("TradeInstrument", back_populates="provider_symbol_mappings")

    __table_args__ = (
        UniqueConstraint(
            "provider_key",
            "provider_market",
            "provider_symbol",
            name="uq_provider_symbol_mappings_provider_symbol",
        ),
        Index(
            "uq_provider_symbol_mappings_asset_provider_market",
            "asset_id",
            "provider_key",
            "provider_market",
            unique=True,
            sqlite_where=instrument_id.is_(None),
            postgresql_where=instrument_id.is_(None),
        ),
        Index(
            "uq_provider_symbol_mappings_instrument_provider_market",
            "instrument_id",
            "provider_key",
            "provider_market",
            unique=True,
            sqlite_where=instrument_id.is_not(None),
            postgresql_where=instrument_id.is_not(None),
        ),
        Index(
            "ix_provider_symbol_mappings_quality_verified",
            "quality_status",
            "last_verified_at",
        ),
    )


class LatestMarketQuote(Base):
    """Last known good quote per asset and provider, not an unbounded tick history."""

    __tablename__ = "latest_market_quotes"
    __table_args__ = (
        UniqueConstraint("asset_id", "provider", name="uq_latest_market_quotes_asset_provider"),
        Index("ix_latest_market_quotes_asset_received", "asset_id", "received_at"),
        Index("ix_latest_market_quotes_provider_received", "provider", "received_at"),
    )

    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("asset_master.id", ondelete="CASCADE"), nullable=False)
    provider = Column(String(50), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    previous_close = Column(Numeric(20, 8), nullable=True)
    open_price = Column(Numeric(20, 8), nullable=True)
    high_price = Column(Numeric(20, 8), nullable=True)
    low_price = Column(Numeric(20, 8), nullable=True)
    volume = Column(Numeric(30, 8), nullable=True)
    change_amount = Column(Numeric(20, 8), nullable=True)
    change_percent = Column(Numeric(20, 8), nullable=True)
    currency = Column(String(10), nullable=True)
    market_time = Column(DateTime(timezone=True), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False)
    quality_status = Column(String(30), nullable=False, default="GOOD")
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    asset = relationship("AssetMaster", back_populates="latest_market_quotes")


class PriceBarDaily(Base):
    """Durable daily OHLCV bar, versioned by provider and adjustment mode."""

    __tablename__ = "price_bars_daily"
    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "trading_date",
            "provider",
            "adjustment_mode",
            name="uq_price_bars_daily_asset_date_provider_adjustment",
        ),
        Index("ix_price_bars_daily_asset_date", "asset_id", "trading_date"),
        Index("ix_price_bars_daily_provider_date", "provider", "trading_date"),
    )

    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("asset_master.id", ondelete="CASCADE"), nullable=False)
    trading_date = Column(Date, nullable=False)
    provider = Column(String(50), nullable=False)
    adjustment_mode = Column(String(20), nullable=False, default="RAW")
    open_price = Column(Numeric(20, 8), nullable=False)
    high_price = Column(Numeric(20, 8), nullable=False)
    low_price = Column(Numeric(20, 8), nullable=False)
    close_price = Column(Numeric(20, 8), nullable=False)
    adjusted_close = Column(Numeric(20, 8), nullable=True)
    volume = Column(Numeric(30, 8), nullable=True)
    currency = Column(String(10), nullable=True)
    received_at = Column(DateTime(timezone=True), nullable=False)
    quality_status = Column(String(30), nullable=False, default="GOOD")
    raw_payload = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    asset = relationship("AssetMaster", back_populates="daily_price_bars")


class MarketDataWatermark(Base):
    """Compact coverage boundary for one asset, provider, and data type."""

    __tablename__ = "market_data_watermarks"
    __table_args__ = (
        UniqueConstraint(
            "asset_id",
            "data_type",
            "provider",
            name="uq_market_data_watermarks_asset_type_provider",
        ),
        Index(
            "ix_market_data_watermarks_provider_type_covered",
            "provider",
            "data_type",
            "covered_to",
        ),
        Index("ix_market_data_watermarks_last_success", "last_success_at"),
    )

    id = Column(Integer, primary_key=True)
    asset_id = Column(Integer, ForeignKey("asset_master.id", ondelete="CASCADE"), nullable=False)
    data_type = Column(String(40), nullable=False)
    provider = Column(String(50), nullable=False)
    covered_from = Column(Date, nullable=True)
    covered_to = Column(Date, nullable=True)
    last_success_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    asset = relationship("AssetMaster", back_populates="market_data_watermarks")


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), unique=True, index=True, nullable=False)
    email_normalized = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    status = Column(String(20), default="ACTIVE", nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(String, default="user")  # user, admin
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    locale = Column(String(20), nullable=True)
    timezone = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    strategies = relationship("Strategy", back_populates="user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    daily_summaries = relationship("DailySummary", back_populates="user")
    weekly_reports = relationship("WeeklyReport", back_populates="user")
    trading_accounts = relationship("TradingAccount", back_populates="user")
    positions = relationship("Position", back_populates="user")
    daily_snapshots = relationship("DailySnapshot", back_populates="user")
    journal_entries = relationship("JournalEntry", back_populates="user")
    ai_summaries = relationship("AISummary", back_populates="user")
    credentials = relationship("UserCredential", back_populates="user", uselist=False)
    sessions = relationship("UserSession", back_populates="user")
    identities = relationship("UserIdentity", back_populates="user")
    auth_tokens = relationship("AuthToken", back_populates="user")
    truth_positions = relationship("TradingPosition", back_populates="user")
    position_events_v2 = relationship("PositionEvent", back_populates="user")
    account_ledger_entries = relationship("AccountLedgerEntry", back_populates="user")


class UserCredential(Base):
    __tablename__ = "user_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    password_updated_at = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="credentials")


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(20), nullable=False, default="ACTIVE")
    ip_address = Column(String(64), nullable=True)
    user_agent = Column(String(512), nullable=True)
    last_seen_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="sessions")
    auth_tokens = relationship("AuthToken", back_populates="session")


class UserIdentity(Base):
    __tablename__ = "user_identities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)
    provider_user_id = Column(String(255), nullable=False)
    email = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="identities")

    __table_args__ = (
        UniqueConstraint("provider", "provider_user_id", name="uq_user_identities_provider_user"),
    )


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    session_id = Column(Integer, ForeignKey("user_sessions.id"), nullable=False)
    token_jti = Column(String(64), unique=True, index=True, nullable=False)
    token_type = Column(String(20), nullable=False, default="bearer")
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="auth_tokens")
    session = relationship("UserSession", back_populates="auth_tokens")


class Invitation(Base):
    __tablename__ = "invitations"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    code_hash = Column(String(64), unique=True, index=True, nullable=False)
    created_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    redeemed_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    revoked_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    redeemed_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class SecurityAuditEvent(Base):
    __tablename__ = "security_audit_events"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    event_type = Column(String(80), nullable=False, index=True)
    outcome = Column(String(20), nullable=False)
    actor_user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    subject_type = Column(String(50), nullable=True)
    subject_public_id = Column(String(100), nullable=True)
    ip_address = Column(String(64), nullable=True)
    metadata_json = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())


class AuthRateLimitBucket(Base):
    __tablename__ = "auth_rate_limit_buckets"

    id = Column(Integer, primary_key=True, index=True)
    action = Column(String(40), nullable=False)
    dimension = Column(String(20), nullable=False)
    key_hash = Column(String(64), nullable=False)
    window_started_at = Column(DateTime(timezone=True), nullable=False)
    attempt_count = Column(Integer, nullable=False, default=0)
    blocked_until = Column(DateTime(timezone=True), nullable=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint(
            "action",
            "dimension",
            "key_hash",
            name="uq_auth_rate_limit_bucket_dimension",
        ),
    )




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
    display_currency = Column(String(10), default="USD")  # 显示币种: USD/HKD/CNY/EUR/GBP
    
    # Non-secret display/source preferences only. Provider credentials are platform-managed.
    ibkr_host = Column(String(255), nullable=True)
    ibkr_port = Column(Integer, nullable=True)
    ibkr_client_id = Column(Integer, nullable=True)
    ibkr_flex_start_date = Column(Date, nullable=True)
    binance_market_type = Column(String(20), nullable=True)
    binance_symbols = Column(JSON, nullable=True)
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
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
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
    truth_positions = relationship("TradingPosition", back_populates="account")
    ledger_entries = relationship("AccountLedgerEntry", back_populates="account")


class SystemSetting(Base):
    """全局系统设置 (Admin Only)"""
    __tablename__ = "system_settings"
    
    key = Column(String(50), primary_key=True)  # 配置键，如 'finnhub_api_key'
    value = Column(Text, nullable=True)         # 配置值
    description = Column(String(200), nullable=True) # 描述
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PlatformSetting(Base):
    __tablename__ = "platform_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    value = Column(Text, nullable=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class IntegrationCredential(Base):
    __tablename__ = "integration_credentials"

    id = Column(Integer, primary_key=True, index=True)
    provider_key = Column(String(50), nullable=False)
    credential_key = Column(String(100), nullable=False)
    secret_ciphertext = Column(Text, nullable=False)
    description = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("provider_key", "credential_key", name="uq_integration_credentials_provider_key"),
    )


class FeatureFlag(Base):
    __tablename__ = "feature_flags"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, index=True, nullable=False)
    enabled = Column(Boolean, default=False, nullable=False)
    actor_targets = Column(JSON, default=list)
    rollout_percentage = Column(Integer, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class TradingPosition(Base):
    __tablename__ = "trading_positions"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("trade_instruments.id"), nullable=False)
    strategy_id = Column(Integer, ForeignKey("strategies.id"), nullable=True)
    status = Column(SQLEnum(TradingPositionStatus), nullable=False, default=TradingPositionStatus.OPEN)
    side = Column(SQLEnum(TradingPositionSide), nullable=False)
    opened_at = Column(DateTime(timezone=True), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    opening_event_id = Column(Integer, nullable=True)
    closing_event_id = Column(Integer, nullable=True)
    base_currency = Column(String(10), nullable=False)
    cost_basis_method = Column(String(20), nullable=False, default="FIFO")
    quantity_opened = Column(Numeric(20, 8), nullable=True, default=0)
    quantity_closed = Column(Numeric(20, 8), nullable=True, default=0)
    avg_open_price = Column(Numeric(20, 8), nullable=True)
    avg_close_price = Column(Numeric(20, 8), nullable=True)
    realized_pnl_gross = Column(Numeric(20, 8), nullable=True, default=0)
    realized_pnl_net = Column(Numeric(20, 8), nullable=True, default=0)
    total_fees = Column(Numeric(20, 8), nullable=True, default=0)
    holding_period_seconds = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", back_populates="truth_positions")
    account = relationship("TradingAccount", back_populates="truth_positions")
    instrument = relationship("TradeInstrument", back_populates="positions")
    strategy = relationship("Strategy")
    events = relationship("PositionEvent", back_populates="position", order_by="PositionEvent.event_time")
    ledger_entries = relationship("AccountLedgerEntry", back_populates="position", order_by="AccountLedgerEntry.occurred_at")


class PositionEvent(Base):
    __tablename__ = "position_events"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("trading_positions.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("trade_instruments.id"), nullable=False)
    event_type = Column(SQLEnum(PositionEventType), nullable=False)
    event_time = Column(DateTime(timezone=True), nullable=False)
    side_effect = Column(String(20), nullable=True)
    quantity = Column(Numeric(20, 8), nullable=True)
    price = Column(Numeric(20, 8), nullable=True)
    currency = Column(String(10), nullable=True)
    gross_amount = Column(Numeric(20, 8), nullable=True)
    fee_amount = Column(Numeric(20, 8), nullable=True)
    fee_currency = Column(String(10), nullable=True)
    fx_rate_to_account_ccy = Column(Numeric(20, 8), nullable=True)
    realized_pnl_gross = Column(Numeric(20, 8), nullable=True)
    realized_pnl_net = Column(Numeric(20, 8), nullable=True)
    broker_exec_id = Column(String(255), nullable=True)
    external_order_id = Column(String(255), nullable=True)
    input_source = Column(String(50), nullable=True)
    source_run_id = Column(String(100), nullable=True)
    reason = Column(Text, nullable=True)
    emotion = Column(String(50), nullable=True)
    confidence = Column(Integer, nullable=True)
    thesis = Column(Text, nullable=True)
    edge_source = Column(Text, nullable=True)
    disconfirming_evidence = Column(Text, nullable=True)
    invalidation_rule = Column(Text, nullable=True)
    expected_holding_period = Column(String(100), nullable=True)
    planned_exit_rule = Column(Text, nullable=True)
    sizing_rationale = Column(Text, nullable=True)
    checklist_snapshot = Column(JSON, nullable=True)
    note = Column(Text, nullable=True)
    is_adjustment = Column(Boolean, nullable=False, default=False)
    reverses_event_id = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="position_events_v2")
    position = relationship("TradingPosition", back_populates="events")
    account = relationship("TradingAccount")
    instrument = relationship("TradeInstrument")
    ledger_entries = relationship("AccountLedgerEntry", back_populates="position_event")


class AccountLedgerEntry(Base):
    __tablename__ = "account_ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)
    position_id = Column(Integer, ForeignKey("trading_positions.id"), nullable=True)
    position_event_id = Column(Integer, ForeignKey("position_events.id"), nullable=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    entry_type = Column(SQLEnum(AccountLedgerEntryType), nullable=False)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    currency = Column(String(10), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    amount_account_ccy = Column(Numeric(20, 8), nullable=True)
    fx_rate_to_account_ccy = Column(Numeric(20, 8), nullable=True)
    source = Column(String(50), nullable=True)
    source_run_id = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="account_ledger_entries")
    account = relationship("TradingAccount", back_populates="ledger_entries")
    position = relationship("TradingPosition", back_populates="ledger_entries")
    position_event = relationship("PositionEvent", back_populates="ledger_entries")
    transaction = relationship("Transaction", back_populates="ledger_entries")


class BrokerSyncRun(Base):
    __tablename__ = "broker_sync_runs"
    __table_args__ = (
        Index("ix_broker_sync_runs_user_provider_created", "user_id", "provider", "created_at"),
        Index("ix_broker_sync_runs_status_created", "status", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), nullable=False)
    market_type = Column(String(50), nullable=True)
    status = Column(String(30), nullable=False, default="RUNNING")
    requested_start_date = Column(Date, nullable=True)
    requested_end_date = Column(Date, nullable=True)
    records_fetched = Column(Integer, nullable=False, default=0)
    records_inserted = Column(Integer, nullable=False, default=0)
    records_skipped = Column(Integer, nullable=False, default=0)
    error_message = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True, default=dict)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    executions = relationship("BrokerExecution", back_populates="sync_run", order_by="BrokerExecution.trade_time")


class BrokerExecution(Base):
    __tablename__ = "broker_executions"
    __table_args__ = (
        UniqueConstraint("idempotency_key", name="uq_broker_executions_idempotency_key"),
        Index("ix_broker_executions_user_provider_time", "user_id", "provider", "trade_time"),
        Index("ix_broker_executions_symbol_time", "symbol", "trade_time"),
    )

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    sync_run_id = Column(Integer, ForeignKey("broker_sync_runs.id"), nullable=True)
    provider = Column(String(50), nullable=False)
    market_type = Column(String(50), nullable=True)
    account_ref = Column(String(100), nullable=True)
    symbol = Column(String(100), nullable=False)
    side = Column(String(20), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    trade_time = Column(DateTime(timezone=True), nullable=False)
    currency = Column(String(10), nullable=True)
    commission = Column(Numeric(20, 8), nullable=True)
    commission_currency = Column(String(10), nullable=True)
    external_trade_id = Column(String(255), nullable=False)
    external_order_id = Column(String(255), nullable=True)
    idempotency_key = Column(String(500), nullable=False)
    raw_payload = Column(JSON, nullable=False, default=dict)
    import_status = Column(String(30), nullable=False, default="RAW")
    position_event_id = Column(Integer, ForeignKey("position_events.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    sync_run = relationship("BrokerSyncRun", back_populates="executions")
    position_event = relationship("PositionEvent")


class JobDefinition(Base):
    __tablename__ = "job_definitions"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    key = Column(String(120), unique=True, index=True, nullable=False)
    display_name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    queue_name = Column(String(80), nullable=False, default="default")
    retry_policy = Column(JSON, nullable=True, default=dict)
    timeout_seconds = Column(Integer, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    runs = relationship("JobRun", back_populates="definition", order_by="JobRun.created_at")


class JobRun(Base):
    __tablename__ = "job_runs"
    __table_args__ = (
        Index("ix_job_runs_status_next_run", "status", "next_run_at"),
        Index("ix_job_runs_user_created", "user_id", "created_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    job_definition_id = Column(Integer, ForeignKey("job_definitions.id"), nullable=False)
    idempotency_key = Column(String(255), nullable=True, index=True)
    status = Column(SQLEnum(JobRunStatus), nullable=False, default=JobRunStatus.QUEUED, index=True)
    priority = Column(Integer, nullable=False, default=0)
    payload = Column(JSON, nullable=True, default=dict)
    result = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=1)
    queue_name = Column(String(80), nullable=False, default="default")
    locked_by = Column(String(120), nullable=True)
    locked_at = Column(DateTime(timezone=True), nullable=True)
    next_run_at = Column(DateTime(timezone=True), nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    definition = relationship("JobDefinition", back_populates="runs")
    events = relationship("JobRunEvent", back_populates="job_run", order_by="JobRunEvent.created_at")
    idempotency_records = relationship("IdempotencyKey", back_populates="job_run")


class JobRunEvent(Base):
    __tablename__ = "job_run_events"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    job_run_id = Column(Integer, ForeignKey("job_runs.id"), nullable=False)
    event_type = Column(SQLEnum(JobRunEventType), nullable=False)
    from_status = Column(SQLEnum(JobRunStatus), nullable=True)
    to_status = Column(SQLEnum(JobRunStatus), nullable=True)
    message = Column(Text, nullable=True)
    metadata_json = Column("metadata", JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job_run = relationship("JobRun", back_populates="events")


class IdempotencyKey(Base):
    __tablename__ = "idempotency_keys"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "scope",
            "key",
            name="uq_idempotency_keys_user_scope_key",
        ),
        Index(
            "uq_idempotency_keys_system_scope_key",
            "scope",
            "key",
            unique=True,
            postgresql_where=text("user_id IS NULL"),
            sqlite_where=text("user_id IS NULL"),
        ),
    )

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    scope = Column(String(120), nullable=False)
    key = Column(String(255), nullable=False)
    request_hash = Column(String(255), nullable=False)
    status = Column(String(40), nullable=False, default="IN_PROGRESS")
    response_json = Column(JSON, nullable=True)
    job_run_id = Column(Integer, ForeignKey("job_runs.id"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")
    job_run = relationship("JobRun", back_populates="idempotency_records")


class BusinessLock(Base):
    __tablename__ = "business_locks"
    __table_args__ = (
        UniqueConstraint("scope", "resource_key", name="uq_business_locks_scope_resource"),
        Index("ix_business_locks_status_expires", "status", "expires_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    scope = Column(String(120), nullable=False, index=True)
    resource_key = Column(String(255), nullable=False, index=True)
    owner_id = Column(String(120), nullable=False)
    owner_type = Column(String(80), nullable=False, default="job_run")
    status = Column(SQLEnum(BusinessLockStatus), nullable=False, default=BusinessLockStatus.ACTIVE, index=True)
    metadata_json = Column("metadata", JSON, nullable=True, default=dict)
    acquired_at = Column(DateTime(timezone=True), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    released_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class DerivedTimelineSnapshot(Base):
    __tablename__ = "derived_timeline_snapshots"
    __table_args__ = (
        UniqueConstraint("user_id", "trading_position_public_id", name="uq_derived_timeline_snapshots_user_position"),
        Index("ix_derived_timeline_snapshots_user_refreshed", "user_id", "refreshed_at"),
    )

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    trading_position_public_id = Column(String(100), nullable=False, index=True)
    source = Column(String(120), nullable=False)
    snapshot_json = Column(JSON, nullable=False, default=dict)
    refreshed_by_job_run_public_id = Column(String(36), nullable=True, index=True)
    refreshed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")


class OutboxEvent(Base):
    __tablename__ = "outbox_events"
    __table_args__ = (
        Index("ix_outbox_events_status_available", "status", "available_at"),
        Index("ix_outbox_events_aggregate", "aggregate_type", "aggregate_public_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    aggregate_type = Column(String(100), nullable=False)
    aggregate_public_id = Column(String(100), nullable=True)
    event_type = Column(String(150), nullable=False)
    queue_name = Column(String(80), nullable=False, default="default")
    dedupe_key = Column(String(255), unique=True, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    status = Column(SQLEnum(OutboxEventStatus), nullable=False, default=OutboxEventStatus.PENDING, index=True)
    attempt_count = Column(Integer, nullable=False, default=0)
    last_error = Column(Text, nullable=True)
    available_at = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User")


class Position(Base):
    """持仓记录 - 汇总同标的的交易批次"""
    __tablename__ = "positions"
    
    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
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
    
    # Phase 2: MAE/MFE Analysis
    max_price_during_hold = Column(Numeric(20, 8), nullable=True) # 持仓期间最高价 (MFE for Long, MAE for Short)
    min_price_during_hold = Column(Numeric(20, 8), nullable=True) # 持仓期间最低价 (MAE for Long, MFE for Short)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    asset_metadata_symbol = Column(String(50), ForeignKey("asset_metadata.symbol"), nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="positions")
    trading_account = relationship("TradingAccount")
    strategy = relationship("Strategy")
    asset_metadata = relationship("AssetMetadata")
    batches = relationship("TradeBatch", back_populates="position", order_by="TradeBatch.time")
    



class TradeBatch(Base):
    """交易批次 - 加仓/减仓记录"""
    __tablename__ = "trade_batches"
    
    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
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
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
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
    ledger_entries = relationship("AccountLedgerEntry", back_populates="transaction")


class AIAnalysisResult(Base):
    """AI 分析结果持久化"""
    __tablename__ = "ai_analysis_results"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    analysis_type = Column(String(50), nullable=False) # e.g. "daily_summary", "time_analysis"
    ai_insights = Column(Text, nullable=True)          # Markdown content
    raw_data = Column(JSON, nullable=True)             # Chart data etc.
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    user = relationship("User")


class InsightRun(Base):
    """Auditable AI or analytics run that can produce evidence-linked artifacts."""
    __tablename__ = "insight_runs"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    run_type = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False, default="RUNNING")
    prompt_version = Column(String(100), nullable=True)
    input_refs = Column(JSON, nullable=False, default=list)
    started_at = Column(DateTime(timezone=True), nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User")
    artifacts = relationship("InsightArtifact", back_populates="run", order_by="InsightArtifact.created_at")


class InsightArtifact(Base):
    """Evidence-linked output produced by an InsightRun."""
    __tablename__ = "insight_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(36), unique=True, index=True, nullable=False, default=lambda: str(uuid.uuid4()))
    insight_run_id = Column(Integer, ForeignKey("insight_runs.id"), nullable=False, index=True)
    artifact_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    content_markdown = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    evidence_refs = Column(JSON, nullable=False, default=list)
    chart_schema = Column(JSON, nullable=True)
    trust_meta = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    run = relationship("InsightRun", back_populates="artifacts")
