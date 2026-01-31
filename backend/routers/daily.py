"""
Trading Noobs Backend - Daily Summary Router
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from database import get_db
from models import DailySummary, User, Trade
from schemas import DailySummaryCreate, DailySummaryUpdate, DailySummaryResponse
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/daily", tags=["Daily Summary"])


@router.get("", response_model=List[DailySummaryResponse])
async def get_daily_summaries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all daily summaries for current user"""
    return db.query(DailySummary).filter(
        DailySummary.user_id == current_user.id
    ).order_by(DailySummary.date.desc()).all()


@router.get("/{summary_date}", response_model=DailySummaryResponse)
async def get_daily_summary(
    summary_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get daily summary for a specific date"""
    summary = db.query(DailySummary).filter(
        DailySummary.user_id == current_user.id,
        DailySummary.date == summary_date
    ).first()
    
    if not summary:
        raise HTTPException(status_code=404, detail="Daily summary not found")
    
    return summary


@router.post("", response_model=DailySummaryResponse, status_code=status.HTTP_201_CREATED)
async def create_daily_summary(
    summary_data: DailySummaryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a daily summary"""
    # Check if summary exists for this date
    existing = db.query(DailySummary).filter(
        DailySummary.user_id == current_user.id,
        DailySummary.date == summary_data.date
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=400,
            detail="Daily summary already exists for this date"
        )
    
    summary = DailySummary(
        user_id=current_user.id,
        date=summary_data.date,
        market_mood=summary_data.market_mood,
        personal_mood=summary_data.personal_mood,
        summary=summary_data.summary
    )
    db.add(summary)
    db.commit()
    db.refresh(summary)
    return summary


@router.patch("/{summary_date}", response_model=DailySummaryResponse)
async def update_daily_summary(
    summary_date: date,
    summary_data: DailySummaryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a daily summary"""
    summary = db.query(DailySummary).filter(
        DailySummary.user_id == current_user.id,
        DailySummary.date == summary_date
    ).first()
    
    if not summary:
        raise HTTPException(status_code=404, detail="Daily summary not found")
    
    update_data = summary_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(summary, field, value)
    
    db.commit()
    db.refresh(summary)
    return summary


@router.delete("/{summary_date}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_daily_summary(
    summary_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a daily summary"""
    summary = db.query(DailySummary).filter(
        DailySummary.user_id == current_user.id,
        DailySummary.date == summary_date
    ).first()
    
    if not summary:
        raise HTTPException(status_code=404, detail="Daily summary not found")
    
    db.delete(summary)
    db.commit()
