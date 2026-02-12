import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import os
from sqlalchemy import text, inspect
from database import engine
from models import Base, BatchType, PositionStatus

def migrate():
    print(f"Starting migration on database: {engine.url.drivername}")
    inspector = inspect(engine)
    
    # 1. Create new tables
    print("Creating new tables...")
    Base.metadata.create_all(bind=engine)
    
    # helper to check if column exists
    def column_exists(table_name, column_name):
        columns = [c['name'] for c in inspector.get_columns(table_name)]
        return column_name in columns

    with engine.connect() as conn:
        # 2. Add role column to users
        if not column_exists('users', 'role'):
            print("Adding role column to users...")
            conn.execute(text("ALTER TABLE users ADD COLUMN role VARCHAR(50) DEFAULT 'user'"))
            conn.commit()
            # Promote first user
            conn.execute(text("UPDATE users SET role = 'admin' WHERE id = (SELECT min(id) FROM users)"))
            conn.commit()

        # 3. Add account_id and pnl columns to trades
        if not column_exists('trades', 'account_id'):
            print("Adding account_id to trades...")
            conn.execute(text("ALTER TABLE trades ADD COLUMN account_id INTEGER"))
            conn.commit()

        if not column_exists('trades', 'pnl'):
            print("Adding pnl columns to trades...")
            conn.execute(text("ALTER TABLE trades ADD COLUMN pnl NUMERIC(20, 8)"))
            conn.execute(text("ALTER TABLE trades ADD COLUMN pnl_percent NUMERIC(10, 4)"))
            conn.commit()

        # 4. Add up_color to user_settings
        if inspector.has_table('user_settings'):
            if not column_exists('user_settings', 'up_color'):
                print("Adding up_color to user_settings...")
                conn.execute(text("ALTER TABLE user_settings ADD COLUMN up_color VARCHAR(20) DEFAULT 'GREEN'"))
                conn.commit()

        # 5. Add asset_type and metadata link to positions
        if inspector.has_table('positions'):
            if not column_exists('positions', 'asset_type'):
                print("Adding asset_type column to positions...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN asset_type VARCHAR(20)"))
                conn.commit()
            
            if not column_exists('positions', 'asset_metadata_symbol'):
                print("Adding asset_metadata_symbol column to positions...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN asset_metadata_symbol VARCHAR(50)"))
                conn.commit()
            
            # 5b. Populate asset_metadata_symbol for existing positions
            print("Linking existing positions to asset_metadata...")
            # Get all positions without asset_metadata_symbol
            unlinked = conn.execute(text(
                "SELECT DISTINCT UPPER(symbol) as symbol FROM positions WHERE asset_metadata_symbol IS NULL"
            )).fetchall()
            
            for row in unlinked:
                sym = row[0]
                # Check if AssetMetadata exists
                exists = conn.execute(text(
                    "SELECT 1 FROM asset_metadata WHERE symbol = :sym"
                ), {'sym': sym}).fetchone()
                
                if not exists:
                    # Create basic metadata
                    conn.execute(text(
                        "INSERT INTO asset_metadata (symbol, name) VALUES (:sym, :sym)"
                    ), {'sym': sym})
                
                # Link positions to metadata
                conn.execute(text(
                    "UPDATE positions SET asset_metadata_symbol = UPPER(symbol) WHERE UPPER(symbol) = :sym"
                ), {'sym': sym})
            
            conn.commit()
            print(f"Linked {len(unlinked)} unique symbols to asset_metadata.")

        # 6. Add current_balance to trading_accounts
        if inspector.has_table('trading_accounts'):
            if not column_exists('trading_accounts', 'current_balance'):
                print("Adding current_balance to trading_accounts...")
                conn.execute(text("ALTER TABLE trading_accounts ADD COLUMN current_balance NUMERIC(20, 2) DEFAULT 0"))
                conn.commit()
            
            if not column_exists('trading_accounts', 'account_type'):
                print("Adding account_type to trading_accounts...")
                conn.execute(text("ALTER TABLE trading_accounts ADD COLUMN account_type VARCHAR(50)"))
                conn.commit()

        # 7. Add account_id to positions
        if inspector.has_table('positions'):
            if not column_exists('positions', 'account_id'):
                print("Adding account_id to positions...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN account_id INTEGER REFERENCES trading_accounts(id)"))
                conn.commit()

        # 7.5 Add pnl to trade_batches
        if inspector.has_table('trade_batches'):
            if not column_exists('trade_batches', 'pnl'):
                print("Adding pnl column to trade_batches...")
                conn.execute(text("ALTER TABLE trade_batches ADD COLUMN pnl NUMERIC(20, 8)"))
                conn.commit()

        # 8. Migrate Trades to Positions if empty
        print("Checking for trades to migrate to positions...")
        res = conn.execute(text("SELECT COUNT(*) FROM positions"))
        pos_count = res.fetchone()[0]
        
        res = conn.execute(text("SELECT COUNT(*) FROM trades"))
        trade_count = res.fetchone()[0]

        if pos_count == 0 and trade_count > 0:
            print(f"Migrating {trade_count} trades to positions...")
            trades = conn.execute(text("SELECT * FROM trades")).fetchall()
            
            # Identify columns for dynamic mapping
            trade_cols = [c['name'] for c in inspector.get_columns('trades')]
            
            for t_row in trades:
                t = dict(zip(trade_cols, t_row))
                
                # Basic position data
                status = t.get('status', 'OPEN')
                direction = 'LONG' # Default for old trades
                
                # INSERT Position
                p_id = conn.execute(text("""
                    INSERT INTO positions (
                        user_id, account_id, strategy_id, symbol, exchange, direction, status,
                        total_quantity, average_entry_price, realized_pnl, asset_type,
                        opened_at, closed_at, trade_review, screenshots, lessons, rating
                    ) VALUES (
                        :user_id, :account_id, :strategy_id, :symbol, :exchange, :direction, :status,
                        :total_quantity, :average_entry_price, :realized_pnl, NULL,
                        :opened_at, :closed_at, :trade_review, :screenshots, :lessons, :rating
                    ) RETURNING id
                """), {
                    'user_id': t['user_id'],
                    'account_id': t.get('account_id'),
                    'strategy_id': t.get('strategy_id'),
                    'symbol': t['symbol'],
                    'exchange': t['exchange'],
                    'direction': direction,
                    'status': status,
                    'total_quantity': 0 if status == 'CLOSED' else t['quantity'],
                    'average_entry_price': t['entry_price'],
                    'realized_pnl': t.get('pnl', 0) if status == 'CLOSED' else 0,
                    'opened_at': t['entry_time'],
                    'closed_at': t.get('exit_time') if status == 'CLOSED' else None,
                    'trade_review': t.get('trade_review'),
                    'screenshots': t.get('screenshots', '[]'),
                    'lessons': t.get('lessons', '[]'),
                    'rating': t.get('rating')
                }).fetchone()[0]

                # INSERT Entry Batch
                conn.execute(text("""
                    INSERT INTO trade_batches (position_id, type, price, quantity, time, reason, emotion, confidence)
                    VALUES (:p_id, 'ENTRY', :price, :qty, :time, :reason, :emotion, :conf)
                """), {
                    'p_id': p_id,
                    'price': t['entry_price'],
                    'qty': t['quantity'],
                    'time': t['entry_time'],
                    'reason': t.get('entry_reason'),
                    'emotion': t.get('entry_emotion'),
                    'conf': t.get('entry_confidence')
                })

                # INSERT Exit Batch if closed
                if status == 'CLOSED' and t.get('exit_price'):
                    conn.execute(text("""
                        INSERT INTO trade_batches (position_id, type, price, quantity, time, reason, emotion, pnl)
                        VALUES (:p_id, 'EXIT', :price, :qty, :time, :reason, :emotion, :pnl)
                    """), {
                        'p_id': p_id,
                        'price': t['exit_price'],
                        'qty': t['quantity'],
                        'time': t.get('exit_time', t['entry_time']),
                        'reason': t.get('exit_reason'),
                        'emotion': t.get('exit_emotion'),
                        'pnl': t.get('pnl', 0)
                    })
            
            conn.commit()
            print("Trade migration complete.")

        # === Phase 1: Pre-Trade Checklist & Plan Drift Detection ===
        
        # Add checklist_items to strategies
        if inspector.has_table('strategies'):
            if not column_exists('strategies', 'checklist_items'):
                print("Adding checklist_items to strategies...")
                conn.execute(text("ALTER TABLE strategies ADD COLUMN checklist_items JSON DEFAULT '[]'"))
                conn.commit()
        
        # Add checklist and plan drift fields to positions
        if inspector.has_table('positions'):
            if not column_exists('positions', 'checklist_responses'):
                print("Adding checklist_responses to positions...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN checklist_responses JSON"))
                conn.commit()
            
            if not column_exists('positions', 'checklist_completed_at'):
                print("Adding checklist_completed_at to positions...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN checklist_completed_at TIMESTAMP"))
                conn.commit()
            
            if not column_exists('positions', 'planned_entry_price'):
                print("Adding planned_entry_price to positions...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN planned_entry_price NUMERIC(20, 8)"))
                conn.commit()
            
            if not column_exists('positions', 'planned_stop_loss'):
                print("Adding planned_stop_loss to positions...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN planned_stop_loss NUMERIC(20, 8)"))
                conn.commit()
            
            if not column_exists('positions', 'planned_take_profit'):
                print("Adding planned_take_profit to positions...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN planned_take_profit JSON"))
                conn.commit()
        
        print("Phase 1 migration complete.")

        # === Phase 2: MAE/MFE Analysis ===
        if inspector.has_table('positions'):
            if not column_exists('positions', 'max_price_during_hold'):
                print("Adding max_price_during_hold to positions...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN max_price_during_hold NUMERIC(20, 8)"))
                conn.commit()
            
            if not column_exists('positions', 'min_price_during_hold'):
                print("Adding min_price_during_hold to positions...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN min_price_during_hold NUMERIC(20, 8)"))
                conn.commit()

        # === Phase 3: Assets & Liabilities ===
        if inspector.has_table('trading_accounts'):
            if not column_exists('trading_accounts', 'total_assets'):
                print("Adding total_assets to trading_accounts...")
                conn.execute(text("ALTER TABLE trading_accounts ADD COLUMN total_assets NUMERIC(20, 2) DEFAULT 0"))
                conn.commit()
            
            if not column_exists('trading_accounts', 'total_liabilities'):
                print("Adding total_liabilities to trading_accounts...")
                conn.execute(text("ALTER TABLE trading_accounts ADD COLUMN total_liabilities NUMERIC(20, 2) DEFAULT 0"))
                conn.commit()

        # === Display Currency Setting ===
        if inspector.has_table('user_settings'):
            if not column_exists('user_settings', 'display_currency'):
                print("Adding display_currency to user_settings...")
                conn.execute(text("ALTER TABLE user_settings ADD COLUMN display_currency VARCHAR(10) DEFAULT 'USD'"))
                conn.commit()

    print("Migration completed.")

if __name__ == "__main__":
    migrate()
