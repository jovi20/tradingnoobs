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
    
    # LLM Settings
    llm_api_url: str = "https://api.openai.com/v1"
    llm_api_key: Optional[str] = None
    llm_model: str = "gpt-4-turbo"
    
    # Market Data API Keys
    finnhub_api_key: Optional[str] = None
    binance_api_key: Optional[str] = None
    binance_api_secret: Optional[str] = None
    
    # Environment
    env_name: str = "development"  # development / production

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    return Settings()
