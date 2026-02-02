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
            
    print("Migration completed.")

if __name__ == "__main__":
    migrate()
