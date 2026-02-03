"""
Trading Noobs Backend - Positions Router
Handles Position CRUD and Batch operations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from decimal import Decimal

from database import get_db
from routers.auth import get_current_user
from models import (
    User, Position, TradeBatch, TradingAccount,
    PositionStatus, PositionDirection, BatchType
)
from schemas import (
    PositionCreate, PositionUpdate, PositionResponse, PositionListResponse,
    TradeBatchCreate, TradeBatchResponse,
    PositionStatusEnum, BatchTypeEnum
)
from services.market_data_service import MarketDataService

router = APIRouter(prefix="/api/positions", tags=["positions"])


def recalculate_position(position: Position, db: Session):
    """Recalculate position aggregates after batch changes"""
    entry_batches = [b for b in position.batches if b.type == BatchType.ENTRY]
    exit_batches = [b for b in position.batches if b.type == BatchType.EXIT]
    
    # Total entry quantity and weighted avg price
    total_entry_qty = sum(float(b.quantity) for b in entry_batches)
    total_exit_qty = sum(float(b.quantity) for b in exit_batches)
    
    position.total_quantity = Decimal(str(total_entry_qty - total_exit_qty))
    
    # Weighted average entry price
    if total_entry_qty > 0:
        weighted_sum = sum(float(b.price) * float(b.quantity) for b in entry_batches)
        position.average_entry_price = Decimal(str(weighted_sum / total_entry_qty))
    
    # Realized PnL from exit batches
    position.realized_pnl = sum(b.pnl or Decimal(0) for b in exit_batches)
    
    # Auto-close if quantity is 0
    if position.total_quantity <= 0:
        position.status = PositionStatus.CLOSED
        from datetime import datetime, timezone
        position.closed_at = datetime.now(timezone.utc)
    else:
        position.status = PositionStatus.OPEN
        position.closed_at = None


@router.get("", response_model=List[PositionListResponse])
async def list_positions(
    status: Optional[PositionStatusEnum] = None,
    symbol: Optional[str] = None,
    account_id: Optional[int] = None,
    asset_type: Optional[str] = None, # Stock, Crypto
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all positions for the current user"""
    query = db.query(Position).filter(Position.user_id == current_user.id)
    
    if status:
        query = query.filter(Position.status == PositionStatus[status.value])
    if symbol:
        query = query.filter(Position.symbol.ilike(f"%{symbol}%"))
    if account_id:
        query = query.filter(Position.account_id == account_id)
    
    positions = query.order_by(desc(Position.opened_at)).all()
    
    # Post-Query Filtering for Asset Type
    if asset_type:
        market_service = MarketDataService(db)
        filtered_positions = []
        target_type = asset_type.lower() # 'stock', 'crypto'
        
        for pos in positions:
            detected_type = market_service.detect_asset_type(pos.symbol, pos.exchange)
            # Map specific types to categories
            category = 'crypto' if detected_type == 'CRYPTO' else 'stock'
            
            if category == target_type:
                filtered_positions.append(pos)
                
        return filtered_positions
        
    return positions


@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single position with all batches"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.user_id == current_user.id
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return position


