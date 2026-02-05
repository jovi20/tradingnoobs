import sqlite3
import os

def add_columns():
    # Target the backend database specifically
    db_path = os.path.join(os.path.dirname(__file__), "tradingnoobs.db")
    print(f"Connecting to database at: {db_path}")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    columns_to_add = [
        ("total_assets", "DECIMAL(20, 2) DEFAULT 0"),
        ("total_liabilities", "DECIMAL(20, 2) DEFAULT 0")
    ]
    
    for col_name, col_type in columns_to_add:
        try:
            print(f"Adding column '{col_name}'...")
            cursor.execute(f"ALTER TABLE trading_accounts ADD COLUMN {col_name} {col_type}")
            print(f"Column '{col_name}' added successfully.")
        except sqlite3.OperationalError as e:
            if "duplicate column" in str(e):
                print(f"Column '{col_name}' already exists.")
            else:
                print(f"Error adding column '{col_name}': {e}")
    
    conn.commit()
    conn.close()
    print("Migration completed.")

if __name__ == "__main__":
    add_columns()
