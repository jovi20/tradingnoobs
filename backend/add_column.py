import sqlite3

def add_column():
    import os
    # Try both locations to be safe or target the specific one
    # But let's look for backend/tradingnoobs.db specifically based on findings
    db_path = os.path.join(os.path.dirname(__file__), "tradingnoobs.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    try:
        cursor.execute("PRAGMA table_info(trading_accounts)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if 'current_balance' not in columns:
            print("Adding current_balance column to trading_accounts...")
            cursor.execute("ALTER TABLE trading_accounts ADD COLUMN current_balance DECIMAL(20, 2) DEFAULT 0")
            conn.commit()
            print("Migration successful!")
        else:
            print("Column current_balance already exists.")
            
    except Exception as e:
        print(f"Migration failed: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    add_column()
