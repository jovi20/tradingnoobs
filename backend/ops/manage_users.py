"""
User Management Script for Trading Noobs
Usage: 
  python manage_users.py promote-admin <email>
  python manage_users.py reset-password <email> <new_password>
"""
import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sqlalchemy.orm import Session

from database import SessionLocal
from models import AuthToken, User, UserCredential, UserSession
from services.auth_service import get_password_hash, normalize_email, utc_now

def promote_admin(email: str):
    db: Session = SessionLocal()
    try:
        user = db.query(User).filter(User.email_normalized == normalize_email(email)).first()
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
        user = db.query(User).filter(User.email_normalized == normalize_email(email)).first()
        if not user:
            print(f"Error: User with email {email} not found.")
            return

        password_hash = get_password_hash(new_password)
        now = utc_now()
        user.hashed_password = password_hash
        credential = db.query(UserCredential).filter(UserCredential.user_id == user.id).first()
        if credential is None:
            credential = UserCredential(user_id=user.id, password_hash=password_hash, password_updated_at=now)
        else:
            credential.password_hash = password_hash
            credential.password_updated_at = now
        db.add(credential)

        active_sessions = db.query(UserSession).filter(
            UserSession.user_id == user.id,
            UserSession.status == "ACTIVE",
            UserSession.revoked_at.is_(None),
        ).all()
        for session in active_sessions:
            session.status = "REVOKED"
            session.revoked_at = now
            session.last_seen_at = now

        active_tokens = db.query(AuthToken).filter(
            AuthToken.user_id == user.id,
            AuthToken.revoked_at.is_(None),
        ).all()
        for auth_token in active_tokens:
            auth_token.revoked_at = now

        db.commit()
        print(
            f"Success: Password for {email} has been updated and "
            f"{len(active_sessions)} active session(s) revoked."
        )
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
        normalized = normalize_email(email)
        existing = db.query(User).filter(User.email_normalized == normalized).first()
        if existing:
            print(f"Error: User {email} already exists.")
            return

        user = User(
            email=email.lower().strip(),
            email_normalized=normalized,
            hashed_password=get_password_hash(password),
            status="ACTIVE",
            role=role,
            is_active=True
        )
        db.add(user)
        db.flush()
        db.add(UserCredential(user_id=user.id, password_hash=user.hashed_password, password_updated_at=utc_now()))
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
        user = db.query(User).filter(User.email_normalized == normalize_email(email)).first()
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
