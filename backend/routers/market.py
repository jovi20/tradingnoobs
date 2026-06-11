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
from services.platform_config_service import get_finnhub_api_key

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
    return await service.validate_symbol(symbol, exchange)


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
        quote = await service.get_quote(symbol, exchange)
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
    asset_type = await service.detect_asset_type_enhanced(symbol, exchange)
    return {
        "symbol": symbol.upper(),
        "asset_type": asset_type,
        "provider": service._get_provider_name(asset_type)
    }


@router.get("/calendar")
async def get_market_calendar(
    market: str = Query("CN", description="Market: CN (A股), US (美股), HK (港股)"),
    year: int = Query(..., ge=2020, le=2030),
    month: int = Query(..., ge=1, le=12),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    获取市场日历
    返回指定市场、年月的交易日和节假日
    """
    from services.market_calendar import MarketCalendarService
    
    finnhub_key = get_finnhub_api_key(db)
    
    service = MarketCalendarService(finnhub_api_key=finnhub_key)
    return service.get_calendar(market, year, month)
