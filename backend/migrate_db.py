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
            else:
                print("account_id column already exists.")
                
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
            
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
