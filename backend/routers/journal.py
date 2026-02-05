"""
Trading Noobs Backend - Journal Entry Router
用户随笔功能：每天最多5条，每条最多500字
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import date

from database import get_db
from models import JournalEntry, User
from schemas import JournalEntryCreate, JournalEntryUpdate, JournalEntryResponse
from services.auth_service import get_current_user

router = APIRouter(prefix="/api/journal", tags=["Journal"])

MAX_ENTRIES_PER_DAY = 5


@router.get("", response_model=List[JournalEntryResponse])
async def get_all_entries(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取当前用户的所有随笔"""
    return db.query(JournalEntry).filter(
        JournalEntry.user_id == current_user.id
    ).order_by(JournalEntry.date.desc(), JournalEntry.created_at.desc()).all()


@router.get("/{entry_date}", response_model=List[JournalEntryResponse])
async def get_entries_by_date(
    entry_date: date,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """获取指定日期的随笔列表"""
    return db.query(JournalEntry).filter(
        JournalEntry.user_id == current_user.id,
        JournalEntry.date == entry_date
    ).order_by(JournalEntry.created_at.desc()).all()


@router.post("", response_model=JournalEntryResponse, status_code=status.HTTP_201_CREATED)
async def create_entry(
    entry_data: JournalEntryCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """创建随笔（每天最多5条）"""
    # 检查当天随笔数量
    count = db.query(JournalEntry).filter(
        JournalEntry.user_id == current_user.id,
        JournalEntry.date == entry_data.date
    ).count()
    
    if count >= MAX_ENTRIES_PER_DAY:
        raise HTTPException(
            status_code=400,
            detail=f"每天最多只能创建 {MAX_ENTRIES_PER_DAY} 条随笔"
        )
    
    entry = JournalEntry(
        user_id=current_user.id,
        date=entry_data.date,
        content=entry_data.content
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


@router.patch("/{entry_id}", response_model=JournalEntryResponse)
async def update_entry(
    entry_id: int,
    entry_data: JournalEntryUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """更新随笔"""
    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id,
        JournalEntry.user_id == current_user.id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="随笔不存在")
    
    if entry_data.content is not None:
        entry.content = entry_data.content
    
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """删除随笔"""
    entry = db.query(JournalEntry).filter(
        JournalEntry.id == entry_id,
        JournalEntry.user_id == current_user.id
    ).first()
    
    if not entry:
        raise HTTPException(status_code=404, detail="随笔不存在")
    
    db.delete(entry)
    db.commit()
