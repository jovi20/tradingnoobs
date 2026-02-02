"""
Trading Noobs Backend - Trades Router
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc
from typing import List, Optional
from datetime import datetime

from database import get_db
from models import Trade, TradeStatus, User, TradingAccount
from schemas import TradeCreate, TradeClose, TradeUpdate, TradeResponse
from services.auth_service import get_current_user
from services.market_data_service import MarketDataService

router = APIRouter(prefix="/api/trades", tags=["Trades"])


@router.get("", response_model=List[TradeResponse])
async def get_trades(
    status: Optional[TradeStatus] = None,
    symbol: Optional[str] = None,
    exchange: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    sort_by: str = Query('entry_time', regex="^(entry_time|symbol|pnl|status)$"),
    order: str = Query('desc', regex="^(asc|desc)$"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all trades for current user with optional filters"""
    query = db.query(Trade).filter(Trade.user_id == current_user.id)
    
    if status:
        query = query.filter(Trade.status == status)
    if symbol:
        query = query.filter(Trade.symbol.ilike(f"%{symbol}%"))
    if exchange:
        query = query.filter(Trade.exchange == exchange)
    
    # Sorting
    if sort_by == 'pnl':
        # PnL is computed, so we might need special handling or just sort by DB column if persisted
        # For now, let's assume Trade.pnl or Trade.exit_price exists but pnl is @property
        # If PnL is not a DB column, we can't sort efficiently in SQL easily without expression
        # Fallback to entry_time if PnL sorting requested but not supported in DB yet
        # OR: sort in memory if page size is small? No, limit applies first.
        # Let's use 'entry_time' as fallback for complex calculated fields for now or sort python side if small
        pass # To be improved if PnL becomes a stored column
    
    sort_attr = getattr(Trade, sort_by, Trade.entry_time)
    if order == 'asc':
        query = query.order_by(asc(sort_attr))
    else:
        query = query.order_by(desc(sort_attr))

    trades = query.offset(skip).limit(limit).all()
    
    # Initialize Market Service
    market_service = MarketDataService(db)
    
    # Add computed properties
    result = []
    for trade in trades:
        # Fetch real-time price for OPEN positions
        if trade.status == TradeStatus.OPEN:
            try:
                quote = market_service.get_quote(trade.symbol)
                if quote and 'c' in quote:
                    trade.current_price = quote['c']
            except Exception as e:
                print(f"Failed to fetch price for {trade.symbol}: {e}")
                # Keep existing current_price or None

        trade_dict = TradeResponse.model_validate(trade).model_dump()
        trade_dict["pnl"] = trade.pnl
        trade_dict["pnl_percent"] = trade.pnl_percent
        result.append(TradeResponse(**trade_dict))
    
    return result


@router.post("", response_model=TradeResponse, status_code=status.HTTP_201_CREATED)
async def create_trade(
    trade_data: TradeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new trade (open or closed position)"""
    # Validate Account
    account = db.query(TradingAccount).filter(
        TradingAccount.id == trade_data.account_id,
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=400, detail="Invalid Trading Account")
        
    # Auto-populate exchange from account
    exchange_name = account.broker
    
    trade = Trade(
        user_id=current_user.id,
        account_id=trade_data.account_id,
        symbol=trade_data.symbol.upper(),
        exchange=exchange_name,
        entry_price=trade_data.entry_price,
        quantity=trade_data.quantity,
        entry_time=trade_data.entry_time,
        strategy_id=trade_data.strategy_id,
        entry_reason=trade_data.entry_reason,
        entry_emotion=trade_data.entry_emotion,
        entry_confidence=trade_data.entry_confidence,
        status=TradeStatus[trade_data.status.value]
    )
    
    # 如果是已平仓交易，设置平仓信息
    if trade_data.status.value == "CLOSED":
        trade.exit_price = trade_data.exit_price
        trade.exit_time = trade_data.exit_time or trade_data.entry_time
        trade.exit_reason = trade_data.exit_reason
    
    db.add(trade)
    db.commit()
    db.refresh(trade)
    return trade


@router.get("/{trade_id}", response_model=TradeResponse)
async def get_trade(
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific trade"""
    trade = db.query(Trade).filter(
        Trade.id == trade_id,
        Trade.user_id == current_user.id
    ).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    return trade


@router.patch("/{trade_id}", response_model=TradeResponse)
async def update_trade(
    trade_id: int,
    trade_data: TradeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a trade"""
    trade = db.query(Trade).filter(
        Trade.id == trade_id,
        Trade.user_id == current_user.id
    ).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    update_data = trade_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(trade, field, value)
    
    db.commit()
    db.refresh(trade)
    return trade


@router.post("/{trade_id}/close", response_model=TradeResponse)
async def close_trade(
    trade_id: int,
    close_data: TradeClose,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Close a trade (exit position)"""
    trade = db.query(Trade).filter(
        Trade.id == trade_id,
        Trade.user_id == current_user.id
    ).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    if trade.status == TradeStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Trade is already closed")
    
    trade.status = TradeStatus.CLOSED
    trade.exit_price = close_data.exit_price
    trade.exit_time = datetime.utcnow()
    trade.exit_reason = close_data.exit_reason
    trade.exit_emotion = close_data.exit_emotion
    trade.trade_review = close_data.trade_review
    trade.screenshots = close_data.screenshots or []
    trade.lessons = close_data.lessons or []
    trade.rating = close_data.rating
    
    db.commit()
    db.refresh(trade)
    return trade


@router.delete("/{trade_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_trade(
    trade_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a trade"""
    trade = db.query(Trade).filter(
        Trade.id == trade_id,
        Trade.user_id == current_user.id
    ).first()
    
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    
    db.delete(trade)
    db.commit()
