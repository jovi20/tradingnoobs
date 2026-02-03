"""
Trading Noobs Backend - Dashboard Router
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, timedelta

from database import get_db
from models import Trade, TradeStatus, User, Position, PositionStatus, TradingAccount
from schemas import DashboardStats, AssetAllocation, PositionMover, AccountAllocation
from services.auth_service import get_current_user
from services.market_data_service import MarketDataService

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics"""
    query = db.query(Trade).filter(Trade.user_id == current_user.id)
    
    if start_date:
        query = query.filter(Trade.entry_time >= start_date)
    if end_date:
        query = query.filter(Trade.entry_time <= end_date)
    
    trades = query.all()
    
    # Calculate stats
    closed_trades = [t for t in trades if t.status == TradeStatus.CLOSED]
    open_trades = [t for t in trades if t.status == TradeStatus.OPEN]
    
    total_pnl = 0.0
    winning_trades = 0
    total_wins = 0.0
    total_losses = 0.0
    
    for trade in closed_trades:
        pnl = trade.pnl or 0
        total_pnl += pnl
        if pnl > 0:
            winning_trades += 1
            total_wins += pnl
        elif pnl < 0:
            total_losses += abs(pnl)
    
    # Add unrealized P&L from open positions
    for trade in open_trades:
        pnl = trade.pnl or 0
        total_pnl += pnl
    
    win_rate = (winning_trades / len(closed_trades) * 100) if closed_trades else 0.0
    avg_pnl_ratio = (total_wins / total_losses) if total_losses > 0 else 0.0
    
    # --- New Logic: Asset Allocation & Movers (Using Positions) ---
    # 1. Get all OPEN positions
    positions = db.query(Position).filter(
        Position.user_id == current_user.id,
        Position.status == PositionStatus.OPEN
    ).all()
    
    # 2. Get Trading Accounts for Cash
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()
    
    # 3. Calculate Market Values & Fetch Prices for Movers
    market_service = MarketDataService(db)
    
    total_portfolio_value = 0.0
    allocation_map = {
        'Stock': 0.0,  # A_STOCK, HK_STOCK, US_STOCK
        'Crypto': 0.0, # CRYPTO
        'Cash': 0.0,
        'Fixed Income': 0.0 # Placeholder
    }
    
    movers_list = []
    
    # Process Positions
    for pos in positions:
        # Detect asset type if not stored (or use helper)
        asset_type = market_service.detect_asset_type(pos.symbol, pos.exchange)
        category = 'Crypto' if asset_type == 'CRYPTO' else 'Stock'
        
        # Use entry price and try to get current price
        entry_price = float(pos.average_entry_price or 0)
        current_price = entry_price
        change_pct = 0.0
        
        if entry_price > 0:
            try:
                # Try to fetch current quote
                quote = market_service.get_quote(pos.symbol, pos.exchange)
                if quote and quote.get('c'):
                    current_price = float(quote['c'])
                    # Calculate P&L percentage based on entry price
                    change_pct = ((current_price - entry_price) / entry_price) * 100
                    # Adjust for direction
                    if pos.direction == 'SHORT':
                        change_pct = -change_pct
            except:
                # If quote fails, calculate based on realized_pnl if available
                if pos.realized_pnl and pos.total_quantity > 0:
                    cost = entry_price * float(pos.total_quantity)
                    if cost > 0:
                        change_pct = (float(pos.realized_pnl) / cost) * 100
        
        market_value = float(pos.total_quantity) * current_price
        allocation_map[category] += market_value
        total_portfolio_value += market_value
        
        movers_list.append(PositionMover(
            id=pos.id,
            symbol=pos.symbol,
            asset_type=asset_type,
            change_percent=round(change_pct, 2),
            current_price=current_price
        ))
        
    # Process Cash
    # NOTE: Since we don't track real-time cash ledger yet, we use initial_balance or simple logic
    # For now, let's sum up initial_balances of accounts (this is rough, usually we need calculated balance)
    # We will assume account.initial_balance is "Available Cash" for this mockup
    for acc in accounts:
        cash = float(acc.initial_balance or 0) # This should be current balance in future
        allocation_map['Cash'] += cash
        total_portfolio_value += cash
        
    # Build Allocation List
    asset_allocation = []
    if total_portfolio_value > 0:
        for name, value in allocation_map.items():
            if value > 0:
                asset_allocation.append(AssetAllocation(
                    name=name,
                    value=value,
                    percent=round((value / total_portfolio_value) * 100, 2)
                ))
    
    # --- New Logic: Account Allocation ---
    account_value_map = {} # account_id -> value
    account_info_map = {acc.id: acc for acc in accounts}
    
    # Init with cash (using initial_balance as proxy for now)
    for acc in accounts:
        account_value_map[acc.id] = float(acc.initial_balance or 0)
        
    # Add open positions value
    for pos in positions:
        # Simplified valuation for account allocation (reuse cached or simple calc)
        # Note: We already calculated current_price in loop above but didn't store it by pos.id map
        # Ideally we should optimization this but for brevity:
        try:
            quote = market_service.get_quote(pos.symbol, pos.exchange)
            price = float(quote['c']) if quote and quote.get('c') else float(pos.average_entry_price or 0)
        except:
            price = float(pos.average_entry_price or 0)
            
        pos_value = float(pos.total_quantity) * price
        if pos.account_id in account_value_map:
            account_value_map[pos.account_id] += pos_value

    # Build Account Allocation List
    account_allocation = []
    if total_portfolio_value > 0:
         # Sort by value desc
         sorted_accounts = sorted(account_value_map.items(), key=lambda x: x[1], reverse=True)
         for acc_id, val in sorted_accounts[:5]: # Top 5
             acc = account_info_map.get(acc_id)
             if acc and val > 0:
                 account_allocation.append(AccountAllocation(
                     name=acc.name,
                     broker=acc.broker,
                     value=val,
                     percent=round((val / total_portfolio_value) * 100, 2)
                 ))
    
    # Build Movers - Sort by P&L percentage (all time performance)
    # Filter out positions with no change data
    valid_movers = [m for m in movers_list if m.change_percent != 0]
    if not valid_movers:
        valid_movers = movers_list  # Use all if none have change data
    
    sorted_movers = sorted(valid_movers, key=lambda x: x.change_percent, reverse=True)
    top_movers = sorted_movers[:3]
    bottom_movers = sorted(valid_movers, key=lambda x: x.change_percent)[:3]
    
    return DashboardStats(
        total_pnl=total_pnl,
        win_rate=win_rate,
        avg_pnl_ratio=avg_pnl_ratio,
        total_trades=len(trades),
        open_positions=len(open_trades),
        closed_trades=len(closed_trades),
        asset_allocation=asset_allocation,
        account_allocation=account_allocation,
        top_movers=top_movers,
        bottom_movers=bottom_movers
    )


