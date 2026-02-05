"""
Trading Noobs Backend - Positions Router
Handles Position CRUD and Batch operations
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse, JSONResponse
from fastapi.encoders import jsonable_encoder
from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Optional
from decimal import Decimal
import csv
import io
from datetime import datetime

from database import get_db
from routers.auth import get_current_user
from models import (
    User, Position, TradeBatch, TradingAccount, AssetMetadata,
    PositionStatus, PositionDirection, BatchType
)
from schemas import (
    PositionCreate, PositionUpdate, PositionResponse, PositionListResponse,
    TradeBatchCreate, TradeBatchUpdate, TradeBatchResponse,
    PositionStatusEnum, BatchTypeEnum, AssetMetadataUpdate
)
from models import AssetCoreType, AssetMarket, AssetRiskLevel, AssetCurrency
from services.market_data_service import MarketDataService
import asyncio

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


@router.get("")
async def list_positions(
    status: Optional[PositionStatusEnum] = None,
    symbol: Optional[str] = None,
    account_id: Optional[int] = None,
    asset_type: Optional[str] = None, # Stock, Crypto
    core_type: Optional[str] = None,
    market: Optional[str] = None,
    risk_level: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all positions for the current user"""
    from sqlalchemy.orm import joinedload
    query = db.query(Position).outerjoin(AssetMetadata).options(
        joinedload(Position.batches),
        joinedload(Position.asset_metadata)
    ).filter(Position.user_id == current_user.id)
    
    if status:
        query = query.filter(Position.status == PositionStatus[status.value])
    if symbol:
        query = query.filter(Position.symbol.ilike(f"%{symbol}%"))
    if account_id:
        query = query.filter(Position.account_id == account_id)
    
    if asset_type:
        query = query.filter(Position.asset_type == asset_type)
    
    if core_type:
        query = query.filter(AssetMetadata.core_type == core_type)
    if market:
        query = query.filter(AssetMetadata.market == market)
    if risk_level:
        query = query.filter(AssetMetadata.risk_level == risk_level)
    
    positions = query.order_by(desc(Position.opened_at)).all()
    
    # Get market data service for current prices
    market_service = MarketDataService(db)
    
    # Batch fetch quotes for open positions (PARALLEL FETCH)
    open_positions = [p for p in positions if p.status == PositionStatus.OPEN]
    quote_results = {}
    if open_positions:
        quote_tasks = [market_service.get_quote(p.symbol, p.exchange) for p in open_positions]
        quotes = await asyncio.gather(*quote_tasks, return_exceptions=True)
        for p, q in zip(open_positions, quotes):
            if not isinstance(q, Exception):
                quote_results[p.id] = q
    
    # Build response
    result = []
    for pos in positions:
        pos_dict = {

            'id': pos.id,
            'account_id': pos.account_id,
            'symbol': pos.symbol,
            'exchange': pos.exchange,
            'asset_type': pos.asset_type,
            'direction': pos.direction.value,
            'status': pos.status.value,
            'total_quantity': pos.total_quantity,
            'average_entry_price': pos.average_entry_price,
            'realized_pnl': pos.realized_pnl,
            'opened_at': pos.opened_at,
            'closed_at': pos.closed_at,
            'created_at': pos.created_at,
            'current_price': None,
            'created_at': pos.created_at,
            'current_price': None,
            'unrealized_pnl': None,
            'asset_metadata': None
        }

        # Populate asset_metadata
        if pos.asset_metadata:
            meta = pos.asset_metadata
            pos_dict['asset_metadata'] = {
                'symbol': meta.symbol,
                'name': meta.name,
                'core_type': meta.core_type,
                'market': meta.market,
                'currency': meta.currency,
                'sector': meta.sector,
                'risk_level': meta.risk_level,
                'risk_level': meta.risk_level,
                'instrument': meta.instrument
            }

        # Populate batches for detailed view (since frontend logic is simplified)
        pos_dict['batches'] = [
            {
                'id': b.id,
                'position_id': b.position_id,
                'type': b.type.value,
                'price': b.price,
                'quantity': b.quantity,
                'time': b.time,
                'reason': b.reason,
                'emotion': b.emotion,
                'confidence': b.confidence,
                'pnl': b.pnl,
                'created_at': b.created_at
            } for b in pos.batches
        ]
        
        if pos.status == PositionStatus.OPEN:
            quote = quote_results.get(pos.id)
            if quote and quote.get('c') is not None:
                current_price = float(quote['c'])
                pos_dict['current_price'] = current_price
                # Calculate unrealized P&L
                if pos.average_entry_price:
                    entry = float(pos.average_entry_price)
                    qty = float(pos.total_quantity)
                    if pos.direction == PositionDirection.LONG:
                        pos_dict['unrealized_pnl'] = (current_price - entry) * qty
                    else:
                        pos_dict['unrealized_pnl'] = (entry - current_price) * qty
        else:
            # For closed positions, calculate weighted average exit price from EXIT batches
            if pos.batches:
                exit_batches = [b for b in pos.batches if b.type == BatchType.EXIT]
                if exit_batches:
                    total_exit_qty = sum(float(b.quantity) for b in exit_batches)
                    if total_exit_qty > 0:
                        weighted_exit_price = sum(
                            float(b.price) * float(b.quantity) for b in exit_batches
                        ) / total_exit_qty
                        pos_dict['current_price'] = weighted_exit_price
        
        result.append(pos_dict)
        

        
    return JSONResponse(content=jsonable_encoder(result))


