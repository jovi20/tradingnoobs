"""
Trading Noobs - Market Data Router
Provides market data endpoints including symbol validation
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Optional

from database import get_db
from routers.auth import get_current_user
from models import User
from services.market_data_service import MarketDataService

router = APIRouter(prefix="/api/market", tags=["market"])


@router.get("/validate/{symbol}")
async def validate_symbol(
    symbol: str,
    exchange: Optional[str] = Query(None, description="Exchange hint (e.g., BINANCE, HKEX)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    验证标的代码是否有效
    Returns symbol info if valid, error if not found
    """
    service = MarketDataService(db)
    return service.validate_symbol(symbol, exchange)


@router.get("/quote/{symbol}")
async def get_quote(
    symbol: str,
    exchange: Optional[str] = Query(None, description="Exchange hint"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取标的实时行情
    Automatically routes to appropriate provider based on symbol type
    """
    service = MarketDataService(db)
    
    try:
        quote = service.get_quote(symbol, exchange)
        asset_type = service.detect_asset_type(symbol, exchange)
        return {
            "symbol": symbol.upper(),
            "asset_type": asset_type,
            "quote": quote
        }
    except Exception as e:
        return {
            "symbol": symbol.upper(),
            "error": str(e)
        }


@router.get("/detect/{symbol}")
async def detect_asset_type(
    symbol: str,
    exchange: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    检测标的类型（不查询价格）
    """
    service = MarketDataService(db)
    asset_type = service.detect_asset_type(symbol, exchange)
    return {
        "symbol": symbol.upper(),
        "asset_type": asset_type,
        "provider": service._get_provider_name(asset_type)
    }
