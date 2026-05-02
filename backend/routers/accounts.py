"""
Trading Noobs Backend - Trading Accounts Router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from database import get_db
from models import Position, PositionStatus, TradingAccount, User
from schemas import TradingAccountCreate, TradingAccountUpdate, TradingAccountResponse
from services.auth_service import get_current_user
from services.market_data_service import MarketDataService
from services.public_id_service import resolve_trading_account
from services.trading_accounting_service import calculate_mark_to_market_position
import asyncio
from decimal import Decimal

router = APIRouter(prefix="/api/accounts", tags=["Trading Accounts"])


def _enum_value(value):
    return value.value if hasattr(value, "value") else str(value)


@router.get("", response_model=List[TradingAccountResponse])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all trading accounts for current user with real-time NAV"""
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id
    ).order_by(TradingAccount.created_at.desc()).all()

    # 1. Get all OPEN positions for real-time valuation
    positions = db.query(Position).filter(
        Position.user_id == current_user.id,
        Position.status == PositionStatus.OPEN
    ).all()

    # 2. Fetch Market Data if there are open positions
    if positions:
        market_service = MarketDataService(db)
        # Parallelize quote fetching
        quote_tasks = [market_service.get_quote(p.symbol, p.exchange) for p in positions]
        quotes = await asyncio.gather(*quote_tasks, return_exceptions=True)
        
        # Map quotes by symbol
        quote_map = {}
        for i, p in enumerate(positions):
            quote = quotes[i]
            if not isinstance(quote, Exception) and quote and quote.get('c'):
                quote_map[f"{p.symbol}_{p.exchange}"] = float(quote['c'])
    else:
        quote_map = {}

    # 3. Calculate Market Value & NAV per Account
    results = []
    
    # Pre-calculate market value per account
    account_mv = {}
    for p in positions:
        if p.account_id:
            current_price = quote_map.get(f"{p.symbol}_{p.exchange}", float(p.average_entry_price or 0))
            mark = calculate_mark_to_market_position(
                open_quantity=p.total_quantity,
                avg_open_price=p.average_entry_price or 0,
                current_price=current_price,
                side=_enum_value(p.direction),
            )
            account_mv[p.account_id] = account_mv.get(p.account_id, 0.0) + float(mark.signed_market_value)

    for acc in accounts:
        mv = account_mv.get(acc.id, 0.0)
        cash = float(acc.cash_balance or 0)
        nav = cash + mv
        
        setattr(acc, 'market_value', Decimal(str(mv)))
        setattr(acc, 'total_equity', Decimal(str(nav)))
        results.append(acc)

    return results


@router.post("", response_model=TradingAccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: TradingAccountCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new trading account"""
    account = TradingAccount(
        user_id=current_user.id,
        name=account_data.name,
        broker=account_data.broker,
        account_type=account_data.account_type,
        currency=account_data.currency,
        initial_balance=account_data.initial_balance,
        description=account_data.description
    )
    db.add(account)
    db.commit()
    db.refresh(account)
    return account


@router.get("/{account_id}", response_model=TradingAccountResponse)
async def get_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific trading account"""
    account = resolve_trading_account(db, current_user.id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")

    # Calculate Real-time NAV & Market Value
    try:
        # 1. Get open positions for this account
        positions = db.query(Position).filter(
            Position.user_id == current_user.id,
            Position.account_id == account.id,
            Position.status == PositionStatus.OPEN
        ).all()

        market_value = Decimal("0")
        if positions:
            # 2. Fetch prices
            market_service = MarketDataService(db)
            quote_tasks = [market_service.get_quote(p.symbol, p.exchange) for p in positions]
            quotes = await asyncio.gather(*quote_tasks, return_exceptions=True)

            # 3. Sum up market value
            for i, p in enumerate(positions):
                quote = quotes[i]
                current_price = float(p.average_entry_price or 0)
                if not isinstance(quote, Exception) and quote and quote.get('c'):
                    current_price = float(quote['c'])
                
                mark = calculate_mark_to_market_position(
                    open_quantity=p.total_quantity,
                    avg_open_price=p.average_entry_price or 0,
                    current_price=current_price,
                    side=_enum_value(p.direction),
                )
                market_value += mark.signed_market_value
        
        # 4. Attach to response
        cash = account.cash_balance or Decimal("0")
        nav = cash + market_value
        
        setattr(account, 'market_value', market_value)
        setattr(account, 'total_equity', nav)
        
    except Exception as e:
        print(f"Error calculating account stats: {e}")
        # Fallback to stored values or 0
        setattr(account, 'market_value', Decimal("0"))
        setattr(account, 'total_equity', account.cash_balance or Decimal("0"))

    return account


@router.patch("/{account_id}", response_model=TradingAccountResponse)
async def update_account(
    account_id: str,
    account_data: TradingAccountUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a trading account"""
    account = resolve_trading_account(db, current_user.id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    update_data = account_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(account, key, value)
    
    db.commit()
    db.refresh(account)
    return account


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a trading account"""
    account = resolve_trading_account(db, current_user.id, account_id)
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    db.delete(account)
    db.commit()
    return None
