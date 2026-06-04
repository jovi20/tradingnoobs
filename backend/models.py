"""
Trading Noobs Backend - Database Models
"""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    ForeignKey, Numeric, JSON, Enum as SQLEnum, Index, UniqueConstraint
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
from services.identity_service import generate_public_id
import enum




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
    public_id = Column(String(26), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    email_normalized = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    status = Column(String(32), default="ACTIVE", nullable=False)
    role = Column(String, default="user")  # user, admin
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    locale = Column(String(16), default="en-US", nullable=False)
    timezone = Column(String(64), default="UTC", nullable=False)
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


class UserCredential(Base):
    __tablename__ = "user_credentials"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    credential_type = Column(String(32), nullable=False)
    credential_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class UserSession(Base):
    __tablename__ = "user_sessions"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(String(32), default="ACTIVE", nullable=False)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)


class UserIdentity(Base):
    __tablename__ = "user_identities"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(64), nullable=False)
    provider_subject = Column(String(255), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class AuthToken(Base):
    __tablename__ = "auth_tokens"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    token_type = Column(String(32), nullable=False)
    token_hash = Column(String(255), nullable=False)
    issued_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)




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


class AssetMaster(Base):
    """Canonical tradable asset identity."""
    __tablename__ = "asset_master"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    symbol = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    asset_class = Column(String(50), nullable=False, default="EQUITY")
    currency = Column(String(10), nullable=False, default="USD")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    instruments = relationship("TradeInstrument", back_populates="asset")


class TradeInstrument(Base):
    """Venue-specific instrument used by trading positions."""
    __tablename__ = "trade_instruments"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    asset_id = Column(Integer, ForeignKey("asset_master.id"), nullable=False)
    symbol = Column(String(50), index=True, nullable=False)
    venue = Column(String(50), nullable=False, default="UNKNOWN")
    instrument_type = Column(String(50), nullable=False, default="EQUITY")
    currency = Column(String(10), nullable=False, default="USD")
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    asset = relationship("AssetMaster", back_populates="instruments")
    positions = relationship("TradingPosition", back_populates="instrument")

    __table_args__ = (
        Index("idx_trade_instruments_symbol_venue", "symbol", "venue"),
    )


class TradingPosition(Base):
    """One complete trading lifecycle from open to close."""
    __tablename__ = "trading_positions"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)
    instrument_id = Column(Integer, ForeignKey("trade_instruments.id"), nullable=False)
    side = Column(String(10), nullable=False)
    status = Column(String(20), nullable=False, default="OPEN", index=True)
    cost_method = Column(String(20), nullable=False, default="FIFO")
    quantity_opened = Column(Numeric(20, 8), nullable=False, default=0)
    quantity_closed = Column(Numeric(20, 8), nullable=False, default=0)
    realized_pnl_gross = Column(Numeric(20, 8), nullable=False, default=0)
    realized_pnl_net = Column(Numeric(20, 8), nullable=False, default=0)
    fifo_lots = Column(JSON, nullable=False, default=list)
    thesis = Column(Text, nullable=True)
    opened_at = Column(DateTime(timezone=True), nullable=False)
    closed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    instrument = relationship("TradeInstrument", back_populates="positions")
    events = relationship("PositionEvent", back_populates="position", order_by="PositionEvent.event_time")
    ledger_entries = relationship("AccountLedgerEntry", back_populates="related_position")

    __table_args__ = (
        Index("idx_trading_positions_user_status", "user_id", "status"),
        Index("idx_trading_positions_account_status", "account_id", "status"),
    )


