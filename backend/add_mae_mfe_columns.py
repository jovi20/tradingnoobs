
from database import engine, Base
from sqlalchemy import text

def migrate():
    with engine.connect() as conn:
        trans = conn.begin()
        try:
            # Check if columns exist
            result = conn.execute(text("PRAGMA table_info(positions)"))
            columns = [row[1] for row in result.fetchall()]
            
            if 'max_price_during_hold' not in columns:
                print("Adding column max_price_during_hold...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN max_price_during_hold NUMERIC(20, 8)"))
            else:
                print("Column max_price_during_hold already exists.")
                
            if 'min_price_during_hold' not in columns:
                print("Adding column min_price_during_hold...")
                conn.execute(text("ALTER TABLE positions ADD COLUMN min_price_during_hold NUMERIC(20, 8)"))
            else:
                print("Column min_price_during_hold already exists.")
                
            trans.commit()
            print("Migration successful!")
        except Exception as e:
            trans.rollback()
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
