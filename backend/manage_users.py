"""
User Management Script for Trading Noobs
Usage: 
  python manage_users.py promote-admin <email>
  python manage_users.py reset-password <email> <new_password>
"""
import sys
from sqlalchemy.orm import Session
from database import SessionLocal
from models import User
from services.auth_service import get_password_hash

def promote_admin(email: str):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower().strip()).first()
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

def reset_password(email: str, new_password: str):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if not user:
            print(f"Error: User with email {email} not found.")
            return
        
        user.hashed_password = get_password_hash(new_password)
        db.commit()
        print(f"Success: Password for {email} has been updated.")
    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python manage_users.py promote-admin <email>")
        print("  python manage_users.py reset-password <email> <new_password>")
        sys.exit(1)
    
    command = sys.argv[1]
    target_email = sys.argv[2]
    
    if command == "promote-admin":
        promote_admin(target_email)
    elif command == "reset-password":
        if len(sys.argv) < 4:
            print("Error: Please provide the new password.")
            sys.exit(1)
        reset_password(target_email, sys.argv[3])
    else:
        print(f"Unknown command: {command}")
