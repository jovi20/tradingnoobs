"""
Create admin user for Trading Noobs
Run: python create_admin.py
"""
import sys
import os

# Suppress warnings
os.environ['PASSLIB_BUILTIN_BCRYPT'] = 'enabled'
import warnings
warnings.filterwarnings('ignore')

sys.path.insert(0, '.')

from database import SessionLocal, engine, Base
from models import User, UserSettings

# Use bcrypt directly to avoid passlib compatibility issues
import bcrypt

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

# Create tables if not exist
Base.metadata.create_all(bind=engine)

def create_admin():
    db = SessionLocal()
    try:
        # Delete existing admin if exists (to fix password hash)
        admin = db.query(User).filter(User.email == "admin@tradingnoobs.com").first()
        if admin:
            # Delete associated settings first
            db.query(UserSettings).filter(UserSettings.user_id == admin.id).delete()
            db.delete(admin)
            db.commit()
            print("Deleted existing admin user to recreate with correct password hash")
        
        # Create admin user with passlib-compatible hash
        admin = User(
            email="admin@tradingnoobs.com",
            hashed_password=get_password_hash("admin123"),
            is_active=True,
            role="admin"
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        
        # Create default settings
        settings = UserSettings(user_id=admin.id)
        db.add(settings)
        db.commit()
        
        print("=" * 40)
        print("Admin user created successfully!")
        print("=" * 40)
        print(f"  Email:    admin@tradingnoobs.com")
        print(f"  Password: admin123")
        print("=" * 40)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    create_admin()
