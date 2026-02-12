"""
User Management Script for Trading Noobs
Usage: 
  python manage_users.py promote-admin <email>
  python manage_users.py reset-password <email> <new_password>
"""
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
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


def list_users():
    db: Session = SessionLocal()
    try:
        users = db.query(User).all()
        print(f"{'ID':<5} {'Email':<30} {'Role':<10} {'Active':<10}")
        print("-" * 60)
        for user in users:
            print(f"{user.id:<5} {user.email:<30} {user.role or 'user':<10} {str(user.is_active):<10}")
        print("-" * 60)
        print(f"Total: {len(users)}")
    finally:
        db.close()

def create_user(email: str, password: str, role: str = "user"):
    db: Session = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email.lower().strip()).first()
        if existing:
            print(f"Error: User {email} already exists.")
            return

        user = User(
            email=email.lower().strip(),
            hashed_password=get_password_hash(password),
            role=role,
            is_active=True
        )
        db.add(user)
        db.commit()
        print(f"Success: User {email} created with role '{role}'.")
    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

def toggle_active(email: str):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email == email.lower().strip()).first()
        if not user:
            print(f"Error: User {email} not found.")
            return
        
        user.is_active = not user.is_active
        db.commit()
        status = "Active" if user.is_active else "Inactive"
        print(f"Success: User {email} is now {status}.")
    except Exception as e:
        print(f"Error: {str(e)}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python manage_users.py list-users")
        print("  python manage_users.py create-user <email> <password> [role]")
        print("  python manage_users.py promote-admin <email>")
        print("  python manage_users.py reset-password <email> <new_password>")
        print("  python manage_users.py toggle-active <email>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list-users":
        list_users()
    elif command == "create-user":
        if len(sys.argv) < 4:
            print("Error: Missing arguments. Usage: create-user <email> <password> [role]")
            sys.exit(1)
        role = sys.argv[4] if len(sys.argv) > 4 else "user"
        create_user(sys.argv[2], sys.argv[3], role)
    elif command == "promote-admin":
        if len(sys.argv) < 3:
            print("Error: Missing email.")
            sys.exit(1)
        promote_admin(sys.argv[2])
    elif command == "reset-password":
        if len(sys.argv) < 4:
            print("Error: Missing arguments. Usage: reset-password <email> <new_password>")
            sys.exit(1)
        reset_password(sys.argv[2], sys.argv[3])
    elif command == "toggle-active":
        if len(sys.argv) < 3:
            print("Error: Missing email.")
            sys.exit(1)
        toggle_active(sys.argv[2])
    else:
        print(f"Unknown command: {command}")

