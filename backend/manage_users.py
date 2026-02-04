"""
User Management Script for Trading Noobs
Usage: python manage_users.py promote-admin <email>
"""
import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User

def promote_admin(email: str):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email).first()
        if not user:
            print(f"Error: User with email {email} not found.")
            return
        
        user.role = "admin"
        db.commit()
        print(f"Success: User {email} has been promoted to administrator.")
    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python manage_users.py promote-admin <email>")
        sys.exit(1)
    
    command = sys.argv[1]
    target_email = sys.argv[2]
    
    if command == "promote-admin":
        promote_admin(target_email)
    else:
        print(f"Unknown command: {command}")
