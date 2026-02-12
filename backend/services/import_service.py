import pandas as pd
import io
import uuid
import logging
from typing import List, Dict, Any, Tuple
from datetime import datetime
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException

from models import AssetCoreType, PositionDirection, BatchType, Position, TradeBatch, Strategy
from schemas import PositionCreate, BatchTypeEnum, PositionDirectionEnum

# In-memory cache for uploaded files preview (in production use Redis)
# format: {token: {rows: [], df: DataFrame, meta: {}}}
IMPORT_CACHE = {}

logger = logging.getLogger(__name__)

class ImportService:
    def __init__(self, db: Session):
        self.db = db

    async def parse_file(self, file: UploadFile) -> Tuple[str, List[Dict]]:
        """
        Parse uploaded file (CSV/Excel) and return a token and preview items.
        """
        content = await file.read()
        filename = file.filename.lower()
        
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(content))
            elif filename.endswith(('.xls', '.xlsx')):
                df = pd.read_excel(io.BytesIO(content))
            else:
                raise HTTPException(status_code=400, detail="Unsupported file format. Use CSV or Excel.")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse file: {str(e)}")
            
        # Normalize headers: strip details, lowercase
        df.columns = [str(c).strip().lower() for c in df.columns]
        
        # Validate required columns
        required_cols = {'symbol', 'date', 'direction', 'action', 'price', 'quantity'}
        missing = required_cols - set(df.columns)
        if missing:
             # Try mapping common alternatives
            column_map = {
                'code': 'symbol', 'ticker': 'symbol',
                'time': 'date', 'datetime': 'date', 'date': 'date',
                'time (yyyy-mm-dd hh:mm)': 'date',
                'side': 'direction', 'type': 'direction',
                'operation': 'action',
                'cost': 'price', 'avg_price': 'price',
                'amount': 'quantity', 'qty': 'quantity',
                'comm': 'commission', 'fee': 'commission',
                'comm': 'commission', 'fee': 'commission',
                'review': 'reason', 'note': 'reason',
                'plan entry': 'planned_entry_price', 'planned entry': 'planned_entry_price',
                'plan sl': 'planned_stop_loss', 'planned sl': 'planned_stop_loss', 'sl': 'planned_stop_loss',
                'asset type': 'asset_type', 'type': 'asset_type'
            }
            df.rename(columns=column_map, inplace=True)
            missing = required_cols - set(df.columns)
            if missing:
                raise HTTPException(status_code=400, detail=f"Missing required columns: {', '.join(missing)}")

        # Limit preview rows
        preview_rows = []
        rows_to_cache = []
        
        for index, row in df.iterrows():
            row_dict = row.to_dict()
            is_valid, errors, parsed = self._validate_row(row_dict)
            
            item = {
                "index": index,
                "data": {k: str(v) for k, v in row_dict.items() if pd.notna(v)}, # Strings for JSON
                "is_valid": is_valid,
                "errors": errors,
                "parsed": parsed
            }
            preview_rows.append(item)
            rows_to_cache.append(item)

        # Generate Token
        token = str(uuid.uuid4())
        IMPORT_CACHE[token] = rows_to_cache
        
        return token, preview_rows

    def _validate_row(self, row: Dict) -> Tuple[bool, List[str], Dict]:
        """
        Validate a single row of data.
        Returns: (is_valid, errors, parsed_data)
        """
        errors = []
        parsed = {}
        
        # 1. Symbol
        if pd.isna(row.get('symbol')):
            errors.append("Symbol is required")
        else:
            parsed['symbol'] = str(row['symbol']).upper()
            
        # 2. Date
        try:
            date_val = row.get('date')
            parsed['entry_time'] = pd.to_datetime(date_val).to_pydatetime()
        except:
            errors.append("Invalid Date format")
            
        # 3. Price & Quantity
        try:
            parsed['price'] = float(row['price'])
            if parsed['price'] < 0: errors.append("Price must be positive")
        except:
             errors.append("Invalid Price")
             
        try:
            parsed['quantity'] = float(row['quantity'])
            if parsed['quantity'] <= 0: errors.append("Quantity must be positive")
        except:
             errors.append("Invalid Quantity")

        # 4. Direction (Long/Short)
        direction_raw = str(row.get('direction', '')).upper()
        if direction_raw in ['LONG', 'BUY', 'L']:
            parsed['direction'] = PositionDirectionEnum.LONG
        elif direction_raw in ['SHORT', 'SELL', 'S']:
            parsed['direction'] = PositionDirectionEnum.SHORT
        else:
            errors.append("Invalid Direction (LONG/SHORT)")

        # 5. Action (Entry/Exit)
        action_raw = str(row.get('action', '')).upper()
        if action_raw in ['OPEN', 'ENTRY', 'BUY', '加仓', '建仓']:
            parsed['type'] = BatchTypeEnum.ENTRY
        elif action_raw in ['CLOSE', 'EXIT', 'SELL', '减仓', '平仓']:
            parsed['type'] = BatchTypeEnum.EXIT
        else:
            errors.append("Invalid Action (OPEN/CLOSE)")
            
        # Optional fields
        parsed['reason'] = str(row.get('reason', '')) if pd.notna(row.get('reason')) else None
        
        # New Fields for Enhanced Import
        parsed['strategy'] = str(row.get('strategy', '')).strip() if pd.notna(row.get('strategy')) else None
        parsed['emotion'] = str(row.get('emotion', '')).strip() if pd.notna(row.get('emotion')) else None
        parsed['asset_type'] = str(row.get('asset_type', '')).strip() if pd.notna(row.get('asset_type')) else None
        
        # Planned Prices
        try:
             if pd.notna(row.get('planned_entry_price')):
                 parsed['planned_entry_price'] = float(row['planned_entry_price'])
             else:
                 parsed['planned_entry_price'] = None
        except:
             parsed['planned_entry_price'] = None

        try:
             if pd.notna(row.get('planned_stop_loss')):
                 parsed['planned_stop_loss'] = float(row['planned_stop_loss'])
             else:
                 parsed['planned_stop_loss'] = None
        except:
             parsed['planned_stop_loss'] = None
        
        # Confidence (1-5)
        if pd.notna(row.get('confidence')):
            try:
                conf = int(float(row['confidence']))
                if 1 <= conf <= 5:
                    parsed['confidence'] = conf
                else:
                    # errors.append("Confidence must be 1-5") # Optional, or clamp/ignore
                    parsed['confidence'] = None
            except:
                pass # Ignore invalid confidence
        else:
            parsed['confidence'] = None
            
        # Commission (optional, simple deduction from pnl or addition to cost)
        # For now, just parse it, logic later
        if pd.notna(row.get('commission')):
            try:
                parsed['commission'] = float(row['commission'])
            except:
                pass
        
        return len(errors) == 0, errors, parsed

    def process_import(self, token: str, account_id: int, user_id: int, selected_indices: List[int] = None):
        """
        Commit the import to the database.
        """
        if token not in IMPORT_CACHE:
            raise HTTPException(status_code=400, detail="Import session expired")
            
        cached_rows = IMPORT_CACHE[token]
        processed_count = 0
        
        # Filter rows
        if selected_indices:
            rows_to_process = [r for r in cached_rows if r['index'] in selected_indices and r['is_valid']]
        else:
            rows_to_process = [r for r in cached_rows if r['is_valid']]
            
        # Sort by time to ensure logical order
        rows_to_process.sort(key=lambda x: x['parsed']['entry_time'])
        
        # Pre-fetch strategies for lookup
        strategies = self.db.query(Strategy).filter(Strategy.user_id == user_id).all()
        strategy_map = {s.name.lower(): s.id for s in strategies}
        
        for row in rows_to_process:
            data = row['parsed']
            
            # Resolve Strategy ID
            strategy_name = data.get('strategy')
            strategy_id = None
            if strategy_name:
                strategy_id = strategy_map.get(strategy_name.lower())
                # If strategy doesn't exist, ignore or create? For now ignore.
                
            data['strategy_id'] = strategy_id
            
            self._save_trade(data, account_id, user_id)
            processed_count += 1
            
        # Clear cache
        del IMPORT_CACHE[token]
        return processed_count

    def _save_trade(self, data: Dict, account_id: int, user_id: int):
        """
        Save a single trade row as a Position or Batch.
        """
        symbol = data['symbol']
        direction = data['direction'] # Enum
        batch_type = data['type'] # Enum
        
        # 1. Find existing open position
        # Rules: Same Symbol, Same Direction, Same Account, Open
        # Note: Direction check is strict. You can't add a SHORT batch to a LONG position usually, unless it's a flip (not supported yet).
        
        # Map Schemas Enum to Model Enum checks
        # models.PositionDirection[data['direction'].value]
        
        position = self.db.query(Position).filter(
            Position.user_id == user_id,
            Position.account_id == account_id,
            Position.symbol == symbol,
            Position.status == "OPEN"
        ).first()
        
        # If no open position, and it's an ENTRY, create new Position
        if not position:
            if batch_type == BatchTypeEnum.ENTRY:
                # Create Position
                # Detect asset type logic could be here, or default to generic
                position = Position(
                    user_id=user_id,
                    account_id=account_id,
                    symbol=symbol,
                    exchange="Imported", # Default
                    asset_type=data.get('asset_type') or "EQUITY", # Use imported type or default
                    direction=direction,
                    strategy_id=data.get('strategy_id'), # Link Strategy
                    status="OPEN",
                    total_quantity=0, # Will be updated by batch
                    average_entry_price=0,
                    opened_at=data['entry_time'],
                    entry_emotion=data.get('emotion'), # Store initial emotion
                    entry_confidence=data.get('confidence'), # Store initial confidence
                    planned_entry_price=data.get('planned_entry_price'),
                    planned_stop_loss=data.get('planned_stop_loss')
                )
                self.db.add(position)
                self.db.flush()
            else:
                # EXIT on no position? 
                # Option A: Create a dummy closed position? 
                # Option B: Skip/Error?
                # For import, we might be importing a full history.
                # If we see a CLOSE without OPEN, it might be data gap.
                # Let's Skip for now to be safe, or error.
                print(f"Skipping orphan exit for {symbol}")
                return

        # 2. Add Batch
        # Calculate PnL if Exit
        pnl = None
        if batch_type == BatchTypeEnum.EXIT:
             if position.average_entry_price and position.total_quantity > 0:
                 entry_price = float(position.average_entry_price)
                 exit_price = float(data['price'])
                 qty = float(data['quantity'])
                 
                 if direction == PositionDirectionEnum.LONG:
                     pnl = (exit_price - entry_price) * qty
                 else:
                     pnl = (entry_price - exit_price) * qty

        batch = TradeBatch(
            position_id=position.id,
            type=batch_type,
            price=data['price'],
            quantity=data['quantity'],
            time=data['entry_time'],
            reason=data.get('reason'),
            emotion=data.get('emotion'),
            confidence=data.get('confidence'),
            pnl=pnl
        )
        self.db.add(batch)
        self.db.flush()
        
        # 3. Update Position Aggregates (Recalculate)
        # We use strict chronological recalculation logic
        # But we need to make sure we don't break logic if we insert a batch in the past.
        # Since we sorted by time, we are hopefully appending mostly. 
        # But importing history might insert into a currently open position's past.
        # Ideally, we should call the router's recalculate_position logic.
        
        from routers.positions import recalculate_position
        recalculate_position(position, self.db)
        
        self.db.commit()
