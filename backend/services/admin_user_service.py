import secrets
import string

from sqlalchemy.orm import Session

from models import AuthToken, User, UserCredential, UserSession
from services.auth_service import get_password_hash, utc_now


class AdminUserNotFound(Exception):
    pass


class AdminUserOperationBlocked(Exception):
    pass


def _find_user_by_public_id(db: Session, user_public_id: str) -> User:
    user = db.query(User).filter(User.public_id == user_public_id).first()
    if not user:
        raise AdminUserNotFound(user_public_id)
    return user


def _active_admin_count(db: Session) -> int:
    return (
        db.query(User)
        .filter(User.role == "admin", User.is_active == True)
        .count()
    )


def promote_user_to_admin(db: Session, user_public_id: str, actor_user: User) -> dict:
    user = _find_user_by_public_id(db, user_public_id)
    user.role = "admin"
    db.add(user)
    return {
        "status": "SUCCESS",
        "user_public_id": user.public_id,
        "role": user.role,
        "message": f"User {user.public_id} promoted to admin.",
    }


def update_user_role(db: Session, user_public_id: str, role: str, actor_user: User) -> dict:
    if role not in {"user", "admin"}:
        raise ValueError("Unsupported role")
    user = _find_user_by_public_id(db, user_public_id)
    if user.role == "admin" and user.is_active and role != "admin" and _active_admin_count(db) <= 1:
        raise AdminUserOperationBlocked("LAST_ACTIVE_ADMIN")
    user.role = role
    db.add(user)
    return {
        "status": "SUCCESS",
        "user_public_id": user.public_id,
        "role": user.role,
        "message": f"User {user.public_id} role updated to {role}.",
    }


def set_user_active_state(db: Session, user_public_id: str, is_active: bool, actor_user: User) -> dict:
    user = _find_user_by_public_id(db, user_public_id)
    if user.public_id == actor_user.public_id and not is_active:
        raise AdminUserOperationBlocked("CANNOT_DISABLE_SELF")
    if user.role == "admin" and user.is_active and not is_active and _active_admin_count(db) <= 1:
        raise AdminUserOperationBlocked("LAST_ACTIVE_ADMIN")
    user.is_active = is_active
    user.status = "ACTIVE" if is_active else "DISABLED"
    db.add(user)
    return {
        "status": "SUCCESS",
        "user_public_id": user.public_id,
        "role": user.role,
        "message": f"User {user.public_id} {'activated' if is_active else 'disabled'}.",
    }


def generate_temporary_password(length: int = 18) -> str:
    if length < 18:
        raise ValueError("Temporary password length must be at least 18")
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def reset_user_password(db: Session, user_public_id: str, actor_user: User) -> dict:
    user = _find_user_by_public_id(db, user_public_id)
    temporary_password = generate_temporary_password()
    password_hash = get_password_hash(temporary_password)
    now = utc_now()

    user.hashed_password = password_hash
    credential = db.query(UserCredential).filter(UserCredential.user_id == user.id).first()
    if credential:
        credential.password_hash = password_hash
        credential.password_updated_at = now
    else:
        credential = UserCredential(
            user_id=user.id,
            password_hash=password_hash,
            password_updated_at=now,
        )
    db.add(user)
    db.add(credential)

    active_sessions = (
        db.query(UserSession)
        .filter(
            UserSession.user_id == user.id,
            UserSession.status == "ACTIVE",
            UserSession.revoked_at.is_(None),
        )
        .all()
    )
    for session in active_sessions:
        session.status = "REVOKED"
        session.revoked_at = now
        session.last_seen_at = now
        db.add(session)

    active_tokens = (
        db.query(AuthToken)
        .filter(
            AuthToken.user_id == user.id,
            AuthToken.revoked_at.is_(None),
        )
        .all()
    )
    for auth_token in active_tokens:
        auth_token.revoked_at = now
        db.add(auth_token)

    return {
        "status": "SUCCESS",
        "user_public_id": user.public_id,
        "temporary_password": temporary_password,
        "active_sessions_revoked": True,
        "revoked_session_count": len(active_sessions),
        "revoked_token_count": len(active_tokens),
        "message": "Temporary password generated and only shown once. Active sessions were revoked.",
    }