class PositionEvent(Base):
    """Append-only event that changes or documents a trading position."""
    __tablename__ = "position_events"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    position_id = Column(Integer, ForeignKey("trading_positions.id"), nullable=False)
    event_type = Column(String(32), nullable=False)
    quantity = Column(Numeric(20, 8), nullable=False)
    price = Column(Numeric(20, 8), nullable=False)
    fee = Column(Numeric(20, 8), nullable=False, default=0)
    realized_pnl_gross = Column(Numeric(20, 8), nullable=False, default=0)
    realized_pnl_net = Column(Numeric(20, 8), nullable=False, default=0)
    thesis = Column(Text, nullable=True)
    edge_source = Column(String(100), nullable=True)
    disconfirming_evidence = Column(Text, nullable=True)
    invalidation_rule = Column(Text, nullable=True)
    expected_holding_period = Column(String(100), nullable=True)
    planned_exit_rule = Column(Text, nullable=True)
    sizing_rationale = Column(Text, nullable=True)
    checklist_snapshot = Column(JSON, nullable=True)
    event_time = Column(DateTime(timezone=True), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    position = relationship("TradingPosition", back_populates="events")


class AccountLedgerEntry(Base):
    """Cash ledger truth for account and position-linked movements."""
    __tablename__ = "account_ledger_entries"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    account_id = Column(Integer, ForeignKey("trading_accounts.id"), nullable=False)
    related_position_id = Column(Integer, ForeignKey("trading_positions.id"), nullable=True)
    related_position_event_id = Column(Integer, ForeignKey("position_events.id"), nullable=True)
    entry_type = Column(String(32), nullable=False)
    amount = Column(Numeric(20, 8), nullable=False)
    currency = Column(String(10), nullable=False, default="USD")
    occurred_at = Column(DateTime(timezone=True), nullable=False, index=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    related_position = relationship("TradingPosition", back_populates="ledger_entries")

    __table_args__ = (
        Index("idx_account_ledger_entries_account_time", "account_id", "occurred_at"),
    )


class OutboxEvent(Base):
    """Pending domain event awaiting asynchronous publication."""
    __tablename__ = "outbox_events"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    event_type = Column(String(100), nullable=False)
    aggregate_type = Column(String(100), nullable=False)
    aggregate_public_id = Column(String(26), nullable=False, index=True)
    payload = Column(JSON, nullable=False)
    status = Column(String(32), nullable=False, default="PENDING", index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    published_at = Column(DateTime(timezone=True), nullable=True)


class JobDefinition(Base):
    """Catalog entry for a visible asynchronous job type."""
    __tablename__ = "job_definitions"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    job_key = Column(String(100), unique=True, index=True, nullable=False)
    description = Column(Text, nullable=True)
    queue_name = Column(String(100), nullable=False, default="default")
    max_attempts = Column(Integer, nullable=False, default=3)
    timeout_seconds = Column(Integer, nullable=False, default=300)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class IdempotencyKey(Base):
    """Retry-safety key scoped to an operation family."""
    __tablename__ = "idempotency_keys"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    scope = Column(String(100), nullable=False)
    key = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="IN_PROGRESS")
    request_hash = Column(String(128), nullable=True)
    response_payload = Column(JSON, nullable=True)
    locked_resource = Column(String(255), nullable=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("scope", "key", name="uq_idempotency_keys_scope_key"),
    )


class JobRun(Base):
    """Visible execution record for queued, running, failed, or completed jobs."""
    __tablename__ = "job_runs"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    job_definition_id = Column(Integer, ForeignKey("job_definitions.id"), nullable=True)
    idempotency_key_id = Column(Integer, ForeignKey("idempotency_keys.id"), nullable=True)
    job_key = Column(String(100), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="QUEUED", index=True)
    locked_resource = Column(String(255), nullable=True, index=True)
    attempts = Column(Integer, nullable=False, default=0)
    max_attempts = Column(Integer, nullable=False, default=3)
    payload = Column(JSON, nullable=False, default=dict)
    result_payload = Column(JSON, nullable=True)
    error_code = Column(String(100), nullable=True)
    error_message = Column(Text, nullable=True)
    queued_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)


class JobRunEvent(Base):
    """Append-only status/event line for a job run."""
    __tablename__ = "job_run_events"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    job_run_id = Column(Integer, ForeignKey("job_runs.id"), nullable=False)
    event_type = Column(String(64), nullable=False)
    message = Column(Text, nullable=True)
    payload = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class EvidenceItem(Base):
    """Source-backed evidence available to timeline, lifecycle, review, and AI artifacts."""
    __tablename__ = "evidence_items"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    kind = Column(String(64), nullable=False)
    source_name = Column(String(255), nullable=False)
    source_url_or_ref = Column(String(500), nullable=True)
    captured_at = Column(DateTime(timezone=True), nullable=False)
    summary = Column(Text, nullable=False)
    linked_tickers = Column(JSON, nullable=False, default=list)
    confidence = Column(String(32), nullable=False, default="MEDIUM")
    invalidates_if = Column(Text, nullable=True)
    linked_object_public_id = Column(String(26), nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ExternalCatalyst(Base):
    """Evidence-linked catalyst; not a raw news feed."""
    __tablename__ = "external_catalysts"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    catalyst_type = Column(String(64), nullable=False)
    title = Column(String(255), nullable=False)
    summary = Column(Text, nullable=False)
    evidence_public_id = Column(String(26), nullable=False, index=True)
    linked_object_public_id = Column(String(26), nullable=False, index=True)
    occurred_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class NarrativeSignal(Base):
    """Derived interpretation over evidence items."""
    __tablename__ = "narrative_signals"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    signal_type = Column(String(64), nullable=False)
    direction = Column(String(32), nullable=False)
    strength = Column(String(32), nullable=False)
    sample_size = Column(Integer, nullable=False, default=1)
    time_window = Column(String(64), nullable=True)
    linked_evidence_public_ids = Column(JSON, nullable=False, default=list)
    linked_object_public_id = Column(String(26), nullable=False, index=True)
    trust_meta = Column(JSON, nullable=False, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ProviderSymbolMapping(Base):
    """Provider-specific symbol mapping distinct from asset and instrument identity."""
    __tablename__ = "provider_symbol_mappings"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    asset_id = Column(Integer, ForeignKey("asset_master.id"), nullable=True)
    instrument_id = Column(Integer, ForeignKey("trade_instruments.id"), nullable=True)
    provider_key = Column(String(100), nullable=False, index=True)
    provider_symbol = Column(String(100), nullable=False)
    provider_market = Column(String(50), nullable=True)
    capabilities_json = Column(JSON, nullable=False, default=dict)
    quality_status = Column(String(32), nullable=False, default="ACTIVE")
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_verified_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_provider_symbol_mappings_provider_symbol", "provider_key", "provider_symbol"),
    )


class MarketDataCoverage(Base):
    """Coverage status for a provider mapping and data capability."""
    __tablename__ = "market_data_coverage"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    provider_symbol_mapping_id = Column(Integer, ForeignKey("provider_symbol_mappings.id"), nullable=False)
    capability = Column(String(64), nullable=False)
    quality_status = Column(String(32), nullable=False, default="ACTIVE")
    first_seen_at = Column(DateTime(timezone=True), server_default=func.now())
    last_verified_at = Column(DateTime(timezone=True), nullable=True)


class DashboardCache(Base):
    """Materialized dashboard/read-model payload with freshness metadata."""
    __tablename__ = "dashboard_cache"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    cache_key = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    as_of = Column(DateTime(timezone=True), nullable=False)
    freshness = Column(String(32), nullable=False, default="FRESH")
    source = Column(String(32), nullable=False, default="DERIVED")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("user_id", "cache_key", name="uq_dashboard_cache_user_key"),
    )


class PositionMetric(Base):
    """Materialized per-position metric payload with freshness metadata."""
    __tablename__ = "position_metrics"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
    position_public_id = Column(String(26), nullable=False, index=True)
    metric_key = Column(String(100), nullable=False)
    payload = Column(JSON, nullable=False, default=dict)
    as_of = Column(DateTime(timezone=True), nullable=False)
    freshness = Column(String(32), nullable=False, default="FRESH")
    source = Column(String(32), nullable=False, default="DERIVED")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    __table_args__ = (
        UniqueConstraint("position_public_id", "metric_key", name="uq_position_metrics_position_key"),
    )


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
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
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


class InsightArtifact(Base):
    """Evidence-linked output produced by an InsightRun."""
    __tablename__ = "insight_artifacts"

    id = Column(Integer, primary_key=True, index=True)
    public_id = Column(String(26), unique=True, index=True, nullable=False, default=generate_public_id)
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