@router.get("/pnl-history")
async def get_pnl_history(
    days: int = Query(30, ge=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get P&L history for chart"""
    # 如果 days 超过 1000，使用用户注册时间作为起点
    if days > 1000 and current_user.created_at:
        start_date = current_user.created_at.date()
    else:
        start_date = date.today() - timedelta(days=days)
    
    trades = db.query(Trade).filter(
        Trade.user_id == current_user.id,
        Trade.status == TradeStatus.CLOSED,
        Trade.exit_time >= start_date
    ).order_by(Trade.exit_time).all()
    
    # Group by date and calculate cumulative P&L
    pnl_by_date = {}
    for trade in trades:
        exit_date = trade.exit_time.date() if trade.exit_time else trade.entry_time.date()
        pnl = trade.pnl or 0
        pnl_by_date[exit_date] = pnl_by_date.get(exit_date, 0) + pnl
    
    # Calculate Total Principal for % calculation
    accounts = db.query(TradingAccount).filter(
        TradingAccount.user_id == current_user.id,
        TradingAccount.is_active == True
    ).all()
    total_principal = sum(float(acc.initial_balance or 0) for acc in accounts)

    # Build cumulative series
    result = []
    cumulative = 0
    current_date = start_date
    while current_date <= date.today():
        cumulative += pnl_by_date.get(current_date, 0)
        pnl_pct = (cumulative / total_principal * 100) if total_principal > 0 else 0
        result.append({
            "date": current_date.isoformat(),
            "pnl": cumulative,
            "pnl_percent": round(pnl_pct, 2)
        })
        current_date += timedelta(days=1)
    
    return result
