import sqlite3
from database import engine
from models import Base
from sqlalchemy import text

def migrate():
    print("Starting migration...")
    
    # 1. Create new tables (SystemSetting)
    print("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    
    # 2. Add role column to users table if not exists
    print("Checking users table schema...")
    with engine.connect() as conn:
        try:
            # Check if column exists
            result = conn.execute(text("PRAGMA table_info(users)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'role' not in columns:
                print("Adding role column to users table...")
                conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR DEFAULT 'user'"))
                conn.commit()
                print("Role column added.")
                
                # Update existing users to have 'user' role (default handles it, but good to be explicit if needed)
                # SQLite ADD COLUMN with DEFAULT handles it for existing rows usually.
                
                # Promote first user to admin for testing
                print("Promoting first user to admin...")
                conn.execute(text("UPDATE users SET role = 'admin' WHERE id = (SELECT min(id) FROM users)"))
                conn.commit()
            else:
                print("Role column already exists.")
                
        except Exception as e:
            print(f"Error during users migration: {e}")

    # 3. Add account_id to trades table
    print("Checking trades table schema...")
    with engine.connect() as conn:
        try:
            result = conn.execute(text("PRAGMA table_info(trades)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'account_id' not in columns:
                print("Adding account_id column to trades table...")
                conn.execute(text("ALTER TABLE trades ADD COLUMN account_id INTEGER REFERENCES trading_accounts(id)"))
                conn.commit()
                print("account_id column added.")
            
            if 'pnl' not in columns:
                print("Adding pnl columns to trades table...")
                conn.execute(text("ALTER TABLE trades ADD COLUMN pnl NUMERIC(20, 8)"))
                conn.execute(text("ALTER TABLE trades ADD COLUMN pnl_percent NUMERIC(10, 4)"))
                conn.commit()
                print("pnl columns added.")
                
                # Backfill P&L for existing trades
                print("Backfilling P&L for historical trades...")
                conn.execute(text("""
                    UPDATE trades 
                    SET pnl = (COALESCE(exit_price, current_price) - entry_price) * quantity,
                        pnl_percent = CASE 
                            WHEN entry_price > 0 THEN ((COALESCE(exit_price, current_price) - entry_price) / entry_price) * 100 
                            ELSE 0 
                        END
                    WHERE entry_price IS NOT NULL AND quantity IS NOT NULL
                """))
                conn.commit()
                print("P&L backfilled.")
            else:
                print("PnL columns already exist.")
                
        except Exception as e:
            print(f"Error during trades migration: {e}")

    # 4. Migrate existing trades to positions + batches
    print("Checking for trades to migrate to positions...")
    with engine.connect() as conn:
        try:
            # Check if positions table exists and has any data
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='positions'"))
            positions_exists = result.fetchone() is not None
            
            if positions_exists:
                # Check if migration already done
                result = conn.execute(text("SELECT COUNT(*) FROM positions"))
                position_count = result.fetchone()[0]
                
                result = conn.execute(text("SELECT COUNT(*) FROM trades"))
                trade_count = result.fetchone()[0]
                
                if position_count == 0 and trade_count > 0:
                    print(f"Migrating {trade_count} trades to positions...")
                    
                    # Fetch all trades
                    trades = conn.execute(text("""
                        SELECT id, user_id, account_id, strategy_id, symbol, exchange,
                               entry_price, quantity, entry_time, exit_price, exit_time, status,
                               entry_reason, entry_emotion, entry_confidence,
                               exit_reason, exit_emotion, trade_review, screenshots, lessons, rating
                        FROM trades
                    """)).fetchall()
                    
                    for trade in trades:
                        trade_id, user_id, account_id, strategy_id, symbol, exchange, \
                        entry_price, quantity, entry_time, exit_price, exit_time, status, \
                        entry_reason, entry_emotion, entry_confidence, \
                        exit_reason, exit_emotion, trade_review, screenshots, lessons, rating = trade
                        
                        # Determine direction (default to LONG for existing trades)
                        direction = 'LONG'
                        
                        # Determine closed_at
                        closed_at = exit_time if status == 'CLOSED' else None
                        
                        # Calculate realized PnL if closed
                        realized_pnl = 0
                        if status == 'CLOSED' and exit_price and entry_price:
                            realized_pnl = (float(exit_price) - float(entry_price)) * float(quantity)
                        
                        # Total quantity (0 if closed, original if open)
                        total_qty = 0 if status == 'CLOSED' else quantity
                        
                        # Insert position
                        conn.execute(text("""
                            INSERT INTO positions (
                                user_id, account_id, strategy_id, symbol, exchange, direction, status,
                                total_quantity, average_entry_price, realized_pnl,
                                opened_at, closed_at, trade_review, screenshots, lessons, rating
                            ) VALUES (
                                :user_id, :account_id, :strategy_id, :symbol, :exchange, :direction, :status,
                                :total_qty, :entry_price, :realized_pnl,
                                :opened_at, :closed_at, :trade_review, :screenshots, :lessons, :rating
                            )
                        """), {
                            'user_id': user_id,
                            'account_id': account_id,
                            'strategy_id': strategy_id,
                            'symbol': symbol,
                            'exchange': exchange,
                            'direction': direction,
                            'status': status,
                            'total_qty': total_qty,
                            'entry_price': entry_price,
                            'realized_pnl': realized_pnl,
                            'opened_at': entry_time,
                            'closed_at': closed_at,
                            'trade_review': trade_review,
                            'screenshots': screenshots,
                            'lessons': lessons,
                            'rating': rating
                        })
                        
                        # Get the newly inserted position ID
                        result = conn.execute(text("SELECT last_insert_rowid()"))
                        position_id = result.fetchone()[0]
                        
                        # Insert entry batch
                        conn.execute(text("""
                            INSERT INTO trade_batches (
                                position_id, type, price, quantity, time, reason, emotion, confidence
                            ) VALUES (
                                :position_id, 'ENTRY', :price, :quantity, :time, :reason, :emotion, :confidence
                            )
                        """), {
                            'position_id': position_id,
                            'price': entry_price,
                            'quantity': quantity,
                            'time': entry_time,
                            'reason': entry_reason,
                            'emotion': entry_emotion,
                            'confidence': entry_confidence
                        })
                        
                        # If trade was closed, insert exit batch
                        if status == 'CLOSED' and exit_price:
                            batch_pnl = (float(exit_price) - float(entry_price)) * float(quantity)
                            conn.execute(text("""
                                INSERT INTO trade_batches (
                                    position_id, type, price, quantity, time, reason, emotion, pnl
                                ) VALUES (
                                    :position_id, 'EXIT', :price, :quantity, :time, :reason, :emotion, :pnl
                                )
                            """), {
                                'position_id': position_id,
                                'price': exit_price,
                                'quantity': quantity,
                                'time': exit_time or entry_time,
                                'reason': exit_reason,
                                'emotion': exit_emotion,
                                'pnl': batch_pnl
                            })
                    
                    conn.commit()
                    print(f"Migration complete. {trade_count} trades converted to positions.")
                elif position_count > 0:
                    print(f"Positions table already has {position_count} records. Skipping migration.")
                else:
                    print("No trades to migrate.")
            else:
                print("Positions table not yet created. Run migration again after table creation.")
                
        except Exception as e:
            print(f"Error during positions migration: {e}")
            import traceback
            traceback.print_exc()
            
            traceback.print_exc()

    # 5. Add up_color to user_settings
    print("Checking user_settings schema...")
    with engine.connect() as conn:
        try:
            # Check if table exists first
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name='user_settings'"))
            if result.fetchone():
                result = conn.execute(text("PRAGMA table_info(user_settings)"))
                columns = [row[1] for row in result.fetchall()]
                
                if 'up_color' not in columns:
                    print("Adding up_color column to user_settings...")
                    conn.execute(text("ALTER TABLE user_settings ADD COLUMN up_color VARCHAR(20) DEFAULT 'GREEN'"))
                    conn.commit()
                    print("up_color column added.")
            else:
                print("user_settings table does not exist (will be created by metadata.create_all).")
                
        except Exception as e:
            print(f"Error during user_settings migration: {e}")

    # 7. Add asset_metadata_symbol to positions & Create asset_metadata table
    print("Checking asset_metadata migration...")
    with engine.connect() as conn:
        try:
            # 1. Create table (Base.metadata.create_all handles this)
            Base.metadata.create_all(bind=engine)
            
            # 2. Add column to positions
            result = conn.execute(text("PRAGMA table_info(positions)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'asset_metadata_symbol' not in columns:
                print("Adding asset_metadata_symbol column to positions...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN asset_metadata_symbol VARCHAR(50) REFERENCES asset_metadata(symbol)"))
                
                # Backfill: For each unique symbol in positions, create a basic entry in asset_metadata and link it
                print("Backfilling asset_metadata link...")
                positions = conn.execute(text("SELECT DISTINCT symbol FROM positions")).fetchall()
                for (sym,) in positions:
                    # Create basic metadata if it doesn't exist
                    conn.execute(text("""
                        INSERT OR IGNORE INTO asset_metadata (symbol, name, created_at)
                        VALUES (:sym, :sym, CURRENT_TIMESTAMP)
                    """), {"sym": sym.upper()})
                    
                    # Update position to point to metadata
                    conn.execute(text("UPDATE positions SET asset_metadata_symbol = :sym_upper WHERE symbol = :sym"), 
                                 {"sym_upper": sym.upper(), "sym": sym})
                
                conn.commit()
                print("asset_metadata migration complete.")
            else:
                print("asset_metadata_symbol column already exists.")
                
        except Exception as e:
            print(f"Error during asset_metadata migration: {e}")
            
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
