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
import asyncio

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
    
    # Calculate stats using SQL aggregations (OOM FIX)
    stats_query = db.query(
        func.count(Trade.id).label("total_trades"),
        func.sum(Trade.pnl).label("total_pnl"),
        func.count(Trade.id).filter(Trade.status == TradeStatus.CLOSED).label("closed_trades"),
        func.count(Trade.id).filter(Trade.status == TradeStatus.OPEN).label("open_positions"),
        func.count(Trade.id).filter(Trade.pnl > 0, Trade.status == TradeStatus.CLOSED).label("winning_trades"),
        func.sum(Trade.pnl).filter(Trade.pnl > 0, Trade.status == TradeStatus.CLOSED).label("total_wins"),
        func.sum(func.abs(Trade.pnl)).filter(Trade.pnl < 0, Trade.status == TradeStatus.CLOSED).label("total_losses")
    ).filter(Trade.user_id == current_user.id)
    
    if start_date:
        stats_query = stats_query.filter(Trade.entry_time >= start_date)
    if end_date:
        stats_query = stats_query.filter(Trade.entry_time <= end_date)
        
    s = stats_query.one()
    
    total_trades = s.total_trades or 0
    total_pnl = float(s.total_pnl or 0)
    closed_trades_count = s.closed_trades or 0
    open_positions_count = s.open_positions or 0
    winning_trades = s.winning_trades or 0
    total_wins = float(s.total_wins or 0)
    total_losses = float(s.total_losses or 0)
    
    win_rate = (winning_trades / closed_trades_count * 100) if closed_trades_count > 0 else 0.0
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
    
    # Parallelize asset type detection for all positions
    detection_tasks = [market_service.detect_asset_type_enhanced(p.symbol, p.exchange) for p in positions]
    asset_types = await asyncio.gather(*detection_tasks)
    
    total_portfolio_value = 0.0
    allocation_map = {
        'CASH': 0.0 # Reserve for cash
    }
    
    movers_list = []
    
    # Batch fetch quotes to fix N+1 (PARALLEL FETCH)
    quote_tasks = [market_service.get_quote(p.symbol, p.exchange) for p in positions]
    quotes = await asyncio.gather(*quote_tasks, return_exceptions=True)
    
    total_portfolio_value = 0.0
    allocation_map = {'CASH': 0.0}
    movers_list = []
    
    # Process Positions
    for pos, asset_type, quote in zip(positions, asset_types, quotes):
        category = asset_type
        entry_price = float(pos.average_entry_price or 0)
        current_price = entry_price
        change_pct = 0.0
        
        # Handle quote result (could be exception)
        if not isinstance(quote, Exception) and quote and quote.get('c'):
            current_price = float(quote['c'])
            if entry_price > 0:
                change_pct = ((current_price - entry_price) / entry_price) * 100
                if pos.direction == 'SHORT':
                    change_pct = -change_pct
        elif entry_price > 0:
            # Fallback if quote fails
            if pos.realized_pnl and pos.total_quantity > 0:
                cost = entry_price * float(pos.total_quantity)
                if cost > 0:
                    change_pct = (float(pos.realized_pnl) / cost) * 100
        
        market_value = float(pos.total_quantity) * current_price
        allocation_map[category] = allocation_map.get(category, 0.0) + market_value
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
        allocation_map['CASH'] += cash
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
        
    # Batch account valuation
    # Reuse current_prices if possible or simplified
    # (For account allocation, we can just use the movers_list data we just computed)
    pos_price_map = {m.id: m.current_price for m in movers_list}
    
    for pos in positions:
        price = pos_price_map.get(pos.id, float(pos.average_entry_price or 0))
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
        total_trades=total_trades,
        open_positions=open_positions_count,
        closed_trades=closed_trades_count,
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
    
    # Calculate daily P&L using SQL GROUP BY (OOM FIX)
    pnl_query = db.query(
        func.date(Trade.exit_time).label("date"),
        func.sum(Trade.pnl).label("daily_pnl")
    ).filter(
        Trade.user_id == current_user.id,
        Trade.status == TradeStatus.CLOSED,
        Trade.exit_time >= start_date
    ).group_by(func.date(Trade.exit_time)).order_by(func.date(Trade.exit_time))
    
    pnl_results = pnl_query.all()
    # Convert date to string for robust matching across SQLite/Postgres
    pnl_by_date = {str(res.date): float(res.daily_pnl or 0) for res in pnl_results}
    
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
        cumulative += pnl_by_date.get(current_date.isoformat(), 0)
        pnl_pct = (cumulative / total_principal * 100) if total_principal > 0 else 0
        result.append({
            "date": current_date.isoformat(),
            "pnl": cumulative,
            "pnl_percent": round(pnl_pct, 2)
        })
        current_date += timedelta(days=1)
    
    return result
