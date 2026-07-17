"""
Trading Noobs Backend - Configuration
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # Database
    # In production, use "postgresql://user:pass@db_host:5432/db_name"
    database_url: str = "sqlite:///./tradingnoobs.db"
    
    # Security
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 43200  # Default 30 days for better experience
    
    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost"
    
    # File Upload
    upload_dir: str = "./uploads"
    max_upload_size: int = 10 * 1024 * 1024  # 10MB
    
    # Environment
    env_name: str = "development"  # development / production
    auto_create_schema: Optional[bool] = None
    release_profile: str = "JOURNAL_BASELINE"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class _OptionalCapabilitySettings(BaseSettings):
    """Environment-backed settings loaded only by one optional capability."""

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


class AIProviderSettings(_OptionalCapabilitySettings):
    llm_api_url: str = "https://api.openai.com/v1"
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4-turbo"


class MarketProviderSettings(_OptionalCapabilitySettings):
    finnhub_api_key: Optional[str] = None


class BrokerProviderSettings(_OptionalCapabilitySettings):
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None


@lru_cache()
def get_settings() -> Settings:
    return Settings()


@lru_cache()
def get_ai_provider_settings() -> AIProviderSettings:
    return AIProviderSettings()


@lru_cache()
def get_market_provider_settings() -> MarketProviderSettings:
    return MarketProviderSettings()


@lru_cache()
def get_broker_provider_settings() -> BrokerProviderSettings:
    return BrokerProviderSettings()
