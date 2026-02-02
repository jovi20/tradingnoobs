from sqlalchemy.orm import Session
from database import SessionLocal, engine
from models import User
from services.auth_service import get_password_hash

def fix_admin():
    db = SessionLocal()
    try:
        email = "admin@tradingnoobs.com"
        password = "admin123456"  # Setting user requested password
        
        user = db.query(User).filter(User.email == email).first()
        
        if user:
            print(f"User {email} found. Updating password and role...")
            user.hashed_password = get_password_hash(password)
            user.role = "admin"
            user.is_active = True
            print("Updated successfully.")
        else:
            print(f"User {email} not found. Creating new admin user...")
            user = User(
                email=email,
                hashed_password=get_password_hash(password),
                role="admin",
                is_active=True
            )
            db.add(user)
            print("Created successfully.")
            
        db.commit()
        print(f"Admin account ready.\nEmail: {email}\nPassword: {password}")
        
    except Exception as e:
        print(f"Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin()