@router.get("/{position_id}", response_model=PositionResponse)
async def get_position(
    position_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a single position with all batches"""
    from sqlalchemy.orm import joinedload
    position = db.query(Position).options(
        joinedload(Position.batches),
        joinedload(Position.asset_metadata)
    ).filter(
        Position.id == position_id,
        Position.user_id == current_user.id
    ).first()
    
    if not position:
        raise HTTPException(status_code=404, detail="Position not found")
    
    # Enrich with market data if open
    if position.status == PositionStatus.OPEN:
        market_service = MarketDataService(db)
        # Use metadata hints for more accurate quote
        meta = position.asset_metadata
        try:
            quote = await market_service.get_quote(
                position.symbol, 
                position.exchange,
                core_type=meta.core_type.value if meta and meta.core_type else None,
                market=meta.market.value if meta and meta.market else None,
                instrument=meta.instrument if meta else None
            )
            
            if quote and quote.get('c') is not None:
                current_price = float(quote['c'])
                position.current_price = current_price
                if position.average_entry_price:
                    entry = float(position.average_entry_price)
                    qty = float(position.total_quantity)
                    if position.direction == PositionDirection.LONG:
                        position.unrealized_pnl = (current_price - entry) * qty
                    else:
                        position.unrealized_pnl = (entry - current_price) * qty
        except Exception as e:
            print(f"Error fetching quote for {position.symbol}: {e}")
            # Continue without real-time price
            pass
                    
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
    
    # Detect Asset Type
    market_service = MarketDataService(db)
    detected_type = position_data.asset_type
    if not detected_type:
        detected_type = await market_service.detect_asset_type_enhanced(position_data.symbol, account.broker)

    # Ensure AssetMetadata exists for this symbol
    symbol_upper = position_data.symbol.upper()
    asset_meta = db.query(AssetMetadata).filter(AssetMetadata.symbol == symbol_upper).first()
    if not asset_meta:
        # Create basic metadata - will be enriched via API or manual update
        asset_meta = AssetMetadata(symbol=symbol_upper, name=symbol_upper)
        db.add(asset_meta)
        db.flush()
    
    # Create position with asset_metadata_symbol link
    position = Position(
        user_id=current_user.id,
        account_id=position_data.account_id,
        strategy_id=position_data.strategy_id,
        symbol=symbol_upper,
        exchange=account.broker,
        asset_type=detected_type,
        asset_metadata_symbol=symbol_upper,  # Link to metadata
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
    
    # Handle Asset Metadata Update
    metadata_update = update_data.pop('asset_metadata', None)
    if metadata_update:
        # Find or create metadata for this symbol
        asset_meta = db.query(AssetMetadata).filter(
            AssetMetadata.symbol == position.symbol
        ).first()
        
        if not asset_meta:
            asset_meta = AssetMetadata(symbol=position.symbol)
            db.add(asset_meta)
            
        # Update fields
        for key, value in metadata_update.items():
            if value is not None:
                # Handle Enums if necessary (SQLAlchemy might handle string->Enum if valid)
                # But manual mapping helps avoid errors if strings don't match exactly or empty
                if key == 'core_type' and value:
                    setattr(asset_meta, key, AssetCoreType[value])
                elif key == 'market' and value:
                    setattr(asset_meta, key, AssetMarket[value])
                elif key == 'risk_level' and value:
                    setattr(asset_meta, key, AssetRiskLevel[value])
                else:
                    setattr(asset_meta, key, value)
        
        # Ensure the link exists
        if position.asset_metadata_symbol != position.symbol:
            position.asset_metadata_symbol = position.symbol
    
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


@router.patch("/batches/{batch_id}", response_model=TradeBatchResponse)
async def update_batch(
    batch_id: int,
    batch_data: TradeBatchUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a trade batch and recalculate position"""
    batch = db.query(TradeBatch).join(Position).filter(
        TradeBatch.id == batch_id,
        Position.user_id == current_user.id
    ).first()
    
    if not batch:
        raise HTTPException(status_code=404, detail="Batch not found")
    
    update_data = batch_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(batch, key, value)
    
    # If this is an EXIT batch, we might need to recalculate its PnL
    # But recalculate_position handles the overall PnL, let's ensure individual batch pnl is correct
    if batch.type == BatchType.EXIT:
        position = batch.position
        if position.average_entry_price:
            if position.direction == PositionDirection.LONG:
                batch.pnl = (batch.price - position.average_entry_price) * batch.quantity
            else:
                batch.pnl = (position.average_entry_price - batch.price) * batch.quantity
    
    db.flush()
    recalculate_position(batch.position, db)
    db.commit()
    db.refresh(batch)
    return batch


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


# ============== Export Endpoints ==============

@router.get("/export/csv")
async def export_positions_csv(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Export all positions and batches to CSV with comprehensive metadata"""
    # Query with all relationships
    from sqlalchemy.orm import joinedload
    positions = db.query(Position).options(
        joinedload(Position.batches),
        joinedload(Position.asset_metadata),
        joinedload(Position.trading_account)
    ).filter(
        Position.user_id == current_user.id
    ).order_by(desc(Position.opened_at)).all()
    
    # Create CSV in memory
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header
    writer.writerow([
        'Position ID', 'Symbol', 'Name', 'Asset Class', 'Market', 'Sector', 
        'Exchange/Broker', 'Account', 'Account Type',
        'Direction', 'Status', 
        'Total Quantity', 'Avg Entry Price', 'Realized PnL',
        'Opened At', 'Closed At', 'Position Review', 'Lessons',
        'Batch ID', 'Batch Type', 'Batch Price', 'Batch Quantity',
        'Batch Time', 'Batch PnL', 'Batch Reason', 'Batch Emotion', 'Batch Confidence'
    ])
    
    # Data rows
    for pos in positions:
        # Prepare position-level fields
        lessons_str = ', '.join(pos.lessons) if pos.lessons else ''
        
        # Asset Metadata fields
        asset_name = pos.asset_metadata.name if pos.asset_metadata else ''
        asset_core_type = pos.asset_metadata.core_type.value if pos.asset_metadata and pos.asset_metadata.core_type else ''
        asset_market = pos.asset_metadata.market.value if pos.asset_metadata and pos.asset_metadata.market else ''
        asset_sector = pos.asset_metadata.sector if pos.asset_metadata else ''
        
        # Account fields
        account_name = pos.trading_account.name if pos.trading_account else ''
        account_type = pos.trading_account.account_type if pos.trading_account else ''
        
        # Helper for basic fields
        def fmt_float(val):
            return float(val) if val is not None else 0
            
        def fmt_date(val):
            return val.isoformat() if val else ''

        # Export position with each batch
        if pos.batches:
            for batch in pos.batches:
                writer.writerow([
                    pos.id,
                    pos.symbol,
                    asset_name,
                    asset_core_type,
                    asset_market,
                    asset_sector,
                    pos.exchange,
                    account_name,
                    account_type,
                    pos.direction.value if pos.direction else '',
                    pos.status.value if pos.status else '',
                    fmt_float(pos.total_quantity),
                    fmt_float(pos.average_entry_price),
                    fmt_float(pos.realized_pnl),
                    fmt_date(pos.opened_at),
                    fmt_date(pos.closed_at),
                    pos.trade_review or '',
                    lessons_str,
                    batch.id,
                    batch.type.value if batch.type else '',
                    fmt_float(batch.price),
                    fmt_float(batch.quantity),
                    fmt_date(batch.time),
                    fmt_float(batch.pnl),
                    batch.reason or '',
                    batch.emotion or '',
                    batch.confidence or ''
                ])
        else:
            # Position without batches (shouldn't happen but handle gracefully)
            writer.writerow([
                pos.id,
                pos.symbol,
                asset_name,
                asset_core_type,
                asset_market,
                asset_sector,
                pos.exchange,
                account_name,
                account_type,
                pos.direction.value if pos.direction else '',
                pos.status.value if pos.status else '',
                fmt_float(pos.total_quantity),
                fmt_float(pos.average_entry_price),
                fmt_float(pos.realized_pnl),
                fmt_date(pos.opened_at),
                fmt_date(pos.closed_at),
                pos.trade_review or '',
                lessons_str,
                '', '', '', '', '', '', '', '', ''
            ])
    
    # Prepare response with UTF-8 BOM for Excel compatibility
    output.seek(0)
    csv_content = '\ufeff' + output.getvalue()  # Add BOM for Excel
    filename = f"trading_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    return StreamingResponse(
        iter([csv_content.encode('utf-8')]),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

