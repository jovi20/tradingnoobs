"""
Trading Noobs Backend - Database Models
"""
from sqlalchemy import (
    Column, Integer, String, Text, Boolean, DateTime, Date,
    ForeignKey, Numeric, JSON, Enum as SQLEnum
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


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    trades = relationship("Trade", back_populates="user")
    strategies = relationship("Strategy", back_populates="user")
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    daily_summaries = relationship("DailySummary", back_populates="user")
    weekly_reports = relationship("WeeklyReport", back_populates="user")


class Trade(Base):
    __tablename__ = "trades"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
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
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="trades")
    strategy = relationship("Strategy", back_populates="trades")
    
    @property
    def pnl(self):
        """Calculate P&L"""
        price = self.exit_price if self.status == TradeStatus.CLOSED else self.current_price
        if price and self.entry_price:
            return (float(price) - float(self.entry_price)) * float(self.quantity)
        return None
    
    @property
    def pnl_percent(self):
        """Calculate P&L percentage"""
        price = self.exit_price if self.status == TradeStatus.CLOSED else self.current_price
        if price and self.entry_price and float(self.entry_price) > 0:
            return ((float(price) - float(self.entry_price)) / float(self.entry_price)) * 100
        return None


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


class UserSettings(Base):
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    
    # Theme
    theme = Column(String(20), default="system")  # light/dark/system
    
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
