"""
Trading Noobs Backend - Dashboard Router
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional
from datetime import date, timedelta

from database import get_db
from models import Trade, TradeStatus, User
from schemas import DashboardStats
from services.auth_service import get_current_user

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
    
    return DashboardStats(
        total_pnl=total_pnl,
        win_rate=win_rate,
        avg_pnl_ratio=avg_pnl_ratio,
        total_trades=len(trades),
        open_positions=len(open_trades),
        closed_trades=len(closed_trades)
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
    
    # Build cumulative series
    result = []
    cumulative = 0
    current_date = start_date
    while current_date <= date.today():
        cumulative += pnl_by_date.get(current_date, 0)
        result.append({
            "date": current_date.isoformat(),
            "pnl": cumulative
        })
        current_date += timedelta(days=1)
    
    return result