@router.post("", response_model=PositionResponse, status_code=status.HTTP_201_CREATED)
async def create_position(
    position_data: PositionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new position with the first entry batch"""
    # Verify account belongs to user
    account = db.query(TradingAccount).filter(
        TradingAccount.id == position_data.account_id,
        TradingAccount.user_id == current_user.id
    ).first()
    
    if not account:
        raise HTTPException(status_code=400, detail="Invalid account_id")
    
    # Create position
    position = Position(
        user_id=current_user.id,
        account_id=position_data.account_id,
        strategy_id=position_data.strategy_id,
        symbol=position_data.symbol.upper(),
        exchange=account.broker,
        direction=PositionDirection[position_data.direction.value],
        status=PositionStatus.OPEN,
        total_quantity=position_data.quantity,
        average_entry_price=position_data.entry_price,
        realized_pnl=Decimal(0),
        opened_at=position_data.entry_time
    )
    db.add(position)
    db.flush()  # Get position ID
    
    # Create first entry batch
    first_batch = TradeBatch(
        position_id=position.id,
        type=BatchType.ENTRY,
        price=position_data.entry_price,
        quantity=position_data.quantity,
        time=position_data.entry_time,
        reason=position_data.entry_reason,
        emotion=position_data.entry_emotion,
        confidence=position_data.entry_confidence
    )
    db.add(first_batch)
    db.commit()
    db.refresh(position)
    
    return position


@router.patch("/{position_id}", response_model=PositionResponse)
async def update_position(
    position_id: int,
    position_data: PositionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update position review fields"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.user_id == current_user.id
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    update_data = position_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(position, key, value)
    
    db.commit()
    db.refresh(position)
    return position


@router.delete("/{position_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_position(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a position and all its batches"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.user_id == current_user.id
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    # Delete all batches first
    db.query(TradeBatch).filter(TradeBatch.position_id == position_id).delete()
    db.delete(position)
    db.commit()


# ============== Batch Endpoints ==============

@router.get("/{position_id}/batches", response_model=List[TradeBatchResponse])
async def list_batches(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all batches for a position"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.user_id == current_user.id
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    return position.batches


@router.post("/{position_id}/batches", response_model=TradeBatchResponse, status_code=status.HTTP_201_CREATED)
async def add_batch(
    position_id: int,
    batch_data: TradeBatchCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Add a new batch (entry or exit) to a position"""
    position = db.query(Position).filter(
        Position.id == position_id,
        Position.user_id == current_user.id
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    if position.status == PositionStatus.CLOSED:
        raise HTTPException(status_code=400, detail="Cannot add batch to closed position")
    
    # For EXIT batches, validate quantity and calculate PnL
    pnl = None
    if batch_data.type == BatchTypeEnum.EXIT:
        if batch_data.quantity > position.total_quantity:
            raise HTTPException(status_code=400, detail="Exit quantity exceeds position quantity")
        
        # Calculate PnL for this exit batch
        if position.average_entry_price:
            if position.direction == PositionDirection.LONG:
                pnl = (batch_data.price - position.average_entry_price) * batch_data.quantity
            else:  # SHORT
                pnl = (position.average_entry_price - batch_data.price) * batch_data.quantity
    
    batch = TradeBatch(
        position_id=position_id,
        type=BatchType[batch_data.type.value],
        price=batch_data.price,
        quantity=batch_data.quantity,
        time=batch_data.time,
        reason=batch_data.reason,
        emotion=batch_data.emotion,
        confidence=batch_data.confidence,
        pnl=pnl
    )
    db.add(batch)
    db.flush()
    
    # Recalculate position aggregates
    recalculate_position(position, db)
    
    db.commit()
    db.refresh(batch)
    return batch


@router.delete("/batches/{batch_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_batch(
    batch_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a batch from a position"""
    batch = db.query(TradeBatch).join(Position).filter(
        TradeBatch.id == batch_id,
        Position.user_id == current_user.id
    ).first()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    position = batch.position
    
    # Prevent deleting the only entry batch
    entry_count = len([b for b in position.batches if b.type == BatchType.ENTRY])
    if batch.type == BatchType.ENTRY and entry_count <= 1:
        raise HTTPException(status_code=400, detail="Cannot delete the only entry batch. Delete the position instead.")
    
    db.delete(batch)
    db.flush()
    
    # Recalculate position aggregates
    recalculate_position(position, db)
    
    db.commit()


# ============== Helper Endpoints ==============

@router.get("/check/{symbol}", response_model=Optional[PositionListResponse])
async def check_open_position(
    symbol: str,
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user has an open position for the given symbol and account"""
    position = db.query(Position).filter(
        Position.user_id == current_user.id,
        Position.symbol == symbol.upper(),
        Position.account_id == account_id,
        Position.status == PositionStatus.OPEN
    ).first()
    
    return position
